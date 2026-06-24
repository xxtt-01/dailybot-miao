import asyncio
import json
import sys
import textwrap
import traceback
from datetime import datetime

import uvicorn
from loguru import logger as log

import common.logger  # noqa: F401 (触发全局日志配置)
from common import config
from crawlers.modules.camouflage_history import camouflage_history_manager
from crawlers.modules.crawler_manager import crawler_manager
from exceptions import handle_logic_exception
from oauth import oauth_platform_manager
from request.core.http_request import HttpRequest
from rpa.modules.rpa_factory import RPAFactory
from token_storage import load_all_tokens
from workflows import WorkflowFactory


async def ensure_playwright_browsers():
    """
    检查并自动安装 Playwright 浏览器驱动 (Chromium)
    实现傻瓜式运行：如果检测到 RPA 开启但环境不就绪，自动下载驱动。
    """
    # 1. 快速检查：是否有任一平台启用了 RPA
    any_rpa_enabled = False
    for p_name in config.get_crawler_source_platforms():
        if config.get_platform(p_name).get("rpa", {}).get("enabled", False):
            any_rpa_enabled = True
            break

    if not any_rpa_enabled:
        return

    log.info("🧪 [系统] 正在准备自动化运行环境...")

    # 2. 调用 playwright CLI 安装 Chromium 浏览器驱动
    try:
        cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        log.info("⏳ [系统] 正在进行环境自检与驱动补全，请稍候...")
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            log.info("✅ [系统] 浏览器环境已就绪。")
        else:
            err_msg = stderr.decode()
            log.warning(
                f"⚠️ [系统] 环境初始化未完全成功 (Code: {process.returncode}): {err_msg}"
            )

    except Exception as e:
        log.error(f"❌ [系统] 尝试自动辅助安装浏览器驱动时出错: {e}")


async def trigger_rpa(platform_name: str, summary_json: str):
    """
    根据配置动态触发 RPA 流程
    """
    try:
        # 1. 检查配置是否启用
        platform_config = config.get_platform(platform_name)
        rpa_enabled = platform_config.get("rpa", {}).get("enabled", False)

        if not rpa_enabled:
            return

        log.info(f"🚀 [RPA] 检测到 {platform_name} 已启用自动化填报，正在准备执行...")

        # 2. 解析 AI 生成的结构化数据
        try:
            report_data = json.loads(summary_json)
        except Exception as e:
            log.error(f"❌ [RPA] AI 返回数据非合法 JSON，跳过 RPA 流程: {e}")
            return

        # 3. 获取 RPA 实例
        rpa_instance = RPAFactory.get_rpa(platform_name, config)
        if not rpa_instance:
            log.warning(f"⚠️ [RPA] 未发现 {platform_name} 的 RPA 驱动实现，已跳过。")
            return

        # 4. 执行 RPA 逻辑 (异步执行，不阻塞主流程日志)
        # 注意：此处直接 await，因为 process_summary 已经在 gather 中异步运行
        await rpa_instance.run(report_data)

    except Exception as e:
        log.error(f"❌ [RPA] {platform_name} 自动化执行发生异常: {e}")


async def run_reporting_logic():
    """全异步工作流：采集 -> AI 总结 -> 推送"""
    log.info("🎬 开始执行报告生成流程...")

    enabled_workflow_names = getattr(config, "ENABLED_WORKFLOWS")
    active_workflows = []

    # 初始化工作流
    for wf_name in enabled_workflow_names:
        wf = WorkflowFactory.get_workflow(wf_name)
        if wf and await wf.prepare():
            active_workflows.append(wf)

    if not active_workflows:
        log.warning("⚠️ 没有可用的工作流，中止任务。")
        return

    # 1. 异步数据采集与可能触发的伪装补充
    log.info("🚀 [采集] 开始数据采集...")
    try:
        raw_report, total_count, is_camouflage, fake_items_used = (
            await crawler_manager.collect_and_camouflage()
        )
    except Exception as e:
        log.error("❌ [采集] 数据采集失败（关键错误）: {}", e)
        return
    log.info("✅ [采集] 数据采集完成，共 {} 条", total_count)

    if not raw_report:
        log.warning("📭 今日没有任何可汇报的数据。")
        for wf in active_workflows:
            try:
                await wf.on_report_success("[]", {"raw_report": ""})
            except Exception as e:
                log.error(f"发送暂无记录通知失败: {e}")
            try:
                from datetime import datetime

                from common.database import db
                db.log_run(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    status="no_data",
                    platform=wf.WORKFLOW_NAME,
                )
            except Exception:
                pass
        return

    log.info(f"🐠 采集到以下原始报文内容 (共 {total_count} 条)：")
    log.info("\n" + "-" * 50 + "\n" + raw_report + "\n" + "-" * 50)

    # 2. 并行起始反馈（个别失败不阻塞其他工作流）
    wf_contexts = []
    start_tasks = [wf.on_report_start(raw_report) for wf in active_workflows]
    start_results = await asyncio.gather(*start_tasks, return_exceptions=True)
    for i, ctx in enumerate(start_results):
        if isinstance(ctx, Exception):
            log.error(
                f"工作流 {active_workflows[i].WORKFLOW_NAME} on_report_start 异常: {ctx}"
            )
            continue
        wf_contexts.append((active_workflows[i], ctx))

    # 3. 准备模型请求任务 (去重：同模型只请求一次)
    log.info("🚀 [AI] 准备发起 AI 总结请求...")
    model_tasks = {}

    async def get_model_summary(m_name: str):
        """确保同模型只发起一次请求，并共享结果"""
        if m_name in model_tasks:
            return await model_tasks[m_name]

        async def _do_request():
            log.info(f"🤖 [AI] 正在为模型供应商 {m_name} 生成统一总结内容...")
            # 寻找第一个使用该模型的工作流来执行具体的 AI 业务逻辑
            sample_wf = next(
                wf
                for wf in active_workflows
                if config.get_platform(wf.WORKFLOW_NAME).get("ai_model") == m_name
            )
            summary = await sample_wf.summarize(raw_report, is_camouflage=is_camouflage)

            # 💡 [精细化排版] 展示 AI 润色结果
            if summary:
                try:
                    res_list = json.loads(summary)
                    if isinstance(res_list, list) and res_list:
                        curr_date = datetime.now().strftime("%Y-%m-%d")
                        border = "-" * 80
                        header = f"  📊 [每日工作总结-AI润色] (日期: {curr_date})"
                        lines = ["", border, "", header]

                        for item in res_list:
                            content = item.get("content", "")
                            result = item.get("result", "无")
                            time_range = f"{item.get('start_time', '??:??')}~{item.get('end_time', '??:??')}"
                            priority = item.get("priority", "重要、不紧急")
                            job_type = item.get("type", "编码")
                            project = item.get("project", "其他")

                            # 动态颜色球逻辑
                            if "不重要、不紧急" in priority:
                                p_emoji = "🟢"
                            elif "重要" in priority:
                                p_emoji = "🔴"
                            else:
                                p_emoji = "🟡"

                            # 自动换行算法
                            wrapped_content = textwrap.fill(
                                content,
                                width=48,
                                initial_indent="    - ",
                                subsequent_indent="      ",
                            )

                            lines.append(wrapped_content)
                            lines.append(f"        └─ 成果: {result}")
                            lines.append(
                                f"        └─ 详情: 🕒 {time_range} | {p_emoji} {priority} | 🏷️ {job_type} | 🏢 {project}"
                            )
                            lines.append("")

                        lines.append(border)
                        log.info("\n".join(lines))
                except Exception as e:
                    log.debug(f"AI 润色结果预览渲染失败: {e}")

            return summary

        task = asyncio.create_task(_do_request())
        model_tasks[m_name] = task
        return await task

    # 4. 并行派发结果并执行 RPA 自动化 (非阻塞模式：谁先好谁先走)
    async def finalize_workflow_async(wf, ctx):
        nonlocal fake_items_used
        try:
            m_name = config.get_platform(wf.WORKFLOW_NAME).get("ai_model")
            if not m_name:
                log.error(f"❌ [工作流: {wf.WORKFLOW_NAME}] 配置错误：未定义 ai_model")
                return

            # 等待所属模型的总结结果 (如果其他工作流已经启动了该模型的请求，此处会共享等待)
            summary = await get_model_summary(m_name)
            if not summary:
                log.error(f"❌ 工作流 {wf.WORKFLOW_NAME} 未能获取到总结结果")
                return

            # 5. 总结成功后的后置动作
            # 如果本次运行使用了伪装素材且 AI 总结成功，更新历史记录以防下次重复
            if fake_items_used:
                # 找到当前模型对应的生成内容（若有多个模型且同一平台，情况复杂，此处默认取第一个）
                variant = summary
                log.info(
                    f"💾 [伪装] 总结成功，正在为 {len(fake_items_used)} 个素材更新记录..."
                )
                for item in fake_items_used:
                    # 传入完整的 item 以记录更多元信息
                    camouflage_history_manager.update_usage(item, variant)
                fake_items_used = []  # 确保只有首个归队的模型任务更新它一次

            # [非阻塞流转日志] 一旦某个模型好了，立即告知并触发后续
            log.info(
                f"✨ [AI总结完毕] 平台 {wf.WORKFLOW_NAME} 所需模型 {m_name} 已就绪，准备执行下一步动作..."
            )

            # 成功回调 (如发送通知)
            log.info(f"🚀 [推送] 正在推送到平台: {wf.WORKFLOW_NAME}")
            await wf.on_report_success(summary, ctx)
            log.info(f"✅ [推送] 平台 {wf.WORKFLOW_NAME} 通知已发送")

            # 记录到数据库
            try:
                from datetime import datetime

                from common.database import db
                db.save_report(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    platform=wf.WORKFLOW_NAME,
                    summary=summary,
                    raw_report=ctx.get("raw_report", "") if isinstance(ctx, dict) else "",
                    is_camouflage=bool(is_camouflage),
                )
                db.log_run(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    status="success",
                    platform=wf.WORKFLOW_NAME,
                )
                log.info(f"✅ [数据库] 平台 {wf.WORKFLOW_NAME} 运行记录已保存")
            except Exception as db_err:
                log.warning("⚠️ [数据库] 平台 {} 记录写入失败（非关键）: {}", wf.WORKFLOW_NAME, db_err)

            # 尝试触发 RPA 自动化
            await trigger_rpa(wf.WORKFLOW_NAME, summary)

        except Exception as e:
            log.error(f"工作流 {wf.WORKFLOW_NAME} 最终处置失败: {e}")
            await wf.on_report_failure(str(e), ctx)
            try:
                from datetime import datetime

                from common.database import db
                db.log_run(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    status="failed",
                    platform=wf.WORKFLOW_NAME,
                    message=str(e),
                )
            except Exception:
                pass

    # 💡 打印开启了 RPA 的平台状态提示
    for wf in active_workflows:
        platform_config = config.get_platform(wf.WORKFLOW_NAME)
        if platform_config.get("rpa", {}).get("enabled", False):
            log.info(
                f"⚡ [RPA检测] {wf.WORKFLOW_NAME} 已开启自动化填报，响应后将即刻启动..."
            )

    # 启动所有工作流的终结任务 (并发运行，互不干扰；个别失败不阻塞其他工作流)
    await asyncio.gather(
        *(finalize_workflow_async(wf, ctx) for wf, ctx in wf_contexts),
        return_exceptions=True,
    )
    log.info("✅ [核心] 报告生成流程执行完毕")


@handle_logic_exception
async def main(strict: bool = False):
    log.info("🚀 [启动] DailyBot 启动，strict={}", strict)

    # 0. 环境自检：如果启用了 RPA，确保浏览器驱动已安装 (傻瓜式运行)
    await ensure_playwright_browsers()

    # 0.5 配置校验
    log.info("🚀 [配置] 开始校验配置...")
    from common.validator import print_validation_errors, validate_config
    validation_errors = validate_config(config)
    print_validation_errors(validation_errors)
    log.info("✅ [配置] 校验完成，发现 {} 个配置问题", len(validation_errors))
    if strict and validation_errors:
        log.error("❌ [配置] 严格模式下配置校验未通过，退出程序")
        return

    # 1. 判断是否需要启动 WebServer (OAuth 授权或未来可能的 WebSocket/Webhook 需要)
    enabled_workflow_names = getattr(config, "ENABLED_WORKFLOWS")
    log.info("🚀 [授权] 检测 OAuth 授权需求...")
    oath_required_platforms = oauth_platform_manager.get_registered_oath_platforms()
    active_oath_platforms = [
        p for p in enabled_workflow_names if p in oath_required_platforms
    ]

    is_server_required = len(active_oath_platforms) > 0

    server = None
    server_task = None

    if is_server_required:
        # 注册管理面板路由
        from web import admin_router
        oauth_platform_manager.app.include_router(admin_router, prefix="")

        srv_cfg = oauth_platform_manager.get_oath_server_config()
        log.info(
            f"🌐 [系统] 启动 OAuth 回调服务器于 {srv_cfg['host']}:{srv_cfg['port']}..."
        )
        config_server = uvicorn.Config(oauth_platform_manager.app, **srv_cfg)
        server = uvicorn.Server(config_server)
        server_task = asyncio.create_task(server.serve())
    else:
        log.info("🌐 [系统] 当前启用的工作流无需 Web 服务支持，跳过服务器启动。")

    # 2. 授权等待逻辑
    timeout_seconds = 60
    start_wait = datetime.now()

    # 识别哪些已启用的平台需要通过授权中心进行 OAuth 授权
    log.info("⏳ 检查环境就绪状态...")

    try:
        while True:
            # 如果启用的平台中没有需要 OAuth 授权的，或者其中之一已经就绪，则不再等待
            if not active_oath_platforms:
                log.info("⚡ 无需 OAuth 授权，直接继续。")
                break

            tokens_map = await load_all_tokens()
            if any(tokens_map.get(p) for p in active_oath_platforms):
                log.info("✨ 授权检测通过。")
                break

            if (datetime.now() - start_wait).total_seconds() > timeout_seconds:
                log.warning("⏱️ 授权轮询超时。")
                break

            # 触发工作流准备
            for wf_name in enabled_workflow_names:
                wf = WorkflowFactory.get_workflow(wf_name)
                # 注意：此处 prepare 会负责发起 Nudge，通常内部会有“仅发送一次”的标记
                if wf:
                    await wf.prepare()

            await asyncio.sleep(5)

        # 3. 执行核心逻辑
        log.info("🚀 [核心] 开始执行报告生成逻辑...")
        await run_reporting_logic()
    finally:
        # 清理资源
        log.info("🧹 程序运行结束，清理资源...")
        try:
            await HttpRequest.close_all()
            if server and server_task:
                server.should_exit = True
                # 给 ProactorEventLoop 留出一点缓冲时间来清理管道
                await asyncio.sleep(0.5)
                await server_task
        except asyncio.CancelledError:
            pass
        except Exception:
            log.debug("[清理] 资源清理出现异常（非关键）")
        log.info("✅ [清理] 资源清理完成")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 用户中断程序")
    except Exception as e:
        print("\n" + "!" * 60)
        print("【运行时错误】程序执行过程中发生崩溃：")
        traceback.print_exc()
        print("!" * 60)
        try:
            log.exception(f"Fatal error: {e}")
        except Exception:
            pass
        input("\n按 Enter 键退出程序...")
