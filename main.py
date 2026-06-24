import asyncio
import traceback
from datetime import datetime

import uvicorn
from loguru import logger as log

import common.logger  # noqa: F401 (触发全局日志配置)
from common import config
from core.engine import ensure_playwright_browsers, run_reporting_logic
from exceptions import handle_logic_exception
from oauth import oauth_platform_manager
from request.core.http_request import HttpRequest
from token_storage import load_all_tokens
from workflows import WorkflowFactory


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

    # 1. 判断是否需要启动 WebServer (OAuth 授权、管理面板等需要)
    enabled_workflow_names = getattr(config, "ENABLED_WORKFLOWS")
    admin_config = config.get("admin", {})
    has_admin = bool(admin_config and admin_config.get("api_key"))
    log.info("🚀 [授权] 检测 OAuth 授权需求...")
    oath_required_platforms = oauth_platform_manager.get_registered_oath_platforms()
    active_oath_platforms = [
        p for p in enabled_workflow_names if p in oath_required_platforms
    ]

    is_server_required = len(active_oath_platforms) > 0 or has_admin

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
