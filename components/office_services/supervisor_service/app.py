"""
Centralized Supervisor FastAPI приложение
HTTP API для микросервиса Supervisor
"""
import os

import logging
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from supervisor import CentralizedSupervisor

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Centralized Supervisor Service",
    description="HTTP API для централизованного Supervisor микросервиса",
    version="1.0.0"
)

# Глобальный экземпляр Supervisor
supervisor: CentralizedSupervisor = None

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global supervisor
    logger.info("🚀 Запуск Centralized Supervisor API...")
    
    # Конфигурация OpenAI
    openai_config = {
        'api_key': 'your-openai-api-key',  # Будет загружаться из настроек
        'proxy_url': 'http://your-proxy-url:port',  # Будет загружаться из настроек
        'model': 'gpt-5-mini'
    }
    
    # Конфигурация базы данных PostgreSQL
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'office_services_user',
        'password': os.environ["SERVICES_CENTRAL_POSTGRES_ENVIRONMENT_POSTGRES_PASSWORD"],
        'database': 'office_services_agents'
    }
    
    supervisor = CentralizedSupervisor(openai_config, db_config)
    await supervisor.initialize()
    logger.info("✅ Centralized Supervisor API готова")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    global supervisor
    if supervisor:
        await supervisor.cleanup()
    logger.info("👋 Centralized Supervisor API остановлена")

class MessageRequest(BaseModel):
    message: str
    user_id: str = "api_user"
    session_id: str = None

@app.get("/")
async def root():
    """Информация о сервисе"""
    return {
        "service": "Centralized Supervisor Service",
        "version": "1.0.0",
        "status": "active",
        "description": "Централизованный Supervisor для управления командой AI-агентов",
        "architecture": "PostgreSQL + GPT-5 + Centralized Management"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    if supervisor:
        status = await supervisor.get_status()
        return status
    else:
        return {"status": "initializing"}

@app.post("/process_message")
async def process_message(request: MessageRequest):
    """Обработка сообщения через Supervisor"""
    if not supervisor:
        raise HTTPException(status_code=503, detail="Supervisor не инициализирован")
    
    try:
        response = await supervisor.process_message(
            request.message, 
            request.user_id, 
            request.session_id
        )
        return {
            "response": response,
            "service": "Centralized Supervisor",
            "user_id": request.user_id,
            "session_id": request.session_id
        }
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system_info")
async def get_system_info():
    """Получение информации о системе"""
    if not supervisor:
        raise HTTPException(status_code=503, detail="Supervisor не инициализирован")
    
    try:
        # Используем внутренний метод для получения системной информации
        result = await supervisor._get_system_info(detailed=True, include_metrics=True)
        return {"system_info": result}
    except Exception as e:
        logger.error(f"❌ Ошибка получения системной информации: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent_status")
async def get_agent_status():
    """Получение статуса всех агентов"""
    if not supervisor:
        raise HTTPException(status_code=503, detail="Supervisor не инициализирован")
    
    try:
        result = await supervisor._get_agent_status(include_performance=True)
        return {"agent_status": result}
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса агентов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics")
async def get_statistics():
    """Получение статистики работы"""
    if not supervisor:
        raise HTTPException(status_code=503, detail="Supervisor не инициализирован")
    
    try:
        result = await supervisor._get_statistics(period="today", metrics=["all"])
        return {"statistics": result}
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("🚀 Запуск Centralized Supervisor FastAPI сервера")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8100,  # Supervisor на порту 8100
        reload=True,
        log_level="info"
    )
