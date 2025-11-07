#!/bin/bash
# Скрипт автоматического обновления Zabbix Telegram Bot с GitHub
# Поддерживает версионирование и проверку релизов

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

# Читаем текущую версию
CURRENT_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Обновление Zabbix Telegram Bot          ║${NC}"
echo -e "${BLUE}║   Текущая версия: v${CURRENT_VERSION}                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Функция для проверки команд
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Функция для сравнения версий (возвращает 0 если $1 < $2)
version_lt() {
    local ver1=$1
    local ver2=$2

    # Убираем префикс 'v' если есть
    ver1=${ver1#v}
    ver2=${ver2#v}

    # Используем sort -V для сравнения версий
    if [[ "$(printf '%s\n' "$ver1" "$ver2" | sort -V | head -n1)" == "$ver1" ]] && [[ "$ver1" != "$ver2" ]]; then
        return 0
    else
        return 1
    fi
}

# Функция для получения информации о последнем релизе с GitHub
get_latest_release() {
    local repo="GezzyDax/zbxtg"

    if command_exists curl; then
        local response=$(curl -s "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null)
        if [[ -n "$response" ]] && [[ "$response" != *"Not Found"* ]]; then
            local tag=$(echo "$response" | grep '"tag_name":' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
            local name=$(echo "$response" | grep '"name":' | head -1 | sed -E 's/.*"name": *"([^"]+)".*/\1/')
            local body=$(echo "$response" | grep '"body":' | head -1 | sed -E 's/.*"body": *"([^"]+)".*/\1/')

            if [[ -n "$tag" ]]; then
                echo "$tag|$name|$body"
                return 0
            fi
        fi
    elif command_exists wget; then
        local response=$(wget -qO- "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null)
        if [[ -n "$response" ]] && [[ "$response" != *"Not Found"* ]]; then
            local tag=$(echo "$response" | grep '"tag_name":' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
            if [[ -n "$tag" ]]; then
                echo "$tag"
                return 0
            fi
        fi
    fi

    return 1
}

# Проверяем необходимые команды
if ! command_exists git; then
    echo -e "${RED}❌ Git не найден. Пожалуйста, установите git${NC}"
    exit 1
fi

# Проверяем, что мы в git репозитории
if [[ ! -d ".git" ]]; then
    echo -e "${RED}❌ Это не git репозиторий${NC}"
    echo "Склонируйте проект: git clone https://github.com/GezzyDax/zbxtg.git"
    exit 1
fi

# Проверяем наличие релизов на GitHub
echo -e "${BLUE}🔍 Проверяем релизы на GitHub...${NC}"
LATEST_RELEASE_INFO=$(get_latest_release)

if [[ -n "$LATEST_RELEASE_INFO" ]]; then
    LATEST_VERSION=$(echo "$LATEST_RELEASE_INFO" | cut -d'|' -f1)
    LATEST_VERSION=${LATEST_VERSION#v}  # Убираем префикс v

    echo -e "${GREEN}📦 Последний релиз: v$LATEST_VERSION${NC}"

    # Сравниваем версии
    if version_lt "$CURRENT_VERSION" "$LATEST_VERSION"; then
        echo -e "${YELLOW}🆕 Доступна новая версия!${NC}"
        echo -e "   Текущая: ${RED}v$CURRENT_VERSION${NC}"
        echo -e "   Новая:   ${GREEN}v$LATEST_VERSION${NC}"
        echo ""
    else
        echo -e "${GREEN}✅ У вас установлена актуальная версия${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Не удалось получить информацию о релизах (проверяем через git)${NC}"
fi

echo ""

# Сохраняем .env файл если он существует
ENV_BACKUP=""
if [[ -f ".env" ]]; then
    ENV_BACKUP=$(mktemp)
    echo -e "${BLUE}💾 Сохраняем конфигурацию .env...${NC}"
    cp .env "$ENV_BACKUP"
fi

# Сохраняем SSL сертификаты если они есть
SSL_BACKUP=""
if [[ -d "ssl-certs" ]] && [[ -n "$(ls -A ssl-certs 2>/dev/null)" ]]; then
    SSL_BACKUP=$(mktemp -d)
    echo -e "${BLUE}🔒 Сохраняем SSL сертификаты...${NC}"
    cp -r ssl-certs/* "$SSL_BACKUP/"
fi

# Получаем текущий коммит
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
echo -e "${BLUE}📍 Текущий коммит: ${CURRENT_COMMIT:0:8}${NC}"

# Проверяем наличие изменений
echo -e "${BLUE}🔍 Проверяем обновления из репозитория...${NC}"
git fetch origin

# Получаем последний коммит из origin/master
LATEST_COMMIT=$(git rev-parse origin/master 2>/dev/null || git rev-parse origin/main 2>/dev/null)
echo -e "${BLUE}📍 Последний коммит: ${LATEST_COMMIT:0:8}${NC}"

# Проверяем, нужно ли обновление
if [[ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ]]; then
    echo -e "${GREEN}✅ Обновления не требуются. У вас актуальная версия.${NC}"

    # Восстанавливаем файлы если были сохранены
    if [[ -n "$ENV_BACKUP" ]]; then
        rm "$ENV_BACKUP"
    fi
    if [[ -n "$SSL_BACKUP" ]]; then
        rm -rf "$SSL_BACKUP"
    fi

    exit 0
fi

echo ""
echo -e "${GREEN}🆕 Доступно обновление!${NC}"
echo ""

# Показываем изменения
echo -e "${YELLOW}📝 Изменения:${NC}"
git log --oneline "$CURRENT_COMMIT..$LATEST_COMMIT" | head -10

echo ""
read -p "$(echo -e ${YELLOW}❓ Продолжить обновление? \(y/N\): ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Обновление отменено${NC}"
    exit 0
fi

# Останавливаем бота если он запущен
if command_exists docker-compose || command_exists docker; then
    echo -e "${BLUE}⏹️  Останавливаем бота...${NC}"
    if [[ -f "docker-run.sh" ]]; then
        ./docker-run.sh stop 2>/dev/null || true
    else
        docker-compose down 2>/dev/null || true
    fi
fi

# Обновляем код
echo -e "${BLUE}⬇️  Загружаем обновления...${NC}"
git stash push -u -m "Auto-stash before update $(date)" 2>/dev/null || true
git pull origin master 2>/dev/null || git pull origin main

# Обновляем версию
NEW_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

# Восстанавливаем .env файл
if [[ -n "$ENV_BACKUP" ]]; then
    echo -e "${BLUE}🔧 Восстанавливаем конфигурацию .env...${NC}"
    cp "$ENV_BACKUP" .env
    rm "$ENV_BACKUP"
fi

# Восстанавливаем SSL сертификаты
if [[ -n "$SSL_BACKUP" ]]; then
    echo -e "${BLUE}🔒 Восстанавливаем SSL сертификаты...${NC}"
    mkdir -p ssl-certs
    cp -r "$SSL_BACKUP"/* ssl-certs/
    rm -rf "$SSL_BACKUP"
fi

# Проверяем изменения в зависимостях
if git diff "$CURRENT_COMMIT" HEAD --name-only | grep -q "requirements.txt"; then
    echo -e "${YELLOW}📦 Обнаружены изменения в зависимостях - потребуется пересборка Docker образа${NC}"
    REBUILD_NEEDED=true
else
    REBUILD_NEEDED=false
fi

# Пересобираем Docker образ если нужно
if [[ -f "Dockerfile" ]] && (command_exists docker-compose || command_exists docker); then
    if [[ "$REBUILD_NEEDED" == "true" ]]; then
        echo -e "${BLUE}🔨 Пересобираем Docker образ...${NC}"
        if [[ -f "docker-run.sh" ]]; then
            ./docker-run.sh build
        else
            docker-compose build --no-cache
        fi
    fi

    echo -e "${BLUE}▶️  Запускаем обновленного бота...${NC}"
    if [[ -f "docker-run.sh" ]]; then
        ./docker-run.sh start
    else
        docker-compose up -d
    fi
else
    echo -e "${YELLOW}⚠️  Docker не обнаружен. Запустите бота вручную:${NC}"
    echo "   python main.py"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Обновление успешно завершено! 🎉      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Информация об обновлении:${NC}"
echo -e "   Предыдущая версия: ${RED}v$CURRENT_VERSION${NC}"
echo -e "   Текущая версия:    ${GREEN}v$NEW_VERSION${NC}"
echo -e "   Коммит: ${CURRENT_COMMIT:0:8} → $(git rev-parse HEAD | cut -c1-8)"

# Показываем статус если Docker доступен
if [[ -f "docker-run.sh" ]]; then
    echo ""
    echo -e "${BLUE}📊 Статус бота:${NC}"
    ./docker-run.sh status || true
fi

echo ""
echo -e "${GREEN}🎉 Готово! Бот обновлен и запущен.${NC}"