#!/bin/bash
# Пример запуска Zabbix Telegram Bot
# ВАЖНО: Не используйте этот файл с реальными данными на GitHub!

# Активируем виртуальное окружение
source venv/bin/activate

# Загружаем переменные из .env файла
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "✅ Загружены настройки из .env файла"
else
    echo "❌ Файл .env не найден!"
    echo "Скопируйте .env.example в .env и заполните своими данными:"
    echo "cp .env.example .env"
    exit 1
fi

echo "Starting Zabbix Telegram Bot..."
echo "Zabbix URL: $ZABBIX_URL"
echo "Chat ID: $TELEGRAM_CHAT_ID"
echo "Poll interval: ${POLL_INTERVAL:-60} seconds"
echo ""

# Запуск бота
python main.py