#!/bin/bash
# Интерактивный скрипт установки Zabbix Telegram Bot
# Поддерживает как интерактивный режим, так и передачу параметров через командную строку

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Читаем версию
VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Zabbix Telegram Bot - Установка v$VERSION   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Функция для проверки команд
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Функция для вывода справки
show_help() {
    cat << EOF
Использование: $0 [OPTIONS]

Интерактивный установщик Zabbix Telegram Bot.
Если параметры не указаны, установщик запросит их интерактивно.

Опции:
  -h, --help                     Показать эту справку
  -v, --version                  Показать версию

  Обязательные параметры:
  --zabbix-url URL              URL сервера Zabbix
  --telegram-token TOKEN        Токен Telegram бота
  --telegram-chat-id ID         ID чата Telegram

  Аутентификация Zabbix (выберите один вариант):
  --zabbix-token TOKEN          API токен Zabbix (рекомендуется)
  --zabbix-user USER            Имя пользователя Zabbix
  --zabbix-password PASS        Пароль пользователя Zabbix

  Дополнительные параметры:
  --poll-interval SECONDS       Интервал проверки (по умолчанию: 60)
  --min-severity LEVEL          Минимальная серьезность (0-5, по умолчанию: 2)
  --log-level LEVEL             Уровень логирования (DEBUG/INFO/WARNING/ERROR)
  --ssl-verify true/false       Проверка SSL сертификата (по умолчанию: true)

  Режимы:
  --docker                      Установка с Docker (по умолчанию)
  --local                       Локальная установка без Docker
  --auto                        Автоматическая установка без подтверждений
  --skip-start                  Не запускать бот после установки

Примеры:
  # Интерактивная установка
  $0

  # Установка с параметрами (с API токеном)
  $0 --zabbix-url https://zabbix.company.com \\
     --zabbix-token YOUR_API_TOKEN \\
     --telegram-token 123456:ABC-DEF \\
     --telegram-chat-id 123456789

  # Установка с логином/паролем
  $0 --zabbix-url https://zabbix.company.com \\
     --zabbix-user admin \\
     --zabbix-password password \\
     --telegram-token 123456:ABC-DEF \\
     --telegram-chat-id 123456789

  # Автоматическая установка без Docker
  $0 --local --auto \\
     --zabbix-url https://zabbix.company.com \\
     --zabbix-token YOUR_API_TOKEN \\
     --telegram-token 123456:ABC-DEF \\
     --telegram-chat-id 123456789

EOF
}

# Переменные по умолчанию
ZABBIX_URL=""
ZABBIX_API_TOKEN=""
ZABBIX_USERNAME=""
ZABBIX_PASSWORD=""
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""
POLL_INTERVAL="60"
MIN_SEVERITY="2"
LOG_LEVEL="INFO"
SSL_VERIFY="true"
USE_DOCKER=true
AUTO_MODE=false
SKIP_START=false

# Парсинг аргументов командной строки
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--version)
            echo "Zabbix Telegram Bot v$VERSION"
            exit 0
            ;;
        --zabbix-url)
            ZABBIX_URL="$2"
            shift 2
            ;;
        --zabbix-token)
            ZABBIX_API_TOKEN="$2"
            shift 2
            ;;
        --zabbix-user)
            ZABBIX_USERNAME="$2"
            shift 2
            ;;
        --zabbix-password)
            ZABBIX_PASSWORD="$2"
            shift 2
            ;;
        --telegram-token)
            TELEGRAM_BOT_TOKEN="$2"
            shift 2
            ;;
        --telegram-chat-id)
            TELEGRAM_CHAT_ID="$2"
            shift 2
            ;;
        --poll-interval)
            POLL_INTERVAL="$2"
            shift 2
            ;;
        --min-severity)
            MIN_SEVERITY="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --ssl-verify)
            SSL_VERIFY="$2"
            shift 2
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --local)
            USE_DOCKER=false
            shift
            ;;
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --skip-start)
            SKIP_START=true
            shift
            ;;
        *)
            echo -e "${RED}Неизвестный параметр: $1${NC}"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

# Проверка зависимостей
echo -e "${BLUE}1. Проверка зависимостей...${NC}"

if [[ "$USE_DOCKER" == true ]]; then
    if ! command_exists docker; then
        echo -e "${RED}❌ Docker не найден. Установите Docker или используйте --local${NC}"
        exit 1
    fi
    if ! command_exists docker-compose && ! docker compose version &>/dev/null; then
        echo -e "${RED}❌ Docker Compose не найден. Установите Docker Compose${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker и Docker Compose установлены${NC}"
else
    if ! command_exists python3; then
        echo -e "${RED}❌ Python 3 не найден. Установите Python 3.8+${NC}"
        exit 1
    fi
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo -e "${GREEN}✅ Python $PYTHON_VERSION установлен${NC}"
fi

if ! command_exists git; then
    echo -e "${YELLOW}⚠️  Git не найден. Рекомендуется для обновлений${NC}"
fi

echo ""

# Интерактивный ввод параметров, если они не указаны
if [[ -z "$ZABBIX_URL" ]] || [[ -z "$TELEGRAM_BOT_TOKEN" ]] || [[ -z "$TELEGRAM_CHAT_ID" ]]; then
    if [[ "$AUTO_MODE" == true ]]; then
        echo -e "${RED}❌ В автоматическом режиме необходимо указать все обязательные параметры${NC}"
        echo "Используйте --help для справки"
        exit 1
    fi

    echo -e "${BLUE}2. Настройка конфигурации${NC}"
    echo ""
    echo -e "${YELLOW}Введите параметры подключения:${NC}"
    echo ""
fi

# Zabbix URL
if [[ -z "$ZABBIX_URL" ]]; then
    read -p "$(echo -e ${GREEN}Zabbix URL${NC}) (например: https://zabbix.company.com): " ZABBIX_URL
    echo ""
fi

# Zabbix аутентификация
if [[ -z "$ZABBIX_API_TOKEN" ]] && [[ -z "$ZABBIX_USERNAME" ]]; then
    echo -e "${YELLOW}Выберите метод аутентификации в Zabbix:${NC}"
    echo "1) API токен (рекомендуется)"
    echo "2) Логин и пароль"
    read -p "Выберите вариант (1-2): " auth_choice
    echo ""

    if [[ "$auth_choice" == "1" ]]; then
        read -p "$(echo -e ${GREEN}Zabbix API Token${NC}): " ZABBIX_API_TOKEN
    else
        read -p "$(echo -e ${GREEN}Zabbix Username${NC}): " ZABBIX_USERNAME
        read -s -p "$(echo -e ${GREEN}Zabbix Password${NC}): " ZABBIX_PASSWORD
        echo ""
    fi
    echo ""
fi

# Telegram
if [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
    echo -e "${YELLOW}Для создания бота:${NC}"
    echo "1. Найдите @BotFather в Telegram"
    echo "2. Отправьте команду /newbot"
    echo "3. Следуйте инструкциям и получите токен"
    echo ""
    read -p "$(echo -e ${GREEN}Telegram Bot Token${NC}): " TELEGRAM_BOT_TOKEN
    echo ""
fi

if [[ -z "$TELEGRAM_CHAT_ID" ]]; then
    echo -e "${YELLOW}Для получения Chat ID:${NC}"
    echo "1. Отправьте /start вашему боту"
    echo "2. Найдите @userinfobot в Telegram"
    echo "3. Отправьте ему любое сообщение"
    echo "4. Скопируйте ваш ID"
    echo ""
    read -p "$(echo -e ${GREEN}Telegram Chat ID${NC}): " TELEGRAM_CHAT_ID
    echo ""
fi

# Проверка обязательных параметров
if [[ -z "$ZABBIX_URL" ]] || [[ -z "$TELEGRAM_BOT_TOKEN" ]] || [[ -z "$TELEGRAM_CHAT_ID" ]]; then
    echo -e "${RED}❌ Не все обязательные параметры указаны${NC}"
    exit 1
fi

if [[ -z "$ZABBIX_API_TOKEN" ]] && [[ -z "$ZABBIX_USERNAME" ]]; then
    echo -e "${RED}❌ Необходимо указать либо API токен, либо логин/пароль для Zabbix${NC}"
    exit 1
fi

# Создание .env файла
echo -e "${BLUE}3. Создание конфигурационного файла...${NC}"

cat > .env << EOF
# Zabbix Telegram Bot Configuration
# Создано автоматически: $(date)
# Версия: $VERSION

# === ZABBIX НАСТРОЙКИ ===
ZABBIX_URL=$ZABBIX_URL
EOF

if [[ -n "$ZABBIX_API_TOKEN" ]]; then
    echo "ZABBIX_API_TOKEN=$ZABBIX_API_TOKEN" >> .env
else
    cat >> .env << EOF
ZABBIX_USERNAME=$ZABBIX_USERNAME
ZABBIX_PASSWORD=$ZABBIX_PASSWORD
EOF
fi

cat >> .env << EOF
ZABBIX_SSL_VERIFY=$SSL_VERIFY

# === TELEGRAM НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID

# === ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ===
POLL_INTERVAL=$POLL_INTERVAL
MIN_SEVERITY=$MIN_SEVERITY
LOG_LEVEL=$LOG_LEVEL
MAX_RETRIES=3
RETRY_DELAY=5

# === UX УЛУЧШЕНИЯ ===
EDIT_ON_UPDATE=true
DELETE_RESOLVED_AFTER=3600
MARK_RESOLVED=true

# === МОНИТОРИНГ И МЕТРИКИ ===
METRICS_ENABLED=true
METRICS_PORT=9090
JSON_LOGGING=false
DATABASE_PATH=data/alerts.db
EOF

echo -e "${GREEN}✅ Конфигурация сохранена в .env${NC}"
echo ""

# Создание необходимых директорий
echo -e "${BLUE}4. Создание директорий...${NC}"
mkdir -p logs data ssl-certs
chmod 755 logs data ssl-certs
echo -e "${GREEN}✅ Директории созданы${NC}"
echo ""

# Установка
if [[ "$USE_DOCKER" == true ]]; then
    echo -e "${BLUE}5. Установка с Docker...${NC}"

    # Сборка образа
    echo "🔨 Сборка Docker образа..."
    if [[ -f "docker-run.sh" ]]; then
        ./docker-run.sh build
    else
        docker-compose build
    fi

    echo -e "${GREEN}✅ Docker образ собран${NC}"
    echo ""

    if [[ "$SKIP_START" != true ]]; then
        # Запуск контейнера
        echo -e "${BLUE}6. Запуск бота...${NC}"
        if [[ -f "docker-run.sh" ]]; then
            ./docker-run.sh start
        else
            docker-compose up -d
        fi

        echo ""
        echo -e "${GREEN}✅ Бот запущен!${NC}"
        echo ""
        echo -e "${YELLOW}Полезные команды:${NC}"
        echo "  Просмотр логов:    ./docker-run.sh logs"
        echo "  Остановка:         ./docker-run.sh stop"
        echo "  Перезапуск:        ./docker-run.sh restart"
        echo "  Статус:            ./docker-run.sh status"
    fi
else
    echo -e "${BLUE}5. Локальная установка...${NC}"

    # Создание виртуального окружения
    if [[ ! -d "venv" ]]; then
        echo "📦 Создание виртуального окружения..."
        python3 -m venv venv
    fi

    # Активация и установка зависимостей
    echo "📥 Установка зависимостей..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    echo -e "${GREEN}✅ Зависимости установлены${NC}"
    echo ""

    if [[ "$SKIP_START" != true ]]; then
        echo -e "${BLUE}6. Запуск бота...${NC}"
        python main.py &
        BOT_PID=$!
        echo $BOT_PID > bot.pid

        sleep 2

        if ps -p $BOT_PID > /dev/null; then
            echo -e "${GREEN}✅ Бот запущен! (PID: $BOT_PID)${NC}"
            echo ""
            echo -e "${YELLOW}Полезные команды:${NC}"
            echo "  Просмотр логов:    tail -f logs/zbxtg.log"
            echo "  Остановка:         kill \$(cat bot.pid)"
            echo "  Перезапуск:        kill \$(cat bot.pid) && python main.py &"
        else
            echo -e "${RED}❌ Не удалось запустить бот. Проверьте логи.${NC}"
            exit 1
        fi
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Установка успешно завершена! 🎉       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Следующие шаги:${NC}"
echo "1. Отправьте /start вашему боту в Telegram"
echo "2. Проверьте работу командой /status"
echo "3. Просмотрите логи для диагностики"
echo ""
echo -e "${BLUE}📖 Документация: https://github.com/GezzyDax/zbxtg${NC}"
echo -e "${BLUE}🐛 Сообщить о проблеме: https://github.com/GezzyDax/zbxtg/issues${NC}"
echo ""
