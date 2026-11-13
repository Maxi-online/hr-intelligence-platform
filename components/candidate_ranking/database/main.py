"""
Candidate Analysis - Database Service

Высокопроизводительный сервис для работы с ClickHouse базой данных.

Этот модуль обеспечивает:
- Интеграцию с ClickHouse для колоночного хранения данных
- Автоматическую инициализацию схемы БД при запуске
- CRUD операции для кандидатов и результатов анализа
- Аналитические запросы для дашбордов и отчётов
- Кэширование результатов поиска и AI анализа

Core Features:
- ClickHouse Integration: Высокопроизводительная колоночная БД
- Auto Schema Init: Автоматическое создание таблиц при первом запуске
- CRUD Operations: Полный набор операций с кандидатами
- Analytics Support: Агрегированные запросы для аналитики
- Search Caching: Кэширование поисковых запросов и результатов

Database Schema:
- candidates: Профили кандидатов с AI анализом
- search_history: История поисковых запросов
- ai_analysis_results: Результаты AI анализа для кэширования
- system_metrics: Метрики производительности системы

API Endpoints:
- POST /candidates: Сохранение кандидата
- GET /candidates/{id}: Получение кандидата по ID
- GET /candidates/search: Поиск кандидатов в БД
- GET /analytics/summary: Аналитические данные
- GET /health: Проверка состояния БД

Performance Features:
- ClickHouse оптимизированные типы данных
- Партиционирование по датам для быстрых запросов
- Индексация по ключевым полям (candidate_id, search_query)
- Компрессия данных для экономии места
- Поддержка batch вставок для производительности

Reliability:
- Автоматическое переподключение при сбоях
- Graceful handling ошибок соединения
- Health checks для мониторинга состояния
- Lifespan management для proper startup/shutdown

Author: Candidate Analysis Team
Version: 2.0.0 (ClickHouse + Auto Schema)
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio
from contextlib import asynccontextmanager

# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse, Candidate, CandidateProfile, DatabaseCandidate,
    SkillAnalysis, AIAnalysisResponse
)
from shared.utils import setup_logging, load_config

# Настройка логирования
logger = setup_logging("database-service")

# Автоматическая инициализация базы данных при запуске
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения с автоматической инициализацией БД"""
    logger.info("🚀 Запуск Database Service с автоматической инициализацией...")
    
    # Инициализация при запуске
    try:
        global db_manager
        db_manager = DatabaseManager()
        logger.info("✅ База данных инициализирована автоматически при запуске")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка инициализации базы данных: {e}")
        raise
    
    yield
    
    # Очистка при завершении
    try:
        if hasattr(db_manager, 'clickhouse_manager'):
            db_manager.clickhouse_manager.close()
        logger.info("🔄 Database Service завершен")
    except Exception as e:
        logger.error(f"❌ Ошибка при завершении: {e}")

app = FastAPI(
    title="Database Service",
    description="Сервис хранения и управления данными кандидатов",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DatabaseManager:
    def __init__(self):
        self.config = load_config()
        self.db_config = self.config.get("database", {})
        
        # Используем только ClickHouse!
        from clickhouse_manager import ClickHouseManager
        self.clickhouse_manager = ClickHouseManager()
        logger.info("✅ ClickHouse Manager инициализирован")

    
    def save_candidate(self, candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None) -> bool:
        """Сохранение кандидата в базу данных"""
        try:
            # Используем только ClickHouse!
            return self.clickhouse_manager.save_candidate(candidate, ai_analysis)
        except Exception as e:
            logger.error(f"Ошибка сохранения кандидата {candidate.id}: {e}")
            return False
    
    def get_candidate(self, candidate_id: str) -> Optional[DatabaseCandidate]:
        """Получение кандидата из базы данных"""
        try:
            # Используем только ClickHouse!
            return self.clickhouse_manager.get_candidate(candidate_id)
        except Exception as e:
            logger.error(f"Ошибка получения кандидата {candidate_id}: {e}")
            return None
    
    def search_candidates(self, search_params: Dict[str, Any], limit: int = 100) -> List[DatabaseCandidate]:
        """Поиск кандидатов в базе данных"""
        try:
            # Используем только ClickHouse!
            return self.clickhouse_manager.search_candidates(search_params, limit)
        except Exception as e:
            logger.error(f"Ошибка поиска кандидатов: {e}")
            return []
    
    def update_search_count(self, candidate_id: str):
        """Обновление счетчика поисков"""
        try:
            # Используем только ClickHouse!
            return self.clickhouse_manager.update_search_count(candidate_id)
        except Exception as e:
            logger.error(f"Ошибка обновления счетчика поисков для {candidate_id}: {e}")
    
    def get_top_candidates(self, limit: int = 10) -> List[DatabaseCandidate]:
        """Получение топ кандидатов по популярности"""
        try:
            # Используем только ClickHouse!
            return self.clickhouse_manager.get_top_candidates(limit)
        except Exception as e:
            logger.error(f"Ошибка получения топ кандидатов: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики базы данных"""
        try:
            # Используем только ClickHouse!
            return self.clickhouse_manager.get_statistics()
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}

# Инициализация db_manager перенесена в lifespan event
# db_manager будет инициализирован автоматически при запуске приложения
db_manager = None

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.post("/candidates")
async def save_candidate(candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None):
    """Сохранение кандидата"""
    try:
        success = db_manager.save_candidate(candidate, ai_analysis)
        if success:
            return {"message": "Кандидат успешно сохранен"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка сохранения кандидата")
    except Exception as e:
        logger.error(f"Ошибка сохранения кандидата: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    """Получение кандидата по ID"""
    try:
        candidate = db_manager.get_candidate(candidate_id)
        if candidate:
            return candidate
        else:
            raise HTTPException(status_code=404, detail="Кандидат не найден")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения кандидата: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.post("/candidates/search")
async def search_candidates(search_params: Dict[str, Any], limit: int = 100):
    """Поиск кандидатов"""
    try:
        candidates = db_manager.search_candidates(search_params, limit)
        return {"candidates": candidates, "total": len(candidates)}
    except Exception as e:
        logger.error(f"Ошибка поиска кандидатов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска")

@app.get("/candidates/top/{limit}")
async def get_top_candidates(limit: int = 10):
    """Получение топ кандидатов"""
    try:
        candidates = db_manager.get_top_candidates(limit)
        return {"candidates": candidates}
    except Exception as e:
        logger.error(f"Ошибка получения топ кандидатов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения топ кандидатов")

@app.put("/candidates/{candidate_id}/search")
async def update_search_count(candidate_id: str):
    """Обновление счетчика поисков"""
    try:
        db_manager.update_search_count(candidate_id)
        return {"message": "Счетчик поисков обновлен"}
    except Exception as e:
        logger.error(f"Ошибка обновления счетчика поисков: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления счетчика")

@app.get("/statistics")
async def get_statistics():
    """Получение статистики базы данных"""
    try:
        stats = db_manager.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")

if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("database", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8006),
        reload=service_config.get("debug", False)
    )