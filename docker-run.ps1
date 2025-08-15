# PowerShell скрипт для запуска Zabbix Telegram Bot в Docker на Windows

param(
    [Parameter(Position=0)]
    [string]$Action = "start"
)

Write-Host "🐳 Zabbix Telegram Bot - Docker запуск" -ForegroundColor Cyan
Write-Host ""

# Создаем директорию для логов
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
}

# Проверяем наличие Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker не найден. Пожалуйста, установите Docker Desktop for Windows" -ForegroundColor Red
    exit 1
}

# Проверяем наличие docker-compose
$ComposeCmd = ""
if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
    $ComposeCmd = "docker-compose"
} elseif (Get-Command "docker" -ErrorAction SilentlyContinue) {
    # Проверяем поддержку docker compose (новая версия)
    $result = docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $ComposeCmd = "docker compose"
    }
}

if ($ComposeCmd -eq "") {
    Write-Host "❌ docker-compose или docker compose не найден" -ForegroundColor Red
    exit 1
}

switch ($Action.ToLower()) {
    "build" {
        Write-Host "🔨 Собираем образ..." -ForegroundColor Yellow
        Invoke-Expression "$ComposeCmd build --no-cache"
    }
    "start" {
        Write-Host "▶️  Запускаем бот..." -ForegroundColor Green
        Invoke-Expression "$ComposeCmd up -d"
        Write-Host ""
        Write-Host "✅ Бот запущен в фоновом режиме" -ForegroundColor Green
        Write-Host "📋 Просмотр логов: .\docker-run.ps1 logs" -ForegroundColor Cyan
        Write-Host "⏹️  Остановка: .\docker-run.ps1 stop" -ForegroundColor Cyan
    }
    "stop" {
        Write-Host "⏹️  Останавливаем бот..." -ForegroundColor Yellow
        Invoke-Expression "$ComposeCmd down"
        Write-Host "✅ Бот остановлен" -ForegroundColor Green
    }
    "restart" {
        Write-Host "🔄 Перезапускаем бот..." -ForegroundColor Yellow
        Invoke-Expression "$ComposeCmd down"
        Invoke-Expression "$ComposeCmd up -d"
        Write-Host "✅ Бот перезапущен" -ForegroundColor Green
    }
    "logs" {
        Write-Host "📋 Просмотр логов (Ctrl+C для выхода):" -ForegroundColor Cyan
        Invoke-Expression "$ComposeCmd logs -f zbxtg"
    }
    "status" {
        Write-Host "📊 Статус контейнера:" -ForegroundColor Cyan
        Invoke-Expression "$ComposeCmd ps"
    }
    "shell" {
        Write-Host "🐚 Вход в контейнер:" -ForegroundColor Cyan
        Invoke-Expression "$ComposeCmd exec zbxtg /bin/bash"
    }
    "clean" {
        Write-Host "🧹 Очистка..." -ForegroundColor Yellow
        Invoke-Expression "$ComposeCmd down -v --remove-orphans"
        docker image prune -f
        Write-Host "✅ Очистка завершена" -ForegroundColor Green
    }
    default {
        Write-Host "Использование: .\docker-run.ps1 [команда]" -ForegroundColor White
        Write-Host ""
        Write-Host "Команды:" -ForegroundColor White
        Write-Host "  start   - Запустить бот (по умолчанию)" -ForegroundColor Gray
        Write-Host "  stop    - Остановить бот" -ForegroundColor Gray
        Write-Host "  restart - Перезапустить бот" -ForegroundColor Gray
        Write-Host "  logs    - Показать логи" -ForegroundColor Gray
        Write-Host "  status  - Показать статус" -ForegroundColor Gray
        Write-Host "  build   - Пересобрать образ" -ForegroundColor Gray
        Write-Host "  shell   - Войти в контейнер" -ForegroundColor Gray
        Write-Host "  clean   - Очистить контейнеры и образы" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Примеры:" -ForegroundColor White
        Write-Host "  .\docker-run.ps1 start" -ForegroundColor Gray
        Write-Host "  .\docker-run.ps1 logs" -ForegroundColor Gray
        Write-Host "  .\docker-run.ps1 stop" -ForegroundColor Gray
    }
}