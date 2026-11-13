"""
Unified LLM Service FastAPI приложение
HTTP API для единого LLM микросервиса
"""
import os

import logging
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from llm_service import UnifiedLLMService

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unified LLM Service",
    description="HTTP API для единого LLM микросервиса GPT-5",
    version="1.0.0"
)

# Глобальный экземпляр LLM Service
llm_service: UnifiedLLMService = None

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global llm_service
    logger.info("🚀 Запуск Unified LLM Service API...")
    
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
    
    llm_service = UnifiedLLMService(openai_config, db_config)
    await llm_service.initialize()
    logger.info("✅ Unified LLM Service API готова")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    global llm_service
    if llm_service:
        await llm_service.cleanup()
    logger.info("👋 Unified LLM Service API остановлена")

class GenerateRequest(BaseModel):
    agent_id: str
    message: str
    user_id: str = "api_user"
    session_id: str = None

@app.get("/")
async def root():
    """Информация о сервисе"""
    return {
        "service": "Unified LLM Service",
        "version": "1.0.0",
        "status": "active",
        "description": "Единый LLM микросервис GPT-5 для всех агентов",
        "architecture": "PostgreSQL + GPT-5 + Agent Configurations"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    if llm_service:
        status = await llm_service.get_agent_status("system")
        return {
            "status": "healthy",
            "service": "Unified LLM Service",
            "database_connected": llm_service.db_connection is not None,
            "timestamp": status.get("timestamp", "unknown")
        }
    else:
        return {"status": "initializing"}

@app.post("/generate_response")
async def generate_response(request: GenerateRequest):
    """Генерация ответа агента через Unified LLM Service"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM Service не инициализирован")
    
    try:
        response = await llm_service.generate_agent_response(
            request.agent_id,
            request.message,
            request.user_id,
            request.session_id
        )
        return {
            "response": response,
            "agent_id": request.agent_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "service": "Unified LLM Service"
        }
    except Exception as e:
        logger.error(f"❌ Ошибка генерации ответа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent_status/{agent_id}")
async def get_agent_status(agent_id: str):
    """Получение статуса агента"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM Service не инициализирован")
    
    try:
        status = await llm_service.get_agent_status(agent_id)
        return {"agent_status": status}
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса агента: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/available_agents")
async def get_available_agents():
    """Получение списка доступных агентов"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM Service не инициализирован")
    
    try:
        # Получаем список всех активных агентов из базы данных
        cursor = llm_service.db_connection.cursor()
        cursor.execute("""
            SELECT agent_id, agent_name, role, is_active
            FROM agent_configurations 
            WHERE is_active = true
            ORDER BY agent_name
        """)
        results = cursor.fetchall()
        cursor.close()
        
        agents = [
            {
                "agent_id": row[0],
                "agent_name": row[1],
                "role": row[2],
                "is_active": row[3]
            }
            for row in results
        ]
        
        return {
            "available_agents": agents,
            "total_count": len(agents)
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка агентов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("🚀 Запуск Unified LLM Service FastAPI сервера")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8102,  # Unified LLM Service на порту 8102
        reload=True,
        log_level="info"
    )
