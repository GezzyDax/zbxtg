"""Tests for the main application module."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import AppConfig, TelegramConfig, ZabbixConfig
from main import ZabbixTelegramBot, main


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


def test_get_version_exists() -> None:
    """Test that get_version returns a version string"""
    from main import get_version

    version = get_version()
    assert version is not None
    assert isinstance(version, str)
    # Should be either a version number or "unknown"
    assert version == "2.0.0" or version == "unknown" or len(version.split(".")) == 3


def test_setup_logging_creates_files(tmp_path: Path, monkeypatch) -> None:
    bot = ZabbixTelegramBot()
    bot.config = make_app_config(log_level="DEBUG")

    monkeypatch.chdir(tmp_path)
    bot.setup_logging()

    log_file = tmp_path / "logs" / "zbxtg.log"
    assert log_file.exists()


def test_setup_logging_without_config() -> None:
    """Test setup_logging raises error when config is not loaded"""
    bot = ZabbixTelegramBot()
    with pytest.raises(RuntimeError, match="Конфигурация не загружена"):
        bot.setup_logging()


@pytest.mark.asyncio
async def test_initialize_success() -> None:
    """Test successful initialization of all components"""
    bot = ZabbixTelegramBot()

    with patch("main.get_config") as mock_get_config:
        with patch("main.ZabbixClient"):
            with patch("main.TelegramBot") as mock_telegram:
                with patch("main.AlertMonitor"):

                    mock_get_config.return_value = make_app_config()
                    mock_telegram_instance = MagicMock()
                    mock_telegram.return_value = mock_telegram_instance
                    mock_telegram_instance.initialize = AsyncMock()
                    mock_telegram_instance.check_connection = AsyncMock(return_value=True)
                    mock_telegram_instance.send_message = AsyncMock(return_value=123)
                    mock_telegram_instance.set_alert_monitor = MagicMock()

                    await bot.initialize()

                    assert bot.config is not None
                    assert bot.zabbix_client is not None
                    assert bot.telegram_bot is not None
                    assert bot.alert_monitor is not None
                    mock_telegram_instance.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_initialize_failure() -> None:
    """Test initialization failure handling"""
    bot = ZabbixTelegramBot()

    with patch("main.get_config") as mock_get_config:
        mock_get_config.side_effect = Exception("Config error")

        with pytest.raises(Exception, match="Config error"):
            await bot.initialize()


@pytest.mark.asyncio
async def test_send_startup_and_shutdown_messages(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    bot = ZabbixTelegramBot()
    bot.telegram_bot = AsyncMock()
    bot.telegram_bot.send_message = AsyncMock()

    await bot.send_startup_message()
    bot.telegram_bot.send_message.assert_awaited()

    # Verify version is included in startup message
    call_args = bot.telegram_bot.send_message.call_args
    assert "Версия:" in call_args[0][0] or "версия" in call_args[0][0].lower()

    await bot.send_shutdown_message()
    assert bot.telegram_bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_send_startup_message_without_bot(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    bot = ZabbixTelegramBot()

    await bot.send_startup_message()
    assert "не инициализирован" in caplog.text


@pytest.mark.asyncio
async def test_send_startup_message_with_error() -> None:
    """Test startup message handling when sending fails"""
    bot = ZabbixTelegramBot()
    bot.telegram_bot = AsyncMock()
    bot.telegram_bot.send_message = AsyncMock(side_effect=Exception("Send failed"))

    # Should not raise exception
    await bot.send_startup_message()


@pytest.mark.asyncio
async def test_send_shutdown_message_without_bot() -> None:
    """Test shutdown message when bot is None"""
    bot = ZabbixTelegramBot()
    # Should not raise exception
    await bot.send_shutdown_message()


@pytest.mark.asyncio
async def test_send_shutdown_message_with_error() -> None:
    """Test shutdown message handling when sending fails"""
    bot = ZabbixTelegramBot()
    bot.telegram_bot = AsyncMock()
    bot.telegram_bot.send_message = AsyncMock(side_effect=Exception("Send failed"))

    # Should not raise exception
    await bot.send_shutdown_message()


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


@pytest.mark.asyncio
async def test_shutdown_with_errors() -> None:
    """Test shutdown handles errors gracefully"""
    bot = ZabbixTelegramBot()
    bot.telegram_bot = AsyncMock()
    bot.telegram_bot.send_message = AsyncMock(side_effect=Exception("Send failed"))
    bot.telegram_bot.stop = AsyncMock(side_effect=Exception("Stop failed"))
    bot.alert_monitor = MagicMock()
    bot.alert_monitor.stop_monitoring.side_effect = Exception("Monitor stop failed")

    # Should not raise exception
    await bot.shutdown()


@pytest.mark.asyncio
async def test_run_with_exception() -> None:
    """Test run handles exceptions"""
    bot = ZabbixTelegramBot()

    async def mock_initialize():
        raise RuntimeError("Test error")

    with patch.object(bot, "initialize", mock_initialize):
        with patch.object(bot, "shutdown", AsyncMock()):
            with pytest.raises(RuntimeError, match="Test error"):
                await bot.run()


@pytest.mark.asyncio
async def test_run_components_not_initialized() -> None:
    """Test run raises error when components are not initialized"""
    bot = ZabbixTelegramBot()

    async def mock_initialize():
        bot.config = make_app_config()
        # Don't set telegram_bot or alert_monitor

    with patch.object(bot, "initialize", mock_initialize):
        with pytest.raises(RuntimeError, match="Компоненты не инициализированы"):
            await bot.run()


@pytest.mark.asyncio
async def test_main_function() -> None:
    """Test main function"""
    with patch("main.ZabbixTelegramBot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.run = AsyncMock()

        await main()

        mock_bot.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_function_keyboard_interrupt() -> None:
    """Test main function handles KeyboardInterrupt"""
    with patch("main.ZabbixTelegramBot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.run = AsyncMock(side_effect=KeyboardInterrupt())

        # Should handle gracefully
        await main()


@pytest.mark.asyncio
async def test_main_function_exception() -> None:
    """Test main function handles exceptions"""
    with patch("main.ZabbixTelegramBot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.run = AsyncMock(side_effect=Exception("Test error"))

        # Should call sys.exit(1)
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1
