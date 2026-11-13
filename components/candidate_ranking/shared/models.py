"""
Candidate Analysis - Shared Data Models

Централизованные Pydantic модели для всех микросервисов системы Candidate Analysis.

Этот модуль определяет единые data models, используемые во всех компонентах системы
для обеспечения type safety, валидации данных и консистентности API.

Model Categories:
- Enums: SearchField, ExperienceLevel, EmploymentType, etc.
- Search Models: SearchRequest, Candidate, SearchResponse
- AI Analysis Models: AIAnalysisRequest/Response, AgentReport
- Multi-Agent Models: MultiAgentAnalysisRequest/Response, MasterCoordinatorReport
- Database Models: DatabaseCandidate, CandidateProfile
- System Models: HealthResponse, RankingWeights

Key Features:
- Type Safety: Строгая типизация для всех API
- Data Validation: Автоматическая валидация входящих данных  
- Serialization: JSON сериализация/десериализация
- Documentation: Автогенерация OpenAPI документации
- Enums: Константы для dropdown значений и фильтров

Design Principles:
- Single Source of Truth: Одни модели для всех сервисов
- Backward Compatibility: Осторожные изменения с Optional полями
- Clear Naming: Понятные имена полей и моделей
- Rich Types: Использование Optional, List, Dict для точности

Usage Examples:
- FastAPI endpoints: response_model=List[Candidate]
- API validation: SearchRequest.model_validate(request_data)
- Type hints: def analyze(request: AIAnalysisRequest) -> AIAnalysisResponse
- JSON conversion: candidate.model_dump_json()

Author: Candidate Analysis Team
Version: 2.0.0 (Multi-Agent Models + Enhanced Validation)
Last Updated: 2025-01-04
"""
import os

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SearchField(str, Enum):
    NAME = "name"
    DESCRIPTION = "description"
    EVERYWHERE = "everywhere"

class ExperienceLevel(str, Enum):
    NO_EXPERIENCE = "noExperience"
    BETWEEN_1_AND_3 = "between1And3"
    BETWEEN_3_AND_6 = "between3And6"
    MORE_THAN_6 = "moreThan6"

class EmploymentType(str, Enum):
    FULL = "full"
    PART = "part"
    PROJECT = "project"
    VOLUNTEER = "volunteer"
    PROBATION = "probation"

class ScheduleType(str, Enum):
    FULL_DAY = "fullDay"
    SHIFT = "shift"
    FLEXIBLE = "flexible"
    REMOTE = "remote"
    FLY_IN_FLY_OUT = "flyInFlyOut"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"

class LanguageLevel(str, Enum):
    A1 = "a1"
    A2 = "a2"
    B1 = "b1"
    B2 = "b2"
    C1 = "c1"
    C2 = "c2"
    NATIVE = "native"  # Родной язык

class Language(BaseModel):
    id: str = Field(..., description="ID языка")
    name: str = Field(..., description="Название языка")
    
class LanguageRequirement(BaseModel):
    language_id: str = Field(..., description="ID языка")
    level: LanguageLevel = Field(..., description="Минимальный уровень владения")

class RankingWeights(BaseModel):
    keyword_relevance: float = Field(0.4, description="Вес релевантности по ключевым словам")
    filter_match: float = Field(0.3, description="Вес соответствия фильтрам")
    recency: float = Field(0.2, description="Вес актуальности")
    profile_completeness: float = Field(0.1, description="Вес полноты профиля")

class SearchRequest(BaseModel):
    text: Optional[str] = Field(None, description="Ключевые слова для поиска")
    search_field: SearchField = Field(SearchField.EVERYWHERE, description="Область поиска")
    area: Optional[List[int]] = Field(None, description="География (ID регионов)")
    salary: Optional[int] = Field(None, description="Максимальная зарплата")
    experience: Optional[ExperienceLevel] = Field(None, description="Опыт работы")
    employment: Optional[List[EmploymentType]] = Field(None, description="Тип занятости")
    schedule: Optional[List[ScheduleType]] = Field(None, description="График работы")
    professional_role: Optional[List[int]] = Field(None, description="Профессиональные роли")
    period: Optional[int] = Field(None, description="Период обновления (в днях)")
    age_from: Optional[int] = Field(None, description="Минимальный возраст")
    age_to: Optional[int] = Field(None, description="Максимальный возраст")
    gender: Optional[Gender] = Field(None, description="Пол")
    language: Optional[List[LanguageRequirement]] = Field(None, description="Требования к знанию языков")
    page: int = Field(1, description="Номер страницы")
    per_page: int = Field(20, description="Количество результатов на странице")
    
    # Веса для AI ранжирования
    ranking_weights: Optional[RankingWeights] = Field(None, description="Веса ранжирования для AI")

class Candidate(BaseModel):
    id: str = Field(..., description="ID кандидата")
    name: Optional[str] = Field(None, description="ФИО кандидата")
    age: Optional[int] = Field(None, description="Возраст")
    title: str = Field(..., description="Название должности")
    area: Dict[str, Any] = Field(..., description="Город/регион")
    experience: Dict[str, Any] = Field(..., description="Опыт работы")
    salary: Optional[Dict[str, Any]] = Field(None, description="Зарплатные ожидания")
    last_work: Optional[Dict[str, Any]] = Field(None, description="Последнее место работы")
    skills: List[str] = Field(default_factory=list, description="Навыки")
    verified_skills: List[str] = Field(default_factory=list, description="Подтвержденные навыки")
    updated_at: datetime = Field(..., description="Дата обновления резюме")
    url: str = Field(..., description="Ссылка на резюме")
    photo_url: Optional[str] = Field(None, description="URL фотографии")
    has_cover_letter: bool = Field(False, description="Наличие сопроводительного письма")
    score: Optional[float] = Field(None, description="Оценка релевантности")
    
    # AI анализ (добавлено для полного использования CandidateProfile)
    skill_analysis: Optional[List[Dict[str, Any]]] = Field(None, description="AI анализ навыков")
    analysis_status: Optional[str] = Field(None, description="Статус AI анализа")
    
    # Детальные поля AI анализа для объяснения оценки
    keyword_relevance_score: Optional[float] = Field(None, description="AI оценка релевантности по ключевым словам")
    filter_match_score: Optional[float] = Field(None, description="AI оценка соответствия фильтрам")
    recency_score: Optional[float] = Field(None, description="AI оценка актуальности")
    profile_completeness_score: Optional[float] = Field(None, description="AI оценка полноты профиля")
    analysis_summary: Optional[str] = Field(None, description="Краткое резюме AI анализа")
    reasoning: Optional[str] = Field(None, description="Обоснование оценки AI")
    
    # Новые поля для мульти-агентной системы
    multi_agent_data: Optional[Dict[str, Any]] = Field(None, description="Полные данные мульти-агентного анализа")
    relevance_boost: Optional[float] = Field(None, description="Бонус за релевантность поискового запроса")

class SearchResponse(BaseModel):
    candidates: List[Candidate] = Field(..., description="Список кандидатов")
    total_count: int = Field(..., description="Общее количество результатов")
    page: int = Field(..., description="Текущая страница")
    pages: int = Field(..., description="Общее количество страниц")

class RankingRequest(BaseModel):
    candidates: List[Candidate] = Field(..., description="Кандидаты для ранжирования")
    search_request: SearchRequest = Field(..., description="Исходный поисковый запрос")
    weights: Optional[RankingWeights] = Field(None, description="Веса для ранжирования")

class RankingResponse(BaseModel):
    ranked_candidates: List[Candidate] = Field(..., description="Отранжированные кандидаты")
    ranking_metadata: Dict[str, Any] = Field(..., description="Метаданные ранжирования")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Статус сервиса")
    timestamp: datetime = Field(..., description="Время проверки")
    version: str = Field(..., description="Версия сервиса")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Описание ошибки")
    details: Optional[str] = Field(None, description="Детали ошибки")
    timestamp: datetime = Field(..., description="Время возникновения ошибки")

class SkillAnalysis(BaseModel):
    skill_name: str = Field(..., description="Название навыка")
    relevance_score: float = Field(..., description="Оценка релевантности (0-1)")
    proficiency_level: str = Field(..., description="Уровень владения")
    years_experience: Optional[float] = Field(None, description="Годы опыта")
    ai_confidence: float = Field(..., description="Уверенность AI в оценке (0-1)")
    analysis_timestamp: datetime = Field(..., description="Время анализа")

class CandidateProfile(BaseModel):
    id: str = Field(..., description="ID кандидата")
    hh_data: Candidate = Field(..., description="Данные из HH.ru")
    skill_analysis: List[SkillAnalysis] = Field(default_factory=list, description="AI-анализ навыков")
    overall_ai_score: float = Field(0.0, description="Общая AI-оценка")
    last_analyzed: Optional[datetime] = Field(None, description="Время последнего анализа")
    analysis_status: str = Field("pending", description="Статус анализа: pending, analyzing, completed, failed")
    
    # Детальные поля AI анализа для объяснения оценки
    keyword_relevance_score: Optional[float] = Field(None, description="AI оценка релевантности по ключевым словам")
    filter_match_score: Optional[float] = Field(None, description="AI оценка соответствия фильтрам")
    recency_score: Optional[float] = Field(None, description="AI оценка актуальности")
    profile_completeness_score: Optional[float] = Field(None, description="AI оценка полноты профиля")
    analysis_summary: Optional[str] = Field(None, description="Краткое резюме AI анализа")
    reasoning: Optional[str] = Field(None, description="Обоснование оценки AI")
    
    # Новые поля для мульти-агентной системы
    multi_agent_data: Optional[Dict[str, Any]] = Field(None, description="Полные данные мульти-агентного анализа")
    relevance_boost: Optional[float] = Field(None, description="Бонус за релевантность поискового запроса")

class AIAnalysisRequest(BaseModel):
    candidate_id: str = Field(..., description="ID кандидата")
    search_query: str = Field(..., description="Поисковый запрос")
    skills: List[str] = Field(..., description="Навыки для анализа")
    experience_description: Optional[str] = Field(None, description="Описание опыта")
    candidate_data: Optional[Dict[str, Any]] = Field(None, description="Полные данные кандидата")
    search_filters: Optional[Dict[str, Any]] = Field(None, description="Фильтры поиска")
    ranking_weights: Optional[RankingWeights] = Field(None, description="Веса ранжирования для AI")

class AIAnalysisResponse(BaseModel):
    candidate_id: str = Field(..., description="ID кандидата")
    skill_analysis: List[SkillAnalysis] = Field(..., description="Результаты анализа навыков")
    overall_score: float = Field(..., description="Общая оценка")
    analysis_summary: str = Field(..., description="Краткое резюме анализа")
    processing_time: float = Field(..., description="Время обработки в секундах")
    
    # Новые поля для детального AI ранжирования
    keyword_relevance_score: Optional[float] = Field(None, description="AI оценка релевантности по ключевым словам")
    filter_match_score: Optional[float] = Field(None, description="AI оценка соответствия фильтрам")
    recency_score: Optional[float] = Field(None, description="AI оценка актуальности")
    profile_completeness_score: Optional[float] = Field(None, description="AI оценка полноты профиля")
    reasoning: Optional[str] = Field(None, description="Обоснование оценки AI")

class DatabaseCandidate(BaseModel):
    id: str = Field(..., description="ID кандидата")
    profile: CandidateProfile = Field(..., description="Профиль кандидата")
    created_at: datetime = Field(..., description="Время создания записи")
    updated_at: datetime = Field(..., description="Время обновления записи")
    search_count: int = Field(0, description="Количество поисков")
    last_searched: Optional[datetime] = Field(None, description="Время последнего поиска")

# ================================
# МУЛЬТИ-АГЕНТНАЯ СИСТЕМА МОДЕЛЕЙ
# ================================

class AgentStatus(str, Enum):
    """Статус выполнения анализа агентом"""
    PASS = 'pass'
    WARNING = "warning" 
    FAIL = "fail"
    ERROR = "error"

class AgentReport(BaseModel):
    """Базовый класс для отчета агента"""
    agent_name: str = Field(..., description="Название агента")
    score: float = Field(..., description="Оценка агента (0-100%)")
    status: AgentStatus = Field(..., description="Статус анализа")
    summary: str = Field(..., description="Краткое резюме анализа")
    details: List[str] = Field(default=[], description="Детальные наблюдения")
    red_flags: List[str] = Field(default=[], description="Красные флаги")
    positive_points: List[str] = Field(default=[], description="Сильные стороны")
    recommendations: List[str] = Field(default=[], description="Рекомендации")
    processing_time: float = Field(..., description="Время обработки в секундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время создания отчета")

class MasterCoordinatorReport(BaseModel):
    """Итоговый отчет мастер-координатора"""
    overall_score: float = Field(..., description="Итоговая оценка (среднее арифметическое)")
    individual_scores: Dict[str, float] = Field(..., description="Оценки от каждого агента")
    master_assessment: str = Field(..., description="Общая текстовая оценка мастера")
    recommendation: str = Field(..., description="Финальная рекомендация")
    total_red_flags: int = Field(..., description="Общее количество красных флагов")
    total_positive_points: int = Field(..., description="Общее количество плюсов")
    agents_with_warnings: List[str] = Field(default=[], description="Агенты с предупреждениями")
    agents_with_failures: List[str] = Field(default=[], description="Агенты с критическими ошибками")
    processing_time: float = Field(..., description="Общее время обработки")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время создания отчета")

class MultiAgentAnalysisRequest(BaseModel):
    """Запрос для мульти-агентного анализа"""
    candidate_id: str = Field(..., description="ID кандидата")
    position_type: str = Field(..., description="Тип позиции (technical, legal, management, general)")
    search_query: str = Field(..., description="Поисковый запрос/название вакансии")
    position_requirements: Dict[str, Any] = Field(..., description="Требования к позиции")
    candidate_data: Dict[str, Any] = Field(..., description="Полные данные кандидата")
    search_filters: Optional[Dict[str, Any]] = Field(None, description="Фильтры поиска")
    active_agents: Optional[List[str]] = Field(None, description="Список активных агентов (если не указан - автоопределение)")

class MultiAgentAnalysisResponse(BaseModel):
    """Ответ мульти-агентного анализа"""
    candidate_id: str = Field(..., description="ID кандидата")
    master_report: MasterCoordinatorReport = Field(..., description="Итоговый отчет мастера")
    agent_reports: List[AgentReport] = Field(..., description="Детальные отчеты всех агентов")
    active_agents: List[str] = Field(..., description="Список активированных агентов")
    total_processing_time: float = Field(..., description="Общее время обработки")

# ================================
# НОВЫЕ МОДЕЛИ ДЛЯ ТОПа ПО ВАКАНСИИ
# ================================

class VacancyTopRequest(BaseModel):
    """Запрос построения ТОПа по ссылке на вакансию"""
    vacancy_url: str = Field(..., description="Ссылка на вакансию на hh.ru")
    limit: Optional[int] = Field(10, description="Ограничение по количеству кандидатов в ТОПе")

class VacancyTopResponse(BaseModel):
    """Ответ с ТОПом кандидатов по конкретной вакансии"""
    vacancy_id: str = Field(..., description="ID вакансии")
    total_responses: int = Field(..., description="Всего откликов по вакансии")
    candidates: List[Candidate] = Field(..., description="Отранжированные кандидаты по AI-оценке")