import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import TelegramError
from config import TelegramConfig


logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram бот для отправки уведомлений"""
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.bot = Bot(token=config.bot_token)
        self.application = None
        self.alert_monitor = None
        
    def set_alert_monitor(self, alert_monitor):
        """Устанавливает ссылку на alert_monitor"""
        self.alert_monitor = alert_monitor
        
    def _authorized_user_filter(self):
        """Создает фильтр для проверки авторизованного пользователя"""
        return filters.User(user_id=self.config.target_chat_id)

    async def initialize(self):
        """Инициализация бота"""
        try:
            self.application = Application.builder().token(self.config.bot_token).build()

            # Фильтр для проверки авторизации
            auth_filter = self._authorized_user_filter()

            # Добавляем обработчики команд с фильтром авторизации
            self.application.add_handler(CommandHandler("start", self._start_command))
            self.application.add_handler(CommandHandler("help", self._help_command, filters=auth_filter))
            self.application.add_handler(CommandHandler("status", self._status_command, filters=auth_filter))
            self.application.add_handler(CommandHandler("problems", self._problems_command, filters=auth_filter))
            self.application.add_handler(CommandHandler("test", self._test_command, filters=auth_filter))

            # Обработчик неизвестных команд (только для авторизованного пользователя)
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & auth_filter, self._unknown_message))

            logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise
    
    async def start(self):
        """Запуск бота"""
        if not self.application:
            await self.initialize()
            
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Telegram bot started and polling for updates")
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise
    
    async def stop(self):
        """Остановка бота"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}")
    
    async def send_message(self, message: str, parse_mode: str = None,
                          reply_markup: Optional[InlineKeyboardMarkup] = None,
                          retry_count: int = 3) -> Optional[int]:
        """Отправляет сообщение целевому пользователю с retry механизмом

        Returns:
            message_id если успешно, None если ошибка
        """
        MAX_MESSAGE_LENGTH = 4096

        for attempt in range(retry_count):
            try:
                # Если сообщение слишком длинное, разбиваем его
                if len(message) > MAX_MESSAGE_LENGTH:
                    logger.warning(f"Message too long ({len(message)} chars), splitting...")

                    # Разбиваем сообщение на части
                    parts = []
                    msg_copy = message
                    while msg_copy:
                        if len(msg_copy) <= MAX_MESSAGE_LENGTH:
                            parts.append(msg_copy)
                            break

                        # Находим последний перенос строки в пределах лимита
                        split_pos = msg_copy.rfind('\n', 0, MAX_MESSAGE_LENGTH)
                        if split_pos == -1:
                            # Если нет переносов, режем по лимиту
                            split_pos = MAX_MESSAGE_LENGTH

                        parts.append(msg_copy[:split_pos])
                        msg_copy = msg_copy[split_pos:].lstrip()

                    # Отправляем все части
                    last_message_id = None
                    for i, part in enumerate(parts, 1):
                        header = f"📄 Часть {i}/{len(parts)}\n\n" if len(parts) > 1 else ""
                        # Кнопки только на последней части
                        part_markup = reply_markup if i == len(parts) else None
                        sent_message = await self.bot.send_message(
                            chat_id=self.config.target_chat_id,
                            text=header + part,
                            parse_mode=parse_mode or self.config.parse_mode,
                            reply_markup=part_markup,
                            disable_web_page_preview=True
                        )
                        last_message_id = sent_message.message_id
                        logger.debug(f"Message part {i}/{len(parts)} sent (message_id: {last_message_id})")

                    return last_message_id

                else:
                    sent_message = await self.bot.send_message(
                        chat_id=self.config.target_chat_id,
                        text=message,
                        parse_mode=parse_mode or self.config.parse_mode,
                        reply_markup=reply_markup,
                        disable_web_page_preview=True
                    )
                    logger.debug(f"Message sent to chat {self.config.target_chat_id} (message_id: {sent_message.message_id})")
                    return sent_message.message_id

            except TelegramError as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Failed to send message (attempt {attempt + 1}/{retry_count}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to send message after {retry_count} attempts: {e}")
                    return None

        return None

    async def edit_message(self, message_id: int, message: str, parse_mode: str = None,
                          reply_markup: Optional[InlineKeyboardMarkup] = None, retry_count: int = 3) -> bool:
        """Редактирует существующее сообщение"""
        for attempt in range(retry_count):
            try:
                await self.bot.edit_message_text(
                    chat_id=self.config.target_chat_id,
                    message_id=message_id,
                    text=message,
                    parse_mode=parse_mode or self.config.parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                logger.debug(f"Message {message_id} edited successfully")
                return True

            except TelegramError as e:
                if "message is not modified" in str(e).lower():
                    logger.debug(f"Message {message_id} content unchanged, skipping edit")
                    return True

                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Failed to edit message (attempt {attempt + 1}/{retry_count}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to edit message after {retry_count} attempts: {e}")
                    return False

        return False

    async def delete_message(self, message_id: int, retry_count: int = 3) -> bool:
        """Удаляет сообщение"""
        for attempt in range(retry_count):
            try:
                await self.bot.delete_message(
                    chat_id=self.config.target_chat_id,
                    message_id=message_id
                )
                logger.debug(f"Message {message_id} deleted successfully")
                return True

            except TelegramError as e:
                if "message to delete not found" in str(e).lower():
                    logger.debug(f"Message {message_id} already deleted or not found")
                    return True

                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Failed to delete message (attempt {attempt + 1}/{retry_count}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to delete message after {retry_count} attempts: {e}")
                    return False

        return False

    async def send_alert(self, alert_data: Dict[str, Any], zabbix_url: str = None) -> Optional[int]:
        """Отправляет форматированное уведомление об алерте

        Returns:
            message_id если успешно, None если ошибка
        """
        try:
            message, reply_markup = self._format_alert_message(alert_data, zabbix_url)
            return await self.send_message(message, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return None

    async def update_alert(self, message_id: int, alert_data: Dict[str, Any],
                          zabbix_url: str = None) -> bool:
        """Обновляет существующее сообщение об алерте

        Returns:
            True если успешно, False если ошибка
        """
        try:
            message, reply_markup = self._format_alert_message(alert_data, zabbix_url)
            return await self.edit_message(message_id, message, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Failed to update alert: {e}")
            return False
    
    def _format_alert_message(self, alert_data: Dict[str, Any],
                             zabbix_url: str = None) -> tuple[str, Optional[InlineKeyboardMarkup]]:
        """Форматирует сообщение об алерте

        Returns:
            tuple: (formatted_message, inline_keyboard_markup)
        """
        problem = alert_data.get("problem", {})
        trigger = alert_data.get("trigger", {})
        hosts = alert_data.get("hosts", [])

        # Определяем серьезность
        severity_map = {
            "0": "🟢 Not classified",
            "1": "🔵 Information",
            "2": "🟡 Warning",
            "3": "🟠 Average",
            "4": "🔴 High",
            "5": "🔥 Disaster"
        }

        severity = severity_map.get(problem.get("severity", "0"), "❓ Unknown")

        # Основная информация
        host_name = hosts[0]["name"] if hosts else "Unknown Host"
        host_ip = ""
        if hosts and "interfaces" in hosts[0]:
            interfaces = hosts[0]["interfaces"]
            if interfaces:
                host_ip = f" ({interfaces[0].get('ip', 'N/A')})"

        problem_name = problem.get("name", "Unknown Problem")
        trigger_description = trigger.get("description", "No description")

        # Время события
        event_time = problem.get("clock", "")
        if event_time:
            from datetime import datetime
            event_time = datetime.fromtimestamp(int(event_time)).strftime("%Y-%m-%d %H:%M:%S")

        # Определяем статус с визуальными индикаторами
        is_resolved = problem.get("r_eventid", "0") != "0"
        acknowledged = problem.get("acknowledged", "0") == "1"

        if is_resolved:
            status_icon = "✅"
            status_text = "RESOLVED"
            alert_header = "✅ <b>Zabbix Alert - RESOLVED</b>"
        elif acknowledged:
            status_icon = "🔕"
            status_text = "ACKNOWLEDGED"
            alert_header = "🔕 <b>Zabbix Alert - ACKNOWLEDGED</b>"
        else:
            status_icon = "🔴"
            status_text = "PROBLEM"
            alert_header = "🚨 <b>Zabbix Alert - ACTIVE</b>"

        # Формируем сообщение с визуальными индикаторами
        message = f"""
{alert_header}

{severity}
<b>Host:</b> {host_name}{host_ip}
<b>Problem:</b> {problem_name}
<b>Description:</b> {trigger_description}
<b>Time:</b> {event_time}
<b>Event ID:</b> {problem.get("eventid", "N/A")}

<b>Status:</b> {status_icon} {status_text}
""".strip()

        # Добавляем время решения проблемы
        if is_resolved and problem.get("r_clock"):
            try:
                from datetime import datetime
                resolved_time = datetime.fromtimestamp(int(problem.get("r_clock"))).strftime("%Y-%m-%d %H:%M:%S")
                message += f"\n<b>Resolved at:</b> {resolved_time}"
            except:
                pass

        # Добавляем теги если есть
        if problem.get("tags"):
            tags = []
            for tag in problem["tags"]:
                tag_value = tag.get("value", "")
                if tag_value:
                    tags.append(f"{tag['tag']}:{tag_value}")
                else:
                    tags.append(tag["tag"])

            if tags:
                message += f"\n<b>Tags:</b> {', '.join(tags)}"

        # Добавляем комментарии к триггеру если есть
        if trigger.get("comments"):
            message += f"\n<b>Comments:</b> {trigger['comments']}"

        # Создаем inline-кнопки
        keyboard = []
        if zabbix_url and problem.get("eventid"):
            # Кнопка для перехода в Zabbix
            event_id = problem.get("eventid")
            # URL формат: https://zabbix.server/zabbix.php?action=problem.view&filter_eventids[]={event_id}
            zabbix_event_url = f"{zabbix_url.rstrip('/')}/zabbix.php?action=problem.view&filter_eventids[]={event_id}"
            keyboard.append([InlineKeyboardButton("🔗 View in Zabbix", url=zabbix_event_url)])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        return message, reply_markup
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        
        if user_id == self.config.target_chat_id:
            await update.message.reply_text(
                "👋 Привет! Я бот для мониторинга Zabbix.\n"
                "Я буду отправлять вам уведомления о проблемах в системе.\n\n"
                "Используйте /help для получения списка команд."
            )
        else:
            await update.message.reply_text(
                "❌ Извините, но я настроен работать только с определенным пользователем."
            )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📋 <b>Доступные команды:</b>

/start - Начать работу с ботом
/help - Показать это сообщение
/status - Проверить статус подключения к Zabbix
/problems - Показать активные проблемы в Zabbix
/test - Отправить тестовое уведомление

🔔 Я автоматически отправляю уведомления о проблемах в Zabbix.
        """
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        if self.alert_monitor:
            await self.alert_monitor.send_status_message()
        else:
            await update.message.reply_text("❌ Мониторинг не инициализирован.")
    
    async def _problems_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /problems"""
        if self.alert_monitor:
            await self.alert_monitor.send_problems_list()
        else:
            await update.message.reply_text("❌ Мониторинг не инициализирован.")
    
    async def _test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test"""
        test_alert = {
            "problem": {
                "eventid": "12345",
                "name": "Test Problem",
                "severity": "3",
                "clock": str(int(asyncio.get_event_loop().time())),
                "r_eventid": "0",
                "tags": [{"tag": "test", "value": "alert"}]
            },
            "trigger": {
                "description": "This is a test alert from Zabbix monitoring bot",
                "comments": "Test trigger for bot verification"
            },
            "hosts": [{
                "name": "Test Host",
                "interfaces": [{"ip": "192.168.1.100"}]
            }]
        }

        success = await self.send_alert(test_alert)
        if success:
            await update.message.reply_text("✅ Тестовое уведомление отправлено!")
        else:
            await update.message.reply_text("❌ Ошибка при отправке тестового уведомления.")
    
    async def _unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных сообщений"""
        await update.message.reply_text(
            "🤖 Я понимаю только команды. Используйте /help для получения списка доступных команд."
        )
    
    async def check_connection(self) -> bool:
        """Проверяет подключение к Telegram API"""
        try:
            me = await self.bot.get_me()
            logger.info(f"Connected to Telegram as @{me.username}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False