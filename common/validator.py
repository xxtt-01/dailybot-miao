"""配置校验模块，启动时检查 config.yaml 的完整性"""
from typing import List, Tuple
from loguru import logger


def validate_config(config_obj) -> List[Tuple[str, str]]:
    errors = []
    enabled_workflows = getattr(config_obj, "ENABLED_WORKFLOWS", [])
    if not enabled_workflows:
        errors.append(("enabled_workflows", "未启用任何工作流"))
    for wf_name in enabled_workflows:
        platform = config_obj.get_platform(wf_name)
        if not platform:
            errors.append((f"platforms.{wf_name}", f"工作流 {wf_name} 配置不存在"))
            continue
        ai_model = platform.get("ai_model", "")
        if not ai_model:
            errors.append((f"platforms.{wf_name}.ai_model", f"平台 {wf_name} 未指定 AI 模型"))
        all_models = config_obj.get("models", {})
        if ai_model and ai_model not in all_models:
            errors.append((f"models.{ai_model}", f"AI 模型 {ai_model} 配置不存在"))
        oauth_port = platform.get("oauth", {}).get("port", 0)
        if oauth_port and not (1 <= oauth_port <= 65535):
            errors.append((f"platforms.{wf_name}.oauth.port", f"端口 {oauth_port} 无效"))
    crawler_sources = config_obj.get("crawler_sources", {})
    has_enabled_source = False
    for source_name, source_config in crawler_sources.items():
        if source_config.get("enabled", False):
            has_enabled_source = True
            repos = source_config.get("repos", [])
            has_auto_discover = source_config.get("auto_discover", False) and source_config.get("target_user")
            valid_repos = [r for r in repos if r.get("path")]
            if not valid_repos and not has_auto_discover:
                errors.append((f"crawler_sources.{source_name}.repos", f"{source_name} 已启用但无有效仓库"))
            base_url = source_config.get("base_url", "")
            if base_url and not base_url.startswith(("http://", "https://")):
                errors.append((f"crawler_sources.{source_name}.base_url", f"URL 格式无效：{base_url}，应以 http:// 或 https:// 开头"))
    if not has_enabled_source:
        errors.append(("crawler_sources", "没有启用任何采集源"))
    return errors


def print_validation_errors(errors):
    if not errors:
        logger.info("配置校验通过")
        return
    logger.warning("配置校验发现问题:")
    for field, msg in errors:
        logger.warning(f"  - [{field}] {msg}")
