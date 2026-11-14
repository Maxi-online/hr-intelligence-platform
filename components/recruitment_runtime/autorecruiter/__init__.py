"""
Recruitment Runtime

Autonomous AI agent for passive recruitment that uses
LLM for autonomous planning and decision-making.

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
