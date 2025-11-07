#!/bin/bash
# Скрипт быстрой установки Zabbix Telegram Bot одной командой
# Принимает минимум параметров для максимально быстрого старта

set -e

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

echo ""
echo -e "${BLUE}⚡ Zabbix Telegram Bot - Быстрый старт v$VERSION${NC}"
echo ""

# Проверка параметров
if [[ $# -lt 4 ]]; then
    echo -e "${YELLOW}Быстрая установка с минимальными параметрами${NC}"
    echo ""
    echo "Использование:"
    echo "  $0 <zabbix-url> <zabbix-token> <telegram-token> <telegram-chat-id>"
    echo ""
    echo "Пример:"
    echo "  $0 https://zabbix.company.com YOUR_API_TOKEN 123456:ABC-DEF 123456789"
    echo ""
    echo "Дополнительно:"
    echo "  Для полной настройки используйте: ./install.sh --help"
    echo ""
    exit 1
fi

ZABBIX_URL="$1"
ZABBIX_TOKEN="$2"
TELEGRAM_TOKEN="$3"
TELEGRAM_CHAT_ID="$4"

echo -e "${BLUE}📋 Параметры:${NC}"
echo "  Zabbix:   $ZABBIX_URL"
echo "  Telegram: Chat ID $TELEGRAM_CHAT_ID"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не найден. Установите Docker для продолжения.${NC}"
    exit 1
fi

# Создание директорий
echo -e "${BLUE}1. Создание директорий...${NC}"
mkdir -p logs data ssl-certs
chmod 755 logs data ssl-certs
echo -e "${GREEN}✅${NC}"

# Создание .env
echo -e "${BLUE}2. Создание конфигурации...${NC}"
cat > .env << EOF
# Quick Start Configuration
# Created: $(date)

ZABBIX_URL=$ZABBIX_URL
ZABBIX_API_TOKEN=$ZABBIX_TOKEN
ZABBIX_SSL_VERIFY=true

TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID

POLL_INTERVAL=60
MIN_SEVERITY=2
LOG_LEVEL=INFO
MAX_RETRIES=3
RETRY_DELAY=5

EDIT_ON_UPDATE=true
DELETE_RESOLVED_AFTER=3600
MARK_RESOLVED=true

METRICS_ENABLED=true
METRICS_PORT=9090
JSON_LOGGING=false
DATABASE_PATH=data/alerts.db
EOF
echo -e "${GREEN}✅${NC}"

# Запуск
echo -e "${BLUE}3. Сборка и запуск...${NC}"
if [[ -f "docker-run.sh" ]]; then
    ./docker-run.sh build
    ./docker-run.sh start
else
    docker-compose build
    docker-compose up -d
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   🎉 Готово! Бот запущен!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Что дальше:${NC}"
echo "  1. Отправьте /start боту в Telegram"
echo "  2. Проверьте логи: ./docker-run.sh logs"
echo "  3. Проверьте статус: /status в Telegram"
echo ""
echo -e "${BLUE}Команды управления:${NC}"
echo "  Логи:       ./docker-run.sh logs"
echo "  Остановка:  ./docker-run.sh stop"
echo "  Перезапуск: ./docker-run.sh restart"
echo "  Статус:     ./docker-run.sh status"
echo ""
