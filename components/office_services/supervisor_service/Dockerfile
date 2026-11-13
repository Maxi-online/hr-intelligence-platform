# ====================================
# Centralized Supervisor Микросервис
# ====================================
FROM python:3.11-slim

LABEL maintainer="HR AI Team"
LABEL description="Centralized Supervisor Микросервис"
LABEL version="1.0.0"

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Рабочая директория
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование кода микросервиса
COPY . .

# Создание директорий для логов
RUN mkdir -p /app/logs

# Создание пользователя для безопасности
RUN groupadd -r supervisor && \
    useradd -r -g supervisor -d /app -s /bin/bash supervisor && \
    chown -R supervisor:supervisor /app

USER supervisor

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

# Открытие порта
EXPOSE 8100

# Запуск FastAPI сервера
CMD ["python", "app.py"]
