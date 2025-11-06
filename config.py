import os
from typing import Optional, List
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class ZabbixConfig:
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    ssl_verify: bool = True
    ssl_cert_path: Optional[str] = None


@dataclass
class TelegramConfig:
    bot_token: str
    target_chat_id: int
    parse_mode: str = "HTML"


@dataclass
class AppConfig:
    zabbix: ZabbixConfig
    telegram: TelegramConfig
    poll_interval: int = 60
    log_level: str = "INFO"
    max_retries: int = 3
    retry_delay: int = 5
    min_severity: int = 2  # Минимальная серьезность для отправки алертов (0-5)
    edit_on_update: bool = True  # Редактировать сообщения при обновлении статуса
    delete_resolved_after: int = 3600  # Удалять resolved алерты через N секунд (0 = не удалять)
    mark_resolved: bool = True  # Помечать resolved алерты вместо удаления

    # Фильтры
    host_groups: Optional[list] = None  # Группы хостов для фильтрации
    excluded_hosts: Optional[list] = None  # Исключенные хосты

    # Тихие часы
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    quiet_hours_min_severity: int = 4


def get_config() -> AppConfig:
    """Получает конфигурацию из переменных окружения"""

    # Обязательные параметры
    required_vars = {
        'ZABBIX_URL': 'URL Zabbix сервера',
        'TELEGRAM_BOT_TOKEN': 'Токен Telegram бота',
        'TELEGRAM_CHAT_ID': 'ID пользователя Telegram'
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")

    if missing_vars:
        raise ValueError(f"Отсутствуют обязательные переменные окружения:\n" +
                        "\n".join(f"- {var}" for var in missing_vars))

    # Валидация URL
    zabbix_url = os.getenv('ZABBIX_URL')
    try:
        parsed_url = urlparse(zabbix_url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValueError(f"Некорректный формат ZABBIX_URL: {zabbix_url}")
        if parsed_url.scheme not in ['http', 'https']:
            raise ValueError(f"ZABBIX_URL должен начинаться с http:// или https://")
    except Exception as e:
        raise ValueError(f"Ошибка валидации ZABBIX_URL: {e}")

    # Проверяем аутентификацию Zabbix
    api_token = os.getenv('ZABBIX_API_TOKEN')
    username = os.getenv('ZABBIX_USERNAME')
    password = os.getenv('ZABBIX_PASSWORD')

    if not api_token and not (username and password):
        raise ValueError(
            "Необходимо указать либо ZABBIX_API_TOKEN, либо ZABBIX_USERNAME и ZABBIX_PASSWORD"
        )

    # Валидация численных параметров
    try:
        poll_interval = int(os.getenv('POLL_INTERVAL', '60'))
        if poll_interval <= 0:
            raise ValueError("POLL_INTERVAL должен быть больше 0")
    except ValueError as e:
        raise ValueError(f"Некорректное значение POLL_INTERVAL: {e}")

    try:
        max_retries = int(os.getenv('MAX_RETRIES', '3'))
        if max_retries < 0:
            raise ValueError("MAX_RETRIES не может быть отрицательным")
    except ValueError as e:
        raise ValueError(f"Некорректное значение MAX_RETRIES: {e}")

    try:
        retry_delay = int(os.getenv('RETRY_DELAY', '5'))
        if retry_delay < 0:
            raise ValueError("RETRY_DELAY не может быть отрицательным")
    except ValueError as e:
        raise ValueError(f"Некорректное значение RETRY_DELAY: {e}")

    try:
        min_severity = int(os.getenv('MIN_SEVERITY', '2'))
        if not 0 <= min_severity <= 5:
            raise ValueError("MIN_SEVERITY должен быть в диапазоне 0-5")
    except ValueError as e:
        raise ValueError(f"Некорректное значение MIN_SEVERITY: {e}")

    # Валидация chat_id
    try:
        chat_id = int(os.getenv('TELEGRAM_CHAT_ID'))
    except ValueError:
        raise ValueError("TELEGRAM_CHAT_ID должен быть числом")

    # Валидация log level
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level not in valid_log_levels:
        raise ValueError(f"LOG_LEVEL должен быть одним из: {', '.join(valid_log_levels)}")

    zabbix_config = ZabbixConfig(
        url=zabbix_url,
        username=username,
        password=password,
        api_token=api_token,
        ssl_verify=os.getenv('ZABBIX_SSL_VERIFY', 'true').lower() == 'true',
        ssl_cert_path=os.getenv('ZABBIX_SSL_CERT_PATH')
    )

    telegram_config = TelegramConfig(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        target_chat_id=chat_id,
        parse_mode=os.getenv('TELEGRAM_PARSE_MODE', 'HTML')
    )

    # Параметры UX улучшений
    edit_on_update = os.getenv('EDIT_ON_UPDATE', 'true').lower() == 'true'
    mark_resolved = os.getenv('MARK_RESOLVED', 'true').lower() == 'true'

    try:
        delete_resolved_after = int(os.getenv('DELETE_RESOLVED_AFTER', '3600'))
        if delete_resolved_after < 0:
            raise ValueError("DELETE_RESOLVED_AFTER не может быть отрицательным")
    except ValueError as e:
        raise ValueError(f"Некорректное значение DELETE_RESOLVED_AFTER: {e}")

    # Фильтры
    host_groups_str = os.getenv('HOST_GROUPS', '')
    host_groups = [g.strip() for g in host_groups_str.split(',') if g.strip()] if host_groups_str else None

    excluded_hosts_str = os.getenv('EXCLUDED_HOSTS', '')
    excluded_hosts = [h.strip() for h in excluded_hosts_str.split(',') if h.strip()] if excluded_hosts_str else None

    # Тихие часы
    quiet_hours_enabled = os.getenv('QUIET_HOURS_ENABLED', 'false').lower() == 'true'
    quiet_hours_start = os.getenv('QUIET_HOURS_START', '22:00')
    quiet_hours_end = os.getenv('QUIET_HOURS_END', '08:00')

    try:
        quiet_hours_min_severity = int(os.getenv('QUIET_HOURS_MIN_SEVERITY', '4'))
        if not 0 <= quiet_hours_min_severity <= 5:
            raise ValueError("QUIET_HOURS_MIN_SEVERITY должен быть в диапазоне 0-5")
    except ValueError as e:
        raise ValueError(f"Некорректное значение QUIET_HOURS_MIN_SEVERITY: {e}")

    return AppConfig(
        zabbix=zabbix_config,
        telegram=telegram_config,
        poll_interval=poll_interval,
        log_level=log_level,
        max_retries=max_retries,
        retry_delay=retry_delay,
        min_severity=min_severity,
        edit_on_update=edit_on_update,
        delete_resolved_after=delete_resolved_after,
        mark_resolved=mark_resolved,
        host_groups=host_groups,
        excluded_hosts=excluded_hosts,
        quiet_hours_enabled=quiet_hours_enabled,
        quiet_hours_start=quiet_hours_start,
        quiet_hours_end=quiet_hours_end,
        quiet_hours_min_severity=quiet_hours_min_severity,
    )