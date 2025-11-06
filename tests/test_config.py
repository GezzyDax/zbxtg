"""Tests for config module."""

import os
import pytest

from config import (
    get_config,
    ZabbixConfig,
    TelegramConfig,
    AppConfig,
)


class TestZabbixConfig:
    """Tests for ZabbixConfig dataclass."""

    def test_zabbix_config_creation(self):
        """Test creating ZabbixConfig with minimal parameters."""
        config = ZabbixConfig(url="https://zabbix.example.com")
        assert config.url == "https://zabbix.example.com"
        assert config.username is None
        assert config.password is None
        assert config.api_token is None
        assert config.ssl_verify is True

    def test_zabbix_config_with_api_token(self):
        """Test ZabbixConfig with API token."""
        config = ZabbixConfig(
            url="https://zabbix.example.com", api_token="test_token"
        )
        assert config.api_token == "test_token"

    def test_zabbix_config_with_credentials(self):
        """Test ZabbixConfig with username/password."""
        config = ZabbixConfig(
            url="https://zabbix.example.com",
            username="admin",
            password="secret",
        )
        assert config.username == "admin"
        assert config.password == "secret"


class TestTelegramConfig:
    """Tests for TelegramConfig dataclass."""

    def test_telegram_config_creation(self):
        """Test creating TelegramConfig."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF", target_chat_id=123456789
        )
        assert config.bot_token == "123456:ABC-DEF"
        assert config.target_chat_id == 123456789
        assert config.parse_mode == "HTML"


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_app_config_creation(self, zabbix_config, telegram_config):
        """Test creating AppConfig."""
        config = AppConfig(zabbix=zabbix_config, telegram=telegram_config)
        assert config.poll_interval == 60
        assert config.log_level == "INFO"
        assert config.max_retries == 3
        assert config.min_severity == 2


class TestGetConfig:
    """Tests for get_config function."""

    def test_get_config_with_api_token(self, mock_env_vars):
        """Test get_config with API token."""
        config = get_config()
        assert isinstance(config, AppConfig)
        assert config.zabbix.url == "https://test-zabbix.example.com"
        assert config.zabbix.api_token == "test_api_token_123"
        assert config.telegram.target_chat_id == 123456789
        assert config.poll_interval == 60

    def test_get_config_with_username_password(self, monkeypatch):
        """Test get_config with username/password."""
        monkeypatch.setenv("ZABBIX_URL", "https://zabbix.example.com")
        monkeypatch.setenv("ZABBIX_USERNAME", "admin")
        monkeypatch.setenv("ZABBIX_PASSWORD", "password")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")

        config = get_config()
        assert config.zabbix.username == "admin"
        assert config.zabbix.password == "password"
        assert config.zabbix.api_token is None

    def test_get_config_missing_zabbix_url(self, monkeypatch):
        """Test get_config raises error when ZABBIX_URL is missing."""
        monkeypatch.delenv("ZABBIX_URL", raising=False)
        with pytest.raises(ValueError, match="Отсутствуют обязательные"):
            get_config()

    def test_get_config_missing_telegram_token(self, mock_env_vars, monkeypatch):
        """Test get_config raises error when TELEGRAM_BOT_TOKEN is missing."""
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
        with pytest.raises(ValueError, match="Отсутствуют обязательные"):
            get_config()

    def test_get_config_missing_telegram_chat_id(self, mock_env_vars, monkeypatch):
        """Test get_config raises error when TELEGRAM_CHAT_ID is missing."""
        monkeypatch.delenv("TELEGRAM_CHAT_ID")
        with pytest.raises(ValueError, match="Отсутствуют обязательные"):
            get_config()

    def test_get_config_missing_auth(self, mock_env_vars, monkeypatch):
        """Test get_config raises error when no auth method provided."""
        monkeypatch.delenv("ZABBIX_API_TOKEN", raising=False)
        with pytest.raises(ValueError, match="Необходимо указать либо"):
            get_config()

    def test_get_config_invalid_url(self, mock_env_vars, monkeypatch):
        """Test get_config raises error for invalid URL."""
        monkeypatch.setenv("ZABBIX_URL", "not-a-valid-url")
        with pytest.raises(ValueError, match="Некорректный формат ZABBIX_URL"):
            get_config()

    def test_get_config_invalid_poll_interval(self, mock_env_vars, monkeypatch):
        """Test get_config raises error for invalid POLL_INTERVAL."""
        monkeypatch.setenv("POLL_INTERVAL", "0")
        with pytest.raises(ValueError, match="POLL_INTERVAL должен быть больше 0"):
            get_config()

    def test_get_config_invalid_chat_id(self, mock_env_vars, monkeypatch):
        """Test get_config raises error for invalid TELEGRAM_CHAT_ID."""
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "not-a-number")
        with pytest.raises(ValueError, match="TELEGRAM_CHAT_ID должен быть числом"):
            get_config()

    def test_get_config_invalid_log_level(self, mock_env_vars, monkeypatch):
        """Test get_config raises error for invalid LOG_LEVEL."""
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        with pytest.raises(ValueError, match="LOG_LEVEL должен быть одним из"):
            get_config()

    def test_get_config_custom_values(self, mock_env_vars, monkeypatch):
        """Test get_config with custom values."""
        monkeypatch.setenv("POLL_INTERVAL", "120")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MAX_RETRIES", "5")
        monkeypatch.setenv("RETRY_DELAY", "10")
        monkeypatch.setenv("MIN_SEVERITY", "4")

        config = get_config()
        assert config.poll_interval == 120
        assert config.log_level == "DEBUG"
        assert config.max_retries == 5
        assert config.retry_delay == 10
        assert config.min_severity == 4

    def test_get_config_ssl_verify_false(self, mock_env_vars, monkeypatch):
        """Test get_config with SSL verification disabled."""
        monkeypatch.setenv("ZABBIX_SSL_VERIFY", "false")
        config = get_config()
        assert config.zabbix.ssl_verify is False

    def test_get_config_ssl_verify_true(self, mock_env_vars, monkeypatch):
        """Test get_config with SSL verification enabled."""
        monkeypatch.setenv("ZABBIX_SSL_VERIFY", "true")
        config = get_config()
        assert config.zabbix.ssl_verify is True
