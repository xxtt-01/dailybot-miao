"""配置加载与访问测试"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_config_yaml():
    """Mock Config 的 _yaml_config 以包含测试所需的完整数据"""
    from common.config import config
    original = config._yaml_config
    # 注入测试数据
    config._yaml_config = {
        "version": "1.0.0",
        "platforms": {
            "wecom": {
                "ai_model": "deepseek",
                "corp_id": "test_corp",
                "corp_secret": "test_secret",
                "rpa": {"speed": 0.5, "browser_type": "chrome"},
            },
            "feishu": {
                "ai_model": "doubao",
                "app_id": "test_app",
            },
        },
        "models": {
            "deepseek": {
                "name": "DeepSeek V3",
                "api_key": "test_key",
                "models": ["deepseek-chat"],
            },
            "doubao": {
                "name": "豆包大模型",
                "api_key": "test_key",
                "models": ["doubao-v1"],
            },
        },
        "crawler_sources": {
            "gitlab": {
                "enabled": True,
                "token": "test_token",
                "repos": [{"path": "test/repo", "branch": "main"}],
            },
            "github": {
                "enabled": True,
                "repos": [{"path": "test/repo"}],
            },
        },
        "enabled_workflows": ["wecom"],
    }
    yield
    config._yaml_config = original


class TestConfigLoading:
    """配置加载测试"""

    def test_config_singleton(self):
        """测试配置模块级单例"""
        from common.config import config as cfg1
        from common.config import config as cfg2
        assert cfg1 is cfg2

    def test_config_class_version(self):
        """测试配置类版本号存在"""
        from common.config import Config
        assert hasattr(Config, "VERSION")

    def test_ignore_category_keys(self):
        """测试忽略的分类键"""
        from common.config import Config
        assert "platforms" in Config.IGNORE_CATEGORY_KEYS
        assert "models" in Config.IGNORE_CATEGORY_KEYS
        assert "crawler_sources" in Config.IGNORE_CATEGORY_KEYS

    def test_path_to_attr_name(self):
        """测试路径转属性名"""
        from common.config import Config
        # 忽略分类前缀后全部大写
        result = Config.path_to_attr_name("models.doubao.name")
        assert result == "DOUBAO_NAME"
        # 正常路径
        result = Config.path_to_attr_name("log.level")
        assert result == "LOG_LEVEL"

    def test_path_to_env_key(self):
        """测试路径转环境变量名"""
        from common.config import Config
        result = Config.path_to_env_key("models.doubao.api_key")
        assert result == "DOUBAO.API_KEY"

    def test_parse_gitlab_crawler_sources(self):
        """测试解析 GitLab 爬虫源字符串"""
        from common.config import Config
        result = Config.parse_gitlab_crawler_sources("path/to/repo:main")
        assert result == [{"path": "path/to/repo", "branch": "main"}]

        result = Config.parse_gitlab_crawler_sources("path/to/repo")
        assert result == [{"path": "path/to/repo", "branch": "master"}]

        result = Config.parse_gitlab_crawler_sources("")
        assert result == []


class TestConfigGet:
    """配置 get 方法测试"""

    def test_get_existing_key(self):
        """测试获取存在的键"""
        from common.config import config
        version = config.get("version")
        assert version == "1.1.2"

    def test_get_nonexistent_key(self):
        """测试获取不存在的键，应返回默认值"""
        from common.config import config
        result = config.get("nonexistent.key", "default")
        assert result == "default"

    def test_get_platform(self, mock_config_yaml):
        """测试获取平台配置"""
        from common.config import config
        platform = config.get_platform("wecom")
        assert isinstance(platform, dict)
        assert "corp_id" in platform
        assert platform["corp_id"] == "test_corp"

    def test_get_model(self, mock_config_yaml):
        """测试获取模型配置"""
        from common.config import config
        model = config.get_model("deepseek")
        assert isinstance(model, dict)
        assert "api_key" in model

    def test_get_provider_for_model(self, mock_config_yaml):
        """测试根据模型 ID 查找提供商"""
        from common.config import config
        provider = config.get_provider_for_model("deepseek-chat")
        assert provider == "deepseek"

        provider = config.get_provider_for_model("nonexistent-model")
        assert provider is None

    def test_get_crawler_source_platforms(self):
        """测试获取爬虫源平台列表"""
        from common.config import config
        platforms = config.get_crawler_source_platforms()
        assert isinstance(platforms, list)

    def test_get_merged_config(self, mock_config_yaml):
        """测试合并配置"""
        from common.config import config
        merged = config.get_merged_config("models", "deepseek")
        assert isinstance(merged, dict)
        assert merged.get("name") == "DeepSeek V3"

    def test_clean_empty_values(self):
        """测试清理空值"""
        from common.config import Config
        cfg = Config()
        assert cfg._clean_empty_values(None) is None
        assert cfg._clean_empty_values("") is None
        assert cfg._clean_empty_values({}) is None
        assert cfg._clean_empty_values([]) is None
        assert cfg._clean_empty_values(0) == 0
        assert cfg._clean_empty_values(False) is False
        assert cfg._clean_empty_values("hello") == "hello"
        assert cfg._clean_empty_values({"a": None, "b": "val"}) == {"b": "val"}

    def test_parse_env_value(self):
        """测试环境变量值解析"""
        from common.config import Config
        assert Config._parse_env_value("simple") == "simple"
        assert Config._parse_env_value('{"key": "val"}') == {"key": "val"}
        assert Config._parse_env_value("[1,2,3]") == [1, 2, 3]
