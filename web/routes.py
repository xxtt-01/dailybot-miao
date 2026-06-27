"""DailyBot Web 管理面板 - FastAPI 路由"""
import asyncio
import json
import os
import signal
import traceback
import yaml
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, Query, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from common import config
from common.database import db
from core.engine import run_reporting_logic


def verify_admin_key(
    key: Optional[str] = Query(None, alias="key"),
    x_desktop_client: Optional[str] = Header(None),
):
    # 桌面版客户端（localhost）跳过鉴权 — 信任本机用户
    if x_desktop_client == "true":
        return "desktop"
    admin_cfg = config.get("admin", {})
    expected_key = admin_cfg.get("api_key", "dailybot-admin")
    if not key or key != expected_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的访问密钥")
    return key


def _write_config_yaml(updates: dict):
    target_path = None
    app_dir = __import__("utils.path_helper", fromlist=["get_app_dir"]).get_app_dir()
    for p in [os.path.join(app_dir, "config.yaml"), os.path.join(app_dir, "config", "config.yaml")]:
        if os.path.exists(p):
            target_path = p
            break
    # 也检查资源路径
    if not target_path:
        rp = __import__("utils.path_helper", fromlist=["get_resource_path"]).get_resource_path("config/config.yaml")
        if os.path.exists(rp):
            target_path = rp
    if not target_path:
        return
    with open(target_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    for k, v in updates.items():
        if isinstance(v, dict) and k in raw and isinstance(raw[k], dict):
            raw[k].update(v)
        else:
            raw[k] = v
    with open(target_path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_admin_key)])


@router.get("/status")
async def get_status():
    enabled_workflows = getattr(config, "ENABLED_WORKFLOWS", [])
    platforms = []
    for wf_name in enabled_workflows:
        platform_config = config.get_platform(wf_name)
        platforms.append({
            "name": wf_name,
            "ai_model": platform_config.get("ai_model", ""),
            "rpa_enabled": platform_config.get("rpa", {}).get("enabled", False),
        })
    return {
        "version": getattr(config, "VERSION", "unknown"),
        "enabled_workflows": list(enabled_workflows),
        "platforms": platforms,
        "time": datetime.now().isoformat(),
    }


@router.get("/config")
async def get_config(masked: bool = Query(True, description="是否脱敏")):
    raw = getattr(config, '_yaml_config', None) or {}
    if not masked:
        return raw

    def mask_sensitive(d):
        if not isinstance(d, dict):
            return d
        sensitive_keys = {"api_key", "token", "app_secret", "corp_secret", "password", "secret"}
        result = {}
        for k, v in d.items():
            if k in sensitive_keys and isinstance(v, str) and v:
                result[k] = v[:4] + "****" + v[-4:] if len(v) > 8 else "****"
            elif isinstance(v, dict):
                result[k] = mask_sensitive(v)
            elif isinstance(v, list):
                result[k] = [mask_sensitive(i) if isinstance(i, dict) else i for i in v]
            else:
                result[k] = v
        return result

    return mask_sensitive(dict(raw))


@router.get("/reports")
async def get_reports(date: Optional[str] = None, platform: Optional[str] = None, search: Optional[str] = None, limit: int = Query(10, ge=1, le=100)):
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    reports = db.get_reports(target_date, platform, limit, search)
    return {"date": target_date, "reports": reports, "count": len(reports)}


@router.get("/logs")
async def get_logs(limit: int = Query(50, ge=1, le=200), search: Optional[str] = None):
    logs = db.get_run_logs(limit, search)
    return {"logs": logs, "count": len(logs)}


@router.api_route("/trigger", methods=["GET", "POST"])
async def trigger_report():
    """手动触发一次完整的日报生成流程（异步后台执行）"""
    from common.validator import print_validation_errors, validate_config

    async def _run_main():
        logger.info("🚀 [面板触发] 收到手动触发日报请求")
        validation_errors = validate_config(config)
        if validation_errors:
            print_validation_errors(validation_errors)
            logger.error("❌ [面板触发] 配置校验未通过，中止执行")
            return

        try:
            await run_reporting_logic()
            logger.info("✅ [面板触发] 日报生成流程执行完毕")
        except Exception as e:
            logger.error(f"❌ [面板触发] 日报生成失败: {e}")
            logger.error(traceback.format_exc())

    asyncio.create_task(_run_main())
    return JSONResponse(
        content={"message": "日报生成任务已提交后台执行", "status": "started"},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/reports/detail")
async def get_report_detail(id: int = Query(...)):
    report = db.get_report_by_id(id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"report": report}


@router.get("/reports/summary")
async def get_reports_summary(start: str = Query(...), end: str = Query(...)):
    """获取指定日期范围内的日报聚合（周报/月报用）"""
    reports = db.get_reports_by_date_range(start, end, 500)
    total = len(reports)
    by_platform: dict = {}
    by_type = {"normal": 0, "camouflage": 0}
    for r in reports:
        p = r.get("platform", "unknown")
        if p not in by_platform:
            by_platform[p] = {"count": 0, "items": []}
        by_platform[p]["count"] += 1
        by_platform[p]["items"].append(r)
        if r.get("is_camouflage"):
            by_type["camouflage"] += 1
        else:
            by_type["normal"] += 1
    return {
        "start": start,
        "end": end,
        "total": total,
        "by_platform": by_platform,
        "by_type": by_type,
        "reports": reports,
    }


@router.get("/stats/trend")
async def get_stats_trend(days: int = Query(7, ge=1, le=90)):
    data = db.get_report_trend(days)
    return {"days": [d["date"] for d in data], "counts": [d["cnt"] for d in data]}


@router.get("/stats/platform")
async def get_platform_stats():
    data = db.get_platform_stats()
    platforms = {}
    for row in data:
        p = row["platform"]
        if p not in platforms:
            platforms[p] = {"name": p, "success": 0, "failed": 0, "no_data": 0}
        status = row["status"]
        if status in platforms[p]:
            platforms[p][status] = row["cnt"]
    return {"platforms": list(platforms.values())}


@router.get("/stats/platform-trend")
async def get_platform_trend(days: int = Query(7, ge=1, le=90)):
    """各平台日报数量趋势（多平台堆叠图用）"""
    rows = db.get_platform_trend(days)
    # 重组为按日期+平台的结构
    days_set: list = []
    platforms_map: dict = {}
    for r in rows:
        d = r["date"]
        p = r["platform"]
        c = r["cnt"]
        if d not in days_set:
            days_set.append(d)
        if p not in platforms_map:
            platforms_map[p] = {}
        platforms_map[p][d] = c
    # 填充为数组
    result: dict = {}
    for p, day_counts in platforms_map.items():
        result[p] = [day_counts.get(d, 0) for d in days_set]
    return {"days": days_set, "platforms": result}


@router.get("/camouflage")
async def get_camouflage_list():
    from crawlers.modules.camouflage_history import camouflage_history_manager
    items = camouflage_history_manager.list_all_items()
    return {"items": items}


@router.delete("/camouflage/{item_id}")
async def delete_camouflage_item(item_id: str):
    from crawlers.modules.camouflage_history import camouflage_history_manager
    ok = camouflage_history_manager.delete_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"success": True, "message": "已删除"}


@router.get("/sources")
async def get_sources():
    sources_cfg = config.get("crawler_sources", {})
    result = []
    for platform_name, cfg in sources_cfg.items():
        if isinstance(cfg, dict):
            repos = cfg.get("repos", [])
            result.append({
                "platform": platform_name,
                "enabled": cfg.get("enabled", False),
                "repo_count": len(repos),
                "repos": [{"path": r.get("path", ""), "branch": r.get("branch", "main")} for r in repos],
            })
    return {"sources": result}


@router.post("/sources")
async def add_source(data: dict):
    platform = data.get("platform", "")
    repo_path = data.get("repo_path", "")
    branch = data.get("branch", "main")
    if not platform or not repo_path:
        raise HTTPException(status_code=400, detail="platform 和 repo_path 必填")
    sources_cfg = config.get("crawler_sources", {})
    if platform not in sources_cfg:
        sources_cfg[platform] = {"enabled": True, "repos": [], "token": ""}
    sources_cfg[platform].setdefault("repos", [])
    sources_cfg[platform]["repos"].append({"path": repo_path, "branch": branch})
    _write_config_yaml({"crawler_sources": sources_cfg})
    config.reload()
    return {"success": True, "message": f"已添加仓库 {repo_path}"}


@router.delete("/sources/{platform}/{repo_index:int}")
async def delete_source(platform: str, repo_index: int):
    sources_cfg = config.get("crawler_sources", {})
    if platform not in sources_cfg:
        raise HTTPException(status_code=404, detail="平台不存在")
    repos = sources_cfg[platform].get("repos", [])
    if repo_index < 0 or repo_index >= len(repos):
        raise HTTPException(status_code=404, detail="仓库索引超出范围")
    removed = repos.pop(repo_index)
    _write_config_yaml({"crawler_sources": sources_cfg})
    config.reload()
    return {"success": True, "message": f"已删除仓库 {removed.get('path', '')}"}


@router.get("/scheduler")
async def get_scheduler_status():
    from dailybot_scheduler import get_registered_task_names
    sc = config.get("scheduler", {})
    tasks = get_registered_task_names()
    return {
        "config": {
            "enabled": sc.get("enabled", False),
            "auto_start": sc.get("auto_start", False),
            "default_time": sc.get("default_time", "18:20"),
        },
        "installed_tasks": tasks,
    }


@router.post("/scheduler/install")
async def install_scheduler(data: dict = {"time": "18:20", "weekdays": [1, 2, 3, 4, 5]}):
    from dailybot_scheduler import register_schtask, get_exe_path, TASK_NAME_PREFIX
    task_name = f"{TASK_NAME_PREFIX}Dashboard"
    time_str = data.get("time", "18:20")
    weekdays = data.get("weekdays")
    exe_path = get_exe_path()
    import logging
    dummy_log = logging.getLogger("scheduler_api")
    ok = register_schtask(task_name, time_str, exe_path, dummy_log, weekdays)
    return {"success": ok, "message": "定时任务已安装" if ok else "安装失败"}


@router.post("/scheduler/uninstall")
async def uninstall_scheduler():
    from dailybot_scheduler import remove_all_tasks
    import logging
    dummy_log = logging.getLogger("scheduler_api")
    remove_all_tasks(dummy_log)
    return {"success": True, "message": "已卸载所有定时任务"}


# ── 桌面版专用 API ──────────────────────────────────────


# SSE 实时日志流：全局队列，trigger 时注册 loguru sink
_live_log_queue: Optional[asyncio.Queue] = None


def _push_log_to_queue(message):
    """loguru sink 回调：向 SSE 队列推送日志"""
    q = _live_log_queue
    if q is not None:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass


@router.post("/config")
async def update_config(data: dict):
    """更新配置（桌面版配置编辑用）"""
    try:
        _write_config_yaml(data)
        config.reload()
        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/desktop-version")
async def check_desktop_version():
    """检查当前版本与 GitHub 最新版（桌面版更新提示用）"""
    current = getattr(config, "VERSION", "1.1.2")
    latest = current
    download_url = ""
    try:
        import httpx
        resp = httpx.get(
            "https://api.github.com/repos/xxtt-01/daily-bot/releases/latest",
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            latest = data.get("tag_name", "").lstrip("v") or current
            download_url = data.get("html_url", "")
    except Exception:
        pass
    return {
        "current_version": current,
        "latest_version": latest,
        "has_update": latest != current,
        "download_url": download_url,
    }


@router.get("/live-logs")
async def stream_live_logs():
    """SSE 实时日志流（桌面版执行日报时展示日志用）"""
    global _live_log_queue
    _live_log_queue = asyncio.Queue(maxsize=500)

    # 注册 loguru sink
    sink_id = logger.add(_push_log_to_queue, format="{time:HH:mm:ss} | {level} | {message}", level="INFO")

    async def event_generator():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(_live_log_queue.get(), timeout=30)
                    yield f"data: {json.dumps({'text': msg}, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'text': 'heartbeat'}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            logger.remove(sink_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/exit")
async def shutdown_backend():
    """关闭后端服务（桌面版退出时调用）"""
    async def _shutdown():
        await asyncio.sleep(0.3)
        logger.info("🛑 收到关闭信号，服务即将退出")
        os.kill(os.getpid(), signal.SIGINT)

    asyncio.create_task(_shutdown())
    return {"message": "服务即将关闭"}
