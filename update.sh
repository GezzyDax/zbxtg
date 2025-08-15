#!/bin/bash
# Скрипт автоматического обновления Zabbix Telegram Bot с GitHub

set -e

echo ""
echo "🔄 Обновление Zabbix Telegram Bot"
echo "================================="
echo ""

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Функция для проверки команд
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Проверяем необходимые команды
if ! command_exists git; then
    echo "❌ Git не найден. Пожалуйста, установите git"
    exit 1
fi

# Проверяем, что мы в git репозитории
if [[ ! -d ".git" ]]; then
    echo "❌ Это не git репозиторий"
    echo "Склонируйте проект: git clone https://github.com/GezzyDax/zbxtg.git"
    exit 1
fi

# Сохраняем .env файл если он существует
ENV_BACKUP=""
if [[ -f ".env" ]]; then
    ENV_BACKUP=$(mktemp)
    echo "💾 Сохраняем конфигурацию .env..."
    cp .env "$ENV_BACKUP"
fi

# Сохраняем SSL сертификаты если они есть
SSL_BACKUP=""
if [[ -d "ssl-certs" ]] && [[ -n "$(ls -A ssl-certs 2>/dev/null)" ]]; then
    SSL_BACKUP=$(mktemp -d)
    echo "🔒 Сохраняем SSL сертификаты..."
    cp -r ssl-certs/* "$SSL_BACKUP/"
fi

# Получаем текущий коммит
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
echo "📍 Текущий коммит: ${CURRENT_COMMIT:0:8}"

# Проверяем наличие изменений
echo "🔍 Проверяем обновления..."
git fetch origin

# Получаем последний коммит из origin/master
LATEST_COMMIT=$(git rev-parse origin/master 2>/dev/null || git rev-parse origin/main 2>/dev/null)
echo "📍 Последний коммит: ${LATEST_COMMIT:0:8}"

# Проверяем, нужно ли обновление
if [[ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ]]; then
    echo "✅ Обновления не требуются. У вас актуальная версия."
    
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
echo "🆕 Доступно обновление!"
echo ""

# Показываем изменения
echo "📝 Изменения:"
git log --oneline "$CURRENT_COMMIT..$LATEST_COMMIT" | head -10

echo ""
read -p "❓ Продолжить обновление? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Обновление отменено"
    exit 0
fi

# Останавливаем бота если он запущен
if command_exists docker-compose || command_exists docker; then
    echo "⏹️  Останавливаем бота..."
    if [[ -f "docker-run.sh" ]]; then
        ./docker-run.sh stop 2>/dev/null || true
    else
        docker-compose down 2>/dev/null || true
    fi
fi

# Обновляем код
echo "⬇️  Загружаем обновления..."
git stash push -u -m "Auto-stash before update $(date)" 2>/dev/null || true
git pull origin master 2>/dev/null || git pull origin main

# Восстанавливаем .env файл
if [[ -n "$ENV_BACKUP" ]]; then
    echo "🔧 Восстанавливаем конфигурацию .env..."
    cp "$ENV_BACKUP" .env
    rm "$ENV_BACKUP"
fi

# Восстанавливаем SSL сертификаты
if [[ -n "$SSL_BACKUP" ]]; then
    echo "🔒 Восстанавливаем SSL сертификаты..."
    mkdir -p ssl-certs
    cp -r "$SSL_BACKUP"/* ssl-certs/
    rm -rf "$SSL_BACKUP"
fi

# Проверяем изменения в зависимостях
if git diff "$CURRENT_COMMIT" HEAD --name-only | grep -q "requirements.txt"; then
    echo "📦 Обнаружены изменения в зависимостях - потребуется пересборка Docker образа"
    REBUILD_NEEDED=true
else
    REBUILD_NEEDED=false
fi

# Пересобираем Docker образ если нужно
if [[ -f "Dockerfile" ]] && (command_exists docker-compose || command_exists docker); then
    if [[ "$REBUILD_NEEDED" == "true" ]]; then
        echo "🔨 Пересобираем Docker образ..."
        if [[ -f "docker-run.sh" ]]; then
            ./docker-run.sh build
        else
            docker-compose build --no-cache
        fi
    fi
    
    echo "▶️  Запускаем обновленного бота..."
    if [[ -f "docker-run.sh" ]]; then
        ./docker-run.sh start
    else
        docker-compose up -d
    fi
else
    echo "⚠️  Docker не обнаружен. Запустите бота вручную:"
    echo "   python main.py"
fi

echo ""
echo "✅ Обновление завершено!"
echo "🆕 Обновлено с ${CURRENT_COMMIT:0:8} до $(git rev-parse HEAD | cut -c1-8)"

# Показываем статус если Docker доступен
if [[ -f "docker-run.sh" ]]; then
    echo ""
    echo "📊 Статус бота:"
    ./docker-run.sh status || true
fi

echo ""
echo "🎉 Готово! Бот обновлен и запущен."