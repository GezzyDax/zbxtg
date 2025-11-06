"""Фильтры для алертов (по группам хостов, времени, и т.д.)."""

import logging
from datetime import datetime, time as dt_time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertFilters:
    """Класс для фильтрации алертов."""

    def __init__(
        self,
        min_severity: int = 2,
        host_groups: Optional[List[str]] = None,
        excluded_hosts: Optional[List[str]] = None,
        quiet_hours_enabled: bool = False,
        quiet_hours_start: str = "22:00",
        quiet_hours_end: str = "08:00",
        quiet_hours_min_severity: int = 4,
    ):
        self.min_severity = min_severity
        self.host_groups = host_groups or []
        self.excluded_hosts = excluded_hosts or []
        self.quiet_hours_enabled = quiet_hours_enabled
        self.quiet_hours_start = self._parse_time(quiet_hours_start)
        self.quiet_hours_end = self._parse_time(quiet_hours_end)
        self.quiet_hours_min_severity = quiet_hours_min_severity

    @staticmethod
    def _parse_time(time_str: str) -> dt_time:
        """Парсит строку времени в объект time."""
        try:
            hour, minute = map(int, time_str.split(":"))
            return dt_time(hour, minute)
        except Exception as e:
            logger.error(f"Failed to parse time '{time_str}': {e}")
            return dt_time(0, 0)

    def is_in_quiet_hours(self) -> bool:
        """Проверяет, находимся ли мы в тихих часах."""
        if not self.quiet_hours_enabled:
            return False

        now = datetime.now().time()

        # Если quiet hours переходят через полночь
        if self.quiet_hours_start > self.quiet_hours_end:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
        else:
            return self.quiet_hours_start <= now <= self.quiet_hours_end

    def should_send_alert(self, problem_details: Dict[str, Any]) -> bool:
        """Определяет, нужно ли отправлять алерт."""
        problem = problem_details.get("problem", {})
        hosts = problem_details.get("hosts", [])

        # Фильтр по серьезности
        severity = int(problem.get("severity", 0))

        # В тихие часы применяем повышенный порог серьезности
        if self.is_in_quiet_hours():
            if severity < self.quiet_hours_min_severity:
                logger.debug(
                    f"Alert filtered during quiet hours: severity {severity} < {self.quiet_hours_min_severity}"
                )
                return False
        else:
            if severity < self.min_severity:
                logger.debug(
                    f"Alert filtered by severity: {severity} < {self.min_severity}"
                )
                return False

        # Фильтр по статусу (только активные проблемы)
        if problem.get("r_eventid", "0") != "0":
            logger.debug("Alert filtered: problem is resolved")
            return False

        # Фильтр по группам хостов
        if self.host_groups:
            host_in_allowed_group = False
            for host in hosts:
                host_groups = host.get("groups", [])
                for group in host_groups:
                    if group.get("name") in self.host_groups:
                        host_in_allowed_group = True
                        break
                if host_in_allowed_group:
                    break

            if not host_in_allowed_group:
                logger.debug(
                    f"Alert filtered: host not in allowed groups {self.host_groups}"
                )
                return False

        # Фильтр исключенных хостов
        if self.excluded_hosts:
            for host in hosts:
                host_name = host.get("host", "")
                if host_name in self.excluded_hosts:
                    logger.debug(f"Alert filtered: host '{host_name}' is excluded")
                    return False

        return True

    def get_filter_summary(self) -> str:
        """Возвращает краткое описание настроенных фильтров."""
        summary = []

        summary.append(f"Минимальная серьезность: {self.min_severity}")

        if self.host_groups:
            summary.append(f"Группы хостов: {', '.join(self.host_groups)}")

        if self.excluded_hosts:
            summary.append(f"Исключенные хосты: {', '.join(self.excluded_hosts)}")

        if self.quiet_hours_enabled:
            summary.append(
                f"Тихие часы: {self.quiet_hours_start.strftime('%H:%M')} - "
                f"{self.quiet_hours_end.strftime('%H:%M')} "
                f"(мин. серьезность: {self.quiet_hours_min_severity})"
            )

        return "\n".join(summary)


def create_filters_from_config(config) -> AlertFilters:
    """Создает объект фильтров из конфигурации."""
    return AlertFilters(
        min_severity=config.min_severity,
        host_groups=config.host_groups if hasattr(config, "host_groups") else None,
        excluded_hosts=config.excluded_hosts
        if hasattr(config, "excluded_hosts")
        else None,
        quiet_hours_enabled=config.quiet_hours_enabled
        if hasattr(config, "quiet_hours_enabled")
        else False,
        quiet_hours_start=config.quiet_hours_start
        if hasattr(config, "quiet_hours_start")
        else "22:00",
        quiet_hours_end=config.quiet_hours_end
        if hasattr(config, "quiet_hours_end")
        else "08:00",
        quiet_hours_min_severity=config.quiet_hours_min_severity
        if hasattr(config, "quiet_hours_min_severity")
        else 4,
    )
