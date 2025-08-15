# 🪟 Zabbix Telegram Bot - Windows Docker

Этот документ описывает как запустить Zabbix Telegram Bot в Docker на Windows.

## Предварительные требования

1. **Docker Desktop for Windows** - [Скачать](https://docs.docker.com/desktop/windows/install/)
2. **Windows 10/11** с поддержкой WSL2 (рекомендуется)

## Быстрый старт

### Вариант 1: PowerShell (рекомендуется)

1. **Откройте PowerShell от администратора**

2. **Настройте переменные окружения** в `docker-compose.yml`:
   ```yaml
   environment:
     - ZABBIX_URL=https://your-zabbix-server.com
     - ZABBIX_API_TOKEN=your_api_token
     - TELEGRAM_BOT_TOKEN=your_bot_token
     - TELEGRAM_CHAT_ID=your_chat_id
   ```

3. **Запустите бот**:
   ```powershell
   .\docker-run.ps1 start
   ```

### Вариант 2: Batch файл

1. **Откройте командную строку от администратора**

2. **Настройте docker-compose.yml** (как выше)

3. **Запустите бот**:
   ```cmd
   docker-run.bat start
   ```

## Управление

### PowerShell команды

```powershell
.\docker-run.ps1 start    # Запустить бот
.\docker-run.ps1 stop     # Остановить бот  
.\docker-run.ps1 restart  # Перезапустить бот
.\docker-run.ps1 logs     # Показать логи
.\docker-run.ps1 status   # Статус контейнера
.\docker-run.ps1 build    # Пересобрать образ
.\docker-run.ps1 shell    # Войти в контейнер
.\docker-run.ps1 clean    # Очистить контейнеры
```

### Batch команды

```cmd
docker-run.bat start    # Запустить бот
docker-run.bat stop     # Остановить бот  
docker-run.bat restart  # Перезапустить бот
docker-run.bat logs     # Показать логи
docker-run.bat status   # Статус контейнера
```

## Переменные окружения

Редактируйте файл `docker-compose.yml`:

### Обязательные
```yaml
- ZABBIX_URL=https://your-zabbix-server.com
- ZABBIX_API_TOKEN=your_api_token
- TELEGRAM_BOT_TOKEN=your_bot_token
- TELEGRAM_CHAT_ID=your_chat_id
```

### Дополнительные
```yaml
- ZABBIX_SSL_VERIFY=true      # Проверка SSL
- POLL_INTERVAL=60            # Интервал проверки (сек)
- LOG_LEVEL=INFO              # Уровень логирования
- MAX_RETRIES=3               # Количество повторов
```

## SSL Сертификаты на Windows

Если используете самоподписанные сертификаты:

1. **Поместите сертификаты в папку `ssl-certs/`**:
   ```
   zbxtg/
   ├── ssl-certs/
   │   ├── your-server.crt
   │   └── your-ca.crt
   └── docker-compose.yml
   ```

2. **Установите `ZABBIX_SSL_VERIFY=true`**

3. **Пересоберите образ**:
   ```powershell
   .\docker-run.ps1 build
   ```

## Логи на Windows

Логи сохраняются в папке `logs/`:

```powershell
# Просмотр логов в реальном времени
.\docker-run.ps1 logs

# Просмотр файла логов
Get-Content logs\zbxtg.log -Tail 50 -Wait

# Открыть папку с логами
explorer logs
```

## Troubleshooting Windows

### Проблема: Docker не запускается

**Решение:**
1. Убедитесь что Docker Desktop запущен
2. Включите WSL2 в настройках Docker Desktop
3. Перезапустите Docker Desktop

### Проблема: "execution policy" в PowerShell

**Решение:**
```powershell
# Разрешить выполнение скриптов (от администратора)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Или запускайте так:
powershell -ExecutionPolicy Bypass -File .\docker-run.ps1 start
```

### Проблема: "docker-compose not found"

**Решение:**
1. Обновите Docker Desktop до последней версии
2. Или установите docker-compose отдельно:
   ```powershell
   # Через Chocolatey
   choco install docker-compose
   
   # Или через pip
   pip install docker-compose
   ```

### Проблема: Медленная работа контейнеров

**Решение:**
1. В Docker Desktop Settings → Resources → WSL Integration
2. Включите интеграцию с WSL2
3. Увеличьте выделенную память (4GB+)

### Проблема: Проблемы с кодировкой в логах

**Решение:**
```cmd
# В командной строке
chcp 65001

# Или используйте PowerShell вместо cmd
```

## Автозапуск на Windows

### Создание службы Windows

1. **Создайте task в Task Scheduler**:
   - Откройте `taskschd.msc`
   - Create Basic Task
   - Trigger: At startup
   - Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-WindowStyle Hidden -File "C:\path\to\zbxtg\docker-run.ps1" start`

### Автозапуск через реестр

```powershell
# Добавить в автозагрузку
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$scriptPath = "powershell.exe -WindowStyle Hidden -File `"$PWD\docker-run.ps1`" start"
Set-ItemProperty -Path $regPath -Name "ZabbixTelegramBot" -Value $scriptPath
```

## Мониторинг

### Через Docker Desktop

1. Откройте Docker Desktop
2. Перейдите в Containers
3. Найдите `zabbix-telegram-bot`
4. Кликните для просмотра логов и статистики

### Через Windows Performance Monitor

Добавьте счетчики Docker контейнеров для мониторинга ресурсов.

## Обновление

```powershell
# Остановить
.\docker-run.ps1 stop

# Обновить код и пересобрать
git pull  # если используете git
.\docker-run.ps1 build

# Запустить
.\docker-run.ps1 start
```

## Полезные команды Windows

```powershell
# Просмотр запущенных контейнеров
docker ps

# Просмотр всех контейнеров
docker ps -a

# Просмотр образов
docker images

# Очистка системы Docker
docker system prune -a

# Просмотр использования ресурсов
docker stats
```