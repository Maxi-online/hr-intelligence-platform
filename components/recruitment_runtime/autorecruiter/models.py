"""
AutoGPT Recruitment Runtime - Models

Модели для настоящих AutoGPT агентов которые используют LLM 
для автономного планирования и принятия решений.

Author: Candidate Analysis Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class AutoGPTTaskStatus(str, Enum):
    """Статус AutoGPT задачи"""
    ACCEPTED = "accepted"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AutoGPTActionType(str, Enum):
    """Типы действий AutoGPT агента"""
    THINK = "think"
    PLAN = "plan"
    EXECUTE_TOOL = "execute_tool"
    EVALUATE = "evaluate"
    DECIDE_NEXT = "decide_next"

# ===== REQUEST MODELS =====

class AutoGPTTaskRequest(BaseModel):
    """Запрос для AutoGPT агента"""
    goal: str = Field(..., description="Высокоуровневая цель для автономного выполнения")
    context: Optional[Dict[str, Any]] = Field(None, description="Контекст и дополнительная информация")
    requirements: Optional[Dict[str, Any]] = Field(None, description="Конкретные требования к результату")
    constraints: Optional[List[str]] = Field(None, description="Ограничения и правила выполнения")
    max_iterations: int = Field(10, description="Максимум итераций автономного планирования")
    tools_allowed: Optional[List[str]] = Field(None, description="Разрешенные инструменты")

# ===== RESPONSE MODELS =====

class AutoGPTTaskResponse(BaseModel):
    """Ответ на создание AutoGPT задачи"""
    task_id: str = Field(..., description="ID автономной задачи")
    status: str = Field(..., description="Статус принятия задачи")
    message: str = Field(..., description="Сообщение от AutoGPT агента")
    estimated_duration: str = Field(..., description="Оценка времени выполнения")
    created_at: datetime = Field(default_factory=datetime.now)

class AutoGPTAction(BaseModel):
    """Действие AutoGPT агента"""
    action_type: AutoGPTActionType = Field(..., description="Тип действия")
    description: str = Field(..., description="Описание действия")
    reasoning: str = Field(..., description="Обоснование действия")
    tool_name: Optional[str] = Field(None, description="Используемый инструмент")
    tool_params: Optional[Dict[str, Any]] = Field(None, description="Параметры инструмента")
    result: Optional[Dict[str, Any]] = Field(None, description="Результат выполнения")
    timestamp: datetime = Field(default_factory=datetime.now)

class AutoGPTTaskStatus(BaseModel):
    """Статус выполнения AutoGPT задачи"""
    task_id: str = Field(..., description="ID задачи")
    status: AutoGPTTaskStatus = Field(..., description="Текущий статус")
    current_action: str = Field(..., description="Текущее действие агента")
    agent_thoughts: List[str] = Field(default_factory=list, description="Мысли агента")
    actions_taken: List[AutoGPTAction] = Field(default_factory=list, description="Выполненные действия")
    created_at: datetime = Field(..., description="Время создания")
    progress_percentage: Optional[float] = Field(None, description="Прогресс выполнения")

# ===== AGENT MODELS =====

class AutoGPTThought(BaseModel):
    """Мысль AutoGPT агента"""
    content: str = Field(..., description="Содержание мысли")
    type: str = Field(..., description="Тип мысли (analysis, planning, evaluation)")
    confidence: float = Field(..., description="Уверенность в мысли (0-1)")
    timestamp: datetime = Field(default_factory=datetime.now)

class AutoGPTMemory(BaseModel):
    """Память AutoGPT агента"""
    task_id: str = Field(..., description="ID задачи")
    goal: str = Field(..., description="Цель задачи")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст")
    thoughts: List[AutoGPTThought] = Field(default_factory=list, description="История мыслей")
    actions: List[AutoGPTAction] = Field(default_factory=list, description="История действий")
    current_plan: Optional[List[str]] = Field(None, description="Текущий план")
    learned_facts: List[str] = Field(default_factory=list, description="Изученные факты")
    available_tools: List[str] = Field(default_factory=list, description="Доступные инструменты")

class AutoGPTPlan(BaseModel):
    """План AutoGPT агента"""
    goal: str = Field(..., description="Цель плана")
    steps: List[str] = Field(..., description="Шаги для выполнения")
    reasoning: str = Field(..., description="Обоснование плана")
    estimated_steps: int = Field(..., description="Ожидаемое количество шагов")
    success_criteria: List[str] = Field(..., description="Критерии успеха")
    tools_needed: List[str] = Field(..., description="Необходимые инструменты")
    created_at: datetime = Field(default_factory=datetime.now)

# ===== TOOL MODELS =====

class AutoGPTTool(BaseModel):
    """Инструмент AutoGPT агента"""
    name: str = Field(..., description="Название инструмента")
    description: str = Field(..., description="Описание возможностей")
    parameters: Dict[str, Any] = Field(..., description="Схема параметров")
    service_url: str = Field(..., description="URL микросервиса")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP метод")

class AutoGPTToolResult(BaseModel):
    """Результат использования инструмента"""
    tool_name: str = Field(..., description="Название инструмента")
    success: bool = Field(..., description="Успешность выполнения")
    result_data: Dict[str, Any] = Field(..., description="Результат выполнения")
    error: Optional[str] = Field(None, description="Ошибка если есть")
    execution_time: float = Field(..., description="Время выполнения")
    timestamp: datetime = Field(default_factory=datetime.now)

# ===== LLM INTERACTION MODELS =====

class AutoGPTPrompt(BaseModel):
    """Промпт для LLM"""
    system_message: str = Field(..., description="Системное сообщение")
    user_message: str = Field(..., description="Сообщение пользователя")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст")
    expected_format: str = Field(..., description="Ожидаемый формат ответа")

class AutoGPTLLMResponse(BaseModel):
    """Ответ от LLM"""
    content: str = Field(..., description="Содержание ответа")
    parsed_data: Optional[Dict[str, Any]] = Field(None, description="Распарсенные данные")
    reasoning: Optional[str] = Field(None, description="Обоснование ответа")
    confidence: Optional[float] = Field(None, description="Уверенность LLM")
    tokens_used: int = Field(0, description="Использовано токенов")
    processing_time: float = Field(0.0, description="Время обработки")

# ===== DECISION MODELS =====

class AutoGPTDecision(BaseModel):
    """Решение AutoGPT агента"""
    decision_type: str = Field(..., description="Тип решения")
    chosen_action: str = Field(..., description="Выбранное действие")
    reasoning: str = Field(..., description="Обоснование решения")
    alternatives_considered: List[str] = Field(..., description="Рассмотренные альтернативы")
    confidence: float = Field(..., description="Уверенность в решении")
    expected_outcome: str = Field(..., description="Ожидаемый результат")
    timestamp: datetime = Field(default_factory=datetime.now)

class AutoGPTEvaluation(BaseModel):
    """Оценка результата действия"""
    action_evaluated: str = Field(..., description="Оцениваемое действие")
    success: bool = Field(..., description="Успешность действия")
    goal_progress: float = Field(..., description="Прогресс к цели (0-1)")
    lessons_learned: List[str] = Field(..., description="Извлеченные уроки")
    next_action_suggestion: Optional[str] = Field(None, description="Предложение следующего действия")
    timestamp: datetime = Field(default_factory=datetime.now)

# ===== RESULT MODELS =====

class AutoGPTTaskResult(BaseModel):
    """Результат выполнения AutoGPT задачи"""
    task_id: str = Field(..., description="ID задачи")
    goal: str = Field(..., description="Цель задачи")
    status: AutoGPTTaskStatus = Field(..., description="Финальный статус")
    success: bool = Field(..., description="Успешность выполнения")
    result_data: Dict[str, Any] = Field(..., description="Результаты выполнения")
    total_iterations: int = Field(..., description="Общее количество итераций")
    actions_taken: List[AutoGPTAction] = Field(..., description="Все выполненные действия")
    agent_thoughts: List[AutoGPTThought] = Field(..., description="Все мысли агента")
    lessons_learned: List[str] = Field(..., description="Извлеченные уроки")
    execution_time: float = Field(..., description="Общее время выполнения")
    tools_used: List[str] = Field(..., description="Использованные инструменты")
    final_evaluation: str = Field(..., description="Финальная оценка результата")
    created_at: datetime = Field(..., description="Время создания")
    completed_at: datetime = Field(..., description="Время завершения")
