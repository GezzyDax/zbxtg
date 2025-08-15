#!/bin/bash
# Скрипт для запуска Zabbix Telegram Bot в Docker

set -e

echo "🐳 Zabbix Telegram Bot - Docker запуск"
echo ""

# Экспортируем USER_ID и GROUP_ID для Docker
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

# Создаем директорию для логов с правильными правами
mkdir -p logs
chmod 755 logs

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose не найден. Используем docker compose"
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

case "${1:-start}" in
    "build")
        echo "🔨 Собираем образ..."
        $COMPOSE_CMD build --no-cache
        ;;
    "start")
        echo "▶️  Запускаем бот..."
        $COMPOSE_CMD up -d
        echo ""
        echo "✅ Бот запущен в фоновом режиме"
        echo "📋 Просмотр логов: $0 logs"
        echo "⏹️  Остановка: $0 stop"
        ;;
    "stop")
        echo "⏹️  Останавливаем бот..."
        $COMPOSE_CMD down
        echo "✅ Бот остановлен"
        ;;
    "restart")
        echo "🔄 Перезапускаем бот..."
        $COMPOSE_CMD down
        $COMPOSE_CMD up -d
        echo "✅ Бот перезапущен"
        ;;
    "logs")
        echo "📋 Просмотр логов (Ctrl+C для выхода):"
        $COMPOSE_CMD logs -f zbxtg
        ;;
    "status")
        echo "📊 Статус контейнера:"
        $COMPOSE_CMD ps
        ;;
    "shell")
        echo "🐚 Вход в контейнер:"
        $COMPOSE_CMD exec zbxtg /bin/bash
        ;;
    "clean")
        echo "🧹 Очистка..."
        $COMPOSE_CMD down -v --remove-orphans
        docker image prune -f
        echo "✅ Очистка завершена"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|logs|status|build|shell|clean}"
        echo ""
        echo "Команды:"
        echo "  start   - Запустить бот (по умолчанию)"
        echo "  stop    - Остановить бот"
        echo "  restart - Перезапустить бот"
        echo "  logs    - Показать логи"
        echo "  status  - Показать статус"
        echo "  build   - Пересобрать образ"
        echo "  shell   - Войти в контейнер"
        echo "  clean   - Очистить контейнеры и образы"
        ;;
esac