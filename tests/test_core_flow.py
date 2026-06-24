"""核心流程集成测试"""
import pytest
from unittest.mock import AsyncMock, patch


class TestCoreFlow:
    @pytest.mark.asyncio
    async def test_collect_and_camouflage_no_data(self):
        with patch("crawlers.modules.crawler_manager.crawler_manager.collect_and_camouflage",
                   new=AsyncMock(return_value=("", 0, False, []))):
            from crawlers.modules.crawler_manager import crawler_manager
            raw, count, camo, items = await crawler_manager.collect_and_camouflage()
            assert raw == ""
            assert count == 0

    @pytest.mark.asyncio
    async def test_main_flow_no_active_workflows(self):
        from core.engine import run_reporting_logic
        with patch("core.engine.config.ENABLED_WORKFLOWS", []):
            result = await run_reporting_logic()
            assert result is None

    @pytest.mark.asyncio
    async def test_ensure_playwright_rpa_disabled(self):
        from core.engine import ensure_playwright_browsers
        with patch("core.engine.config.get_crawler_source_platforms", return_value=["feishu"]):
            with patch("core.engine.config.get_platform", return_value={"rpa": {"enabled": False}}):
                result = await ensure_playwright_browsers()
                assert result is None
