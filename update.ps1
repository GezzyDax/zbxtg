# PowerShell скрипт автоматического обновления Zabbix Telegram Bot с GitHub

param(
    [switch]$Force = $false
)

Write-Host ""
Write-Host "🔄 Обновление Zabbix Telegram Bot" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем наличие Git
if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git не найден. Пожалуйста, установите Git" -ForegroundColor Red
    exit 1
}

# Проверяем, что мы в git репозитории
if (-not (Test-Path ".git")) {
    Write-Host "❌ Это не git репозиторий" -ForegroundColor Red
    Write-Host "Склонируйте проект: git clone https://github.com/GezzyDax/zbxtg.git"
    exit 1
}

# Сохраняем .env файл если он существует
$envBackup = $null
if (Test-Path ".env") {
    $envBackup = New-TemporaryFile
    Write-Host "💾 Сохраняем конфигурацию .env..." -ForegroundColor Yellow
    Copy-Item ".env" $envBackup.FullName
}

# Сохраняем SSL сертификаты если они есть
$sslBackup = $null
if ((Test-Path "ssl-certs") -and (Get-ChildItem "ssl-certs" -ErrorAction SilentlyContinue)) {
    $sslBackup = New-Item -ItemType Directory -Path ([System.IO.Path]::GetTempPath()) -Name "ssl-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Write-Host "🔒 Сохраняем SSL сертификаты..." -ForegroundColor Yellow
    Copy-Item "ssl-certs\*" $sslBackup.FullName -Recurse
}

# Получаем текущий коммит
try {
    $currentCommit = git rev-parse HEAD
    Write-Host "📍 Текущий коммит: $($currentCommit.Substring(0,8))" -ForegroundColor Gray
} catch {
    $currentCommit = "unknown"
    Write-Host "📍 Текущий коммит: неизвестен" -ForegroundColor Gray
}

# Проверяем наличие изменений
Write-Host "🔍 Проверяем обновления..." -ForegroundColor Cyan
git fetch origin

# Получаем последний коммит из origin
try {
    $latestCommit = git rev-parse origin/master
} catch {
    try {
        $latestCommit = git rev-parse origin/main
    } catch {
        Write-Host "❌ Не удалось получить информацию о последних изменениях" -ForegroundColor Red
        exit 1
    }
}

Write-Host "📍 Последний коммит: $($latestCommit.Substring(0,8))" -ForegroundColor Gray

# Проверяем, нужно ли обновление
if (($currentCommit -eq $latestCommit) -and (-not $Force)) {
    Write-Host "✅ Обновления не требуются. У вас актуальная версия." -ForegroundColor Green
    
    # Очищаем временные файлы
    if ($envBackup) { Remove-Item $envBackup.FullName }
    if ($sslBackup) { Remove-Item $sslBackup.FullName -Recurse }
    
    exit 0
}

Write-Host ""
Write-Host "🆕 Доступно обновление!" -ForegroundColor Green
Write-Host ""

# Показываем изменения
Write-Host "📝 Изменения:" -ForegroundColor Cyan
git log --oneline "$currentCommit..$latestCommit" | Select-Object -First 10

Write-Host ""
if (-not $Force) {
    $response = Read-Host "❓ Продолжить обновление? (y/N)"
    if ($response -notmatch '^[Yy]$') {
        Write-Host "❌ Обновление отменено" -ForegroundColor Red
        exit 0
    }
}

# Останавливаем бота если он запущен
if ((Get-Command "docker" -ErrorAction SilentlyContinue) -and (Test-Path "docker-run.ps1")) {
    Write-Host "⏹️  Останавливаем бота..." -ForegroundColor Yellow
    try {
        & ".\docker-run.ps1" stop
    } catch {
        Write-Host "Не удалось остановить через скрипт, продолжаем..." -ForegroundColor Yellow
    }
}

# Обновляем код
Write-Host "⬇️  Загружаем обновления..." -ForegroundColor Cyan
try {
    git stash push -u -m "Auto-stash before update $(Get-Date)"
} catch {
    # Игнорируем ошибки stash если нет изменений
}

try {
    git pull origin master
} catch {
    git pull origin main
}

# Восстанавливаем .env файл
if ($envBackup) {
    Write-Host "🔧 Восстанавливаем конфигурацию .env..." -ForegroundColor Yellow
    Copy-Item $envBackup.FullName ".env"
    Remove-Item $envBackup.FullName
}

# Восстанавливаем SSL сертификаты
if ($sslBackup) {
    Write-Host "🔒 Восстанавливаем SSL сертификаты..." -ForegroundColor Yellow
    if (-not (Test-Path "ssl-certs")) {
        New-Item -ItemType Directory -Path "ssl-certs"
    }
    Copy-Item "$($sslBackup.FullName)\*" "ssl-certs\" -Recurse -Force
    Remove-Item $sslBackup.FullName -Recurse
}

# Проверяем изменения в зависимостях
$requirementsChanged = git diff "$currentCommit" HEAD --name-only | Select-String "requirements.txt"
if ($requirementsChanged) {
    Write-Host "📦 Обнаружены изменения в зависимостях - потребуется пересборка Docker образа" -ForegroundColor Yellow
    $rebuildNeeded = $true
} else {
    $rebuildNeeded = $false
}

# Пересобираем Docker образ если нужно
if ((Test-Path "Dockerfile") -and (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    if ($rebuildNeeded) {
        Write-Host "🔨 Пересобираем Docker образ..." -ForegroundColor Yellow
        if (Test-Path "docker-run.ps1") {
            & ".\docker-run.ps1" build
        } else {
            docker-compose build --no-cache
        }
    }
    
    Write-Host "▶️  Запускаем обновленного бота..." -ForegroundColor Green
    if (Test-Path "docker-run.ps1") {
        & ".\docker-run.ps1" start
    } else {
        docker-compose up -d
    }
} else {
    Write-Host "⚠️  Docker не обнаружен. Запустите бота вручную:" -ForegroundColor Yellow
    Write-Host "   python main.py"
}

$newCommit = git rev-parse HEAD
Write-Host ""
Write-Host "✅ Обновление завершено!" -ForegroundColor Green
Write-Host "🆕 Обновлено с $($currentCommit.Substring(0,8)) до $($newCommit.Substring(0,8))" -ForegroundColor Cyan

# Показываем статус если Docker доступен
if (Test-Path "docker-run.ps1") {
    Write-Host ""
    Write-Host "📊 Статус бота:" -ForegroundColor Cyan
    try {
        & ".\docker-run.ps1" status
    } catch {
        Write-Host "Не удалось получить статус" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "🎉 Готово! Бот обновлен и запущен." -ForegroundColor Green