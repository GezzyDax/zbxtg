FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash zbxtg

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем SSL сертификаты
COPY ssl-certs/ /usr/local/share/ca-certificates/

# Обновляем trust store
RUN update-ca-certificates

# Копируем исходный код
COPY --chown=zbxtg:zbxtg *.py ./

# Переключаемся на пользователя
USER zbxtg

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV POLL_INTERVAL=60

# Проверка здоровья контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.telegram.org', timeout=5)" || exit 1

# Запускаем приложение
CMD ["python", "main.py"]