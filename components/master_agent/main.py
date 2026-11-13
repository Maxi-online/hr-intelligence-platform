"""
Master Agent Service - Основной сервис мастер-агента

FastAPI сервис для запуска и управления мастер-агентом РЕКС.
Предоставляет REST API для взаимодействия с агентом.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .master_agent import MasterAgent
from .models import (
    MasterTaskRequest, MasterTaskResponse, MasterTaskStatus,
    ConversationMessage, MasterTaskStatusUpdate
)


def _resolve_settings_env(value):
    """Resolve required environment references in already parsed configuration."""
    import os
    import re
    if isinstance(value, dict):
        return {key: _resolve_settings_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_settings_env(item) for item in value]
    if not isinstance(value, str):
        return value
    match = re.fullmatch(r"\$\{([A-Z_][A-Z0-9_]*)(?::(int|float|bool))?\}", value)
    if match is None:
        return value
    name, kind = match.groups()
    content = os.environ.get(name)
    if content is None or not content.strip():
        raise RuntimeError(f"Required configuration variable is missing: {name}")
    if kind == "int":
        return int(content)
    if kind == "float":
        return float(content)
    if kind == "bool":
        if content.lower() not in {"true", "false", "1", "0"}:
            raise ValueError(f"Expected a boolean configuration variable: {name}")
        return content.lower() in {"true", "1"}
    return content



# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("master-agent-service")

# Создание FastAPI приложения
app = FastAPI(
    title="Master Agent (РЕКС) API",
    description="Главный координатор нейросотрудников организации",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Добавление CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production ограничить домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные
master_agent: Optional[MasterAgent] = None
config: Dict[str, Any] = {}
active_tasks: Dict[str, Dict[str, Any]] = {}
task_callbacks: Dict[str, List] = {}


# Модели запросов
class TaskCreationRequest(BaseModel):
    goal: str
    context: Dict[str, Any] = {}
    priority: str = "normal"
    deadline: Optional[str] = None
    requester: str = "api_user"
    channel: str = "api"
    constraints: List[str] = []


class ConversationRequest(BaseModel):
    message: str
    sender: str
    channel: str = "api"
    conversation_id: Optional[str] = None


class WebhookMessage(BaseModel):
    """Модель для webhook сообщений от мессенджеров"""
    channel: str
    raw_message: Dict[str, Any]


# События жизненного цикла
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервиса"""
    global master_agent, config
    
    try:
        logger.info("🚀 Запуск Master Agent сервиса...")
        
        # Загрузка конфигурации
        config = load_config()
        
        # Создание и инициализация мастер-агента
        master_agent = MasterAgent(config)
        await master_agent.initialize()
        
        # Настройка обработчиков сообщений
        if hasattr(master_agent, 'messenger'):
            master_agent.messenger.add_message_handler(handle_incoming_message)
        
        logger.info("✅ Master Agent сервис успешно запущен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Master Agent сервиса: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Завершение работы сервиса"""
    global master_agent
    
    try:
        logger.info("🛑 Завершение работы Master Agent сервиса...")
        
        if master_agent and hasattr(master_agent, 'memory_manager'):
            await master_agent.memory_manager.save_session()
        
        logger.info("✅ Master Agent сервис завершен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка завершения сервиса: {e}")


# API endpoints
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    if master_agent is None:
        raise HTTPException(status_code=503, detail="Master Agent не инициализирован")
    
    status = await master_agent.get_status()
    
    return {
        "status": "healthy",
        "service": "master_agent",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "agent_status": status
    }


@app.post("/api/master-agent/tasks", response_model=MasterTaskResponse)
async def create_task(request: TaskCreationRequest, background_tasks: BackgroundTasks):
    """Создание новой задачи для мастер-агента"""
    if master_agent is None:
        raise HTTPException(status_code=503, detail="Master Agent не инициализирован")
    
    try:
        # Создание задачи
        task_request = MasterTaskRequest(
            goal=request.goal,
            context=request.context,
            priority=request.priority,
            requester=request.requester,
            channel=request.channel,
            constraints=request.constraints
        )
        
        # Создание callback для отслеживания прогресса
        task_progress_updates = []
        
        async def progress_callback(task_id: str, status: str, messages: List[str]):
            task_progress_updates.append({
                "task_id": task_id,
                "status": status,
                "messages": messages,
                "timestamp": datetime.now().isoformat()
            })
        
        # Запуск задачи в фоне
        background_tasks.add_task(
            process_task_in_background,
            master_agent,
            task_request,
            progress_callback
        )
        
        # Возврат начального ответа
        response = MasterTaskResponse(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            status=MasterTaskStatus.RECEIVED,
            message="Задача принята к выполнению",
            estimated_duration="Анализирую...",
            assigned_agents=[]
        )
        
        # Сохранение callback для получения обновлений
        task_callbacks[response.task_id] = task_progress_updates
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Получение статуса выполнения задачи"""
    if task_id not in active_tasks and task_id not in task_callbacks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    try:
        # Получение обновлений из callback
        updates = task_callbacks.get(task_id, [])
        
        if not updates:
            return {
                "task_id": task_id,
                "status": "pending",
                "progress": 0.0,
                "messages": ["Задача в очереди"]
            }
        
        # Последнее обновление
        latest_update = updates[-1]
        
        return {
            "task_id": task_id,
            "status": latest_update["status"],
            "progress": len(updates) * 0.2,  # Примерный прогресс
            "messages": latest_update["messages"],
            "updates_count": len(updates),
            "last_update": latest_update["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """Получение результата выполнения задачи"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена или еще выполняется")
    
    try:
        task_data = active_tasks[task_id]
        
        return {
            "task_id": task_id,
            "status": task_data.get("status"),
            "result": task_data.get("result"),
            "execution_time": task_data.get("execution_time"),
            "quality_metrics": task_data.get("quality_metrics"),
            "agent_results": task_data.get("agent_results", [])
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения результата задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/master-agent/conversation")
async def handle_conversation(request: ConversationRequest):
    """Обработка диалога с мастер-агентом"""
    if master_agent is None:
        raise HTTPException(status_code=503, detail="Master Agent не инициализирован")
    
    try:
        # Создание сообщения
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"
        
        message = ConversationMessage(
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            sender=request.sender,
            recipient="master_agent",
            content=request.message,
            channel=request.channel,
            conversation_id=conversation_id
        )
        
        # Обработка сообщения
        response_message = await master_agent.handle_conversation(message)
        
        return {
            "conversation_id": conversation_id,
            "response": response_message.content,
            "timestamp": response_message.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки диалога: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/master-agent/webhook/{channel}")
async def handle_webhook(channel: str, webhook_data: WebhookMessage):
    """Обработка webhook от мессенджеров"""
    if master_agent is None or not hasattr(master_agent, 'messenger'):
        raise HTTPException(status_code=503, detail="Messenger Interface недоступен")
    
    try:
        # Обработка входящего сообщения
        message = await master_agent.messenger.handle_incoming_message(
            webhook_data.raw_message, 
            channel
        )
        
        if message:
            # Генерация ответа
            response_message = await master_agent.handle_conversation(message)
            
            # Отправка ответа обратно
            await master_agent.messenger.send_message(response_message)
            
            return {"status": "processed", "message_id": message.message_id}
        else:
            return {"status": "ignored", "reason": "Не удалось обработать сообщение"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/stats")
async def get_stats():
    """Получение статистики мастер-агента"""
    if master_agent is None:
        raise HTTPException(status_code=503, detail="Master Agent не инициализирован")
    
    try:
        # Сбор статистики со всех компонентов
        agent_stats = await master_agent.get_status()
        
        stats = {
            "master_agent": agent_stats,
            "service_uptime": (datetime.now() - agent_stats.get("uptime_start", datetime.now())).total_seconds(),
            "active_tasks_count": len(active_tasks),
            "callbacks_count": len(task_callbacks)
        }
        
        # Статистика компонентов
        if hasattr(master_agent, 'task_distributor'):
            stats["task_distributor"] = await master_agent.task_distributor.get_stats()
        
        if hasattr(master_agent, 'memory_manager'):
            stats["memory_manager"] = await master_agent.memory_manager.get_stats()
        
        if hasattr(master_agent, 'quality_controller'):
            stats["quality_controller"] = await master_agent.quality_controller.get_stats()
        
        if hasattr(master_agent, 'org_context'):
            stats["organization_context"] = await master_agent.org_context.get_stats()
        
        if hasattr(master_agent, 'messenger'):
            stats["messenger"] = await master_agent.messenger.get_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/quality/report")
async def get_quality_report(period_days: int = 7):
    """Получение отчета о качестве"""
    if master_agent is None or not hasattr(master_agent, 'quality_controller'):
        raise HTTPException(status_code=503, detail="Quality Controller недоступен")
    
    try:
        report = await master_agent.quality_controller.generate_quality_report(period_days)
        return report
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации отчета качества: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Вспомогательные функции
async def process_task_in_background(agent: MasterAgent, task_request: MasterTaskRequest, 
                                   progress_callback):
    """Обработка задачи в фоновом режиме"""
    try:
        result = await agent.process_task(task_request, progress_callback)
        
        # Сохранение результата
        active_tasks[result.task_id] = {
            "status": result.status,
            "result": result,
            "completion_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка фоновой обработки задачи: {e}")


async def handle_incoming_message(message: ConversationMessage):
    """Обработчик входящих сообщений от мессенджеров"""
    try:
        logger.info(f"📨 Получено сообщение от {message.sender}: {message.content[:50]}...")
        
        # Здесь может быть дополнительная логика обработки
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки входящего сообщения: {e}")


def load_config() -> Dict[str, Any]:
    """Загрузка конфигурации"""
    try:
        # Попытка загрузки из config/settings.yaml
        config_path = "config/settings.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = _resolve_settings_env(yaml.safe_load(f))
            logger.info(f"✅ Конфигурация загружена из {config_path}")
            return config
        
        # Базовая конфигурация
        logger.warning("⚠️ Файл конфигурации не найден, используется базовая")
        return get_default_config()
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Базовая конфигурация"""
    return {
        "master_agent": {
            "main_model": "gpt-5-mini",
            "fast_model": "gpt-5-mini",
            "max_completion_tokens": 4000,
            "temperature": 0.2,
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "base_url": "https://openrouter.ai/api/v1",
            "proxy": {
                "enabled": False
            },
            "gpt5_features": {
                "default_verbosity": "medium",
                "default_reasoning_effort": "medium"
            },
            "memory": {
                "chroma_persist_directory": "data/master_memory/chroma_db",
                "embedding_model": "text-embedding-3-small"
            }
        },
        "services": {
            "master_agent": {
                "port": 8020,
                "host": "0.0.0.0"
            },
            "recruitment_runtime": {
                "port": 8010,
                "host": "localhost"
            }
        },
        "messengers": {
            "teams": {
                "enabled": False
            },
            "telegram": {
                "enabled": False
            },
            "email": {
                "enabled": False
            }
        },
        "quality_control": {
            "min_success_rate": 0.8,
            "max_response_time": 300,
            "min_user_satisfaction": 0.7,
            "escalation_failure_rate": 0.3
        }
    }


# Запуск сервиса
if __name__ == "__main__":
    # Настройка из переменных окружения или конфигурации
    host = os.getenv("MASTER_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("MASTER_AGENT_PORT", "8020"))
    
    logger.info(f"🚀 Запуск Master Agent сервиса на {host}:{port}")
    
    uvicorn.run(
        "master_agent.main:app",
        host=host,
        port=port,
        reload=False,  # В production отключить
        log_level="info"
    )
