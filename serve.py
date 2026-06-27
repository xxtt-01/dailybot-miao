"""
DailyBot 后端服务（纯 Web 模式）

用法:
    python serve.py              # 启动服务（默认 127.0.0.1:8001）
    python serve.py --port 9001  # 指定端口

与 main.py 的区别:
    - main.py 执行完整的日报采集→总结→推送流程
    - serve.py 只启动 Web 服务（管理面板 + API），不执行日报逻辑
    - serve.py 由 Electron 桌面版作为子进程启动
"""
import sys
import uvicorn
from loguru import logger

import common.logger  # noqa: F401 (触发全局日志配置)
from common import config
from oauth import oauth_platform_manager
from web import admin_router


def create_app():
    """创建 FastAPI 应用实例并挂载管理路由"""
    app = oauth_platform_manager.app
    app.include_router(admin_router, prefix="")
    return app


def main():
    port = 8001
    host = "127.0.0.1"

    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    logger.info(f"🚀 DailyBot 后端服务启动于 http://{host}:{port}")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
