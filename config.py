import os
from typing import Optional
from dataclasses import dataclass


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
    
    # Проверяем аутентификацию Zabbix
    api_token = os.getenv('ZABBIX_API_TOKEN')
    username = os.getenv('ZABBIX_USERNAME')
    password = os.getenv('ZABBIX_PASSWORD')
    
    if not api_token and not (username and password):
        raise ValueError(
            "Необходимо указать либо ZABBIX_API_TOKEN, либо ZABBIX_USERNAME и ZABBIX_PASSWORD"
        )
    
    zabbix_config = ZabbixConfig(
        url=os.getenv('ZABBIX_URL'),
        username=username,
        password=password,
        api_token=api_token,
        ssl_verify=os.getenv('ZABBIX_SSL_VERIFY', 'true').lower() == 'true',
        ssl_cert_path=os.getenv('ZABBIX_SSL_CERT_PATH')
    )
    
    telegram_config = TelegramConfig(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        target_chat_id=int(os.getenv('TELEGRAM_CHAT_ID')),
        parse_mode=os.getenv('TELEGRAM_PARSE_MODE', 'HTML')
    )
    
    return AppConfig(
        zabbix=zabbix_config,
        telegram=telegram_config,
        poll_interval=int(os.getenv('POLL_INTERVAL', '60')),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        max_retries=int(os.getenv('MAX_RETRIES', '3')),
        retry_delay=int(os.getenv('RETRY_DELAY', '5'))
    )