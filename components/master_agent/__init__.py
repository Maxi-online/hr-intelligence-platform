"""
Master Agent (REX) - Chief Coordinator of Neuro Officers

Autonomous AI agent who manages all the Neuro staff of the organization:
- Recruitment Runtime (existing)
- Active Recruiter (new)
- Screener (new) 
- Onboarder (new)

Main opportunities:
- Natural communication with people through Teams/Telegram
- Understanding the context of the organization
- Autonomous planning and delegation of tasks
Quality control and training
- Multichannel communication

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
