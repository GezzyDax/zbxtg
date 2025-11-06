"""Tests for telegram_bot module."""

from unittest.mock import MagicMock, patch

import pytest
from telegram.error import TelegramError

from telegram_bot import TelegramBot


class TestTelegramBot:
    """Tests for TelegramBot class."""

    def test_telegram_bot_initialization(self, telegram_config):
        """Test TelegramBot initialization."""
        bot = TelegramBot(telegram_config)
        assert bot.config == telegram_config
        assert bot.bot is not None
        assert bot.application is None
        assert bot.alert_monitor is None

    def test_set_alert_monitor(self, telegram_config):
        """Test setting alert monitor."""
        bot = TelegramBot(telegram_config)
        mock_monitor = MagicMock()
        bot.set_alert_monitor(mock_monitor)
        assert bot.alert_monitor == mock_monitor

    @pytest.mark.asyncio
    async def test_send_message_success(self, telegram_config, mock_telegram_bot):
        """Test sending message successfully."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        message_id = await bot.send_message("Test message")

        assert message_id == 1
        mock_telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_markup(self, telegram_config, mock_telegram_bot):
        """Test sending message with inline keyboard."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        keyboard = [[InlineKeyboardButton("Test", url="https://example.com")]]
        markup = InlineKeyboardMarkup(keyboard)

        await bot.send_message("Test", reply_markup=markup)
        mock_telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_long_text(self, telegram_config, mock_telegram_bot):
        """Test sending long message that needs splitting."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        # Create message longer than 4096 characters
        long_message = "A" * 5000

        await bot.send_message(long_message)

        # Should be called multiple times due to splitting
        assert mock_telegram_bot.send_message.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_message_retry_on_error(self, telegram_config, mock_telegram_bot):
        """Test message retry on Telegram error."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        # First call fails, second succeeds
        mock_telegram_bot.send_message.side_effect = [
            TelegramError("Network error"),
            MagicMock(message_id=1),
        ]

        message_id = await bot.send_message("Test", retry_count=2)

        assert message_id == 1
        assert mock_telegram_bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_failure(self, telegram_config, mock_telegram_bot):
        """Test message sending failure after all retries."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        mock_telegram_bot.send_message.side_effect = TelegramError("Network error")

        message_id = await bot.send_message("Test", retry_count=3)

        assert message_id is None
        assert mock_telegram_bot.send_message.call_count == 3

    @pytest.mark.asyncio
    async def test_edit_message_success(self, telegram_config, mock_telegram_bot):
        """Test editing message successfully."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        result = await bot.edit_message(123, "Updated text")

        assert result is True
        mock_telegram_bot.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_message_not_modified(self, telegram_config, mock_telegram_bot):
        """Test editing message when content is the same."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        mock_telegram_bot.edit_message_text.side_effect = TelegramError("message is not modified")

        result = await bot.edit_message(123, "Same text")

        assert result is True  # Should return True for "not modified" error

    @pytest.mark.asyncio
    async def test_delete_message_success(self, telegram_config, mock_telegram_bot):
        """Test deleting message successfully."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        result = await bot.delete_message(123)

        assert result is True
        mock_telegram_bot.delete_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_message_not_found(self, telegram_config, mock_telegram_bot):
        """Test deleting message that doesn't exist."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        mock_telegram_bot.delete_message.side_effect = TelegramError("message to delete not found")

        result = await bot.delete_message(123)

        assert result is True  # Should return True for "not found" error

    @pytest.mark.asyncio
    async def test_send_alert(self, telegram_config, mock_telegram_bot, mock_problem_details):
        """Test sending alert message."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        message_id = await bot.send_alert(mock_problem_details, "https://zabbix.example.com")

        assert message_id == 1
        mock_telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_alert(self, telegram_config, mock_telegram_bot, mock_problem_details):
        """Test updating alert message."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        result = await bot.update_alert(123, mock_problem_details)

        assert result is True
        mock_telegram_bot.edit_message_text.assert_called_once()

    def test_format_alert_message(self, telegram_config, mock_problem_details):
        """Test alert message formatting."""
        bot = TelegramBot(telegram_config)

        message, markup = bot._format_alert_message(
            mock_problem_details, "https://zabbix.example.com"
        )

        assert "High CPU usage" in message
        assert "web-server-01" in message
        assert "192.168.1.100" in message
        assert markup is not None

    def test_format_alert_message_resolved(self, telegram_config, mock_problem_details):
        """Test formatting resolved alert."""
        bot = TelegramBot(telegram_config)

        # Mark problem as resolved
        mock_problem_details["problem"]["r_eventid"] = "99999"

        message, markup = bot._format_alert_message(mock_problem_details)

        assert "РЕШЕНО" in message
        assert "✅" in message

    def test_format_alert_message_acknowledged(self, telegram_config, mock_problem_details):
        """Test formatting acknowledged alert."""
        bot = TelegramBot(telegram_config)

        # Mark problem as acknowledged
        mock_problem_details["problem"]["acknowledged"] = "1"

        message, markup = bot._format_alert_message(mock_problem_details)

        assert "ПОДТВЕРЖДЕНО" in message
        assert "🔕" in message

    @pytest.mark.asyncio
    async def test_check_connection_success(self, telegram_config, mock_telegram_bot):
        """Test successful connection check."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        result = await bot.check_connection()

        assert result is True
        mock_telegram_bot.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, telegram_config, mock_telegram_bot):
        """Test failed connection check."""
        bot = TelegramBot(telegram_config)
        bot.bot = mock_telegram_bot

        mock_telegram_bot.get_me.side_effect = TelegramError("Network error")

        result = await bot.check_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_initialize(self, telegram_config):
        """Test bot initialization."""
        bot = TelegramBot(telegram_config)

        with patch("telegram_bot.Application.builder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app

            await bot.initialize()

            assert bot.application is not None
