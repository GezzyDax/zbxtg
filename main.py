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

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from alert_monitor import AlertMonitor
from config import AppConfig, get_config
from telegram_bot import TelegramBot
from zabbix_client import ZabbixClient


class ZabbixTelegramBot:
    """Главный класс приложения"""

    def __init__(self) -> None:
        self.config: Optional[AppConfig] = None
        self.zabbix_client: Optional[ZabbixClient] = None
        self.telegram_bot: Optional[TelegramBot] = None
        self.alert_monitor: Optional[AlertMonitor] = None
        self.logger = logging.getLogger(__name__)

    def setup_logging(self) -> None:
        """Настраивает логирование"""
        if self.config is None:
            raise RuntimeError("Конфигурация не загружена, логирование невозможно настроить")

        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)

        # Создаем директорию для логов если нужно
        os.makedirs("logs", exist_ok=True)

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/zbxtg.log")],
        )

        # Снижаем уровень логирования для некоторых библиотек
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        self.logger.info("Логирование инициализировано с уровнем: %s", self.config.log_level)

    async def initialize(self) -> None:
        """Инициализация всех компонентов"""
        try:
            # Загружаем конфигурацию
            self.config = get_config()
            self.setup_logging()

            self.logger.info("Запуск Zabbix Telegram бота...")
            self.logger.info("Zabbix URL: %s", self.config.zabbix.url)
            self.logger.info("ID целевого чата: %s", self.config.telegram.target_chat_id)
            self.logger.info("Интервал опроса: %sс", self.config.poll_interval)

            # Инициализируем клиенты
            self.zabbix_client = ZabbixClient(self.config.zabbix)
            self.telegram_bot = TelegramBot(self.config.telegram)

            # Проверяем подключения
            self.logger.info("Проверка подключений...")

            # Проверяем Zabbix
            if not self.zabbix_client.authenticate():
                raise RuntimeError("Не удалось аутентифицироваться в Zabbix")
            self.logger.info("✓ Подключение к Zabbix успешно")

            # Проверяем Telegram
            if not await self.telegram_bot.check_connection():
                raise RuntimeError("Не удалось подключиться к Telegram")
            self.logger.info("✓ Подключение к Telegram успешно")

            # Инициализируем Telegram бота
            await self.telegram_bot.initialize()

            # Создаем монитор алертов
            self.alert_monitor = AlertMonitor(self.config, self.zabbix_client, self.telegram_bot)

            # Устанавливаем ссылку на монитор в боте
            self.telegram_bot.set_alert_monitor(self.alert_monitor)

            # Отправляем стартовое сообщение
            await self.send_startup_message()

            self.logger.info("Все компоненты успешно инициализированы")

        except Exception as e:
            self.logger.error("Инициализация не удалась: %s", e)
            raise

    async def send_startup_message(self) -> None:
        """Отправляет сообщение о запуске бота"""
        if self.telegram_bot is None:
            self.logger.warning("Telegram бот не инициализирован, стартовое сообщение не отправлено")
            return

        try:
            message = """
🚀 <b>Zabbix монитор запущен</b>

✅ Успешно подключено к:
- Zabbix API
- Telegram Bot API

🔔 Теперь я буду отслеживать новые алерты и отправлять их в этот чат.

Используйте /help чтобы увидеть доступные команды.
            """.strip()

            await self.telegram_bot.send_message(message)

        except Exception as e:
            self.logger.error("Не удалось отправить стартовое сообщение: %s", e)

    async def send_shutdown_message(self) -> None:
        """Отправляет сообщение об остановке бота"""
        if self.telegram_bot is None:
            return

        try:
            message = "🛑 <b>Zabbix монитор остановлен</b>\n\nМониторинг был завершен."
            await self.telegram_bot.send_message(message)

        except Exception as e:
            self.logger.error("Не удалось отправить сообщение об остановке: %s", e)

    async def run(self) -> None:
        """Запускает основной цикл приложения"""
        try:
            await self.initialize()

            if self.telegram_bot is None or self.alert_monitor is None:
                raise RuntimeError("Компоненты не инициализированы")

            # Запускаем компоненты параллельно
            tasks = [
                asyncio.create_task(self.telegram_bot.start(), name="telegram_bot"),
                asyncio.create_task(self.alert_monitor.start_monitoring(), name="alert_monitor"),
            ]

            # Добавляем обработчик сигналов для корректной остановки
            loop = asyncio.get_event_loop()

            def signal_handler() -> None:
                self.logger.info("Получен сигнал завершения")
                if self.alert_monitor:
                    self.alert_monitor.stop_monitoring()
                for task in tasks:
                    task.cancel()

            # Устанавливаем обработчики сигналов через event loop
            for sig in [signal.SIGTERM, signal.SIGINT]:
                loop.add_signal_handler(sig, signal_handler)

            self.logger.info("Бот работает. Нажмите Ctrl+C для остановки.")

            # Ждем завершения всех задач
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                self.logger.info("Задачи отменены, завершение работы...")
            finally:
                # Удаляем обработчики сигналов
                for sig in [signal.SIGTERM, signal.SIGINT]:
                    loop.remove_signal_handler(sig)

        except KeyboardInterrupt:
            self.logger.info("Получено прерывание с клавиатуры")
        except Exception as e:
            self.logger.error("Ошибка выполнения: %s", e)
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Корректно завершает работу всех компонентов"""
        self.logger.info("Завершение работы...")

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
            self.logger.error("Ошибка при завершении: %s", e)

        self.logger.info("Завершение выполнено")


async def main() -> None:
    """Точка входа в приложение"""
    bot = ZabbixTelegramBot()

    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\nЗапрошено завершение...")
    except Exception as e:  # pragma: no cover - защита от критических ошибок при запуске
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Запускаем приложение
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nДо свидания!")
    except Exception as e:
        print(f"Не удалось запустить: {e}")
        sys.exit(1)
