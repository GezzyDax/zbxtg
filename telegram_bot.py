import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Update, Bot
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
        
    async def initialize(self):
        """Инициализация бота"""
        try:
            self.application = Application.builder().token(self.config.bot_token).build()
            
            # Добавляем обработчики команд
            self.application.add_handler(CommandHandler("start", self._start_command))
            self.application.add_handler(CommandHandler("help", self._help_command))
            self.application.add_handler(CommandHandler("status", self._status_command))
            self.application.add_handler(CommandHandler("problems", self._problems_command))
            self.application.add_handler(CommandHandler("test", self._test_command))
            
            # Обработчик неизвестных команд
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._unknown_message))
            
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
    
    async def send_message(self, message: str, parse_mode: str = None) -> bool:
        """Отправляет сообщение целевому пользователю"""
        try:
            await self.bot.send_message(
                chat_id=self.config.target_chat_id,
                text=message,
                parse_mode=parse_mode or self.config.parse_mode,
                disable_web_page_preview=True
            )
            
            logger.debug(f"Message sent to chat {self.config.target_chat_id}")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Отправляет форматированное уведомление об алерте"""
        try:
            message = self._format_alert_message(alert_data)
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    def _format_alert_message(self, alert_data: Dict[str, Any]) -> str:
        """Форматирует сообщение об алерте"""
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
        
        # Формируем сообщение
        message = f"""
🚨 <b>Zabbix Alert</b>

{severity}
<b>Host:</b> {host_name}{host_ip}
<b>Problem:</b> {problem_name}
<b>Description:</b> {trigger_description}
<b>Time:</b> {event_time}
<b>Event ID:</b> {problem.get("eventid", "N/A")}

<b>Status:</b> {"🔴 PROBLEM" if problem.get("r_eventid", "0") == "0" else "🟢 RESOLVED"}
""".strip()
        
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
            
        return message
    
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
        user_id = update.effective_user.id
        
        if user_id == self.config.target_chat_id:
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
        else:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        user_id = update.effective_user.id
        
        if user_id == self.config.target_chat_id:
            if self.alert_monitor:
                await self.alert_monitor.send_status_message()
            else:
                await update.message.reply_text("❌ Мониторинг не инициализирован.")
        else:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
    
    async def _problems_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /problems"""
        user_id = update.effective_user.id
        
        if user_id == self.config.target_chat_id:
            if self.alert_monitor:
                await self.alert_monitor.send_problems_list()
            else:
                await update.message.reply_text("❌ Мониторинг не инициализирован.")
        else:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
    
    async def _test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test"""
        user_id = update.effective_user.id
        
        if user_id == self.config.target_chat_id:
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
        else:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
    
    async def _unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных сообщений"""
        user_id = update.effective_user.id
        
        if user_id == self.config.target_chat_id:
            await update.message.reply_text(
                "🤖 Я понимаю только команды. Используйте /help для получения списка доступных команд."
            )
        else:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
    
    async def check_connection(self) -> bool:
        """Проверяет подключение к Telegram API"""
        try:
            me = await self.bot.get_me()
            logger.info(f"Connected to Telegram as @{me.username}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False