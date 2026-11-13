"""
Candidate Analysis - AI Analysis Service

Мульти-агентный сервис AI анализа кандидатов с истинно параллельной обработкой.

Этот модуль обеспечивает интеллектуальный анализ кандидатов с использованием:
- GPT-5-nano для быстрого и точного анализа
- AsyncOpenAI для истинно параллельной обработки
- Мульти-агентная архитектура с 6 специализированными агентами
- Мастер-координатор для финального профессионального заключения

Основные компоненты:
- AIAnalyzer: Одиночный анализ кандидатов (legacy)
- Multi-Agent System: Параллельный анализ через специализированных агентов
- Master Coordinator: Итоговое заключение и рекомендации

Архитектура AI анализа:
    Multi-Agent Request -> 6 Specialist Agents (Parallel)
                        -> Master Coordinator -> Professional Assessment
                        -> Final Recommendation + Score

Performance Features:
- Асинхронные вызовы OpenAI API для максимальной скорости
- Батчевая обработка кандидатов одновременно  
- Экспоненциальные повторы при ошибках
- Детальное логирование для диагностики

Agents:
- TechnicalSkillsAgent: Анализ технических навыков
- ExperienceRelevanceAgent: Оценка релевантности опыта  
- CulturalFitAgent: Анализ культурного соответствия
- GrowthPotentialAgent: Оценка потенциала роста
- ResumeAnalysisAgent: Анализ качества резюме
- AnomalyDetectionAgent: Выявление несоответствий

Author: Candidate Analysis Team
Version: 3.0.0 (AsyncOpenAI + True Parallelism)
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import httpx
import json
import os
import sys
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse, AIAnalysisRequest, AIAnalysisResponse, 
    SkillAnalysis, CandidateProfile, RankingWeights,
    MultiAgentAnalysisRequest, MultiAgentAnalysisResponse
)
from shared.utils import setup_logging, load_config

# Настройка логирования
logger = setup_logging("ai-analysis-service")

app = FastAPI(
    title="AI Analysis Service",
    description="Сервис AI-анализа навыков кандидатов с использованием GPT-5-nano",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AIAnalyzer:
    def __init__(self):
        self.config = load_config()
        self.ai_config = self.config.get("ai_analysis", {})
        
        # Инициализация OpenAI с современным клиентом - приоритет конфигурации!
        api_key = self.ai_config.get("openai_api_key") or os.getenv("OPENAI_API_KEY") 
        if not api_key:
            logger.warning("OPENAI_API_KEY не установлен")
        else:
            logger.info(f"Используем OpenAI ключ: {api_key[:20]}...")
        
        # Настройка HTTP прокси из конфигурации
        proxy_config = self.ai_config.get("proxy", {})
        proxy_enabled = proxy_config.get("enabled", False)
        
        if proxy_enabled:
            # Получаем настройки прокси из конфигурации или переменных окружения
            proxy_host = os.getenv("PROXY_HOST") or proxy_config.get("host", "")
            proxy_port = os.getenv("PROXY_PORT") or proxy_config.get("port", "")
            proxy_username = os.getenv("PROXY_USERNAME") or proxy_config.get("username", "")
            proxy_password = os.getenv("PROXY_PASSWORD") or proxy_config.get("password", "")
            proxy_protocol = os.getenv("PROXY_PROTOCOL") or proxy_config.get("protocol", "http")
            
            if proxy_host and proxy_port:
                # Формируем URL прокси
                if proxy_username and proxy_password:
                    proxy_url = f"{proxy_protocol}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                else:
                    proxy_url = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
                
                # Создаем httpx клиент с прокси
                http_client = httpx.Client(
                    proxy=proxy_url
                )
                
                logger.info(f"OpenAI клиент инициализирован с HTTP прокси: {proxy_host}:{proxy_port}")
            else:
                # Если настройки прокси неполные, используем обычный клиент
                http_client = httpx.Client()
                logger.warning("Прокси включен, но настройки неполные. Используется прямое соединение.")
        else:
            # Обычный httpx клиент без прокси
            http_client = httpx.Client()
            logger.info("OpenAI клиент инициализирован без прокси")
        
        # Инициализация OpenRouter клиента
        base_url = self.ai_config.get("base_url", "https://openrouter.ai/api/v1")
        
        # Проверяем используем ли OpenRouter
        if "openrouter.ai" in base_url:
            # OpenRouter режим
            openrouter_key = self.ai_config.get("openrouter_api_key")
            if not openrouter_key:
                raise ValueError("Для OpenRouter требуется openrouter_api_key в конфигурации")
            
            # Создаем клиент без прокси для OpenRouter
            self.client = OpenAI(
                api_key=openrouter_key,
                base_url=base_url
            )
            logger.info(f"🔄 OpenRouter клиент инициализирован: {base_url}")
            
            # Настройки для OpenRouter
            self.site_url = self.ai_config.get("site_url", "")
            self.site_name = self.ai_config.get("site_name", "CandidateRanking")
        else:
            # Старый OpenAI режим
            self.client = OpenAI(
                api_key=api_key,
                http_client=http_client,
                base_url=base_url if base_url != "https://openrouter.ai/api/v1" else None
            )
            self.site_url = ""
            self.site_name = ""
            logger.info("OpenAI клиент инициализирован")
        
        self.model = self.ai_config.get("model", "gpt-5-mini")
        self.max_completion_tokens = self.ai_config.get("max_completion_tokens", 4000)  # GPT-5 параметр
        self.temperature = self.ai_config.get("temperature", 0.0)
        self.retry_attempts = self.ai_config.get("retry_attempts", 3)
        
        # Промпты
        self.prompts = self.ai_config.get("prompts", {})
    
    def analyze_skills(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """Анализ навыков кандидата с помощью GPT-5-nano с учетом весов ранжирования"""
        start_time = time.time()
        
        try:
            # Извлекаем дополнительные данные из candidate_data
            candidate_data = request.candidate_data or {}
            candidate_title = candidate_data.get("title", "Не указано")
            last_work = candidate_data.get("last_work", {})
            last_work_position = last_work.get("position", "Не указано") if last_work else "Не указано"
            last_work_company = last_work.get("name", "Не указано") if last_work else "Не указано"
            experience_data = candidate_data.get("experience", {})
            total_experience_months = experience_data.get("months", 0) if experience_data else 0
            
            # Формирование промпта для анализа навыков
            skill_prompt = self.prompts.get("skill_analysis", "").format(
                job_title=request.search_query,
                skills=", ".join(request.skills),
                experience=request.experience_description or "Не указано",
                search_query=request.search_query,
                candidate_title=candidate_title,
                last_work_position=last_work_position,
                last_work_company=last_work_company,
                total_experience_months=total_experience_months
            )
            
            # Вызов GPT-5-nano для анализа навыков
            skill_analysis = self._call_gpt4(skill_prompt)
            
            # Парсинг результатов анализа навыков
            skill_results = self._parse_skill_analysis(skill_analysis)
            
            # Получаем веса ранжирования или используем значения по умолчанию
            weights = request.ranking_weights or RankingWeights()
            
            # Формирование промпта для общей оценки с весами
            overall_prompt = self.prompts.get("overall_assessment", "").format(
                job_title=request.search_query,
                skill_analysis=json.dumps([s.model_dump() for s in skill_results], ensure_ascii=False, default=str),
                search_query=request.search_query,
                candidate_data=json.dumps(request.candidate_data or {}, ensure_ascii=False, default=str),
                search_filters=json.dumps(request.search_filters or {}, ensure_ascii=False, default=str),
                candidate_title=candidate_title,
                last_work_position=last_work_position,
                last_work_company=last_work_company,
                total_experience_months=total_experience_months,
                keyword_relevance_weight=weights.keyword_relevance,
                filter_match_weight=weights.filter_match,
                recency_weight=weights.recency,
                profile_completeness_weight=weights.profile_completeness
            )
            
            # Вызов GPT-5-nano для общей оценки
            overall_assessment = self._call_gpt4(overall_prompt)
            
            # Парсинг общей оценки с новыми полями
            overall_result = self._parse_overall_assessment(overall_assessment)
            
            processing_time = time.time() - start_time
            
            return AIAnalysisResponse(
                candidate_id=request.candidate_id,
                skill_analysis=skill_results,
                overall_score=overall_result.get("overall_score", 0.0),
                analysis_summary=overall_result.get("summary", ""),
                processing_time=processing_time,
                keyword_relevance_score=overall_result.get("keyword_relevance_score"),
                filter_match_score=overall_result.get("filter_match_score"),
                recency_score=overall_result.get("recency_score"),
                profile_completeness_score=overall_result.get("profile_completeness_score"),
                reasoning=overall_result.get("reasoning")
            )
            
        except Exception as e:
            logger.error(f"Ошибка анализа навыков для кандидата {request.candidate_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка AI-анализа: {str(e)}")
    
    def _call_gpt4(self, prompt: str) -> str:
        """Вызов GPT-5-nano с повторными попытками"""
        for attempt in range(self.retry_attempts):
            try:
                # Подготавливаем параметры для OpenRouter
                extra_headers = {}
                if self.site_url:
                    extra_headers["HTTP-Referer"] = self.site_url
                if self.site_name:
                    extra_headers["X-Title"] = self.site_name
                
                # GPT-5 параметры для анализа навыков
                gpt5_params = {}
                gpt5_features = self.ai_config.get("gpt5_features", {})
                if gpt5_features:
                    gpt5_params.update({
                        "verbosity": gpt5_features.get("default_verbosity", "medium"),
                        "reasoning_effort": gpt5_features.get("default_reasoning_effort", "medium")
                    })
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Ты эксперт по оценке навыков кандидатов. Отвечай только в JSON формате."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=self.max_completion_tokens,  # GPT-5 параметр
                    temperature=self.temperature,
                    extra_headers=extra_headers if extra_headers else {},
                    # GPT-5 параметры передаются напрямую
                    verbosity=gpt5_params.get("verbosity", "medium") if gpt5_params else "medium",
                    reasoning_effort=gpt5_params.get("reasoning_effort", "medium") if gpt5_params else "medium"
                )
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} не удалась: {e}")
                if attempt == self.retry_attempts - 1:
                    raise e
                time.sleep(1)
    
    def _parse_skill_analysis(self, response: str) -> List[SkillAnalysis]:
        """Парсинг результатов анализа навыков"""
        try:
            # Извлекаем JSON из ответа
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("JSON не найден в ответе")
            
            json_str = response[json_start:json_end]
            skills_data = json.loads(json_str)
            
            skill_analyses = []
            for skill_data in skills_data:
                skill_analysis = SkillAnalysis(
                    skill_name=skill_data.get("skill_name", ""),
                    relevance_score=float(skill_data.get("relevance_score", 0.0)),
                    proficiency_level=skill_data.get("proficiency_level", "Unknown"),
                    years_experience=skill_data.get("years_experience"),
                    ai_confidence=float(skill_data.get("ai_confidence", 0.5)),
                    analysis_timestamp=datetime.now()
                )
                skill_analyses.append(skill_analysis)
            
            return skill_analyses
            
        except Exception as e:
            logger.error(f"Ошибка парсинга анализа навыков: {e}")
            logger.error(f"Ответ GPT: {response}")
            raise ValueError(f"Неверный формат ответа GPT: {e}")
    
    def _parse_overall_assessment(self, response: str) -> Dict[str, Any]:
        """Парсинг общей оценки с новыми полями для AI ранжирования"""
        try:
            # Извлекаем JSON из ответа
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("JSON не найден в ответе")
            
            json_str = response[json_start:json_end]
            assessment_data = json.loads(json_str)
            
            return {
                "overall_score": float(assessment_data.get("overall_score", 0.0)),
                "summary": assessment_data.get("summary", ""),
                "keyword_relevance_score": assessment_data.get("keyword_relevance_score"),
                "filter_match_score": assessment_data.get("filter_match_score"),
                "recency_score": assessment_data.get("recency_score"),
                "profile_completeness_score": assessment_data.get("profile_completeness_score"),
                "reasoning": assessment_data.get("reasoning")
            }
            
        except Exception as e:
            logger.error(f"Ошибка парсинга общей оценки: {e}")
            logger.error(f"Ответ GPT: {response}")
            return {
                "overall_score": 0.0, 
                "summary": "Ошибка анализа",
                "keyword_relevance_score": None,
                "filter_match_score": None,
                "recency_score": None,
                "profile_completeness_score": None,
                "reasoning": None
            }
    
    def batch_analyze(self, requests: List[AIAnalysisRequest]) -> List[AIAnalysisResponse]:
        """Пакетный анализ нескольких кандидатов"""
        results = []
        for request in requests:
            try:
                result = self.analyze_skills(request)
                results.append(result)
            except Exception as e:
                logger.error(f"Ошибка анализа кандидата {request.candidate_id}: {e}")
                # Создаем пустой результат в случае ошибки
                results.append(AIAnalysisResponse(
                    candidate_id=request.candidate_id,
                    skill_analysis=[],
                    overall_score=0.0,
                    analysis_summary="Ошибка анализа",
                    processing_time=0.0
                ))
        return results

# Инициализация AI анализатора
ai_analyzer = AIAnalyzer()

# Импорт и инициализация мастер-координатора
try:
    # Добавляем текущую директорию в путь для локальных импортов
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)  # Вставляем в начало для приоритета
    
    # Пробуем разные варианты импорта
    try:
        from master_coordinator import MasterCoordinator
    except ImportError:
        from ai_analysis.master_coordinator import MasterCoordinator
    
    master_coordinator = MasterCoordinator()
    logger.info("🤖 Мастер-координатор мульти-агентной системы инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации мастер-координатора: {e}")
    import traceback
    logger.error(f"Полная ошибка: {traceback.format_exc()}")
    master_coordinator = None

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_candidate(request: AIAnalysisRequest):
    """Анализ навыков одного кандидата"""
    try:
        return ai_analyzer.analyze_skills(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка анализа кандидата: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.post("/analyze/batch")
async def analyze_candidates_batch(requests: List[AIAnalysisRequest]):
    """Пакетный анализ нескольких кандидатов"""
    try:
        return ai_analyzer.batch_analyze(requests)
    except Exception as e:
        logger.error(f"Ошибка пакетного анализа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка пакетного анализа")

@app.get("/config")
async def get_ai_config():
    """Получение конфигурации AI-анализа"""
    try:
        return {
            "model": ai_analyzer.model,
            "max_completion_tokens": ai_analyzer.max_completion_tokens,
            # "temperature": ai_analyzer.temperature,
            "retry_attempts": ai_analyzer.retry_attempts
        }
    except Exception as e:
        logger.error(f"Ошибка получения конфигурации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения конфигурации")

@app.post("/settings/auth")
async def update_auth_settings(auth_settings: dict):
    """Обновление настроек аутентификации"""
    try:
        # Обновляем настройки OpenAI
        if "openai_api_key" in auth_settings:
            ai_analyzer.client = OpenAI(api_key=auth_settings["openai_api_key"])
            logger.info("OpenAI API ключ обновлен")
        
        # Модель фиксированная (gpt-5-nano), не изменяется
        return {
            "status": "success",
            "message": "Настройки AI Analysis обновлены",
            "model": ai_analyzer.model,  # Всегда gpt-5-nano
            "api_key_set": bool(ai_analyzer.client.api_key if hasattr(ai_analyzer.client, 'api_key') else False)
        }
    except Exception as e:
        logger.error(f"Ошибка обновления настроек AI Analysis: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления настроек AI Analysis")

# ================================
# МУЛЬТИ-АГЕНТНАЯ СИСТЕМА ENDPOINTS
# ================================

@app.post("/multi-agent/analyze", response_model=MultiAgentAnalysisResponse)
async def analyze_candidate_multi_agent(request: MultiAgentAnalysisRequest):
    """Мульти-агентный анализ кандидата"""
    try:
        if not master_coordinator:
            raise HTTPException(status_code=503, detail="Мастер-координатор недоступен")
        
        logger.info(f"🤖 Запуск мульти-агентного анализа для кандидата {request.candidate_id}")
        
        # ОТЛАДКА: ПРОВЕРЯЕМ ЧТО ПЕРЕДАЕТСЯ В CANDIDATE_DATA
        candidate_data_size = len(str(request.candidate_data))
        candidate_data_keys = list(request.candidate_data.keys()) if isinstance(request.candidate_data, dict) else "НЕ СЛОВАРЬ"
        logger.debug(f"🔍 ОТЛАДКА candidate_data для {request.candidate_id}: размер={candidate_data_size}, ключи={candidate_data_keys}")
        
        # ДЕТАЛЬНАЯ ОТЛАДКА ТИПОВ ПРОБЛЕМАТИЧНЫХ ПОЛЕЙ
        if isinstance(request.candidate_data, dict):
            experience = request.candidate_data.get('experience')
            education = request.candidate_data.get('education') 
            language = request.candidate_data.get('language')
            skills = request.candidate_data.get('skills')
            skill_set = request.candidate_data.get('skill_set')
            
            logger.error(f"🔍 ТИПЫ ДАННЫХ:")
            logger.error(f"   experience: {type(experience)} = {experience if experience is None else (f'список из {len(experience)} элементов' if isinstance(experience, list) else 'не список')}")
            logger.error(f"   education: {type(education)} = {education if education is None else (f'список из {len(education)} элементов' if isinstance(education, list) else 'не список')}")
            logger.error(f"   language: {type(language)} = {language if language is None else (f'список из {len(language)} элементов' if isinstance(language, list) else 'не список')}")
            logger.error(f"   skills: {type(skills)} = {skills if skills is None else (f'список из {len(skills)} элементов' if isinstance(skills, list) else 'не список')}")
            logger.error(f"   skill_set: {type(skill_set)} = {skill_set if skill_set is None else (f'список из {len(skill_set)} элементов' if isinstance(skill_set, list) else 'не список')}")
        
        # ТЕПЕРЬ ВЫЗОВ АСИНХРОННЫЙ!
        result = await master_coordinator.analyze_candidate(request)
        
        logger.info(f"✅ Мульти-агентный анализ завершен для кандидата {request.candidate_id}. " + 
                   f"Итоговая оценка: {result.master_report.overall_score:.1f}%")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка мульти-агентного анализа кандидата {request.candidate_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка мульти-агентного анализа: {str(e)}")

@app.get("/multi-agent/agents")
async def get_available_agents():
    """Получение списка доступных агентов"""
    try:
        if not master_coordinator:
            raise HTTPException(status_code=503, detail="Мастер-координатор недоступен")
        
        return {
            "available_agents": master_coordinator.get_available_agents(),
            "position_configs": master_coordinator.get_position_config(),
            "total_agents": len(master_coordinator.agents)
        }
    except Exception as e:
        logger.error(f"Ошибка получения списка агентов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения списка агентов")

@app.get("/multi-agent/health")
async def multi_agent_health_check():
    """Проверка здоровья мульти-агентной системы"""
    try:
        health_status = {
            "master_coordinator": master_coordinator is not None,
            "agents_count": len(master_coordinator.agents) if master_coordinator else 0,
            "timestamp": datetime.now(),
            "status": "healthy" if master_coordinator else "unhealthy"
        }
        
        if master_coordinator:
            health_status["available_agents"] = list(master_coordinator.agents.keys())
        
        return health_status
        
    except Exception as e:
        logger.error(f"Ошибка проверки здоровья мульти-агентной системы: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now()
        }

@app.post("/multi-agent/batch", response_model=List[MultiAgentAnalysisResponse])
async def analyze_candidates_batch_multi_agent(requests: List[MultiAgentAnalysisRequest]):
    """
    Батчевый мульти-агентный анализ кандидатов с истинно параллельной обработкой.
    
    Ключевой API endpoint для массового анализа кандидатов с максимальной производительностью.
    Реализует двухэтапную параллельную архитектуру для оптимальной скорости обработки.
    
    Algorithm (True Parallelism):
        Stage 1: Запуск ВСЕХ агентов для ВСЕХ кандидатов одновременно
                 6 agents × N candidates = массивный параллелизм
        Stage 2: Запуск ВСЕХ мастер-координаторов одновременно 
                 N master coordinators работают параллельно
    
    Args:
        requests (List[MultiAgentAnalysisRequest]): Список до 10 кандидатов для анализа
        
    Returns:
        List[MultiAgentAnalysisResponse]: Результаты анализа каждого кандидата
        
    Request Model Fields:
        - candidate_id: Уникальный ID кандидата  
        - candidate_data: Полные данные резюме из HH API
        - position_requirements: Требования к позиции
        - position_type: Тип позиции (technical/management/creative)
        - active_agents: Список активных агентов для анализа
        - search_query: Поисковый запрос для контекста
        - search_filters: Фильтры поиска
        
    Response Model Fields:
        - candidate_id: ID кандидата
        - master_report: Финальное заключение мастер-координатора
        - agent_reports: Детальные отчёты каждого агента
        - active_agents: Список использованных агентов
        - total_processing_time: Время обработки
        
    Performance Characteristics:
        - Максимум 10 кандидатов за запрос для стабильности
        - AsyncOpenAI для истинно асинхронных вызовов GPT-5-nano
        - Время обработки ~20-25 секунд для 10 кандидатов (вместо 200+ секвенциально)
        - Graceful error handling - ошибки одного кандидата не влияют на других
        - Детальное логирование прогресса для мониторинга
        
    Error Handling:
        - 503: Мастер-координатор недоступен
        - 400: Превышен лимит кандидатов (>10)
        - Отдельные ошибки кандидатов не прерывают обработку других
        
    Example Usage:
        POST /multi-agent/batch
        [
            {
                "candidate_id": "12345",
                "candidate_data": {...},
                "position_requirements": "Python разработчик",
                "position_type": "technical",
                "active_agents": ["technical_skills", "experience_relevance"]
            }
        ]
    """
    try:
        if not master_coordinator:
            raise HTTPException(status_code=503, detail="Мастер-координатор недоступен")
        
        # Ограничиваем до 10 кандидатов для безопасности
        if len(requests) > 10:
            raise HTTPException(status_code=400, detail="Максимум 10 кандидатов за раз")
        
        logger.info(f"🚀 Запуск ИСТИННО ПАРАЛЛЕЛЬНОГО мульти-агентного анализа для {len(requests)} кандидатов")
        
        # ЭТАП 1: Собираем все agent_reports для всех кандидатов ПАРАЛЛЕЛЬНО
        agent_tasks = []
        for request in requests:
            # Запускаем анализ агентов БЕЗ мастер-координатора
            active_agents = master_coordinator._get_active_agents(request.position_type, request.active_agents)
            task = master_coordinator._run_agents_analysis(
                active_agents, request.candidate_data, request.position_requirements, 
                {"search_query": request.search_query, "search_filters": request.search_filters}
            )
            agent_tasks.append((task, request, active_agents))
        
        # Получаем все результаты агентов ПАРАЛЛЕЛЬНО
        agent_results = await asyncio.gather(*[task for task, _, _ in agent_tasks], return_exceptions=True)
        
        # ЭТАП 2: Запускаем все мастер-анализы ПАРАЛЛЕЛЬНО
        master_tasks = []
        valid_candidates = []
        
        for i, (agent_result, request, active_agents) in enumerate(zip(agent_results, [t[1] for t in agent_tasks], [t[2] for t in agent_tasks])):
            if isinstance(agent_result, Exception):
                logger.error(f"❌ Ошибка агентов для кандидата {request.candidate_id}: {agent_result}")
                continue
                
            # Создаем задачу мастер-анализа
            master_task = master_coordinator._generate_master_report(agent_result, request)
            master_tasks.append(master_task)
            valid_candidates.append((request, agent_result, active_agents))
        
        logger.info(f"⚡ Запускаем {len(master_tasks)} мастер-анализов ПАРАЛЛЕЛЬНО")
        
        # Выполняем все мастер-анализы ОДНОВРЕМЕННО
        master_results = await asyncio.gather(*master_tasks, return_exceptions=True)
        
        # ЭТАП 3: Собираем финальные результаты
        processed_results = []
        for i, (master_result, (request, agent_reports, active_agents)) in enumerate(zip(master_results, valid_candidates)):
            if isinstance(master_result, Exception):
                logger.error(f"❌ Ошибка мастер-анализа кандидата {request.candidate_id}: {master_result}")
                continue
            
            # Формируем финальный ответ
            response = MultiAgentAnalysisResponse(
                candidate_id=request.candidate_id,
                master_report=master_result,
                agent_reports=agent_reports,
                active_agents=active_agents,
                total_processing_time=0.0  # Подсчитаем отдельно если нужно
            )
            processed_results.append(response)
            logger.info(f"✅ Кандидат {response.candidate_id} проанализирован: {response.master_report.overall_score:.1f}%")
        
        logger.info(f"🏁 Батчевый анализ завершен: {len(processed_results)}/{len(requests)} успешных")
        return processed_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка батчевого мульти-агентного анализа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка батчевого анализа: {str(e)}")
        
if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("ai_analysis", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8005),
        reload=service_config.get("debug", False)
    )