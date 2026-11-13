"""
Модели для Master Agent (РЕКС)

Определяет структуры данных для взаимодействия с мастер-агентом,
управления задачами, контекста организации и коммуникации.

Author: Candidate Analysis Team  
Version: 1.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class MasterTaskStatus(str, Enum):
    """Статус задачи мастер-агента"""
    RECEIVED = "received"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    DELEGATING = "delegating"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class TaskPriority(str, Enum):
    """Приоритет задачи"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class ToolType(str, Enum):
    """Типы инструментов (нейросотрудники + системы)"""
    # HR инструменты
    PASSIVE_RECRUITER = "recruitment_runtime"
    ACTIVE_RECRUITER = "active_recruiter"
    SCREENER = "screener"
    ONBOARDER = "onboarder"
    
    # Технические инструменты
    DATA_ANALYST = "data_analyst"
    CODE_REVIEWER = "code_reviewer"
    
    # Маркетинговые инструменты
    CONTENT_GENERATOR = "content_generator"
    
    # Сервисные инструменты
    CUSTOMER_SUPPORT = "customer_support"
    
    # Финансовые инструменты
    FINANCE_HELPER = "finance_helper"
    
    # Универсальный инструмент
    GENERIC_TOOL = "generic_tool"


class MasterTaskRequest(BaseModel):
    """Запрос задачи для мастер-агента"""
    goal: str = Field(..., description="Высокоуровневая цель в естественном языке")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст задачи")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Приоритет задачи")
    deadline: Optional[datetime] = Field(None, description="Дедлайн выполнения")
    requester: str = Field(..., description="Кто поставил задачу")
    channel: str = Field("api", description="Канал получения (teams/telegram/api)")
    constraints: List[str] = Field(default_factory=list, description="Ограничения")
    expected_tools: Optional[List[ToolType]] = Field(None, description="Ожидаемые инструменты")
    human_assignees: Optional[List[str]] = Field(None, description="Назначенные люди (email/username)")
    departments: Optional[List[str]] = Field(None, description="Задействованные отделы")


class MasterTaskResponse(BaseModel):
    """Ответ на создание задачи мастер-агента"""
    task_id: str = Field(..., description="Уникальный ID задачи")
    status: MasterTaskStatus = Field(..., description="Статус принятия задачи")
    message: str = Field(..., description="Сообщение от мастер-агента")
    estimated_duration: str = Field(..., description="Оценка времени выполнения")
    assigned_tools: List[ToolType] = Field(default_factory=list, description="Назначенные инструменты")
    assigned_humans: List[str] = Field(default_factory=list, description="Назначенные люди")
    created_at: datetime = Field(default_factory=datetime.now)


class TaskAssignment(BaseModel):
    """Назначение задачи (инструменту или человеку)"""
    task_id: str = Field(..., description="ID основной задачи")
    assignment_type: str = Field(..., description="Тип назначения: 'tool' или 'human'")
    
    # Для инструментов
    tool_type: Optional[ToolType] = Field(None, description="Тип инструмента")
    tool_config: Dict[str, Any] = Field(default_factory=dict, description="Конфигурация инструмента")
    
    # Для людей
    human_assignee: Optional[str] = Field(None, description="Назначенный человек")
    department: Optional[str] = Field(None, description="Отдел назначенного")
    role: Optional[str] = Field(None, description="Роль назначенного")
    
    # Общие поля
    goal: str = Field(..., description="Конкретная цель")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст задачи")
    priority: TaskPriority = Field(..., description="Приоритет")
    dependencies: List[str] = Field(default_factory=list, description="Зависимости")
    estimated_time: str = Field(..., description="Оценка времени")
    status: str = Field("pending", description="Статус")
    deadline: Optional[datetime] = Field(None, description="Дедлайн")
    
    # Дополнительная информация
    instructions: str = Field("", description="Дополнительные инструкции")
    expected_format: str = Field("", description="Ожидаемый формат результата")
    approval_required: bool = Field(False, description="Требуется ли утверждение")


class ConversationMessage(BaseModel):
    """Сообщение в диалоге"""
    message_id: str = Field(..., description="ID сообщения")
    sender: str = Field(..., description="Отправитель (human/master_agent/agent_name)")
    recipient: str = Field(..., description="Получатель")
    content: str = Field(..., description="Содержание сообщения")
    message_type: str = Field("text", description="Тип сообщения (text/file/action)")
    channel: str = Field(..., description="Канал (teams/telegram/email)")
    conversation_id: str = Field(..., description="ID диалога")
    task_id: Optional[str] = Field(None, description="Связанная задача")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")


class OrganizationContext(BaseModel):
    """Контекст организации"""
    company_name: str = Field(..., description="Название компании")
    industry: str = Field(..., description="Отрасль")
    company_size: str = Field(..., description="Размер компании")
    
    # Структура компании
    departments: List[Dict[str, Any]] = Field(default_factory=list, description="Отделы")
    roles: Dict[str, Any] = Field(default_factory=dict, description="Роли и права")
    hierarchy: Dict[str, Any] = Field(default_factory=dict, description="Иерархия")
    
    # Бизнес-процессы
    hiring_process: Dict[str, Any] = Field(default_factory=dict, description="Процесс найма")
    approval_chains: Dict[str, Any] = Field(default_factory=dict, description="Цепочки согласований")
    sla_requirements: Dict[str, Any] = Field(default_factory=dict, description="SLA требования")
    
    # Культура и ценности
    company_values: List[str] = Field(default_factory=list, description="Ценности компании")
    culture_description: str = Field("", description="Описание культуры")
    communication_style: str = Field("professional", description="Стиль общения")
    
    # Технические требования
    tech_stack: List[str] = Field(default_factory=list, description="Технологический стек")
    tools_used: List[str] = Field(default_factory=list, description="Используемые инструменты")
    
    last_updated: datetime = Field(default_factory=datetime.now)


class ToolStatus(BaseModel):
    """Статус инструмента"""
    tool_type: ToolType = Field(..., description="Тип инструмента")
    status: str = Field(..., description="Текущий статус")
    current_task: Optional[str] = Field(None, description="Текущая задача")
    workload: float = Field(0.0, description="Загрузка (0-1)")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    last_activity: datetime = Field(default_factory=datetime.now)
    capabilities: List[str] = Field(default_factory=list, description="Возможности инструмента")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    
class HumanAssignee(BaseModel):
    """Информация о назначенном человеке"""
    email: str = Field(..., description="Email сотрудника")
    name: str = Field(..., description="Полное имя")
    department: str = Field(..., description="Отдел")
    role: str = Field(..., description="Роль")
    permissions: List[str] = Field(default_factory=list, description="Разрешения")
    availability: str = Field("available", description="Доступность")
    current_workload: float = Field(0.0, description="Текущая загрузка")
    preferred_contact: str = Field("email", description="Предпочитаемый способ связи")
    timezone: str = Field("UTC+3", description="Часовой пояс")


class WorkflowRule(BaseModel):
    """Правило рабочего процесса"""
    rule_id: str = Field(..., description="ID правила")
    name: str = Field(..., description="Название правила")
    condition: Dict[str, Any] = Field(..., description="Условие активации")
    action: Dict[str, Any] = Field(..., description="Действие")
    priority: int = Field(1, description="Приоритет правила")
    active: bool = Field(True, description="Активно ли правило")
    created_by: str = Field(..., description="Кто создал")
    created_at: datetime = Field(default_factory=datetime.now)


class MasterMemory(BaseModel):
    """Память мастер-агента"""
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    active_tasks: Dict[str, TaskAssignment] = Field(default_factory=dict)
    tool_statuses: Dict[str, ToolStatus] = Field(default_factory=dict)
    human_assignees: Dict[str, HumanAssignee] = Field(default_factory=dict)
    organization_context: Optional[OrganizationContext] = Field(None)
    learned_patterns: Dict[str, Any] = Field(default_factory=dict)
    successful_strategies: List[Dict[str, Any]] = Field(default_factory=list)
    department_interactions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)


class QualityMetrics(BaseModel):
    """Метрики качества выполнения"""
    task_id: str = Field(..., description="ID задачи")
    completion_time: float = Field(..., description="Время выполнения (секунды)")
    success_rate: float = Field(..., description="Показатель успешности (0-1)")
    user_satisfaction: Optional[float] = Field(None, description="Удовлетворенность пользователя")
    quality_score: float = Field(..., description="Общая оценка качества")
    errors_count: int = Field(0, description="Количество ошибок")
    escalations_count: int = Field(0, description="Количество эскалаций")
    feedback: List[str] = Field(default_factory=list, description="Обратная связь")
    timestamp: datetime = Field(default_factory=datetime.now)


class EscalationEvent(BaseModel):
    """Событие эскалации"""
    event_id: str = Field(..., description="ID события")
    task_id: str = Field(..., description="ID задачи")
    assignment_type: str = Field(..., description="Тип назначения: 'tool' или 'human'")
    assignee: str = Field(..., description="Назначенный (инструмент или человек)")
    reason: str = Field(..., description="Причина эскалации")
    severity: str = Field(..., description="Серьезность (low/medium/high/critical)")
    escalated_to: str = Field(..., description="Кому эскалировано")
    escalation_type: str = Field("manual", description="Тип эскалации (automatic/manual)")
    resolved: bool = Field(False, description="Решено ли")
    resolution: Optional[str] = Field(None, description="Способ решения")
    timestamp: datetime = Field(default_factory=datetime.now)


class MasterTaskStatusUpdate(BaseModel):
    """Обновление статуса задачи"""
    task_id: str = Field(..., description="ID задачи")
    status: MasterTaskStatus = Field(..., description="Новый статус")
    progress: float = Field(..., description="Прогресс выполнения (0-1)")
    current_action: str = Field(..., description="Текущее действие")
    agent_updates: List[Dict[str, Any]] = Field(default_factory=list, description="Обновления от агентов")
    estimated_completion: Optional[datetime] = Field(None, description="Оценка времени завершения")
    blockers: List[str] = Field(default_factory=list, description="Блокеры")
    next_steps: List[str] = Field(default_factory=list, description="Следующие шаги")
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolCapability(BaseModel):
    """Возможность инструмента"""
    name: str = Field(..., description="Название возможности")
    description: str = Field(..., description="Описание")
    category: str = Field(..., description="Категория (analysis/creation/communication/etc)")
    complexity: str = Field("medium", description="Сложность (low/medium/high)")
    estimated_time: str = Field(..., description="Ориентировочное время")
    required_inputs: List[str] = Field(default_factory=list, description="Необходимые входные данные")
    output_format: str = Field("", description="Формат выходных данных")
    
class ToolRegistration(BaseModel):
    """Регистрация инструмента в системе"""
    tool_id: str = Field(..., description="Уникальный ID инструмента")
    tool_type: ToolType = Field(..., description="Тип инструмента")
    name: str = Field(..., description="Название инструмента")
    description: str = Field(..., description="Описание")
    version: str = Field("1.0.0", description="Версия")
    
    # Технические параметры
    endpoint: Optional[str] = Field(None, description="API endpoint")
    health_check_url: Optional[str] = Field(None, description="URL проверки здоровья")
    authentication: Dict[str, Any] = Field(default_factory=dict, description="Параметры аутентификации")
    
    # Возможности
    capabilities: List[ToolCapability] = Field(default_factory=list)
    
    # Метаданные
    tags: List[str] = Field(default_factory=list, description="Теги для поиска")
    department_affinity: List[str] = Field(default_factory=list, description="Предпочтительные отделы")
    priority_level: int = Field(1, description="Приоритет выбора (1-5)")
    max_concurrent_tasks: int = Field(5, description="Максимум одновременных задач")
    
    # Статус
    active: bool = Field(True, description="Активность")
    registered_at: datetime = Field(default_factory=datetime.now)
    last_health_check: Optional[datetime] = Field(None)
    
class HumanTaskNotification(BaseModel):
    """Уведомление о задаче для человека"""
    notification_id: str = Field(..., description="ID уведомления")
    task_id: str = Field(..., description="ID связанной задачи")
    recipient: HumanAssignee = Field(..., description="Получатель")
    
    # Содержание
    subject: str = Field(..., description="Тема уведомления")
    message: str = Field(..., description="Текст сообщения")
    task_description: str = Field(..., description="Описание задачи")
    priority: TaskPriority = Field(..., description="Приоритет")
    deadline: Optional[datetime] = Field(None, description="Дедлайн")
    
    # Метаданные
    channel: str = Field(..., description="Канал доставки (email/teams/telegram)")
    format_type: str = Field("text", description="Формат (text/html/markdown)")
    attachments: List[str] = Field(default_factory=list, description="Приложения")
    
    # Статус
    status: str = Field("pending", description="Статус доставки")
    sent_at: Optional[datetime] = Field(None)
    read_at: Optional[datetime] = Field(None)
    responded_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.now)
    
class DirectorDecision(BaseModel):
    """Решение директора (РЕКС)"""
    decision_id: str = Field(..., description="ID решения")
    task_id: str = Field(..., description="ID связанной задачи")
    
    # Информация о решении
    decision_type: str = Field(..., description="Тип решения (approve/reject/delegate/escalate/request_info)")
    reasoning: str = Field(..., description="Обоснование решения")
    confidence: float = Field(..., description="Уверенность в решении (0-1)")
    
    # Действия
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="План действий")
    assignments: List[TaskAssignment] = Field(default_factory=list, description="Новые назначения")
    
    # Контроль
    review_required: bool = Field(False, description="Требуется ли проверка")
    escalation_path: Optional[str] = Field(None, description="Путь эскалации")
    
    # Статус
    status: str = Field("active", description="Статус решения")
    created_at: datetime = Field(default_factory=datetime.now)
    executed_at: Optional[datetime] = Field(None)
    
class CommunicationChannel(BaseModel):
    """Канал коммуникации"""
    channel_id: str = Field(..., description="ID канала")
    channel_type: str = Field(..., description="Тип канала (teams/telegram/email)")
    name: str = Field(..., description="Название канала")
    participants: List[str] = Field(default_factory=list, description="Участники")
    active: bool = Field(True, description="Активен ли канал")
    bot_enabled: bool = Field(False, description="Включен ли бот")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Настройки канала")
    created_at: datetime = Field(default_factory=datetime.now)
