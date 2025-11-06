import asyncio
import logging
import time
from typing import Set, Dict, Any, List
from datetime import datetime, timedelta
from zabbix_client import ZabbixClient, ZabbixAPIError
from telegram_bot import TelegramBot
from config import AppConfig


logger = logging.getLogger(__name__)


class AlertMonitor:
    """Монитор алертов Zabbix"""
    
    def __init__(self, config: AppConfig, zabbix_client: ZabbixClient, telegram_bot: TelegramBot):
        self.config = config
        self.zabbix_client = zabbix_client
        self.telegram_bot = telegram_bot

        # Отслеживание отправленных алертов с временем
        self.sent_alerts: Dict[str, float] = {}  # event_id -> timestamp
        self.last_check_time = 0
        self.is_running = False

        # Очередь неотправленных алертов (graceful degradation)
        self.failed_alerts: List[Dict[str, Any]] = []

        # Статистика
        self.stats = {
            "total_checks": 0,
            "problems_found": 0,
            "alerts_sent": 0,
            "errors": 0,
            "last_error": None,
            "start_time": None
        }
    
    async def start_monitoring(self):
        """Запускает мониторинг алертов"""
        self.is_running = True
        self.stats["start_time"] = datetime.now()
        self.last_check_time = int(time.time()) - self.config.poll_interval
        
        logger.info(f"Starting alert monitoring with {self.config.poll_interval}s interval")
        
        while self.is_running:
            try:
                await self._check_for_alerts()
                self.stats["total_checks"] += 1

                # Попытка отправить неудавшиеся алерты
                await self._retry_failed_alerts()
                
            except Exception as e:
                self.stats["errors"] += 1
                self.stats["last_error"] = str(e)
                logger.error(f"Error during alert check: {e}")
                
                # Попытка переподключения к Zabbix
                if isinstance(e, ZabbixAPIError):
                    logger.info("Attempting to reconnect to Zabbix...")
                    try:
                        await asyncio.to_thread(self.zabbix_client.check_connection)
                    except Exception as reconnect_error:
                        logger.error(f"Failed to reconnect to Zabbix: {reconnect_error}")
            
            # Ждем до следующей проверки
            if self.is_running:
                await asyncio.sleep(self.config.poll_interval)
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        logger.info("Alert monitoring stopped")
    
    async def _check_for_alerts(self):
        """Проверяет новые алерты"""
        try:
            # Получаем проблемы из Zabbix
            problems = await asyncio.to_thread(self.zabbix_client.get_problems, 50)
            
            if not problems:
                logger.debug("No problems found in Zabbix")
                return
            
            self.stats["problems_found"] += len(problems)
            new_problems = []
            
            for problem in problems:
                problem_id = problem.get("eventid")
                if not problem_id:
                    continue
                
                # Проверяем, не отправляли ли мы уже этот алерт
                if problem_id in self.sent_alerts:
                    continue
                
                # Проверяем время события (отправляем только новые события)
                event_time = int(problem.get("clock", 0))
                if event_time <= self.last_check_time:
                    continue
                
                new_problems.append(problem)
            
            if new_problems:
                logger.info(f"Found {len(new_problems)} new problems")
                
                # Обрабатываем новые проблемы
                for problem in new_problems:
                    await self._process_problem(problem)
            
            # Обновляем время последней проверки
            self.last_check_time = int(time.time())
            
            # Очищаем старые алерты из памяти (старше 24 часов)
            await self._cleanup_old_alerts()
            
        except Exception as e:
            logger.error(f"Error checking for alerts: {e}")
            raise
    
    async def _process_problem(self, problem: Dict[str, Any]):
        """Обрабатывает отдельную проблему"""
        try:
            problem_id = problem.get("eventid")
            
            # Получаем детальную информацию о проблеме
            problem_details = await asyncio.to_thread(
                self.zabbix_client.get_problem_details, 
                problem
            )
            
            # Применяем фильтры (при необходимости)
            if not self._should_send_alert(problem_details):
                logger.debug(f"Alert {problem_id} filtered out")
                return
            
            # Отправляем алерт
            success = await self.telegram_bot.send_alert(problem_details)

            if success:
                self.sent_alerts[problem_id] = time.time()
                self.stats["alerts_sent"] += 1
                logger.info(f"Alert {problem_id} sent successfully")
            else:
                logger.error(f"Failed to send alert {problem_id}")
                # Сохраняем неотправленный алерт для повторной попытки
                self.failed_alerts.append({
                    "problem_details": problem_details,
                    "timestamp": time.time(),
                    "attempts": 1
                })
                logger.info(f"Alert {problem_id} added to retry queue")
                
        except Exception as e:
            logger.error(f"Error processing problem {problem.get('eventid', 'unknown')}: {e}")
            raise
    
    def _should_send_alert(self, problem_details: Dict[str, Any]) -> bool:
        """Определяет, нужно ли отправлять алерт"""
        problem = problem_details.get("problem", {})

        # Фильтр по серьезности (настраивается через MIN_SEVERITY)
        severity = int(problem.get("severity", 0))

        if severity < self.config.min_severity:
            logger.debug(f"Alert filtered: severity {severity} < min {self.config.min_severity}")
            return False
        
        # Фильтр по статусу (только активные проблемы)
        if problem.get("r_eventid", "0") != "0":
            return False  # Проблема уже решена
        
        # Можно добавить дополнительные фильтры:
        # - по тегам
        # - по именам хостов  
        # - по времени дня
        # - по группам хостов
        
        return True
    
    async def _cleanup_old_alerts(self):
        """Очищает старые алерты из памяти"""
        if len(self.sent_alerts) > 1000:  # Лимит для предотвращения роста памяти
            try:
                current_time = time.time()
                old_threshold = current_time - (24 * 3600)  # 24 часа

                # Очищаем алерты старше 24 часов
                old_alerts = [
                    event_id for event_id, timestamp in self.sent_alerts.items()
                    if timestamp < old_threshold
                ]

                for event_id in old_alerts:
                    del self.sent_alerts[event_id]

                if old_alerts:
                    logger.debug(f"Cleaned up {len(old_alerts)} old alerts from memory")

            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    async def _retry_failed_alerts(self):
        """Повторная попытка отправки неудавшихся алертов"""
        if not self.failed_alerts:
            return

        logger.info(f"Retrying {len(self.failed_alerts)} failed alerts...")
        still_failed = []

        for alert_info in self.failed_alerts:
            problem_details = alert_info["problem_details"]
            attempts = alert_info["attempts"]
            problem_id = problem_details.get("problem", {}).get("eventid")

            # Максимум 5 попыток
            if attempts >= 5:
                logger.warning(f"Alert {problem_id} exceeded max retry attempts, dropping")
                continue

            success = await self.telegram_bot.send_alert(problem_details)

            if success:
                self.sent_alerts[problem_id] = time.time()
                self.stats["alerts_sent"] += 1
                logger.info(f"Alert {problem_id} sent successfully on retry #{attempts}")
            else:
                alert_info["attempts"] += 1
                still_failed.append(alert_info)
                logger.debug(f"Alert {problem_id} still failed (attempt #{attempts + 1})")

        self.failed_alerts = still_failed
        logger.debug(f"{len(self.failed_alerts)} alerts still in retry queue")

    async def get_status(self) -> Dict[str, Any]:
        """Возвращает статус мониторинга"""
        status = {
            "running": self.is_running,
            "stats": self.stats.copy(),
            "sent_alerts_count": len(self.sent_alerts),
            "failed_alerts_count": len(self.failed_alerts),
            "last_check_time": datetime.fromtimestamp(self.last_check_time).isoformat() if self.last_check_time else None
        }
        
        # Добавляем uptime
        if self.stats["start_time"]:
            uptime = datetime.now() - self.stats["start_time"]
            status["uptime_seconds"] = int(uptime.total_seconds())
            status["uptime_str"] = str(uptime).split('.')[0]  # Убираем микросекунды
        
        # Проверяем подключения
        try:
            # Простая проверка через API call без auth
            await asyncio.to_thread(self.zabbix_client._make_request, "apiinfo.version", None, True)
            status["zabbix_connected"] = True
        except Exception as e:
            logger.debug(f"Zabbix connection check failed: {e}")
            status["zabbix_connected"] = False
            
        try:
            telegram_connected = await self.telegram_bot.check_connection()
            status["telegram_connected"] = telegram_connected
        except Exception:
            status["telegram_connected"] = False
        
        return status
    
    async def send_status_message(self):
        """Отправляет сообщение со статусом в Telegram"""
        try:
            status = await self.get_status()
            
            message = f"""
📊 <b>Zabbix Monitor Status</b>

🔄 <b>Monitoring:</b> {"✅ Running" if status["running"] else "❌ Stopped"}
⏱ <b>Uptime:</b> {status.get("uptime_str", "N/A")}

📡 <b>Connections:</b>
- Zabbix: {"✅" if status["zabbix_connected"] else "❌"}
- Telegram: {"✅" if status["telegram_connected"] else "❌"}

📈 <b>Statistics:</b>
- Total checks: {status["stats"]["total_checks"]}
- Problems found: {status["stats"]["problems_found"]}
- Alerts sent: {status["stats"]["alerts_sent"]}
- Errors: {status["stats"]["errors"]}

💾 <b>Memory:</b> {status["sent_alerts_count"]} tracked alerts
🔄 <b>Retry queue:</b> {status["failed_alerts_count"]} pending
            """.strip()
            
            if status["stats"]["last_error"]:
                message += f"\n\n❌ <b>Last error:</b> {status['stats']['last_error']}"
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send status message: {e}")
    
    async def send_problems_list(self):
        """Отправляет список активных проблем в Telegram"""
        try:
            problems = await asyncio.to_thread(self.zabbix_client.get_problems, 20)
            
            if not problems:
                message = "✅ <b>Активных проблем не найдено</b>"
            else:
                message = f"🚨 <b>Активные проблемы ({len(problems)}):</b>\n\n"
                
                for i, problem in enumerate(problems[:10], 1):  # Показываем максимум 10
                    severity_icons = {
                        "0": "🔵",  # Not classified
                        "1": "🟦",  # Information
                        "2": "🟡",  # Warning
                        "3": "🟠",  # Average
                        "4": "🔴",  # High
                        "5": "🔥"   # Disaster
                    }
                    
                    severity = problem.get("severity", "0")
                    icon = severity_icons.get(severity, "❗")
                    
                    # Получаем детали проблемы
                    details = await asyncio.to_thread(self.zabbix_client.get_problem_details, problem)
                    hosts = details.get("hosts", [])
                    host_name = hosts[0].get("name", "Unknown") if hosts else "Unknown"
                    
                    # Форматируем время
                    try:
                        timestamp = int(problem.get("clock", 0))
                        problem_time = datetime.fromtimestamp(timestamp)
                        time_str = problem_time.strftime("%d.%m %H:%M")
                    except:
                        time_str = "Unknown"
                    
                    message += f"{icon} <b>{problem.get('name', 'Unknown')}</b>\n"
                    message += f"   📍 Host: {host_name}\n"
                    message += f"   ⏰ Time: {time_str}\n\n"
                
                if len(problems) > 10:
                    message += f"... и еще {len(problems) - 10} проблем"
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send problems list: {e}")
            await self.telegram_bot.send_message("❌ Ошибка при получении списка проблем")