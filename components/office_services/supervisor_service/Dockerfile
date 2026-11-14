# ====================================
# Centralized Supervisor Microservices
# ====================================
FROM python:3.11-slim

LABEL maintainer="HR AI Team"
LABEL descritation="Centralized Supervisor Microservice"
LABEL version="1.0.0"

# Changing environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Working Directorate
WORKDIR /app

# Installation of systems relationships
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copying and Installation of Python Dependences
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copying the Microservice Code
COPY . .

# Create directors for lairs
RUN mkdir -p /app/logs

# Creating a user for safety
RUN groupadd -r supervisor && \
    useradd -r -g supervisor -d /app -s /bin/bash supervisor && \
    chown -R supervisor:supervisor /app

USER supervisor

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

# Opening of the port
EXPOSE 8100

# FastAPI server start-up
CMD ["python", "app.py"]
