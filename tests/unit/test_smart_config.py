"""
Unit tests for SmartConfig system

Tests configuration management, validation, and hot reload
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import json


@pytest.mark.unit
class TestConfigSource:
    """Test ConfigSource enumeration"""

    def test_config_source_values(self):
        """Test all config source values exist"""
        from utils.smart_config import ConfigSource

        assert ConfigSource.ENV.value == "env"
        assert ConfigSource.FILE.value == "file"
        assert ConfigSource.DATABASE.value == "database"
        assert ConfigSource.REMOTE.value == "remote"


@pytest.mark.unit
class TestConfigType:
    """Test ConfigType enumeration"""

    def test_config_type_values(self):
        """Test all config type values exist"""
        from utils.smart_config import ConfigType

        assert ConfigType.STRING.value == "string"
        assert ConfigType.INTEGER.value == "integer"
        assert ConfigType.FLOAT.value == "float"
        assert ConfigType.BOOLEAN.value == "boolean"
        assert ConfigType.LIST.value == "list"
        assert ConfigType.DICT.value == "dict"
        assert ConfigType.JSON.value == "json"


@pytest.mark.unit
class TestConfigItem:
    """Test ConfigItem dataclass"""

    def test_config_item_creation(self):
        """Test creating a config item"""
        from utils.smart_config import ConfigItem, ConfigType, ConfigSource
        from datetime import datetime

        item = ConfigItem(
            key="test.key",
            value="test_value",
            config_type=ConfigType.STRING,
            source=ConfigSource.ENV,
            description="Test configuration",
            required=True
        )

        assert item.key == "test.key"
        assert item.value == "test_value"
        assert item.config_type == ConfigType.STRING
        assert item.source == ConfigSource.ENV
        assert item.required is True
        assert isinstance(item.last_updated, datetime)

    def test_config_item_with_defaults(self):
        """Test config item with default values"""
        from utils.smart_config import ConfigItem, ConfigType, ConfigSource

        item = ConfigItem(
            key="test.key",
            value="test",
            config_type=ConfigType.STRING,
            source=ConfigSource.ENV
        )

        assert item.description == ""
        assert item.required is False
        assert item.is_sensitive is False


@pytest.mark.unit
class TestSmartConfig:
    """Test SmartConfig class"""

    @pytest.fixture
    def config(self):
        """Create SmartConfig instance"""
        from utils.smart_config import SmartConfig
        return SmartConfig()

    def test_init(self, config):
        """Test SmartConfig initialization"""
        assert config.configs is not None
        assert config.sources is not None
        assert config.validators is not None
        assert config.update_callbacks is not None

    def test_get_config_value(self, config):
        """Test getting config value"""
        # Set a test value
        config.configs["test.key"] = MagicMock(value="test_value")

        value = config.get("test.key")
        assert value == "test_value"

    def test_get_config_with_default(self, config):
        """Test getting non-existent config returns default"""
        value = config.get("nonexistent.key", default="default_value")
        assert value == "default_value"

    def test_set_config_value(self, config):
        """Test setting config value"""
        from utils.smart_config import ConfigSource

        success = config.set("new.key", "new_value", ConfigSource.ENV)
        assert success is True
        assert "new.key" in config.configs

    def test_set_config_validation(self, config):
        """Test config validation on set"""
        from utils.smart_config import ConfigSource

        # Add a validator that requires non-empty strings
        config.validators["validated.key"] = lambda x: len(x) > 0

        success = config.set("validated.key", "valid_value", ConfigSource.ENV)
        assert success is True

    def test_get_section(self, config):
        """Test getting config section"""
        from utils.smart_config import ConfigType, ConfigSource

        # Add some configs in a section
        config.configs["app.name"] = MagicMock(value="TestApp")
        config.configs["app.version"] = MagicMock(value="1.0.0")
        config.configs["other.key"] = MagicMock(value="other")

        section = config.get_section("app")

        assert "name" in section
        assert "version" in section
        assert "other" not in section
        assert section["name"] == "TestApp"

    def test_infer_config_type(self, config):
        """Test inferring config type from value"""
        from utils.smart_config import ConfigType

        assert config._infer_config_type("string") == ConfigType.STRING
        assert config._infer_config_type(42) == ConfigType.INTEGER
        assert config._infer_config_type(3.14) == ConfigType.FLOAT
        assert config._infer_config_type(True) == ConfigType.BOOLEAN
        assert config._infer_config_type([1, 2, 3]) == ConfigType.LIST
        assert config._infer_config_type({"key": "value"}) == ConfigType.DICT

    def test_convert_value_string(self, config):
        """Test converting string values"""
        from utils.smart_config import ConfigType

        result = config._convert_value("test", ConfigType.STRING)
        assert result == "test"

    def test_convert_value_integer(self, config):
        """Test converting to integer"""
        from utils.smart_config import ConfigType

        result = config._convert_value("42", ConfigType.INTEGER)
        assert result == 42
        assert isinstance(result, int)

    def test_convert_value_float(self, config):
        """Test converting to float"""
        from utils.smart_config import ConfigType

        result = config._convert_value("3.14", ConfigType.FLOAT)
        assert result == 3.14
        assert isinstance(result, float)

    def test_convert_value_boolean(self, config):
        """Test converting to boolean"""
        from utils.smart_config import ConfigType

        assert config._convert_value("true", ConfigType.BOOLEAN) is True
        assert config._convert_value("TRUE", ConfigType.BOOLEAN) is True
        assert config._convert_value("1", ConfigType.BOOLEAN) is True
        assert config._convert_value("yes", ConfigType.BOOLEAN) is True
        assert config._convert_value("false", ConfigType.BOOLEAN) is False
        assert config._convert_value("0", ConfigType.BOOLEAN) is False

    def test_convert_value_list(self, config):
        """Test converting to list"""
        from utils.smart_config import ConfigType

        result = config._convert_value('["a", "b", "c"]', ConfigType.JSON)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_convert_value_returns_default_on_failure(self, config):
        """Test conversion returns default on failure"""
        from utils.smart_config import ConfigType

        result = config._convert_value("not_a_number", ConfigType.INTEGER)
        # Should return default for type instead of None
        assert result == 0

    def test_get_default_for_type(self, config):
        """Test getting default value for type"""
        from utils.smart_config import ConfigType

        assert config._get_default_for_type(ConfigType.STRING) == ""
        assert config._get_default_for_type(ConfigType.INTEGER) == 0
        assert config._get_default_for_type(ConfigType.FLOAT) == 0.0
        assert config._get_default_for_type(ConfigType.BOOLEAN) is False
        assert config._get_default_for_type(ConfigType.LIST) == []
        assert config._get_default_for_type(ConfigType.DICT) == {}

    def test_add_validator(self, config):
        """Test adding a validator"""
        def validate_positive(value):
            return value > 0

        config.add_validator("positive.key", validate_positive)

        assert "positive.key" in config.validators

    def test_add_validation_rule(self, config):
        """Test adding validation rule"""
        config.add_validation_rule("test.key", "min:0")

        assert "test.key" in config.validation_rules
        assert "min:0" in config.validation_rules["test.key"]

    def test_apply_validation_rule_min(self, config):
        """Test min validation rule"""
        assert config._apply_validation_rule("min:10", 15) is True
        assert config._apply_validation_rule("min:10", 5) is False

    def test_apply_validation_rule_max(self, config):
        """Test max validation rule"""
        assert config._apply_validation_rule("max:100", 50) is True
        assert config._apply_validation_rule("max:100", 150) is False

    def test_apply_validation_rule_min_length(self, config):
        """Test min_length validation rule"""
        assert config._apply_validation_rule("min_length:5", "hello") is True
        assert config._apply_validation_rule("min_length:5", "hi") is False

    def test_apply_validation_rule_max_length(self, config):
        """Test max_length validation rule"""
        assert config._apply_validation_rule("max_length:10", "hello") is True
        assert config._apply_validation_rule("max_length:5", "hello world") is False

    def test_apply_validation_rule_pattern(self, config):
        """Test pattern validation rule"""
        assert config._apply_validation_rule("pattern:^\\d+$", "12345") is True
        assert config._apply_validation_rule("pattern:^\\d+$", "abc") is False

    def test_apply_validation_rule_in(self, config):
        """Test in validation rule"""
        assert config._apply_validation_rule("in:red,green,blue", "red") is True
        assert config._apply_validation_rule("in:red,green,blue", "yellow") is False

    def test_add_update_callback(self, config):
        """Test adding update callback"""
        callback = MagicMock()

        config.add_update_callback("test.key", callback)

        assert "test.key" in config.update_callbacks
        assert callback in config.update_callbacks["test.key"]

    def test_get_config_stats(self, config):
        """Test getting config statistics"""
        from utils.smart_config import ConfigItem, ConfigType, ConfigSource

        # Add some test configs
        config.configs["key1"] = ConfigItem(
            key="key1",
            value="value1",
            config_type=ConfigType.STRING,
            source=ConfigSource.ENV
        )
        config.configs["key2"] = ConfigItem(
            key="key2",
            value="value2",
            config_type=ConfigType.STRING,
            source=ConfigSource.FILE
        )

        stats = config.get_config_stats()

        assert "total_configs" in stats
        assert stats["total_configs"] >= 2
        assert "source_stats" in stats
        assert "type_stats" in stats

    def test_is_safe_path(self, config):
        """Test path safety validation"""
        # Safe paths
        assert config._is_safe_path("config.json") is True
        assert config._is_safe_path("./config/settings.yaml") is True

        # The function should validate based on the whitelist
        # Exact behavior depends on the current working directory


@pytest.mark.unit
class TestSmartConfigSingleton:
    """Test SmartConfig singleton pattern"""

    def test_get_smart_config_singleton(self):
        """Test get_smart_config returns singleton"""
        from utils.smart_config import get_smart_config, smart_config

        config1 = get_smart_config()
        config2 = get_smart_config()

        assert config1 is config2
        assert config1 is smart_config


@pytest.mark.unit
class TestConfigLoading:
    """Test config loading functionality"""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as f:
            json.dump({
                "test": {
                    "key": "value",
                    "number": 42
                }
            }, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    def test_load_json_config_file(self, temp_config_file):
        """Test loading JSON config file"""
        from utils.smart_config import SmartConfig

        config = SmartConfig()
        # 测试中临时文件位于系统临时目录，绕过安全路径校验（该校验由 test_is_safe_path 单独测试）
        config._is_safe_path = lambda path: True
        import asyncio

        async def load_test():
            await config._load_config_file(temp_config_file)
            # Check if configs were loaded
            assert len(config.configs) > 0

        asyncio.run(load_test())

    def test_load_invalid_json(self, temp_config_file, tmp_path):
        """Test loading invalid JSON file"""
        from utils.smart_config import SmartConfig
        import asyncio

        # Create invalid JSON file
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        config = SmartConfig()

        async def load_test():
            # Should handle error gracefully
            await config._load_config_file(str(invalid_file))

        asyncio.run(load_test())

        # Should not crash
        assert config is not None
