"""Tests for telegram_bot module."""

from unittest.mock import AsyncMock, MagicMock, patch

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

    @pytest.mark.asyncio
    async def test_initialize_failure(self, telegram_config):
        """Test bot initialization failure."""
        bot = TelegramBot(telegram_config)

        with patch("telegram_bot.Application.builder") as mock_builder:
            mock_builder.side_effect = Exception("Builder failed")

            with pytest.raises(Exception, match="Builder failed"):
                await bot.initialize()

    @pytest.mark.asyncio
    async def test_start_without_initialization(self, telegram_config):
        """Test starting bot without prior initialization."""
        bot = TelegramBot(telegram_config)

        with patch.object(bot, 'initialize') as mock_init, \
             patch("telegram_bot.Application") as mock_app_class:
            mock_app = MagicMock()
            mock_app.updater = MagicMock()
            mock_init.return_value = None
            bot.application = mock_app

            await bot.start()

            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_success(self, telegram_config):
        """Test successful bot start."""
        bot = TelegramBot(telegram_config)
        mock_app = MagicMock()
        mock_app.updater = MagicMock()
        mock_app.initialize = AsyncMock()
        mock_app.start = AsyncMock()
        mock_app.updater.start_polling = AsyncMock()
        bot.application = mock_app

        await bot.start()

        mock_app.initialize.assert_called_once()
        mock_app.start.assert_called_once()
        mock_app.updater.start_polling.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_no_updater(self, telegram_config):
        """Test starting bot when updater is None."""
        bot = TelegramBot(telegram_config)
        mock_app = MagicMock()
        mock_app.updater = None
        mock_app.initialize = AsyncMock()
        mock_app.start = AsyncMock()
        bot.application = mock_app

        with pytest.raises(RuntimeError, match="Updater не настроен"):
            await bot.start()

    @pytest.mark.asyncio
    async def test_start_failure(self, telegram_config):
        """Test bot start failure."""
        bot = TelegramBot(telegram_config)
        mock_app = MagicMock()
        mock_app.initialize = AsyncMock(side_effect=Exception("Start failed"))
        bot.application = mock_app

        with pytest.raises(Exception, match="Start failed"):
            await bot.start()

    @pytest.mark.asyncio
    async def test_stop_success(self, telegram_config):
        """Test successful bot stop."""
        bot = TelegramBot(telegram_config)
        mock_app = MagicMock()
        mock_app.updater = MagicMock()
        mock_app.updater.stop = AsyncMock()
        mock_app.stop = AsyncMock()
        mock_app.shutdown = AsyncMock()
        bot.application = mock_app

        await bot.stop()

        mock_app.updater.stop.assert_called_once()
        mock_app.stop.assert_called_once()
        mock_app.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_without_application(self, telegram_config):
        """Test stop when application is None."""
        bot = TelegramBot(telegram_config)

        # Should not raise exception
        await bot.stop()

    @pytest.mark.asyncio
    async def test_stop_with_error(self, telegram_config):
        """Test stop when error occurs."""
        bot = TelegramBot(telegram_config)
        mock_app = MagicMock()
        mock_app.updater = MagicMock()
        mock_app.updater.stop = AsyncMock(side_effect=Exception("Stop failed"))
        bot.application = mock_app

        # Should not raise exception
        await bot.stop()

    @pytest.mark.asyncio
    async def test_start_command(self, telegram_config):
        """Test /start command handler."""
        from telegram import Update

        bot = TelegramBot(telegram_config)
        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Привет" in call_args[1]["text"] or "привет" in call_args[1]["text"].lower()

    @pytest.mark.asyncio
    async def test_help_command(self, telegram_config):
        """Test /help command handler."""
        from telegram import Update

        bot = TelegramBot(telegram_config)
        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "/help" in call_args[1]["text"] or "/status" in call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_status_command_with_monitor(self, telegram_config):
        """Test /status command with alert monitor."""
        from telegram import Update

        bot = TelegramBot(telegram_config)
        mock_monitor = MagicMock()
        mock_monitor.get_status = AsyncMock(return_value="All systems operational")
        bot.alert_monitor = mock_monitor

        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._status_command(mock_update, mock_context)

        mock_monitor.get_status.assert_called_once()
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_command_without_monitor(self, telegram_config):
        """Test /status command without alert monitor."""
        from telegram import Update

        bot = TelegramBot(telegram_config)

        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._status_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "не инициализирован" in call_args[1]["text"] or "недоступен" in call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_problems_command_with_monitor(self, telegram_config):
        """Test /problems command with alert monitor."""
        from telegram import Update

        bot = TelegramBot(telegram_config)
        mock_monitor = MagicMock()
        mock_monitor.send_status_message = AsyncMock()
        bot.alert_monitor = mock_monitor

        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._problems_command(mock_update, mock_context)

        mock_monitor.send_status_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_problems_command_without_monitor(self, telegram_config):
        """Test /problems command without alert monitor."""
        from telegram import Update

        bot = TelegramBot(telegram_config)

        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._problems_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_command(self, telegram_config):
        """Test /test command handler."""
        from telegram import Update

        bot = TelegramBot(telegram_config)
        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._test_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "работает" in call_args[1]["text"].lower() or "успешно" in call_args[1]["text"].lower()

    @pytest.mark.asyncio
    async def test_unknown_message(self, telegram_config):
        """Test unknown message handler."""
        from telegram import Update

        bot = TelegramBot(telegram_config)
        mock_update = MagicMock(spec=Update)
        mock_context = MagicMock()
        mock_update.effective_chat.id = telegram_config.target_chat_id
        mock_update.message.reply_text = AsyncMock()

        await bot._unknown_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "/help" in call_args[1]["text"]

    def test_authorized_user_filter(self, telegram_config):
        """Test authorized user filter creation."""
        bot = TelegramBot(telegram_config)
        user_filter = bot._authorized_user_filter()

        assert user_filter is not None
