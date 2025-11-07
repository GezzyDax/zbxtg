from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import TelegramConfig

if TYPE_CHECKING:
    from alert_monitor import AlertMonitor

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


class TelegramBot:
    """Telegram бот для отправки уведомлений."""

    def __init__(self, config: TelegramConfig):
        self.config = config
        self.bot = Bot(token=config.bot_token)
        self.application: Optional[Application] = None
        self.alert_monitor: Optional[AlertMonitor] = None

    def set_alert_monitor(self, alert_monitor: AlertMonitor) -> None:
        """Устанавливает ссылку на alert_monitor."""
        self.alert_monitor = alert_monitor

    def _authorized_user_filter(self) -> filters.User:
        """Создает фильтр для проверки авторизованного пользователя."""
        return filters.User(user_id=self.config.target_chat_id)

    async def initialize(self) -> None:
        """Инициализация бота."""
        try:
            application = Application.builder().token(self.config.bot_token).build()
            self.application = application

            # Фильтр для проверки авторизации
            auth_filter = self._authorized_user_filter()

            # Добавляем обработчики команд с фильтром авторизации
            application.add_handler(CommandHandler("start", self._start_command))
            application.add_handler(CommandHandler("help", self._help_command, filters=auth_filter))
            application.add_handler(
                CommandHandler("status", self._status_command, filters=auth_filter)
            )
            application.add_handler(
                CommandHandler("problems", self._problems_command, filters=auth_filter)
            )
            application.add_handler(CommandHandler("test", self._test_command, filters=auth_filter))

            # Обработчик неизвестных команд (только для авторизованного пользователя)
            application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND & auth_filter, self._unknown_message)
            )

            logger.info("Telegram бот успешно инициализирован")

        except Exception as exc:
            logger.error("Не удалось инициализировать Telegram бот: %s", exc)
            raise

    async def start(self) -> None:
        """Запуск бота."""
        if self.application is None:
            await self.initialize()

        if self.application is None:
            raise RuntimeError("Не удалось инициализировать Telegram приложение")

        try:
            application = self.application
            await application.initialize()
            await application.start()

            if application.updater is None:
                raise RuntimeError("Updater не настроен для Telegram приложения")

            await application.updater.start_polling()
            logger.info("Telegram бот запущен и опрашивает обновления")

        except Exception as exc:
            logger.error("Не удалось запустить Telegram бот: %s", exc)
            raise

    async def stop(self) -> None:
        """Остановка бота."""
        if self.application is None:
            return

        application = self.application
        try:
            if application.updater is not None:
                await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("Telegram бот остановлен")
        except Exception as exc:
            logger.error("Ошибка остановки Telegram бота: %s", exc)

    async def send_message(
        self,
        message: str,
        parse_mode: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        retry_count: int = 3,
    ) -> Optional[int]:
        """Отправляет сообщение целевому пользователю с retry механизмом."""
        for attempt in range(retry_count):
            try:
                # Если сообщение слишком длинное, разбиваем его
                if len(message) > MAX_MESSAGE_LENGTH:
                    logger.warning(
                        "Сообщение слишком длинное (%s символов), разбиваем...", len(message)
                    )
                    return await self._send_long_message(
                        message, parse_mode=parse_mode, reply_markup=reply_markup
                    )

                sent_message = await self.bot.send_message(
                    chat_id=self.config.target_chat_id,
                    text=message,
                    parse_mode=parse_mode or self.config.parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
                sent_message_id = sent_message.message_id
                logger.debug(
                    "Message sent to chat %s (message_id: %s)",
                    self.config.target_chat_id,
                    sent_message_id,
                )
                return sent_message_id

            except TelegramError as exc:
                if attempt < retry_count - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "Не удалось отправить сообщение (попытка %s/%s): %s",
                        attempt + 1,
                        retry_count,
                        exc,
                    )
                    logger.info("Повтор через %ss...", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Не удалось отправить сообщение после %s попыток: %s", retry_count, exc
                    )
                    return None

        return None

    async def _send_long_message(
        self,
        message: str,
        parse_mode: Optional[str],
        reply_markup: Optional[InlineKeyboardMarkup],
    ) -> Optional[int]:
        """Разбивает длинное сообщение на части и отправляет его."""
        parts: list[str] = []
        msg_copy = message
        while msg_copy:
            if len(msg_copy) <= MAX_MESSAGE_LENGTH:
                parts.append(msg_copy)
                break

            split_pos = msg_copy.rfind("\n", 0, MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = MAX_MESSAGE_LENGTH

            parts.append(msg_copy[:split_pos])
            msg_copy = msg_copy[split_pos:].lstrip()

        last_message_id: Optional[int] = None
        total_parts = len(parts)
        for index, part in enumerate(parts, 1):
            header = f"📄 Часть {index}/{total_parts}\n\n" if total_parts > 1 else ""
            part_markup = reply_markup if index == total_parts else None
            sent_message = await self.bot.send_message(
                chat_id=self.config.target_chat_id,
                text=header + part,
                parse_mode=parse_mode or self.config.parse_mode,
                reply_markup=part_markup,
                disable_web_page_preview=True,
            )
            last_message_id = sent_message.message_id
            logger.debug(
                "Message part %s/%s sent (message_id: %s)", index, total_parts, last_message_id
            )

        return last_message_id

    async def edit_message(
        self,
        message_id: int,
        message: str,
        parse_mode: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        retry_count: int = 3,
    ) -> bool:
        """Редактирует существующее сообщение."""
        for attempt in range(retry_count):
            try:
                await self.bot.edit_message_text(
                    chat_id=self.config.target_chat_id,
                    message_id=message_id,
                    text=message,
                    parse_mode=parse_mode or self.config.parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
                logger.debug("Сообщение %s успешно отредактировано", message_id)
                return True

            except TelegramError as exc:
                if "message is not modified" in str(exc).lower():
                    logger.debug(
                        "Содержимое сообщения %s не изменилось, пропуск редактирования", message_id
                    )
                    return True

                if attempt < retry_count - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Не удалось отредактировать сообщение (попытка %s/%s): %s",
                        attempt + 1,
                        retry_count,
                        exc,
                    )
                    logger.info("Повтор через %ss...", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Не удалось отредактировать сообщение после %s попыток: %s",
                        retry_count,
                        exc,
                    )
                    return False

        return False

    async def delete_message(self, message_id: int, retry_count: int = 3) -> bool:
        """Удаляет сообщение."""
        for attempt in range(retry_count):
            try:
                await self.bot.delete_message(
                    chat_id=self.config.target_chat_id, message_id=message_id
                )
                logger.debug("Сообщение %s успешно удалено", message_id)
                return True

            except TelegramError as exc:
                if "message to delete not found" in str(exc).lower():
                    logger.debug("Сообщение %s уже удалено или не найдено", message_id)
                    return True

                if attempt < retry_count - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Не удалось удалить сообщение (попытка %s/%s): %s",
                        attempt + 1,
                        retry_count,
                        exc,
                    )
                    logger.info("Повтор через %ss...", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Не удалось удалить сообщение после %s попыток: %s", retry_count, exc
                    )
                    return False

        return False

    async def send_alert(
        self, alert_data: Dict[str, Any], zabbix_url: Optional[str] = None
    ) -> Optional[int]:
        """Отправляет форматированное уведомление об алерте."""
        try:
            message, reply_markup = self._format_alert_message(alert_data, zabbix_url)
            return await self.send_message(message, reply_markup=reply_markup)

        except Exception as exc:
            logger.error("Не удалось отправить алерт: %s", exc)
            return None

    async def update_alert(
        self, message_id: int, alert_data: Dict[str, Any], zabbix_url: Optional[str] = None
    ) -> bool:
        """Обновляет существующее сообщение об алерте."""
        try:
            message, reply_markup = self._format_alert_message(alert_data, zabbix_url)
            return await self.edit_message(message_id, message, reply_markup=reply_markup)

        except Exception as exc:
            logger.error("Не удалось обновить алерт: %s", exc)
            return False

    def _format_alert_message(
        self, alert_data: Dict[str, Any], zabbix_url: Optional[str] = None
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Форматирует сообщение об алерте."""
        problem = alert_data.get("problem", {})
        trigger = alert_data.get("trigger", {})
        hosts = alert_data.get("hosts", [])

        severity_map = {
            "0": "🟢 Не классифицировано",
            "1": "🔵 Информация",
            "2": "🟡 Предупреждение",
            "3": "🟠 Средняя",
            "4": "🔴 Высокая",
            "5": "🔥 Критическая",
        }

        severity = severity_map.get(problem.get("severity", "0"), "❓ Неизвестно")

        host_name = hosts[0]["name"] if hosts else "Неизвестный хост"
        host_ip = ""
        if hosts and "interfaces" in hosts[0]:
            interfaces = hosts[0]["interfaces"]
            if interfaces:
                host_ip = f" ({interfaces[0].get('ip', 'N/A')})"

        problem_name = problem.get("name", "Неизвестная проблема")
        trigger_description = trigger.get("description", "Нет описания")

        event_time = problem.get("clock", "")
        if event_time:
            try:
                event_time = datetime.fromtimestamp(int(event_time)).strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                event_time = "Неизвестно"

        is_resolved = problem.get("r_eventid", "0") != "0"
        acknowledged = problem.get("acknowledged", "0") == "1"

        if is_resolved:
            status_icon = "✅"
            status_text = "РЕШЕНО"
            alert_header = "✅ <b>Zabbix алерт - РЕШЕНО</b>"
        elif acknowledged:
            status_icon = "🔕"
            status_text = "ПОДТВЕРЖДЕНО"
            alert_header = "🔕 <b>Zabbix алерт - ПОДТВЕРЖДЕНО</b>"
        else:
            status_icon = "🔴"
            status_text = "ПРОБЛЕМА"
            alert_header = "🚨 <b>Zabbix алерт - АКТИВНО</b>"

        message = f"""
{alert_header}

{severity}
<b>Хост:</b> {host_name}{host_ip}
<b>Проблема:</b> {problem_name}
<b>Описание:</b> {trigger_description}
<b>Время:</b> {event_time}
<b>ID события:</b> {problem.get("eventid", "N/A")}

<b>Статус:</b> {status_icon} {status_text}
        """.strip()

        if is_resolved and problem.get("r_clock"):
            try:
                resolved_time = datetime.fromtimestamp(int(problem.get("r_clock"))).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                message += f"\n<b>Решено в:</b> {resolved_time}"
            except (TypeError, ValueError):
                logger.debug("Не удалось преобразовать время решения проблемы", exc_info=True)

        if problem.get("tags"):
            tags = []
            for tag in problem["tags"]:
                tag_key = tag.get("tag", "")
                tag_value = tag.get("value", "")
                if tag_key:
                    if tag_value:
                        tags.append(f"{tag_key}:{tag_value}")
                    else:
                        tags.append(tag_key)

            if tags:
                message += f"\n<b>Теги:</b> {', '.join(tags)}"

        if trigger.get("comments"):
            message += f"\n<b>Комментарии:</b> {trigger['comments']}"

        keyboard: list[list[InlineKeyboardButton]] = []
        if zabbix_url and problem.get("eventid"):
            event_id = problem.get("eventid")
            zabbix_event_url = (
                f"{zabbix_url.rstrip('/')}/zabbix.php?action=problem.view&filter_eventids[]="
                f"{event_id}"
            )
            keyboard.append([InlineKeyboardButton("🔗 Открыть в Zabbix", url=zabbix_event_url)])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        return message, reply_markup

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start."""
        if update.message is None or update.effective_user is None:
            return

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

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help."""
        if update.message is None:
            return

        help_text = """
📋 <b>Доступные команды:</b>

/start - Начать работу с ботом
/help - Показать это сообщение
/status - Проверить статус мониторинга
/problems - Показать активные проблемы
/test - Отправить тестовое уведомление

🔔 Я автоматически отправляю уведомления о проблемах в Zabbix.
        """
        await update.message.reply_text(help_text, parse_mode="HTML")

    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /status."""
        if self.alert_monitor:
            await self.alert_monitor.send_status_message()
        elif update.message is not None:
            await update.message.reply_text("❌ Мониторинг не инициализирован.")

    async def _problems_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /problems."""
        if self.alert_monitor:
            await self.alert_monitor.send_problems_list()
        elif update.message is not None:
            await update.message.reply_text("❌ Мониторинг не инициализирован.")

    async def _test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /test."""
        if update.message is None:
            return

        test_alert = {
            "problem": {
                "eventid": "12345",
                "name": "Тестовая проблема",
                "severity": "3",
                "clock": str(int(asyncio.get_event_loop().time())),
                "r_eventid": "0",
                "tags": [{"tag": "тест", "value": "алерт"}],
            },
            "trigger": {
                "description": "Это тестовый алерт от бота мониторинга Zabbix",
                "comments": "Тестовый триггер для проверки бота",
            },
            "hosts": [{"name": "Тестовый хост", "interfaces": [{"ip": "192.168.1.100"}]}],
        }

        success = await self.send_alert(test_alert)
        if success:
            await update.message.reply_text("✅ Тестовое уведомление отправлено!")
        else:
            await update.message.reply_text("❌ Ошибка при отправке тестового уведомления.")

    async def _unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик неизвестных сообщений."""
        if update.message is None:
            return

        await update.message.reply_text(
            "🤖 Я понимаю только команды. Используйте /help для получения списка доступных команд."
        )

    async def check_connection(self) -> bool:
        """Проверяет подключение к Telegram API."""
        try:
            me = await self.bot.get_me()
            logger.info("Подключено к Telegram как @%s", me.username)
            return True
        except TelegramError as exc:
            logger.error("Не удалось подключиться к Telegram: %s", exc)
            return False
