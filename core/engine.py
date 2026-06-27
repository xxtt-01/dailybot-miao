"""DailyBot 核心报告引擎 — 负责采集 → AI 总结 → 推送的完整流程"""
import asyncio
import json
import sys
import textwrap
import traceback
from datetime import datetime

from loguru import logger as log

from common import config
from common.database import db
from crawlers.modules.camouflage_history import camouflage_history_manager
from crawlers.modules.crawler_manager import crawler_manager
from request.core.http_request import HttpRequest
from rpa.modules.rpa_factory import RPAFactory
from workflows import WorkflowFactory


async def ensure_playwright_browsers():
    """
    检查并自动安装 Playwright 浏览器驱动 (Chromium)
    实现傻瓜式运行：如果检测到 RPA 开启但环境不就绪，自动下载驱动。
    """
    any_rpa_enabled = False
    for p_name in config.get_crawler_source_platforms():
        if config.get_platform(p_name).get("rpa", {}).get("enabled", False):
            any_rpa_enabled = True
            break

    if not any_rpa_enabled:
        return

    log.info("🧪 [系统] 正在准备自动化运行环境...")

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
    """根据配置动态触发 RPA 流程"""
    try:
        platform_config = config.get_platform(platform_name)
        rpa_enabled = platform_config.get("rpa", {}).get("enabled", False)

        if not rpa_enabled:
            return

        log.info(f"🚀 [RPA] 检测到 {platform_name} 已启用自动化填报，正在准备执行...")

        try:
            report_data = json.loads(summary_json)
        except Exception as e:
            log.error(f"❌ [RPA] AI 返回数据非合法 JSON，跳过 RPA 流程: {e}")
            return

        rpa_instance = RPAFactory.get_rpa(platform_name, config)
        if not rpa_instance:
            log.warning(f"⚠️ [RPA] 未发现 {platform_name} 的 RPA 驱动实现，已跳过。")
            return

        await rpa_instance.run(report_data)
    except Exception as e:
        log.error(f"❌ [RPA] {platform_name} 自动化执行发生异常: {e}")


async def run_reporting_logic():
    """全异步工作流：采集 -> AI 总结 -> 推送"""
    log.info("🎬 开始执行报告生成流程...")

    try:
        db.add_notification(title="日报开始执行", body="日报生成流程已启动", type="report_started")
    except Exception:
        pass

    enabled_workflow_names = getattr(config, "ENABLED_WORKFLOWS")
    active_workflows = []

    for wf_name in enabled_workflow_names:
        wf = WorkflowFactory.get_workflow(wf_name)
        if wf and await wf.prepare():
            active_workflows.append(wf)

    if not active_workflows:
        log.warning("⚠️ 没有可用的工作流，中止任务。")
        return

    # 1. 数据采集
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

    # 2. 并行起始反馈
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

    # 3. 模型请求（去重：同模型只请求一次）
    log.info("🚀 [AI] 准备发起 AI 总结请求...")
    model_tasks = {}

    async def get_model_summary(m_name: str):
        if m_name in model_tasks:
            return await model_tasks[m_name]

        async def _do_request():
            log.info(f"🤖 [AI] 正在为模型供应商 {m_name} 生成统一总结内容...")
            sample_wf = next(
                wf
                for wf in active_workflows
                if config.get_platform(wf.WORKFLOW_NAME).get("ai_model") == m_name
            )
            summary = await sample_wf.summarize(raw_report, is_camouflage=is_camouflage)

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

                            if "不重要、不紧急" in priority:
                                p_emoji = "🟢"
                            elif "重要" in priority:
                                p_emoji = "🔴"
                            else:
                                p_emoji = "🟡"

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

    # 4. 并行派发结果并执行 RPA
    async def finalize_workflow_async(wf, ctx):
        nonlocal fake_items_used
        try:
            m_name = config.get_platform(wf.WORKFLOW_NAME).get("ai_model")
            if not m_name:
                log.error(f"❌ [工作流: {wf.WORKFLOW_NAME}] 配置错误：未定义 ai_model")
                return

            summary = await get_model_summary(m_name)
            if not summary:
                log.error(f"❌ 工作流 {wf.WORKFLOW_NAME} 未能获取到总结结果")
                return

            if fake_items_used:
                variant = summary
                log.info(
                    f"💾 [伪装] 总结成功，正在为 {len(fake_items_used)} 个素材更新记录..."
                )
                for item in fake_items_used:
                    camouflage_history_manager.update_usage(item, variant)
                fake_items_used = []

            log.info(
                f"✨ [AI总结完毕] 平台 {wf.WORKFLOW_NAME} 所需模型 {m_name} 已就绪，准备执行下一步动作..."
            )

            log.info(f"🚀 [推送] 正在推送到平台: {wf.WORKFLOW_NAME}")

            # 检查是否启用自动推送，默认 true
            platform_config = config.get_platform(wf.WORKFLOW_NAME)
            auto_push = platform_config.get("auto_push", True)

            if auto_push:
                await wf.on_report_success(summary, ctx)
                log.info(f"✅ [推送] 平台 {wf.WORKFLOW_NAME} 通知已发送")
                pushed = 1
                try:
                    db.add_notification(
                        title="日报推送成功",
                        body=f"{wf.WORKFLOW_NAME} 平台日报已推送完成",
                        type="push_success",
                    )
                except Exception:
                    pass
            else:
                log.info(f"📝 [草稿] 平台 {wf.WORKFLOW_NAME} 自动推送已关闭，保存为草稿")
                pushed = 0
                try:
                    db.add_notification(
                        title="日报已存草稿",
                        body=f"{wf.WORKFLOW_NAME} 平台日报已保存为草稿",
                        type="draft_saved",
                    )
                except Exception:
                    pass

            try:
                db.save_report(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    platform=wf.WORKFLOW_NAME,
                    summary=summary,
                    raw_data=ctx.get("raw_report", "") if isinstance(ctx, dict) else "",
                    is_camouflage=bool(is_camouflage),
                    pushed=pushed,
                )
                db.log_run(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    status="success",
                    platform=wf.WORKFLOW_NAME,
                )
                log.info(f"✅ [数据库] 平台 {wf.WORKFLOW_NAME} 运行记录已保存")
            except Exception as db_err:
                log.warning("⚠️ [数据库] 平台 {} 记录写入失败（非关键）: {}", wf.WORKFLOW_NAME, db_err)

            await trigger_rpa(wf.WORKFLOW_NAME, summary)

        except Exception as e:
            log.error(f"工作流 {wf.WORKFLOW_NAME} 最终处置失败: {e}")
            await wf.on_report_failure(str(e), ctx)
            try:
                db.add_notification(
                    title="日报推送失败",
                    body=f"{wf.WORKFLOW_NAME} 平台: {str(e)[:100]}",
                    type="push_failed",
                )
            except Exception:
                pass
            try:
                db.log_run(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    status="failed",
                    platform=wf.WORKFLOW_NAME,
                    message=str(e),
                )
            except Exception:
                pass

    for wf in active_workflows:
        platform_config = config.get_platform(wf.WORKFLOW_NAME)
        if platform_config.get("rpa", {}).get("enabled", False):
            log.info(
                f"⚡ [RPA检测] {wf.WORKFLOW_NAME} 已开启自动化填报，响应后将即刻启动..."
            )

    await asyncio.gather(
        *(finalize_workflow_async(wf, ctx) for wf, ctx in wf_contexts),
        return_exceptions=True,
    )
    log.info("✅ [核心] 报告生成流程执行完毕")
