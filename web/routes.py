"""DailyBot Web 管理面板 - FastAPI 路由"""
import asyncio
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger

from common import config
from common.database import db
from core.engine import run_reporting_logic


def verify_admin_key(key: Optional[str] = Query(None, alias="key")):
    admin_cfg = config.get("admin", {})
    expected_key = admin_cfg.get("api_key", "dailybot-admin")
    if not key or key != expected_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的访问密钥")
    return key


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
async def get_reports(date: Optional[str] = None, platform: Optional[str] = None, limit: int = Query(10, ge=1, le=100)):
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    reports = db.get_reports(target_date, platform, limit)
    return {"date": target_date, "reports": reports, "count": len(reports)}


@router.get("/logs")
async def get_logs(limit: int = Query(50, ge=1, le=200)):
    logs = db.get_run_logs(limit)
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
