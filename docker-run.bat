@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM Batch скрипт для запуска Zabbix Telegram Bot в Docker на Windows

echo 🐳 Zabbix Telegram Bot - Docker запуск
echo.

REM Создаем директорию для логов
if not exist "logs" mkdir logs

REM Проверяем наличие Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker не найден. Пожалуйста, установите Docker Desktop for Windows
    pause
    exit /b 1
)

REM Определяем команду compose
set COMPOSE_CMD=
where docker-compose >nul 2>&1
if %errorlevel% equ 0 (
    set COMPOSE_CMD=docker-compose
) else (
    docker compose version >nul 2>&1
    if !errorlevel! equ 0 (
        set COMPOSE_CMD=docker compose
    )
)

if "%COMPOSE_CMD%"=="" (
    echo ❌ docker-compose или docker compose не найден
    pause
    exit /b 1
)

REM Устанавливаем действие по умолчанию
set ACTION=%1
if "%ACTION%"=="" set ACTION=start

if /i "%ACTION%"=="build" goto BUILD
if /i "%ACTION%"=="start" goto START
if /i "%ACTION%"=="stop" goto STOP
if /i "%ACTION%"=="restart" goto RESTART
if /i "%ACTION%"=="logs" goto LOGS
if /i "%ACTION%"=="status" goto STATUS
if /i "%ACTION%"=="shell" goto SHELL
if /i "%ACTION%"=="clean" goto CLEAN
goto HELP

:BUILD
echo 🔨 Собираем образ...
%COMPOSE_CMD% build --no-cache
goto END

:START
echo ▶️ Запускаем бот...
%COMPOSE_CMD% up -d
echo.
echo ✅ Бот запущен в фоновом режиме
echo 📋 Просмотр логов: docker-run.bat logs
echo ⏹️ Остановка: docker-run.bat stop
goto END

:STOP
echo ⏹️ Останавливаем бот...
%COMPOSE_CMD% down
echo ✅ Бот остановлен
goto END

:RESTART
echo 🔄 Перезапускаем бот...
%COMPOSE_CMD% down
%COMPOSE_CMD% up -d
echo ✅ Бот перезапущен
goto END

:LOGS
echo 📋 Просмотр логов (Ctrl+C для выхода):
%COMPOSE_CMD% logs -f zbxtg
goto END

:STATUS
echo 📊 Статус контейнера:
%COMPOSE_CMD% ps
goto END

:SHELL
echo 🐚 Вход в контейнер:
%COMPOSE_CMD% exec zbxtg /bin/bash
goto END

:CLEAN
echo 🧹 Очистка...
%COMPOSE_CMD% down -v --remove-orphans
docker image prune -f
echo ✅ Очистка завершена
goto END

:HELP
echo Использование: docker-run.bat [команда]
echo.
echo Команды:
echo   start   - Запустить бот (по умолчанию)
echo   stop    - Остановить бот
echo   restart - Перезапустить бот
echo   logs    - Показать логи
echo   status  - Показать статус
echo   build   - Пересобрать образ
echo   shell   - Войти в контейнер
echo   clean   - Очистить контейнеры и образы
echo.
echo Примеры:
echo   docker-run.bat start
echo   docker-run.bat logs
echo   docker-run.bat stop
goto END

:END
if /i "%ACTION%"=="logs" goto NOPAUSE
if /i "%ACTION%"=="shell" goto NOPAUSE
echo.
echo Нажмите любую клавишу для выхода...
pause >nul

:NOPAUSE