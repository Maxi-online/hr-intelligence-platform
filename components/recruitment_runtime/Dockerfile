FROM python:3.11-slim

# Установка переменных окружения для UTF-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для логов
RUN mkdir -p logs

# Установка прав доступа
RUN chmod +x *.py

# Открытие портов
EXPOSE 8000 8001 8002 8003 8004

# Команда по умолчанию
CMD ["python", "gateway/main.py"]