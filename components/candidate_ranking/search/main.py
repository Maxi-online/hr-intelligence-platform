"""
Candidate Analysis - Search Service

Основной сервис поиска и оркестрации кандидатов.

Этот модуль является центральным компонентом системы Candidate Analysis, который:
- Организует поиск кандидатов через HeadHunter API
- Координирует AI-анализ резюме в истинно параллельном режиме
- Интегрирует результаты поиска, ранжирования и анализа
- Предоставляет API для frontend'а с детальной статистикой

Основные возможности:
- Интеграция с HeadHunter.ru API для поиска кандидатов
- Многопоточная обработка резюме для высокой производительности
- Батчевая отправка кандидатов на AI-анализ
- Сбор и предоставление статистики HH API (429/503 ошибки)
- Кэширование и оптимизация запросов

Архитектура:
    SearchService -> HH API Service -> HeadHunter.ru
                  -> AI Analysis Service -> OpenAI GPT-4.1-nano
                  -> Database Service -> ClickHouse

Author: Candidate Analysis Team
Version: 2.0.0
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional, Tuple
import requests
import httpx
import asyncio
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse,
    SearchRequest,
    Candidate,
    AIAnalysisRequest,
    AIAnalysisResponse,
    CandidateProfile,
    DatabaseCandidate,
    MultiAgentAnalysisRequest,
    MultiAgentAnalysisResponse,
    VacancyTopRequest,
    VacancyTopResponse,
    RankingRequest
)
from shared.utils import setup_logging, load_config

# Настройка логирования
logger = setup_logging("search-service")

# --- FastAPI приложение ---
app = FastAPI(
    title="Search Service",
    description="Сервис для поиска кандидатов, orchestrating HH.ru API, AI Analysis, and Database services.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchService:
    """
    Основной класс сервиса поиска и оркестрации кандидатов.
    
    Координирует взаимодействие между различными микросервисами для обеспечения
    полного цикла поиска, анализа и ранжирования кандидатов.
    
    Архитектурные особенности:
    - Ленивая инициализация URL сервисов для поддержки Docker и локального окружения
    - Батчевая обработка кандидатов для оптимизации производительности
    - Детальный сбор статистики HH API для мониторинга
    - Graceful handling ошибок и recovery механизмы
    
    Attributes:
        config (dict): Конфигурация из settings.yaml
        services_config (dict): Конфигурация микросервисов
        logger: Логгер для отслеживания операций
        _hh_api_url (str): URL HeadHunter API сервиса (lazy)
        _ai_analysis_url (str): URL AI Analysis сервиса (lazy) 
        _database_url (str): URL Database сервиса (lazy)
    """
    
    def __init__(self):
        """
        Инициализация сервиса поиска.
        
        Загружает конфигурацию и подготавливает lazy-инициализацию URL сервисов.
        """
        self.config = load_config()
        self.services_config = self.config.get("services", {})
        self.logger = logger
        # Инициализация URL будет происходить по требованию
        self._hh_api_url = None
        self._ranking_url = None
        self._ai_analysis_url = None
        self._database_url = None

    def _get_service_url(self, service_name: str, is_docker: bool) -> str:
        """
        Получение URL микросервиса с поддержкой Docker и локального окружения.
        
        Args:
            service_name (str): Имя сервиса (hh_api, ai_analysis, database)
            is_docker (bool): Флаг Docker окружения
            
        Returns:
            str: Полный URL сервиса (http://host:port)
            
        Raises:
            ValueError: Если порт для сервиса не настроен
            
        Note:
            В Docker используется docker_host, локально - host (localhost)
        """
        conf = self.services_config.get(service_name, {})
        host = conf.get('docker_host') if is_docker else conf.get('host', 'localhost')
        port = conf.get('port')
        if not port:
            raise ValueError(f"Порт для сервиса {service_name} не настроен")
        return f"http://{host}:{port}"

    @property
    def hh_api_url(self):
        if self._hh_api_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._hh_api_url = self._get_service_url("hh_api", is_docker)
        return self._hh_api_url

    # ranking_url больше не нужен - используем только AI ранжирование

    @property
    def ai_analysis_url(self):
        if self._ai_analysis_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._ai_analysis_url = self._get_service_url("ai_analysis", is_docker)
        return self._ai_analysis_url

    @property
    def ranking_url(self):
        if self._ranking_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._ranking_url = self._get_service_url("ranking", is_docker)
        return self._ranking_url

    @property
    def database_url(self):
        if self._database_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._database_url = self._get_service_url("database", is_docker)
        return self._database_url

    def _get_full_resume_data(self, candidate_id: str) -> Tuple[Optional[Dict], Dict[str, Any]]:
        """
        Получение детальных данных резюме из HeadHunter API с умной retry логикой.
        
        Этот метод обеспечивает устойчивое получение полных данных резюме с:
        - Экспоненциальными повторами при ошибках 429 (Too Many Requests)
        - Анализом качества полученных данных
        - Детальной статистикой для мониторинга HH API
        
        Args:
            candidate_id (str): Уникальный идентификатор кандидата в HH
            
        Returns:
            Tuple[Optional[Dict], Dict[str, Any]]:
                - Optional[Dict]: Полные данные резюме или None при ошибке
                - Dict[str, Any]: Статус API запроса с детальной информацией
                
        API Status Dict содержит:
            - success (bool): Успешность запроса
            - status_code (int): HTTP статус код ответа
            - attempts (int): Количество попыток
            - error_message (str): Сообщение об ошибке (если есть)
            - data_quality (str): Качество данных (good/partial/poor/unknown)
            
        Data Quality Assessment:
            - "good": Есть "О себе", опыт и образование
            - "partial": Есть некоторые из ключевых полей
            - "poor": Только базовая информация
            - "unknown": Ошибка при оценке качества
            
        Retry Strategy:
            - Максимум 3 попытки
            - Экспоненциальная задержка: 1s, 2s, 4s
            - Jitter для избежания thundering herd
            - Graceful handling 429/503/500 ошибок
        """
        import random
        import time
        
        max_retries = 3
        base_delay = 1.0
        api_status = {
            "success": False,
            "status_code": None,
            "attempts": 0,
            "error_message": None,
            "data_quality": "unknown"
        }
        
        for attempt in range(max_retries):
            api_status["attempts"] = attempt + 1
            try:
                if attempt > 0:
                    # Экспоненциальная задержка с jitter для избежания 429
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                    self.logger.warning(f"🔄 Попытка {attempt + 1}/{max_retries} для {candidate_id}, ждем {delay:.1f}с")
                    time.sleep(delay)
                
                self.logger.info(f"🔍 Запрос полных данных резюме: {candidate_id} (попытка {attempt + 1})")
                
                url = f"{self.hh_api_url}/resume/{candidate_id}"
                response = requests.get(url, timeout=15)
                api_status["status_code"] = response.status_code

                if response.status_code == 200:
                    try:
                        full_data = response.json()
                        self.logger.info(f"✅ Данные получены для {candidate_id}: {len(str(full_data))} символов")
                        
                        # ПРОВЕРЯЕМ КАЧЕСТВО ДАННЫХ
                        if isinstance(full_data, dict):
                            has_about = bool(full_data.get('about', ''))
                            has_experience = bool(full_data.get('experience', []))
                            has_education = bool(full_data.get('education', []))
                            
                            if has_about or has_experience or has_education:
                                api_status["data_quality"] = "good"
                                self.logger.info(f"📊 Качественные данные для {candidate_id}: about={has_about}, exp={has_experience}, edu={has_education}")
                            else:
                                api_status["data_quality"] = "partial"
                                self.logger.warning(f"⚠️ Данные неполные для {candidate_id}, но используем что есть")
                        
                        api_status["success"] = True
                        return full_data, api_status
                        
                    except Exception as json_error:
                        api_status["error_message"] = f"JSON ошибка: {json_error}"
                        self.logger.error(f"❌ JSON ошибка для {candidate_id}: {json_error}")
                        if attempt == max_retries - 1:
                            return None, api_status
                        continue
                        
                elif response.status_code == 429:
                    api_status["error_message"] = "Rate limit exceeded"
                    self.logger.warning(f"🚫 HH API лимит для {candidate_id} (429), retry через {base_delay * (2 ** attempt)}s")
                    if attempt == max_retries - 1:
                        self.logger.error(f"💥 Не удалось получить данные {candidate_id} после {max_retries} попыток")
                        return None, api_status
                    continue
                    
                else:
                    api_status["error_message"] = f"HH API ошибка {response.status_code}"
                    self.logger.error(f"🚨 HH API ошибка {response.status_code} для {candidate_id}")
                    if attempt == max_retries - 1:
                        return None, api_status
                    continue
                
            except Exception as e:
                api_status["error_message"] = f"Сетевая ошибка: {e}"
                self.logger.error(f"❌ Сетевая ошибка для {candidate_id}: {e}")
                if attempt == max_retries - 1:
                    return None, api_status
                continue
        
        return None, api_status

    def _get_vacancy_responses(self, vacancy_url: str) -> Dict[str, Any]:
        """Прокси к hh_api для получения откликов по ссылке вакансии"""
        try:
            response = requests.post(f"{self.hh_api_url}/vacancy/responses", json={"vacancy_url": vacancy_url}, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Ошибка получения откликов по вакансии: {e}")
            raise HTTPException(status_code=500, detail="Ошибка получения откликов по вакансии")

    def _get_vacancy_details(self, vacancy_url: str) -> Dict[str, Any]:
        """Прокси к hh_api для получения детальной информации о вакансии"""
        try:
            response = requests.post(f"{self.hh_api_url}/vacancy/details", json={"vacancy_url": vacancy_url}, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Ошибка получения вакансии: {e}")
            raise HTTPException(status_code=500, detail="Ошибка получения вакансии")

    def _resume_to_candidate(self, resume_data: Dict[str, Any]) -> Candidate:
        """Локальная конвертация ответа HH /resume в модель Candidate (минимально совместимая)."""
        from shared.utils import parse_date, parse_salary
        resume_id = resume_data.get("id", "")
        title = resume_data.get("title", "")
        area = resume_data.get("area", {})
        experience = resume_data.get("total_experience", {})
        salary_data = resume_data.get("salary")
        updated_at = parse_date(resume_data.get("updated_at", ""))

        name = "Кандидат"
        age = resume_data.get("age")

        skills: List[str] = []
        if "skill_set" in resume_data and isinstance(resume_data["skill_set"], list):
            skills.extend([s for s in resume_data["skill_set"] if isinstance(s, str)])
        if "key_skills" in resume_data and isinstance(resume_data["key_skills"], list):
            skills.extend([s.get("name", "") for s in resume_data["key_skills"] if isinstance(s, dict)])

        last_work = {}
        if "experience" in resume_data and isinstance(resume_data["experience"], list) and resume_data["experience"]:
            last_exp = resume_data["experience"][0]
            last_work = {
                "name": last_exp.get("company", ""),
                "position": last_exp.get("position", ""),
                "description": last_exp.get("description", "")
            }

        salary = parse_salary(salary_data) if salary_data else None
        resume_url = f"https://hh.ru/resume/{resume_id}"
        photo_url = None
        if resume_data.get("photo"):
            photo_url = resume_data["photo"].get("medium", resume_data["photo"].get("small"))

        has_cover_letter = resume_data.get("has_cover_letter", False)

        return Candidate(
            id=resume_id,
            name=name,
            age=age,
            title=title,
            area=area,
            experience=experience,
            salary=salary,
            last_work=last_work,
            skills=skills,
            verified_skills=[],
            updated_at=updated_at,
            url=resume_url,
            photo_url=photo_url,
            has_cover_letter=has_cover_letter
        )

    def get_dictionaries(self) -> Dict[str, Any]:
        try:
            areas_response = requests.get(f"{self.hh_api_url}/areas", timeout=30)
            areas = areas_response.json() if areas_response.status_code == 200 else []

            roles_response = requests.get(f"{self.hh_api_url}/professional-roles", timeout=30)
            roles = roles_response.json() if roles_response.status_code == 200 else []
            
            languages_response = requests.get(f"{self.hh_api_url}/languages", timeout=30)
            languages = languages_response.json() if languages_response.status_code == 200 else []
            
            # Получаем все справочники одним запросом (если доступно)
            dictionaries_response = requests.get(f"{self.hh_api_url}/dictionaries", timeout=30)
            dictionaries = dictionaries_response.json() if dictionaries_response.status_code == 200 else {}
            
            return {
                "areas": areas, 
                "professional_roles": roles,
                "languages": languages,
                "dictionaries": dictionaries
            }
        except Exception as e:
            self.logger.error(f"Ошибка при получении справочников: {e}")
            return {}

    def _process_single_candidate(self, candidate: Candidate, search_request: SearchRequest) -> Tuple[CandidateProfile, bool]:
        """Обрабатывает одного кандидата (может выполняться параллельно)"""
        try:
            candidate_start_time = time.time()
            import threading
            thread_id = threading.current_thread().ident
            
            print(f"🎯 DEBUG PRINT: ВХОД в _process_single_candidate для кандидата {candidate.id} [Thread-{thread_id}]")
            self.logger.info(f"🎯 ПАРАЛЛЕЛЬНЫЙ ПОТОК {thread_id}: НАЧАЛО обработки кандидата {candidate.id}")  # ОТЛАДОЧНЫЙ ЛОГ
            # ПОЛУЧАЕМ ПОЛНЫЕ ДАННЫЕ РЕЗЮМЕ ИЗ HH.RU API ДЛЯ КАЖДОГО КАНДИДАТА!
            self.logger.info(f"🔍 DEBUG: Вызываем _get_full_resume_data для {candidate.id}")
            full_resume_data, api_status = self._get_full_resume_data(candidate.id)
            self.logger.info(f"🔍 DEBUG: Результат _get_full_resume_data: {bool(full_resume_data)}, API статус: {api_status}")
            print(f"🔍 DEBUG PRINT: Результат _get_full_resume_data: {bool(full_resume_data)}, API статус: {api_status}")
            
            # Проверяем есть ли кандидат в базе с завершённым анализом
            db_candidate = self._get_candidate_from_db(candidate.id)
            
            if db_candidate and db_candidate.profile.analysis_status == 'completed':
                return db_candidate.profile, True
            
            # ИСПРАВЛЕНИЕ: Создаем профиль без AI анализа (AI анализ будет в batch)
                candidate.score = 0.0
                
                profile = CandidateProfile(
                    id=candidate.id,
                    hh_data=candidate,
                    skill_analysis=[],
                    overall_ai_score=0.0,
                analysis_status='pending'  # Ожидает batch анализа
                )
            success = True  # Успешно подготовили данные
            
            # Сохраняем в базу данных
            self._save_candidate_to_db(profile)
            
            # КРИТИЧЕСКОЕ ЛОГИРОВАНИЕ: Время завершения обработки кандидата
            candidate_time = time.time() - candidate_start_time
            self.logger.info(f"✅ ПОТОК {thread_id}: ЗАВЕРШЕН кандидат {candidate.id} за {candidate_time:.2f}s, успех: {success}")
            print(f"✅ DEBUG PRINT: ЗАВЕРШЕН {candidate.id} [Thread-{thread_id}] за {candidate_time:.2f}s")
            
            return profile, success
            
        except Exception as e:
            candidate_time = time.time() - candidate_start_time
            self.logger.error(f"❌ ПОТОК {thread_id}: ОШИБКА в кандидате {candidate.id} за {candidate_time:.2f}s: {e}")
            print(f"❌ DEBUG PRINT: ОШИБКА {candidate.id} [Thread-{thread_id}] за {candidate_time:.2f}s")
            
            # Создаем профиль без AI анализа
            profile = CandidateProfile(
                id=candidate.id,
                hh_data=candidate,
                skill_analysis=[],
                overall_ai_score=0.0,
                analysis_status='failed'
            )
            self._save_candidate_to_db(profile)
            return profile, False

    def search_candidates(self, search_request: SearchRequest) -> Tuple[List[Candidate], Dict[str, Any]]:
        """
        Основной метод поиска и анализа кандидатов с истинно параллельной обработкой.
        
        Выполняет полный цикл обработки кандидатов:
        1. Поиск базовых данных через HeadHunter API
        2. Параллельное получение детальных данных резюме 
        3. Батчевая отправка на AI-анализ для максимальной эффективности
        4. Сбор подробной статистики HH API для мониторинга
        
        Args:
            search_request (SearchRequest): Параметры поиска (текст, регион, опыт и т.д.)
            
        Returns:
            Tuple[List[Candidate], Dict[str, Any]]: 
                - List[Candidate]: Список проанализированных кандидатов с AI оценками
                - Dict[str, Any]: Статистика HH API (успешные/неудачные запросы, ошибки)
                
        Raises:
            HTTPException: При ошибках HH API или AI Analysis
            
        Algorithm Flow:
            1. HH API Search → получение списка кандидатов
            2. Parallel Resume Fetch → детальные данные каждого резюме
            3. Batch AI Analysis → все кандидаты обрабатываются параллельно
            4. Results Integration → объединение данных и статистики
            
        Performance Features:
            - Батчевая обработка по 10 кандидатов для оптимизации
            - Истинно параллельный AI анализ через AsyncOpenAI
            - Детальная статистика ошибок (429, 503, 500) для диагностики
            - Graceful degradation при проблемах с HH API
            
        HH API Statistics Tracking:
            - total_requests: Общее количество запросов к HH API
            - successful_requests: Успешные запросы (200 OK)
            - status_429_errors: Ошибки превышения лимита
            - status_503_errors: Ошибки недоступности сервиса
            - rate_limit_exceeded: Общее количество превышений лимитов
            - good_data_count: Резюме с полными данными
            - partial_data_count: Резюме с частичными данными
        """
        try:
            # 1. Поиск в HH API
            search_params = search_request.model_dump(exclude_none=True)
            self.logger.info(f"Отправляем запрос к HH API с параметрами: {search_params}")
            
            hh_response = requests.get(f"{self.hh_api_url}/search", params=search_params, timeout=120)
            
            if hh_response.status_code != 200:
                raise HTTPException(status_code=hh_response.status_code, detail=f"Ошибка HH API: {hh_response.text}")
            
            hh_data = hh_response.json()
            self.logger.info(f"Получен ответ от HH API: {len(hh_data.get('candidates', []))} кандидатов")
            
            hh_candidates = [Candidate(**item) for item in hh_data.get("candidates", [])]
            self.logger.info(f"Обработано {len(hh_candidates)} кандидатов")
            
            # 2. ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА КАНДИДАТОВ БАТЧАМИ ПО 10 🚀
            start_time = time.time()
            self.logger.info(f"🚀 Начинаем параллельную обработку {len(hh_candidates)} кандидатов батчами по 10...")
            print(f"🔍 DEBUG ПОСЛЕ ЛОГГЕРА: len(hh_candidates)={len(hh_candidates)}")
            
            # Разбиваем кандидатов на батчи по 10
            batch_size = 10
            batches = [hh_candidates[i:i + batch_size] for i in range(0, len(hh_candidates), batch_size)]
            self.logger.info(f"📦 Разбили на {len(batches)} батчей по {batch_size} кандидатов")
            
            processed_profiles: List[CandidateProfile] = []
            successful_ai_analyses = 0
            
            # Отслеживание статуса HH API
            hh_api_stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "status_500_errors": 0,
                "status_429_errors": 0,
                "status_503_errors": 0,
                "rate_limit_exceeded": 0,
                "partial_data_count": 0,
                "good_data_count": 0,
                "failed_candidates": []
            }
            
            # НАСТОЯЩАЯ ПАРАЛЛЕЛЬНОСТЬ: Собираем ВСЕХ кандидатов и отправляем ОДНИМ batch запросом
            all_candidates = []
            all_requests = []
            
            for batch_num, batch in enumerate(batches, 1):
                self.logger.info(f"🔄 Подготавливаем батч {batch_num}/{len(batches)} ({len(batch)} кандидатов)")
                
                # Подготавливаем данные для каждого кандидата (без AI анализа)
                for idx, candidate in enumerate(batch):
                    try:
                        # Небольшая задержка между кандидатами для избежания 429 при массовой обработке
                        if idx > 0:  # Не делаем задержку для первого кандидата
                            import random
                            delay = random.uniform(0.2, 0.5)  # 200-500мс задержка
                            time.sleep(delay)
                        
                        # Получаем полные данные резюме
                        full_resume_data, api_status = self._get_full_resume_data(candidate.id)
                        
                        # Обновляем статистику HH API
                        hh_api_stats["total_requests"] += 1
                        if api_status["success"]:
                            hh_api_stats["successful_requests"] += 1
                            if api_status["data_quality"] == "good":
                                hh_api_stats["good_data_count"] += 1
                            elif api_status["data_quality"] == "partial":
                                hh_api_stats["partial_data_count"] += 1
                        else:
                            hh_api_stats["failed_requests"] += 1
                            hh_api_stats["failed_candidates"].append({
                                "candidate_id": candidate.id,
                                "status_code": api_status.get("status_code"),
                                "error_message": api_status.get("error_message"),
                                "attempts": api_status.get("attempts")
                            })
                            if api_status.get("status_code") == 500:
                                hh_api_stats["status_500_errors"] += 1
                            elif api_status.get("status_code") == 429:
                                hh_api_stats["status_429_errors"] += 1
                                hh_api_stats["rate_limit_exceeded"] += 1
                            elif api_status.get("status_code") == 503:
                                hh_api_stats["status_503_errors"] += 1
                                hh_api_stats["rate_limit_exceeded"] += 1
                        
                        # Проверяем есть ли кандидат в базе с завершённым анализом
                        db_candidate = self._get_candidate_from_db(candidate.id)
                        
                        if db_candidate and hasattr(db_candidate, 'analysis_status') and db_candidate.analysis_status == "completed":
                            # Используем готовый анализ из БД
                            profile = CandidateProfile(
                                id=candidate.id,  # ИСПРАВЛЕНИЕ: Добавляем обязательное поле id
                                hh_data=candidate,
                                overall_ai_score=db_candidate.overall_ai_score,
                                skill_analysis=db_candidate.skill_analysis,
                                analysis_status="completed",
                                keyword_relevance_score=db_candidate.keyword_relevance_score,
                                filter_match_score=db_candidate.filter_match_score,
                                recency_score=db_candidate.recency_score,
                                profile_completeness_score=db_candidate.profile_completeness_score,
                                analysis_summary=db_candidate.analysis_summary,
                                reasoning=db_candidate.reasoning,
                                multi_agent_data=db_candidate.multi_agent_data,
                                relevance_boost=db_candidate.relevance_boost
                            )
                            processed_profiles.append(profile)
                            successful_ai_analyses += 1
                            self.logger.info(f"✅ Использован готовый анализ из БД для кандидата {candidate.id}")
                        else:
                            # Подготавливаем запрос для AI анализа
                            position_type = self._determine_position_type(search_request.text or "")
                            position_requirements = self._extract_position_requirements(search_request)
                            
                            if full_resume_data:
                                if isinstance(full_resume_data, dict) and 'resume' in full_resume_data:
                                    candidate_data = full_resume_data['resume']
                                else:
                                    candidate_data = full_resume_data
                            else:
                                candidate_data = candidate.model_dump()
                            
                            multi_agent_request = MultiAgentAnalysisRequest(
                                candidate_id=candidate.id,
                                position_type=position_type,
                                search_query=search_request.text or "",
                                position_requirements=position_requirements,
                                candidate_data=candidate_data,
                                search_filters=search_request.model_dump(exclude={'ranking_weights'})
                            )
                            
                            all_candidates.append(candidate)
                            all_requests.append(multi_agent_request)
                            
                    except Exception as e:
                        self.logger.error(f"Ошибка подготовки кандидата {candidate.id}: {e}")
            
            # НАСТОЯЩАЯ ПАРАЛЛЕЛЬНОСТЬ: Отправляем ВСЕХ кандидатов ОДНИМ batch запросом
            if all_requests:
                self.logger.info(f"🚀 НАСТОЯЩАЯ ПАРАЛЛЕЛЬНОСТЬ: Отправляем {len(all_requests)} кандидатов ОДНИМ batch запросом!")
                
                try:
                    response = requests.post(
                        f"{self.ai_analysis_url}/multi-agent/batch", 
                        json=[req.model_dump(mode='json') for req in all_requests],
                        timeout=3600  # 1 час для обработки 200-300 кандидатов
                    )
                    response.raise_for_status()
                    
                    # Обрабатываем результаты batch
                    batch_responses = response.json()
                    for i, batch_response in enumerate(batch_responses):
                        try:
                            multi_agent_response = MultiAgentAnalysisResponse(**batch_response)
                            candidate = all_candidates[i]
                            
                            # Рассчитываем итоговый скор
                            final_score = self._calculate_relevance_score(
                                candidate, 
                                search_request.text or "",
                                multi_agent_response.master_report.overall_score
                            )
                            
                            # Создаем профиль кандидата
                            profile = CandidateProfile(
                                id=candidate.id,  # ИСПРАВЛЕНИЕ: Добавляем обязательное поле id
                                hh_data=candidate,
                                overall_ai_score=final_score,
                                skill_analysis=[],  # Пока оставляем пустым, данные в agent_reports
                                analysis_status="completed",
                                keyword_relevance_score=final_score,
                                filter_match_score=0.0,
                                recency_score=0.0,
                                profile_completeness_score=0.0,
                                analysis_summary=multi_agent_response.master_report.master_assessment[:500] + "..." if len(multi_agent_response.master_report.master_assessment) > 500 else multi_agent_response.master_report.master_assessment,
                                reasoning=multi_agent_response.master_report.recommendation,
                                multi_agent_data=multi_agent_response.model_dump(),
                                relevance_boost=0.0
                            )
                            
                            processed_profiles.append(profile)
                            successful_ai_analyses += 1
                            
                            # Сохраняем в БД
                            self._save_candidate_to_db(profile)
                            
                            self.logger.info(f"✅ Кандидат {candidate.id}: AI оценка {final_score:.1f}%")
                            
                        except Exception as e:
                            self.logger.error(f"Ошибка обработки результата для кандидата {all_candidates[i].id}: {e}")
                    
                    self.logger.info(f"✅ НАСТОЯЩАЯ ПАРАЛЛЕЛЬНОСТЬ: Обработано {successful_ai_analyses} кандидатов из {len(all_requests)}")
                    
                except Exception as e:
                    self.logger.error(f"Ошибка batch AI анализа: {e}")
                    # В случае ошибки создаем профили без AI анализа
                    for candidate in all_candidates:
                        profile = CandidateProfile(
                            id=candidate.id,  # ИСПРАВЛЕНИЕ: Добавляем обязательное поле id
                            hh_data=candidate,
                            overall_ai_score=0.0,
                            skill_analysis=[],
                            analysis_status="failed",
                            keyword_relevance_score=0.0,
                            filter_match_score=0.0,
                            recency_score=0.0,
                            profile_completeness_score=0.0,
                            analysis_summary="AI анализ не выполнен",
                            reasoning="Ошибка AI анализа",
                            multi_agent_data={},
                            relevance_boost=0.0
                        )
                        processed_profiles.append(profile)
            
            processing_time = time.time() - start_time
            self.logger.info(f"⚡ Параллельная обработка завершена за {processing_time:.2f}s. Успешных AI анализов: {successful_ai_analyses}/{len(hh_candidates)}")

            self.logger.info(f"Обработано {len(processed_profiles)} профилей, успешных AI анализов: {successful_ai_analyses}")
            
            # Если нет успешных AI анализов, возвращаем fallback
            if successful_ai_analyses == 0:
                self.logger.warning("AI анализ не работает, возвращаем первые 10 кандидатов без ранжирования")
                return hh_candidates[:10]
            
            # 3. AI ранжирование (замена алгоритмического ранжирования)
            if not processed_profiles:
                self.logger.warning("Нет профилей для ранжирования")
                return []

            try:
                # Создаем кандидатов с полным AI анализом
                ai_ranked_candidates = []
                for profile in processed_profiles:
                    candidate_data = profile.hh_data.model_dump()
                    candidate_data['score'] = profile.overall_ai_score
                    # Добавляем AI анализ навыков 
                    candidate_data['skill_analysis'] = [skill.model_dump() for skill in profile.skill_analysis]
                    candidate_data['analysis_status'] = profile.analysis_status
                    # Добавляем детальные поля AI анализа для объяснения оценки
                    candidate_data['keyword_relevance_score'] = profile.keyword_relevance_score
                    candidate_data['filter_match_score'] = profile.filter_match_score
                    candidate_data['recency_score'] = profile.recency_score
                    candidate_data['profile_completeness_score'] = profile.profile_completeness_score
                    candidate_data['analysis_summary'] = profile.analysis_summary
                    candidate_data['reasoning'] = profile.reasoning
                    # 🔥 КРИТИЧЕСКИ ВАЖНО: Добавляем мульти-агентные данные!
                    candidate_data['multi_agent_data'] = profile.multi_agent_data
                    candidate_data['relevance_boost'] = profile.relevance_boost
                    ai_ranked_candidates.append(Candidate(**candidate_data))
                
                # Сортируем по AI оценке (убывание)
                ai_ranked_candidates.sort(key=lambda x: x.score or 0.0, reverse=True)
                
                self.logger.info(f"AI ранжирование завершено: {len(ai_ranked_candidates)} кандидатов отсортированы по AI оценке")
                
                # Обновляем счетчик поиска в БД
                for candidate in ai_ranked_candidates:
                    self._update_search_count_in_db(candidate.id)
                    
                # Логируем статистику HH API
                self.logger.info(f"📊 Статистика HH API: {hh_api_stats['successful_requests']}/{hh_api_stats['total_requests']} успешных запросов")
                if hh_api_stats['status_500_errors'] > 0:
                    self.logger.warning(f"🚨 Ошибок 500: {hh_api_stats['status_500_errors']}")
                if hh_api_stats['status_429_errors'] > 0:
                    self.logger.warning(f"🚫 Ошибок 429: {hh_api_stats['status_429_errors']}")
                if hh_api_stats['status_503_errors'] > 0:
                    self.logger.warning(f"🔴 Ошибок 503 (лимит исчерпан): {hh_api_stats['status_503_errors']}")
                if hh_api_stats['rate_limit_exceeded'] > 0:
                    self.logger.warning(f"⚡ Всего превышений лимита: {hh_api_stats['rate_limit_exceeded']}")
                    
                return ai_ranked_candidates, hh_api_stats
                
            except Exception as e:
                self.logger.error(f"Ошибка AI ранжирования: {e}")
                # В случае ошибки возвращаем первые 10 кандидатов
                self.logger.warning(f"📊 Статистика HH API (с ошибкой): {hh_api_stats['successful_requests']}/{hh_api_stats['total_requests']} успешных запросов")
                return hh_candidates[:10], hh_api_stats

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка сети при поиске: {e}")
            raise HTTPException(status_code=503, detail=f"Сетевая ошибка: {e}")
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка при поиске: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {e}")

    def build_top_for_vacancy(self, vacancy_url: str, limit: int = 10) -> VacancyTopResponse:
        """Новый поток: вакансия → отклики → AI-анализ → ТОП кандидатов"""
        # 1) Получаем отклики по вакансии
        vacancy_details = self._get_vacancy_details(vacancy_url)
        responses_data = self._get_vacancy_responses(vacancy_url)
        vacancy_id = responses_data.get("vacancy_id", "")
        items = responses_data.get("items", [])

        # Ожидаем, что items содержит массив резюме или их id
        candidates: List[Candidate] = []
        for item in items:
            try:
                # Унификация: если сразу есть резюме-объект, конвертим, если id — тянем детали
                resume_id = item.get("resume_id") if isinstance(item, dict) else None
                resume_obj = item.get("resume") if isinstance(item, dict) else None
                if resume_obj:
                    candidate = self._resume_to_candidate(resume_obj)
                elif resume_id:
                    full = requests.get(f"{self.hh_api_url}/resume/{resume_id}", timeout=60)
                    full.raise_for_status()
                    candidate = self._resume_to_candidate(full.json().get("resume", {}))
                else:
                    continue
                candidates.append(candidate)
            except Exception as e:
                self.logger.warning(f"Пропуск элемента отклика: {e}")

        if not candidates:
            return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=0, candidates=[])

        # 2) Подтягиваем детальные данные + готовим батч мультиагентного анализа
        all_candidates = []
        all_requests = []
        for candidate in candidates:
            full_resume_data, _ = self._get_full_resume_data(candidate.id)
            candidate_data = full_resume_data.get("resume", full_resume_data) if isinstance(full_resume_data, dict) else candidate.model_dump()
            # Пытаемся извлечь требования из вакансии (название + ключевые слова)
            vacancy_title = (vacancy_details.get("name") or "") if isinstance(vacancy_details, dict) else ""
            position_type = self._determine_position_type(vacancy_title or candidate.title or "")
            position_requirements = self._extract_position_requirements(SearchRequest(text=vacancy_title, page=1, per_page=1))
            all_candidates.append(candidate)
            all_requests.append(MultiAgentAnalysisRequest(
                candidate_id=candidate.id,
                position_type=position_type,
                search_query=vacancy_title or candidate.title or "",
                position_requirements=position_requirements,
                candidate_data=candidate_data,
                search_filters={}
            ))

        # 3) Отправляем батч в AI Analysis
        try:
            response = requests.post(
                f"{self.ai_analysis_url}/multi-agent/batch",
                json=[r.model_dump(mode='json') for r in all_requests],
                timeout=3600
            )
            response.raise_for_status()
            batch_responses = response.json()
        except Exception as e:
            self.logger.error(f"Ошибка AI анализа откликов: {e}")
            # Если AI недоступен — вернуть без сортировки
            return VacancyTopResponse(
                vacancy_id=vacancy_id,
                total_responses=len(all_candidates),
                candidates=all_candidates[:limit]
            )

        # 4) Считаем финальные баллы и сортируем
        tops: List[Candidate] = []
        for i, br in enumerate(batch_responses):
            try:
                ma = MultiAgentAnalysisResponse(**br)
                base_score = ma.master_report.overall_score
                candidate = all_candidates[i]
                final_score = self._calculate_relevance_score(candidate, candidate.title or "", base_score)
                candidate.score = round(final_score, 3)
                tops.append(candidate)
            except Exception as e:
                self.logger.warning(f"Ошибка сборки результата для кандидата {all_candidates[i].id}: {e}")

        tops.sort(key=lambda c: c.score or 0, reverse=True)
        # Финальная сортировка через сервис ранжирования (AI-first, по score)
        try:
            rank_payload = RankingRequest(candidates=tops, search_request=SearchRequest(text=vacancy_title or "", page=1, per_page=len(tops)))
            resp = requests.post(f"{self.ranking_url}/rank", json=rank_payload.model_dump(mode='json'), timeout=60)
            resp.raise_for_status()
            ranked_data = resp.json()
            ranked_candidates = ranked_data.get("ranked_candidates", [])
            if limit:
                ranked_candidates = ranked_candidates[:limit]
            # Преобразуем в объекты Candidate при необходимости
            final_list = []
            for c in ranked_candidates:
                if isinstance(c, dict):
                    final_list.append(Candidate(**c))
                else:
                    final_list.append(c)
            return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=len(all_candidates), candidates=final_list)
        except Exception:
            # Fallback на локальную сортировку
            if limit:
                tops = tops[:limit]
            return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=len(all_candidates), candidates=tops)

    def _get_candidate_from_db(self, candidate_id: str) -> Optional[DatabaseCandidate]:
        try:
            response = requests.get(f"{self.database_url}/candidates/{candidate_id}", timeout=60)
            if response.status_code == 200:
                return DatabaseCandidate(**response.json())
            return None
        except Exception as e:
            self.logger.warning(f"Не удалось получить кандидата {candidate_id} из БД: {e}")
            return None


    
    def _determine_position_type(self, search_query: str) -> str:
        """Определяет тип позиции на основе поискового запроса"""
        query_lower = search_query.lower()
        
        # Технические позиции
        if any(tech in query_lower for tech in ["разработчик", "developer", "программист", "devops", "fullstack", "backend", "frontend"]):
            return "technical"
        
        # Управленческие позиции  
        if any(mgmt in query_lower for mgmt in ["менеджер", "manager", "руководитель", "директор", "тимлид", "lead"]):
            return "management"
        
        # Продажи
        if any(sales in query_lower for sales in ["продаж", "sales", "менеджер по продажам"]):
            return "sales"
        
        return "general"
    
    def _extract_position_requirements(self, search_request: SearchRequest) -> dict:
        """Извлекает требования к позиции из поискового запроса"""
        search_text = search_request.text or ""
        
        # Извлекаем навыки из поискового запроса
        required_skills = []
        
        # Технологии из запроса
        tech_keywords = ["python", "java", "javascript", "react", "django", "spring", "nodejs", "golang", "kubernetes", "docker"]
        for tech in tech_keywords:
            if tech in search_text.lower():
                required_skills.append(tech.title())
        
        # УЛУЧШЕНО: Передаем ПОЛНУЮ информацию об опыте
        experience_info = self._get_detailed_experience_requirements(getattr(search_request, 'experience', None))
        
        # УЛУЧШЕНО: Передаем детальные требования из всех фильтров поиска
        return {
            "required_skills": required_skills,
            "min_experience_years": experience_info["min_years"],
            "max_experience_years": experience_info["max_years"], 
            "experience_description": experience_info["description"],
            "experience_level": experience_info["level"],
            "search_query": search_text,
            "employment_types": [emp.value for emp in (search_request.employment or [])],
            "schedule_types": [sch.value for sch in (search_request.schedule or [])],
            "professional_roles": search_request.professional_role or [],
            "areas": search_request.area or [],
            "salary_max": search_request.salary,
            "age_range": {
                "min": search_request.age_from,
                "max": search_request.age_to
            },
            "education": [],
            "languages": search_request.language or []
        }
    
    def _get_detailed_experience_requirements(self, experience_str) -> dict:
        """Преобразует строку опыта HH.ru в детальную информацию о требованиях"""
        if not experience_str or experience_str == "noExperience":
            return {
                "min_years": 0,
                "max_years": 0,
                "description": "Без опыта",
                "level": "noExperience"
            }
        elif experience_str == "between1And3":
            return {
                "min_years": 1,
                "max_years": 3,
                "description": "От 1 года до 3 лет",
                "level": "between1And3"
            }
        elif experience_str == "between3And6":
            return {
                "min_years": 3,
                "max_years": 6,
                "description": "От 3 до 6 лет",
                "level": "between3And6"
            }
        elif experience_str == "moreThan6":
            return {
                "min_years": 6,
                "max_years": None,
                "description": "Более 6 лет",
                "level": "moreThan6"
            }
        else:
            # Если передано число, возвращаем его
            try:
                years = int(experience_str)
                return {
                    "min_years": years,
                    "max_years": years,
                    "description": f"Ровно {years} лет",
                    "level": "custom"
                }
            except (ValueError, TypeError):
                return {
                    "min_years": 0,
                    "max_years": None,
                    "description": "Требования к опыту не указаны",
                    "level": "unknown"
                }

    def _convert_experience_to_years(self, experience_str) -> int:
        """Преобразует строку опыта HH.ru в минимальные годы (совместимость)"""
        experience_info = self._get_detailed_experience_requirements(experience_str)
        return experience_info["min_years"]
    
    def _calculate_relevance_score(self, candidate: Candidate, search_query: str, base_score: float) -> float:
        """Рассчитывает финальный скор с учетом релевантности поискового запроса"""
        if not search_query:
            return base_score
        
        relevance_boost = 0.0
        query_words = search_query.lower().split()
        
        # Проверяем соответствие названия должности
        candidate_title = (candidate.title or "").lower()
        for word in query_words:
            if word in candidate_title:
                relevance_boost += 15.0  # Большой бонус за соответствие названию
        
        # Проверяем соответствие навыков
        candidate_skills = [skill.lower() for skill in (candidate.skills or [])]
        for word in query_words:
            for skill in candidate_skills:
                if word in skill:
                    relevance_boost += 5.0  # Бонус за соответствие навыкам
        
        # Проверяем описание опыта
        candidate_experience = (getattr(candidate, 'experience_text', '') or '').lower()
        for word in query_words:
            if word in candidate_experience:
                relevance_boost += 2.0  # Небольшой бонус за упоминание в опыте
        
        # Ограничиваем максимальный буст
        relevance_boost = min(relevance_boost, 25.0)
        
        return min(100.0, base_score + relevance_boost)

    def _save_candidate_to_db(self, profile: CandidateProfile):
        try:
            # Database API ожидает объект Candidate и отдельно ai_analysis
            candidate_data = profile.hh_data.model_dump(mode='json')
            
            # Формируем AI Analysis если есть
            ai_analysis_data = None
            if profile.skill_analysis and profile.overall_ai_score > 0:
                # Правильно сериализуем объекты SkillAnalysis
                skill_analysis_data = []
                if isinstance(profile.skill_analysis, list):
                    skill_analysis_data = [
                        skill.model_dump(mode='json') if hasattr(skill, 'model_dump') 
                        else skill for skill in profile.skill_analysis
                    ]
                
                ai_analysis_data = {
                    "candidate_id": profile.id,
                    "skill_analysis": skill_analysis_data,
                    "overall_score": profile.overall_ai_score,
                    "analysis_summary": f"Анализ завершен со статусом: {profile.analysis_status}",
                    "processing_time": 1.0
                }
            
            # Отправляем согласно API database
            payload = {
                "candidate": candidate_data,
                "ai_analysis": ai_analysis_data
            }
            
            requests.post(f"{self.database_url}/candidates", json=payload, timeout=120).raise_for_status()
        except Exception as e:
            self.logger.error(f"Не удалось сохранить кандидата {profile.id} в БД: {e}")

    def _update_search_count_in_db(self, candidate_id: str):
        try:
            requests.put(f"{self.database_url}/candidates/{candidate_id}/search", timeout=60).raise_for_status()
        except Exception as e:
            self.logger.warning(f"Не удалось обновить счетчик поиска для {candidate_id}: {e}")


search_service = SearchService()

@app.get("/ping")
async def ping():
    """Простая проверка доступности search сервиса"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/filters", tags=["Filters"])
def get_filters():
    return search_service.get_dictionaries()

@app.get("/dictionaries", tags=["Dictionaries"])
def get_dictionaries():
    """Получение всех справочников"""
    try:
        result = search_service.get_dictionaries()
        if not result:
            raise HTTPException(status_code=500, detail="Ошибка получения справочников")
        return result
    except Exception as e:
        logger.error(f"Ошибка получения справочников: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения справочников")

# ===== НОВОЕ: Эндпоинт для ТОПа по ссылке вакансии =====
@app.post("/vacancy/top", response_model=VacancyTopResponse)
def build_vacancy_top(req: VacancyTopRequest):
    return search_service.build_top_for_vacancy(req.vacancy_url, req.limit or 10)

def create_search_request_search(
    text: Optional[str] = Query(None, description="Ключевые слова для поиска"),
    search_field: Optional[str] = Query("everywhere", description="Область поиска"), 
    area: Optional[List[int]] = Query(None, description="ID регионов"),
    salary: Optional[int] = Query(None, description="Максимальная зарплата"),
    experience: Optional[str] = Query(None, description="Опыт работы"),
    employment: Optional[List[str]] = Query(None, description="Тип занятости"),
    schedule: Optional[List[str]] = Query(None, description="График работы"),
    professional_role: Optional[List[str]] = Query(None, description="Профессиональные роли"),
    period: Optional[int] = Query(None, description="Период обновления в днях"),
    age_from: Optional[int] = Query(None, description="Возраст от"),
    age_to: Optional[int] = Query(None, description="Возраст до"), 
    gender: Optional[str] = Query(None, description="Пол"),
    language_id: Optional[str] = Query(None, description="ID языка"),
    language_level: Optional[str] = Query(None, description="Минимальный уровень языка"),
    page: int = Query(1, description="Номер страницы"),
    per_page: int = Query(20, description="Количество на странице")
) -> SearchRequest:
    """Создание SearchRequest из query параметров в Search сервисе"""
    
    # Обработка языковых требований
    language_requirements = None
    if language_id and language_level:
        from shared.models import LanguageRequirement, LanguageLevel
        try:
            language_requirements = [LanguageRequirement(
                language_id=language_id,
                level=LanguageLevel(language_level)
            )]
        except ValueError:
            # Если неверный уровень языка, игнорируем
            language_requirements = None
    
    return SearchRequest(
        text=text,
        search_field=search_field,
        area=area,
        salary=salary,
        experience=experience,
        employment=employment,
        schedule=schedule,
        professional_role=professional_role,
        period=period,
        age_from=age_from,
        age_to=age_to,
        gender=gender,
        language=language_requirements,
        page=page,
        per_page=per_page
    )

@app.get("/search", tags=["Search"])
def search(search_request: SearchRequest = Depends(create_search_request_search)):
    """Поиск кандидатов через GET запрос"""
    try:
        candidates, hh_api_stats = search_service.search_candidates(search_request)
        
        # Формируем правильную структуру ответа с информацией о HH API
        return {
            "candidates": [candidate.model_dump() for candidate in candidates],
            "total_count": len(candidates),
            "page": search_request.page,
            "pages": 1,  # Пока возвращаем одну страницу
            "hh_api_status": {
                "total_requests": hh_api_stats["total_requests"],
                "successful_requests": hh_api_stats["successful_requests"],
                "failed_requests": hh_api_stats["failed_requests"],
                "status_500_errors": hh_api_stats["status_500_errors"],
                "status_429_errors": hh_api_stats["status_429_errors"],
                "status_503_errors": hh_api_stats["status_503_errors"],
                "rate_limit_exceeded": hh_api_stats["rate_limit_exceeded"],
                "good_data_count": hh_api_stats["good_data_count"],
                "partial_data_count": hh_api_stats["partial_data_count"],
                "has_issues": hh_api_stats["failed_requests"] > 0,
                "is_rate_limited": hh_api_stats["rate_limit_exceeded"] > 0,
                "success_rate": (hh_api_stats["successful_requests"] / hh_api_stats["total_requests"] * 100) if hh_api_stats["total_requests"] > 0 else 100
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска")

if __name__ == "__main__":
    import uvicorn
    config = load_config()
    service_config = config.get("services", {}).get("search", {})
    port = service_config.get("port", 8001)
    host = service_config.get("host", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)