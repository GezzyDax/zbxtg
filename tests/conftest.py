"""Pytest configuration and fixtures."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Bot
from telegram.ext import Application

from config import AppConfig, TelegramConfig, ZabbixConfig


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Устанавливает минимальные переменные окружения для тестов."""
    env_vars = {
        "ZABBIX_URL": "https://test-zabbix.example.com",
        "ZABBIX_API_TOKEN": "test_api_token_123",
        "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        "TELEGRAM_CHAT_ID": "123456789",
        "POLL_INTERVAL": "60",
        "LOG_LEVEL": "INFO",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def zabbix_config():
    """Создает тестовую конфигурацию Zabbix."""
    return ZabbixConfig(
        url="https://test-zabbix.example.com",
        api_token="test_api_token_123",
        ssl_verify=False,
    )


@pytest.fixture
def telegram_config():
    """Создает тестовую конфигурацию Telegram."""
    return TelegramConfig(
        bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        target_chat_id=123456789,
    )


@pytest.fixture
def app_config(zabbix_config, telegram_config):
    """Создает полную тестовую конфигурацию приложения."""
    return AppConfig(
        zabbix=zabbix_config,
        telegram=telegram_config,
        poll_interval=60,
        log_level="INFO",
        max_retries=3,
        retry_delay=5,
        min_severity=2,
    )


@pytest.fixture
def mock_zabbix_response():
    """Создает мок-ответ от Zabbix API."""
    return {
        "jsonrpc": "2.0",
        "result": [
            {
                "eventid": "12345",
                "objectid": "54321",
                "name": "Test problem",
                "severity": "3",
                "clock": "1234567890",
                "r_eventid": "0",
                "acknowledged": "0",
                "tags": [{"tag": "test", "value": "value"}],
            }
        ],
        "id": 1,
    }


@pytest.fixture
def mock_problem():
    """Создает тестовую проблему Zabbix."""
    return {
        "eventid": "12345",
        "objectid": "54321",
        "name": "High CPU usage",
        "severity": "3",
        "clock": "1234567890",
        "r_eventid": "0",
        "acknowledged": "0",
        "tags": [{"tag": "service", "value": "web"}],
    }


@pytest.fixture
def mock_problem_details():
    """Создает детальную информацию о проблеме."""
    return {
        "problem": {
            "eventid": "12345",
            "name": "High CPU usage",
            "severity": "3",
            "clock": "1234567890",
            "r_eventid": "0",
            "acknowledged": "0",
        },
        "trigger": {
            "triggerid": "54321",
            "description": "CPU usage is above 90%",
            "hosts": [{"hostid": "10001"}],
        },
        "hosts": [
            {
                "hostid": "10001",
                "name": "web-server-01",
                "interfaces": [{"ip": "192.168.1.100"}],
            }
        ],
    }


@pytest.fixture
def mock_telegram_bot():
    """Создает мок Telegram бота."""
    bot = AsyncMock(spec=Bot)
    bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    bot.edit_message_text = AsyncMock()
    bot.delete_message = AsyncMock()
    return bot


@pytest.fixture
def mock_telegram_application(mock_telegram_bot):
    """Создает мок Telegram Application."""
    app = AsyncMock(spec=Application)
    app.bot = mock_telegram_bot
    app.initialize = AsyncMock()
    app.start = AsyncMock()
    app.stop = AsyncMock()
    app.shutdown = AsyncMock()
    app.updater = MagicMock()
    app.updater.start_polling = AsyncMock()
    app.updater.stop = AsyncMock()
    return app


@pytest.fixture
def event_loop():
    """Создает event loop для асинхронных тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
