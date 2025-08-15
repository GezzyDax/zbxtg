# 🚀 Zabbix Telegram Bot

Современный бот для автоматической отправки алертов из Zabbix в Telegram. Поддерживает Docker, работает на Linux и Windows, обеспечивает безопасную конфигурацию через переменные окружения.

## ✨ Ключевые возможности

- 🔔 **Мониторинг в реальном времени** - автоматическое отслеживание новых проблем в Zabbix
- 📱 **Instant уведомления** - мгновенная доставка алертов в Telegram
- 🐳 **Docker Ready** - готовые образы и скрипты для Linux/Windows
- 🔒 **Безопасность** - поддержка SSL, включая самоподписанные сертификаты
- 🎯 **Персонализация** - отправка уведомлений конкретному пользователю
- 🛠️ **Интерактивность** - команды управления прямо в Telegram
- ⚡ **Производительность** - асинхронная архитектура на Python 3.8+
- 🔧 **Настраиваемость** - фильтры по серьезности, интервалы опроса

## 🚀 Быстрый старт с Docker (рекомендуется)

### 1. Клонирование и настройка

```bash
git clone https://github.com/GezzyDax/zbxtg.git
cd zbxtg

# Создайте файл конфигурации
cp .env.example .env
```

### 2. Заполните конфигурацию в `.env`:

```env
# Настройки Zabbix
ZABBIX_URL=https://your-zabbix-server.com
ZABBIX_API_TOKEN=your_api_token_here

# Настройки Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Запуск в Docker

#### Linux:
```bash
# Сборка и запуск
./docker-run.sh start

# Просмотр логов
./docker-run.sh logs

# Остановка
./docker-run.sh stop
```

#### Windows (PowerShell):
```powershell
# Сборка и запуск
.\docker-run.ps1 start

# Просмотр логов
.\docker-run.ps1 logs

# Остановка
.\docker-run.ps1 stop
```

#### Windows (Batch):
```cmd
# Сборка и запуск
docker-run.bat start

# Просмотр логов
docker-run.bat logs
```

#### Ручной запуск Docker:
```bash
# Сборка
docker-compose build

# Запуск
docker-compose up -d

# Логи
docker-compose logs -f
```

## 📋 Настройка Telegram бота и Zabbix

### Создание Telegram бота

1. Найдите @BotFather в Telegram
2. Создайте нового бота: `/newbot`
3. Получите токен бота
4. Узнайте свой Chat ID:
   - Отправьте `/start` вашему боту
   - Посмотрите в логах: "Received message from chat_id: XXXXXX"
   - Или используйте @userinfobot

### Создание API токена в Zabbix

1. Войдите в веб-интерфейс Zabbix
2. Перейдите в **Administration → API tokens**
3. Нажмите **Create API token**
4. Укажите имя токена (например: "Telegram Bot")
5. Выберите пользователя с правами на чтение проблем
6. Скопируйте созданный токен

## 🐍 Запуск без Docker

### Требования
- Python 3.8+
- pip

### Установка и запуск

```bash
# Клонирование репозитория
git clone https://github.com/GezzyDax/zbxtg.git
cd zbxtg

# Создание виртуального окружения
python -m venv venv

# Активация окружения
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp .env.example .env
# Отредактируйте .env файл

# Запуск бота
python main.py
```

## ⚙️ Конфигурация

### Обязательные параметры

| Параметр | Описание | Пример |
|----------|----------|--------|
| `ZABBIX_URL` | URL сервера Zabbix | `https://zabbix.company.com` |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | `123456:ABC-DEF1234ghIkl` |
| `TELEGRAM_CHAT_ID` | ID чата для уведомлений | `123456789` |

### Аутентификация в Zabbix (выберите один вариант)

**Вариант 1: API Token (рекомендуется)**
```env
ZABBIX_API_TOKEN=your_api_token_here
```

**Вариант 2: Логин/пароль**
```env
ZABBIX_USERNAME=your_username
ZABBIX_PASSWORD=your_password
```

### Дополнительные параметры

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `POLL_INTERVAL` | `60` | Интервал проверки алертов (сек) |
| `LOG_LEVEL` | `INFO` | Уровень логирования (DEBUG/INFO/WARNING/ERROR) |
| `ZABBIX_SSL_VERIFY` | `true` | Проверка SSL сертификата |
| `MAX_RETRIES` | `3` | Количество повторных попыток |
| `RETRY_DELAY` | `5` | Задержка между попытками (сек) |

## 🔒 SSL Сертификаты (для самоподписанных)

Если ваш Zabbix использует самоподписанные сертификаты:

### 1. Поместите сертификаты в папку `ssl-certs/`:
```
zbxtg/
└── ssl-certs/
    ├── your-server.crt
    └── your-ca.crt
```

### 2. Установите переменную:
```env
ZABBIX_SSL_VERIFY=true
```

### 3. Пересоберите Docker образ:
```bash
./docker-run.sh build
```

## 🤖 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запуск и приветствие |
| `/help` | Список всех команд |
| `/status` | Статус подключений к Zabbix и Telegram |
| `/problems` | Список текущих проблем в Zabbix |

## 📨 Формат уведомлений

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

## 🎛️ Фильтрация алертов

По умолчанию отправляются алерты с уровнем "Warning" и выше:

| Уровень | Отправка | Эмодзи |
|---------|----------|--------|
| Not classified | ❌ | 🟢 |
| Information | ❌ | 🔵 |
| Warning | ✅ | 🟡 |
| Average | ✅ | 🟠 |
| High | ✅ | 🔴 |
| Disaster | ✅ | 🔥 |

## 📊 Мониторинг и логи

### Просмотр логов

```bash
# Docker - все логи
./docker-run.sh logs

# Docker - логи в реальном времени
./docker-run.sh logs -f

# Локальные логи
tail -f logs/zbxtg.log
```

### Статус контейнера

```bash
# Статус Docker контейнера
./docker-run.sh status

# Или напрямую
docker-compose ps
```

## 🚀 Запуск как сервис

### systemd (Linux)

```bash
# Создайте сервис файл
sudo tee /etc/systemd/system/zbxtg.service << EOF
[Unit]
Description=Zabbix Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/zbxtg
EnvironmentFile=/path/to/zbxtg/.env
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск
sudo systemctl daemon-reload
sudo systemctl enable zbxtg
sudo systemctl start zbxtg
```

### Docker Compose как сервис

```bash
# Автозапуск Docker контейнера
docker-compose up -d --restart unless-stopped
```

## 🔧 Troubleshooting

### Проблемы с Zabbix

| Проблема | Решение |
|----------|---------|
| SSL certificate verify failed | Добавьте сертификаты в `ssl-certs/` или `ZABBIX_SSL_VERIFY=false` |
| Authentication failed | Проверьте API токен или логин/пароль |
| Connection refused | Проверьте URL и доступность Zabbix API |

### Проблемы с Telegram

| Проблема | Решение |
|----------|---------|
| Bot token invalid | Проверьте токен у @BotFather |
| Chat not found | Отправьте `/start` боту и найдите Chat ID в логах |
| Network error | Проверьте интернет соединение |

### Отладка

```bash
# Включите подробные логи
echo "LOG_LEVEL=DEBUG" >> .env

# Перезапустите бота
./docker-run.sh restart

# Смотрите логи
./docker-run.sh logs
```

## 🏗️ Архитектура проекта

```
zbxtg/
├── 📄 main.py              # Точка входа приложения
├── ⚙️ config.py            # Управление конфигурацией
├── 🔌 zabbix_client.py     # Клиент Zabbix API
├── 🤖 telegram_bot.py      # Telegram бот
├── 📡 alert_monitor.py     # Мониторинг алертов
├── 🐳 Dockerfile          # Образ Docker
├── 🐳 docker-compose.yml  # Оркестрация Docker
├── 📋 requirements.txt    # Python зависимости
├── 📁 ssl-certs/          # SSL сертификаты
├── 📁 logs/               # Файлы логов
└── 📜 .env                # Конфигурация (не в git)
```

## 🤝 Поддержка

**Возникли проблемы?**

1. 📋 Проверьте логи: `./docker-run.sh logs`
2. 🔍 Включите DEBUG: `LOG_LEVEL=DEBUG`
3. 🤖 Используйте `/status` в Telegram
4. 📝 Создайте [Issue](https://github.com/GezzyDax/zbxtg/issues) с описанием

## 📜 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

⭐ **Если проект помог - поставьте звездочку на GitHub!**