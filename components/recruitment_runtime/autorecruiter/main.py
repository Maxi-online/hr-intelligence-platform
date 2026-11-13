"""
AutoRecruiter - Автономный агент для пассивного рекрутинга

Автономный AI агент который использует LLM для планирования и принятия решений,
работая с существующими микросервисами как с инструментами.

Author: Candidate Analysis Team  
Version: 2.0.0 (AutoRecruiter Implementation)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uuid
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import setup_logging, load_config
from .models import AutoGPTTaskRequest, AutoGPTTaskResponse, AutoGPTTaskStatus
from .recruitment_runtime_agent import PassiveRecruiterAgent

# Настройка логирования
logger = setup_logging("autorecruiter")

app = FastAPI(
    title="AutoRecruiter",
    description="Автономный AI агент для пассивного рекрутинга с LLM планированием",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные компоненты
master_agent = None
active_tasks: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """Инициализация AutoGPT системы"""
    global master_agent
    
    try:
        logger.info("🤖 Инициализация AutoRecruiter...")
        
        config = load_config()
        master_agent = PassiveRecruiterAgent(config)
        await master_agent.initialize()
        
        logger.info("✅ AutoRecruiter система готова к работе")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации AutoRecruiter: {e}")
        raise

@app.get("/health")
async def health_check():
    """Проверка здоровья AutoRecruiter системы"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "master_agent": master_agent is not None,
        "active_tasks": len(active_tasks)
    }

@app.post("/api/autorecruiter/tasks", response_model=AutoGPTTaskResponse)
async def create_autorecruiter_task(request: AutoGPTTaskRequest, background_tasks: BackgroundTasks):
    """
    Создание автономной задачи для AutoRecruiter агента
    
    AutoRecruiter агент получает высокоуровневую цель и автономно планирует
    и выполняет необходимые действия используя существующие микросервисы
    """
    try:
        task_id = f"autorecruiter_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🎯 Новая AutoRecruiter задача: {task_id}")
        logger.info(f"🎯 Цель: {request.goal}")
        
        # Регистрируем задачу
        active_tasks[task_id] = {
            "id": task_id,
            "goal": request.goal,
            "context": request.context,
            "requirements": request.requirements,
            "constraints": request.constraints,
            "status": "accepted",
            "created_at": datetime.now(),
            "current_action": "planning",
            "agent_thoughts": [],
            "actions_taken": [],
            "results": None
        }
        
        # Запускаем AutoRecruiter агент в фоне
        background_tasks.add_task(execute_autorecruiter_task, task_id, request)
        
        return AutoGPTTaskResponse(
            task_id=task_id,
            status="accepted",
            message="AutoRecruiter агент начал автономное выполнение задачи",
            estimated_duration="Агент определит сам"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания AutoRecruiter задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/autorecruiter/tasks/{task_id}/status", response_model=AutoGPTTaskStatus)
async def get_autorecruiter_task_status(task_id: str):
    """Получение статуса выполнения AutoRecruiter задачи"""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        task = active_tasks[task_id]
        
        return AutoGPTTaskStatus(
            task_id=task_id,
            status=task["status"],
            current_action=task["current_action"],
            agent_thoughts=task["agent_thoughts"],
            actions_taken=task["actions_taken"],
            created_at=task["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса AutoRecruiter задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/autorecruiter/tasks/{task_id}/result")
async def get_autorecruiter_task_result(task_id: str):
    """Получение результатов AutoRecruiter задачи"""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        task = active_tasks[task_id]
        
        if task["status"] not in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="Задача еще не завершена")
        
        return {
            "task_id": task_id,
            "status": task["status"],
            "goal": task["goal"],
            "agent_thoughts": task["agent_thoughts"],
            "actions_taken": task["actions_taken"],
            "results": task["results"],
            "completed_at": task.get("completed_at"),
            "total_duration": task.get("total_duration")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения результатов AutoRecruiter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_autorecruiter_task(task_id: str, request: AutoGPTTaskRequest):
    """
    Выполнение AutoRecruiter задачи
    
    AutoRecruiter агент работает автономно:
    1. Анализирует цель через LLM
    2. Планирует необходимые действия
    3. Выполняет действия через инструменты (API микросервисов)
    4. Оценивает результаты и принимает решения о следующих шагах
    5. Повторяет цикл до достижения цели
    """
    try:
        logger.info(f"🤖 AutoRecruiter агент начинает работу над задачей {task_id}")
        
        # Обновляем статус
        active_tasks[task_id]["status"] = "in_progress"
        
        # Запускаем автономный цикл AutoRecruiter
        # Добавляем requirements и constraints в context
        enriched_context = dict(request.context) if request.context else {}
        enriched_context.update({
            "requirements": request.requirements,
            "constraints": request.constraints
        })
        
        result = await master_agent.execute_autonomous_goal(
            goal=request.goal,
            context=enriched_context,
            task_id=task_id,
            progress_callback=lambda action, thoughts: update_task_progress(task_id, action, thoughts)
        )
        
        # Сохраняем результаты
        active_tasks[task_id]["status"] = "completed"
        active_tasks[task_id]["results"] = result
        active_tasks[task_id]["completed_at"] = datetime.now()
        active_tasks[task_id]["total_duration"] = (
            active_tasks[task_id]["completed_at"] - active_tasks[task_id]["created_at"]
        ).total_seconds()
        
        logger.info(f"✅ AutoRecruiter задача {task_id} выполнена автономно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения AutoRecruiter задачи {task_id}: {e}")
        
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["completed_at"] = datetime.now()

def update_task_progress(task_id: str, action: str, thoughts: List[str]):
    """Обновление прогресса выполнения AutoRecruiter задачи"""
    if task_id in active_tasks:
        active_tasks[task_id]["current_action"] = action
        active_tasks[task_id]["agent_thoughts"].extend(thoughts)
        active_tasks[task_id]["actions_taken"].append({
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "thoughts": thoughts
        })

if __name__ == "__main__":
    import uvicorn
    
    config = load_config()
    service_config = config.get("services", {}).get("autorecruiter", {
        "host": "0.0.0.0",
        "port": 8010,
        "debug": False
    })
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8010),
        reload=service_config.get("debug", False)
    )
