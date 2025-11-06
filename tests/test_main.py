"""Tests for the main application module."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from config import AppConfig, TelegramConfig, ZabbixConfig
from main import ZabbixTelegramBot


def make_app_config(log_level: str = "INFO") -> AppConfig:
    return AppConfig(
        zabbix=ZabbixConfig(url="https://example.com/zabbix", api_token="token"),
        telegram=TelegramConfig(bot_token="telegram-token", target_chat_id=123456),
        poll_interval=60,
        log_level=log_level,
        max_retries=3,
        retry_delay=5,
        min_severity=2,
    )


def test_setup_logging_creates_files(tmp_path: Path, monkeypatch) -> None:
    bot = ZabbixTelegramBot()
    bot.config = make_app_config(log_level="DEBUG")

    monkeypatch.chdir(tmp_path)
    bot.setup_logging()

    log_file = tmp_path / "logs" / "zbxtg.log"
    assert log_file.exists()


@pytest.mark.asyncio
async def test_send_startup_and_shutdown_messages(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    bot = ZabbixTelegramBot()
    bot.telegram_bot = AsyncMock()
    bot.telegram_bot.send_message = AsyncMock()

    await bot.send_startup_message()
    bot.telegram_bot.send_message.assert_awaited()

    await bot.send_shutdown_message()
    bot.telegram_bot.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_send_startup_message_without_bot(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    bot = ZabbixTelegramBot()

    await bot.send_startup_message()
    assert "не инициализирован" in caplog.text


@pytest.mark.asyncio
async def test_shutdown_sequence() -> None:
    bot = ZabbixTelegramBot()
    bot.telegram_bot = AsyncMock()
    bot.telegram_bot.send_message = AsyncMock()
    bot.telegram_bot.stop = AsyncMock()
    bot.alert_monitor = MagicMock()

    await bot.shutdown()

    bot.alert_monitor.stop_monitoring.assert_called_once()
    bot.telegram_bot.stop.assert_awaited()
