"""
Recruitment Runtime

Автономный AI агент для пассивного рекрутинга который использует
LLM для автономного планирования и принятия решений.

Author: Candidate Analysis Team
Version: 2.0.0
"""

from .recruitment_runtime_agent import PassiveRecruiterAgent
from .models import (
    AutoGPTTaskRequest, AutoGPTTaskResponse, AutoGPTTaskStatus,
    AutoGPTAction, AutoGPTMemory, AutoGPTPlan
)

__all__ = [
    "PassiveRecruiterAgent",
    "AutoGPTTaskRequest", 
    "AutoGPTTaskResponse",
    "AutoGPTTaskStatus",
    "AutoGPTAction",
    "AutoGPTMemory", 
    "AutoGPTPlan"
]
