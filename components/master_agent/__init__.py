"""
Master Agent (РЕКС) - Главный координатор нейросотрудников

Автономный AI агент который управляет всеми нейросотрудниками организации:
- Recruitment Runtime (существующий)
- Active Recruiter (новый)
- Screener (новый) 
- Onboarder (новый)

Основные возможности:
- Естественное общение с людьми через Teams/Telegram
- Понимание контекста организации
- Автономное планирование и делегирование задач
- Контроль качества и обучение
- Многоканальная коммуникация

Author: Candidate Analysis Team
Version: 1.0.0
"""

from .master_agent import MasterAgent
from .models import (
    MasterTaskRequest, MasterTaskResponse, MasterTaskStatus,
    ConversationMessage, OrganizationContext, TaskAssignment,
    ToolType, ToolStatus, ToolRegistration, ToolCapability,
    HumanAssignee, HumanTaskNotification, DirectorDecision
)
from .messenger_interface import MessengerInterface
from .task_distributor import TaskDistributor
from .organization_context import OrganizationContextManager

__all__ = [
    "MasterAgent",
    "MasterTaskRequest",
    "MasterTaskResponse", 
    "MasterTaskStatus",
    "ConversationMessage",
    "OrganizationContext",
    "TaskAssignment",
    "ToolType",
    "ToolStatus", 
    "ToolRegistration",
    "ToolCapability",
    "HumanAssignee",
    "HumanTaskNotification",
    "DirectorDecision",
    "MessengerInterface",
    "TaskDistributor",
    "OrganizationContextManager"
]
