# 🚀 Zabbix Telegram Bot

Простой и надежный бот для отправки алертов из Zabbix в Telegram. Поддерживает Docker и работает на Linux/Windows.

## ⚠️ Безопасность

**ВАЖНО:** Перед загрузкой на GitHub убедитесь, что:
- Скопировали `.env.example` в `.env` и заполнили своими данными
- Файл `.env` добавлен в `.gitignore` (уже сделано)
- В `docker-compose.yml` используются переменные окружения, а не реальные данные

## Возможности

- 🔔 **Мониторинг в реальном времени** - автоматическая проверка новых алертов
- 📊 **Детальная информация** - хост, IP, описание проблемы, серьезность, время
- 🎯 **Персональные уведомления** - отправка только определенному пользователю
- 🔧 **Интерактивные команды** - статус, тестирование, помощь
- 🛡️ **Надежность** - retry-механизмы, обработка ошибок, переподключение
- ⚡ **Современный код** - async/await, type hints, логирование
- 🎛️ **Гибкая настройка** - фильтры по серьезности, переменные окружения

## Структура проекта

```
zbxtg/
├── main.py              # Основной скрипт запуска
├── config.py            # Конфигурация и настройки
├── zabbix_client.py     # Клиент для работы с Zabbix API
├── telegram_bot.py      # Telegram бот с обработкой команд
├── alert_monitor.py     # Система мониторинга алертов
├── requirements.txt     # Зависимости Python
├── .env.example         # Пример настроек
└── README.md           # Документация
```

## Быстрый старт

### 1. Установка зависимостей

```bash
# Создание виртуального окружения
python -m venv venv

# Активация окружения
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Создание Telegram бота

1. Найдите @BotFather в Telegram
2. Создайте нового бота: `/newbot`
3. Получите токен бота
4. Узнайте свой Chat ID (можно использовать @userinfobot)

### 3. Создание API токена в Zabbix

1. Войдите в веб-интерфейс Zabbix
2. Перейдите в **Administration → API tokens**
3. Нажмите **Create API token**
4. Укажите имя токена (например: "Telegram Bot")
5. Выберите пользователя с правами на чтение проблем
6. Скопируйте созданный токен

### 4. Настройка переменных окружения

**ВАЖНО:** Не загружайте реальные данные на GitHub!

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте .env файл своими данными
nano .env
```

Заполните файл `.env` (НЕ загружается на GitHub):

```bash
# Настройки Zabbix
ZABBIX_URL=https://your-zabbix-server.com
ZABBIX_API_TOKEN=your_api_token

# Настройки Telegram  
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 5. Запуск

```bash
# Активация виртуального окружения
source venv/bin/activate

# Экспорт переменных окружения
source .env

# Запуск бота
python main.py
```

Или используйте готовый скрипт (не забудьте указать ваши настройки):
```bash
./run_example.sh
```

## Переменные окружения

### Обязательные

- `ZABBIX_URL` - URL сервера Zabbix (например: https://zabbix.company.com)
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `TELEGRAM_CHAT_ID` - ID пользователя Telegram (число)

**Аутентификация Zabbix (один из вариантов):**
- `ZABBIX_API_TOKEN` - API токен Zabbix (рекомендуется, Zabbix 5.4+)
- ИЛИ `ZABBIX_USERNAME` + `ZABBIX_PASSWORD` - логин и пароль пользователя

### Опциональные

- `POLL_INTERVAL` - интервал проверки алертов в секундах (по умолчанию: 60)
- `LOG_LEVEL` - уровень логирования: DEBUG, INFO, WARNING, ERROR (по умолчанию: INFO)
- `ZABBIX_SSL_VERIFY` - проверка SSL сертификата: true/false (по умолчанию: true)
- `MAX_RETRIES` - количество повторных попыток (по умолчанию: 3)
- `RETRY_DELAY` - задержка между попытками в секундах (по умолчанию: 5)
- `TELEGRAM_PARSE_MODE` - режим парсинга сообщений: HTML/Markdown (по умолчанию: HTML)

## Команды бота

После запуска бот поддерживает следующие команды:

- `/start` - запуск и приветствие
- `/help` - список всех команд
- `/status` - проверка статуса подключений и статистика
- `/test` - отправка тестового уведомления

## Формат уведомлений

Бот отправляет структурированные сообщения с полной информацией:

```
🚨 Zabbix Alert

🔴 High
Host: web-server-01 (192.168.1.100)
Problem: High CPU usage on web server
Description: CPU utilization is above 90% for 5 minutes
Time: 2024-01-15 14:30:25
Event ID: 12345

Status: 🔴 PROBLEM
Tags: environment:production, service:web
```

## Фильтрация алертов

По умолчанию бот отправляет алерты с уровнем серьезности "Warning" и выше:

- 🟢 Not classified (фильтруется)
- 🔵 Information (фильтруется)
- 🟡 Warning ✅
- 🟠 Average ✅
- 🔴 High ✅
- 🔥 Disaster ✅

Фильтр можно изменить в файле `alert_monitor.py`, метод `_should_send_alert()`.

## Запуск как сервис

### systemd (Linux)

Создайте файл `/etc/systemd/system/zbxtg.service`:

```ini
[Unit]
Description=Zabbix Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/zbxtg
Environment=ZABBIX_URL=https://your-zabbix.com
Environment=ZABBIX_USERNAME=your_user
Environment=ZABBIX_PASSWORD=your_password
Environment=TELEGRAM_BOT_TOKEN=your_token
Environment=TELEGRAM_CHAT_ID=your_chat_id
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск сервиса:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zbxtg
sudo systemctl start zbxtg
sudo systemctl status zbxtg
```

### Docker

Создайте `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Сборка и запуск:

```bash
docker build -t zbxtg .
docker run -d --name zbxtg \
  -e ZABBIX_URL=https://your-zabbix.com \
  -e ZABBIX_USERNAME=your_user \
  -e ZABBIX_PASSWORD=your_password \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  zbxtg
```

## Логирование

Бот ведет логи в файл `zbxtg.log` и выводит в консоль. Уровень логирования настраивается через переменную `LOG_LEVEL`.

## Безопасность

- Не коммитьте файл `.env` с реальными данными
- Используйте отдельного пользователя Zabbix с минимальными правами (только чтение проблем)
- Регулярно ротируйте пароли и токены
- Используйте HTTPS для Zabbix API

## Устранение неполадок

### Ошибки подключения к Zabbix

1. Проверьте URL и доступность сервера
2. Убедитесь в правильности учетных данных
3. Проверьте права пользователя Zabbix
4. При проблемах с SSL попробуйте `ZABBIX_SSL_VERIFY=false`

### Ошибки Telegram

1. Проверьте токен бота
2. Убедитесь, что Chat ID корректный
3. Запустите бота и отправьте ему `/start`

### Общие проблемы

- Проверьте логи в файле `zbxtg.log`
- Увеличьте уровень логирования: `LOG_LEVEL=DEBUG`
- Используйте команду `/status` для диагностики

## Разработка

Структура кода организована модульно:

- `config.py` - централизованное управление настройками
- `zabbix_client.py` - работа с Zabbix API с retry-механизмами
- `telegram_bot.py` - Telegram бот с командами и форматированием
- `alert_monitor.py` - основная логика мониторинга
- `main.py` - точка входа и оркестрация компонентов

Все компоненты используют async/await для максимальной производительности.

## Лицензия

MIT License

## Поддержка

При возникновении проблем:

1. Проверьте логи
2. Изучите документацию Zabbix API и Telegram Bot API
3. Создайте issue с подробным описанием проблемы