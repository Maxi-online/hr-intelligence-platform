#!/usr/bin/env python3
"""
Скрипт для запуска всех микросервисов Candidate Analysis
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path

def check_service_health(url: str, service_name: str) -> bool:
    """Проверка здоровья сервиса"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_service(service_name: str, command: str, port: int):
    """Запуск сервиса"""
    print(f"🚀 Запуск {service_name}...")
    
    try:
        # Запуск процесса
        process = subprocess.Popen(
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Ожидание запуска
        time.sleep(3)
        
        # Проверка здоровья
        health_url = f"http://localhost:{port}"
        if check_service_health(health_url, service_name):
            print(f"✅ {service_name} успешно запущен на порту {port}")
            return process
        else:
            print(f"❌ {service_name} не отвечает на порту {port}")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запуска {service_name}: {e}")
        return None

def main():
    """Основная функция"""
    print("🎯 Candidate Analysis - Запуск микросервисов")
    print("=" * 50)
    
    # Проверка наличия файлов
    required_files = [
        "config/main.py",
        "hh_api/main.py", 
        "ranking/main.py",
        "search/main.py",
        "gateway/main.py",
        "ai_analysis/main.py",
        "database/main.py",
        "frontend/app.py"
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Файл {file_path} не найден")
            sys.exit(1)
    
    # Создание директории для логов
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    print("📁 Директории созданы")
    
    # Определение сервисов для запуска
    services = [
        {
            "name": "Config Service",
            "command": "python config/main.py",
            "port": 8004,
            "url": "http://localhost:8004"
        },
        {
            "name": "HH API Service", 
            "command": "python hh_api/main.py",
            "port": 8003,
            "url": "http://localhost:8003"
        },
        {
            "name": "Ranking Service",
            "command": "python ranking/main.py", 
            "port": 8002,
            "url": "http://localhost:8002"
        },
        {
            "name": "AI Analysis Service",
            "command": "python ai_analysis/main.py",
            "port": 8005,
            "url": "http://localhost:8005"
        },
        {
            "name": "Database Service",
            "command": "python database/main.py",
            "port": 8006,
            "url": "http://localhost:8006"
        },
        {
            "name": "Search Service",
            "command": "python search/main.py",
            "port": 8001,
            "url": "http://localhost:8001"
        },
        {
            "name": "API Gateway",
            "command": "python gateway/main.py",
            "port": 8088,
            "url": "http://localhost:8088"
        },
        {
            "name": "Frontend (Streamlit)",
            "command": "streamlit run frontend/app.py --server.port=8501 --server.address=0.0.0.0",
            "port": 8501,
            "url": "http://localhost:8501"
        }
    ]
    
    processes = []
    
    # Запуск сервисов
    for service in services:
        process = start_service(service["name"], service["command"], service["port"])
        if process:
            processes.append((service["name"], process))
        else:
            print(f"❌ Не удалось запустить {service['name']}")
            # Остановка уже запущенных процессов
            for name, proc in processes:
                proc.terminate()
            sys.exit(1)
    
    print("\n🎉 Все сервисы успешно запущены!")
    print("\n📋 Доступные сервисы:")
    print("- Frontend: http://localhost:8501")
    print("- API Gateway: http://localhost:8088")
    print("- API Documentation: http://localhost:8088/docs")
    print("- Search Service: http://localhost:8001")
    print("- Ranking Service: http://localhost:8002")
    print("- HH API Service: http://localhost:8003")
    print("- Config Service: http://localhost:8004")
    print("- AI Analysis Service: http://localhost:8005")
    print("- Database Service: http://localhost:8006")
    
    print("\n💡 Для остановки всех сервисов нажмите Ctrl+C")
    
    try:
        # Ожидание завершения
        while True:
            time.sleep(1)
            # Проверка здоровья всех сервисов
            for service in services:
                if not check_service_health(service["url"], service["name"]):
                    print(f"⚠️ {service['name']} не отвечает")
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервисов...")
        for name, process in processes:
            print(f"Остановка {name}...")
            process.terminate()
        print("✅ Все сервисы остановлены")

if __name__ == "__main__":
    main()