#!/usr/bin/env python3
"""
Zabbix Telegram Bot - отправляет алерты из Zabbix в Telegram определенному пользователю

Использование:
    python main.py

Переменные окружения:
    ZABBIX_URL - URL сервера Zabbix (обязательно)
    ZABBIX_USERNAME - имя пользователя Zabbix (обязательно)
    ZABBIX_PASSWORD - пароль пользователя Zabbix (обязательно)
    TELEGRAM_BOT_TOKEN - токен Telegram бота (обязательно)
    TELEGRAM_CHAT_ID - ID пользователя Telegram (обязательно)
    
    POLL_INTERVAL - интервал проверки в секундах (по умолчанию: 60)
    LOG_LEVEL - уровень логирования (по умолчанию: INFO)
    ZABBIX_SSL_VERIFY - проверка SSL сертификата (по умолчанию: true)
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config, AppConfig
from zabbix_client import ZabbixClient
from telegram_bot import TelegramBot
from alert_monitor import AlertMonitor


class ZabbixTelegramBot:
    """Главный класс приложения"""
    
    def __init__(self):
        self.config: AppConfig = None
        self.zabbix_client: ZabbixClient = None
        self.telegram_bot: TelegramBot = None
        self.alert_monitor: AlertMonitor = None
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self):
        """Настраивает логирование"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Создаем директорию для логов если нужно
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/zbxtg.log')
            ]
        )
        
        # Снижаем уровень логирования для некоторых библиотек
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('telegram').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        self.logger.info(f"Logging initialized with level: {self.config.log_level}")
    
    async def initialize(self):
        """Инициализация всех компонентов"""
        try:
            # Загружаем конфигурацию
            self.config = get_config()
            self.setup_logging()
            
            self.logger.info("Starting Zabbix Telegram Bot...")
            self.logger.info(f"Zabbix URL: {self.config.zabbix.url}")
            self.logger.info(f"Target Chat ID: {self.config.telegram.target_chat_id}")
            self.logger.info(f"Poll interval: {self.config.poll_interval}s")
            
            # Инициализируем клиенты
            self.zabbix_client = ZabbixClient(self.config.zabbix)
            self.telegram_bot = TelegramBot(self.config.telegram)
            
            # Проверяем подключения
            self.logger.info("Checking connections...")
            
            # Проверяем Zabbix
            if not self.zabbix_client.authenticate():
                raise RuntimeError("Failed to authenticate to Zabbix")
            self.logger.info("✓ Zabbix connection successful")
            
            # Проверяем Telegram
            if not await self.telegram_bot.check_connection():
                raise RuntimeError("Failed to connect to Telegram")
            self.logger.info("✓ Telegram connection successful")
            
            # Инициализируем Telegram бота
            await self.telegram_bot.initialize()
            
            # Создаем монитор алертов
            self.alert_monitor = AlertMonitor(
                self.config, 
                self.zabbix_client, 
                self.telegram_bot
            )
            
            # Устанавливаем ссылку на монитор в боте
            self.telegram_bot.set_alert_monitor(self.alert_monitor)
            
            # Отправляем стартовое сообщение
            await self.send_startup_message()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise
    
    async def send_startup_message(self):
        """Отправляет сообщение о запуске бота"""
        try:
            message = """
🚀 <b>Zabbix Monitor Started</b>

✅ Successfully connected to:
- Zabbix API
- Telegram Bot API

🔔 I will now monitor for new alerts and send them to this chat.

Use /help to see available commands.
            """.strip()
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Failed to send startup message: {e}")
    
    async def send_shutdown_message(self):
        """Отправляет сообщение об остановке бота"""
        try:
            message = "🛑 <b>Zabbix Monitor Stopped</b>\n\nMonitoring has been terminated."
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Failed to send shutdown message: {e}")
    
    async def run(self):
        """Запускает основной цикл приложения"""
        try:
            await self.initialize()

            # Запускаем компоненты параллельно
            tasks = [
                asyncio.create_task(self.telegram_bot.start(), name="telegram_bot"),
                asyncio.create_task(self.alert_monitor.start_monitoring(), name="alert_monitor")
            ]

            # Добавляем обработчик сигналов для корректной остановки
            loop = asyncio.get_event_loop()

            def signal_handler():
                self.logger.info("Received shutdown signal")
                self.alert_monitor.stop_monitoring()
                for task in tasks:
                    task.cancel()

            # Устанавливаем обработчики сигналов через event loop
            for sig in [signal.SIGTERM, signal.SIGINT]:
                loop.add_signal_handler(sig, signal_handler)

            self.logger.info("Bot is running. Press Ctrl+C to stop.")

            # Ждем завершения всех задач
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                self.logger.info("Tasks cancelled, shutting down...")
            finally:
                # Удаляем обработчики сигналов
                for sig in [signal.SIGTERM, signal.SIGINT]:
                    loop.remove_signal_handler(sig)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Runtime error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Корректно завершает работу всех компонентов"""
        self.logger.info("Shutting down...")
        
        try:
            # Отправляем сообщение об остановке
            if self.telegram_bot:
                await self.send_shutdown_message()
                
            # Останавливаем мониторинг
            if self.alert_monitor:
                self.alert_monitor.stop_monitoring()
            
            # Останавливаем Telegram бота
            if self.telegram_bot:
                await self.telegram_bot.stop()
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        self.logger.info("Shutdown complete")


async def main():
    """Точка входа в приложение"""
    bot = ZabbixTelegramBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Проверяем версию Python
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # Запускаем приложение
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Failed to start: {e}")
        sys.exit(1)