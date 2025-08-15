@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM Batch скрипт автоматического обновления Zabbix Telegram Bot с GitHub

echo.
echo ==========================================
echo    Обновление Zabbix Telegram Bot
echo ==========================================
echo.

REM Проверяем наличие Git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Git не найден. Пожалуйста, установите Git
    pause
    exit /b 1
)

REM Проверяем, что мы в git репозитории
if not exist ".git" (
    echo [ОШИБКА] Это не git репозиторий
    echo Склонируйте проект: git clone https://github.com/GezzyDax/zbxtg.git
    pause
    exit /b 1
)

REM Сохраняем .env файл если он существует
set ENV_BACKUP=
if exist ".env" (
    set ENV_BACKUP=%TEMP%\zbxtg_env_backup_%RANDOM%.tmp
    echo [INFO] Сохраняем конфигурацию .env...
    copy ".env" "!ENV_BACKUP!" >nul
)

REM Сохраняем SSL сертификаты если они есть
set SSL_BACKUP=
if exist "ssl-certs" (
    dir /b ssl-certs 2>nul | findstr /r ".*" >nul
    if not errorlevel 1 (
        set SSL_BACKUP=%TEMP%\zbxtg_ssl_backup_%RANDOM%
        echo [INFO] Сохраняем SSL сертификаты...
        mkdir "!SSL_BACKUP!" 2>nul
        xcopy "ssl-certs\*" "!SSL_BACKUP!\" /E /Q >nul
    )
)

REM Получаем текущий коммит
for /f %%i in ('git rev-parse HEAD 2^>nul') do set CURRENT_COMMIT=%%i
if "!CURRENT_COMMIT!"=="" set CURRENT_COMMIT=unknown
echo [INFO] Текущий коммит: !CURRENT_COMMIT:~0,8!

REM Проверяем наличие изменений
echo [INFO] Проверяем обновления...
git fetch origin >nul 2>&1

REM Получаем последний коммит
for /f %%i in ('git rev-parse origin/master 2^>nul') do set LATEST_COMMIT=%%i
if "!LATEST_COMMIT!"=="" (
    for /f %%i in ('git rev-parse origin/main 2^>nul') do set LATEST_COMMIT=%%i
)

if "!LATEST_COMMIT!"=="" (
    echo [ОШИБКА] Не удалось получить информацию о последних изменениях
    pause
    exit /b 1
)

echo [INFO] Последний коммит: !LATEST_COMMIT:~0,8!

REM Проверяем, нужно ли обновление
if "!CURRENT_COMMIT!"=="!LATEST_COMMIT!" (
    echo [УСПЕХ] Обновления не требуются. У вас актуальная версия.
    
    REM Очищаем временные файлы
    if not "!ENV_BACKUP!"=="" del "!ENV_BACKUP!" 2>nul
    if not "!SSL_BACKUP!"=="" rmdir /s /q "!SSL_BACKUP!" 2>nul
    
    pause
    exit /b 0
)

echo.
echo [INFO] Доступно обновление!
echo.

REM Показываем изменения
echo [INFO] Последние изменения:
git log --oneline !CURRENT_COMMIT!..!LATEST_COMMIT! | findstr /n "^" | findstr "^[1-5]:"

echo.
set /p RESPONSE="Продолжить обновление? (y/N): "
if /i not "!RESPONSE!"=="y" (
    echo [INFO] Обновление отменено
    pause
    exit /b 0
)

REM Останавливаем бота если он запущен
if exist "docker-run.bat" (
    echo [INFO] Останавливаем бота...
    call docker-run.bat stop >nul 2>&1
)

REM Обновляем код
echo [INFO] Загружаем обновления...
git stash push -u -m "Auto-stash before update" >nul 2>&1
git pull origin master >nul 2>&1 || git pull origin main >nul 2>&1

REM Восстанавливаем .env файл
if not "!ENV_BACKUP!"=="" (
    echo [INFO] Восстанавливаем конфигурацию .env...
    copy "!ENV_BACKUP!" ".env" >nul
    del "!ENV_BACKUP!"
)

REM Восстанавливаем SSL сертификаты
if not "!SSL_BACKUP!"=="" (
    echo [INFO] Восстанавливаем SSL сертификаты...
    if not exist "ssl-certs" mkdir ssl-certs
    xcopy "!SSL_BACKUP!\*" "ssl-certs\" /E /Q /Y >nul
    rmdir /s /q "!SSL_BACKUP!"
)

REM Проверяем изменения в зависимостях
git diff !CURRENT_COMMIT! HEAD --name-only | findstr "requirements.txt" >nul
if not errorlevel 1 (
    echo [INFO] Обнаружены изменения в зависимостях - потребуется пересборка
    set REBUILD_NEEDED=true
) else (
    set REBUILD_NEEDED=false
)

REM Пересобираем Docker образ если нужно
where docker >nul 2>&1
if not errorlevel 1 (
    if exist "Dockerfile" (
        if "!REBUILD_NEEDED!"=="true" (
            echo [INFO] Пересобираем Docker образ...
            if exist "docker-run.bat" (
                call docker-run.bat build
            ) else (
                docker-compose build --no-cache
            )
        )
        
        echo [INFO] Запускаем обновленного бота...
        if exist "docker-run.bat" (
            call docker-run.bat start
        ) else (
            docker-compose up -d
        )
    )
) else (
    echo [ВНИМАНИЕ] Docker не обнаружен. Запустите бота вручную: python main.py
)

REM Получаем новый коммит
for /f %%i in ('git rev-parse HEAD') do set NEW_COMMIT=%%i

echo.
echo [УСПЕХ] Обновление завершено!
echo [INFO] Обновлено с !CURRENT_COMMIT:~0,8! до !NEW_COMMIT:~0,8!

REM Показываем статус если Docker доступен
if exist "docker-run.bat" (
    echo.
    echo [INFO] Статус бота:
    call docker-run.bat status
)

echo.
echo [УСПЕХ] Готово! Бот обновлен и запущен.
pause