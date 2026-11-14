"""
AutoGPT Recruitment Runtime - Models

Models for real AutoGPT agents that use LLM 
For autonomous planning and decision-making.

Author: Candidate Analysis Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class AutoGPTTaskStatus(str, Enum):
    'AutoGPT Task Status'
    ACCEPTED = "accepted"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AutoGPTActionType(str, Enum):
    'AutoGPT Agent Activity Types'
    THINK = "think"
    PLAN = "plan"
    EXECUTE_TOOL = "execute_tool"
    EVALUATE = "evaluate"
    DECIDE_NEXT = "decide_next"

# ===== REQUEST MODELS =====

class AutoGPTTaskRequest(BaseModel):
    'Request for AutoGPT Agent'
    goal: str = Field(..., description='High-level objective for autonomous implementation')
    context: Optional[Dict[str, Any]] = Field(None, description='Context and additional information')
    requirements: Optional[Dict[str, Any]] = Field(None, description='Specific result requirements')
    constraints: Optional[List[str]] = Field(None, description='Limitations and implementation rules')
    max_iterations: int = Field(10, description='Maximum iterations of autonomous planning')
    tools_allowed: Optional[List[str]] = Field(None, description='Authorized tools')

# ===== RESPONSE MODELS =====

class AutoGPTTaskResponse(BaseModel):
    'Response to AutoGPT Task'
    task_id: str = Field(..., description='ID Self-contained task')
    status: str = Field(..., description='Status of acceptance of task')
    message: str = Field(..., description='Message from AutoGPT Agent')
    estimated_duration: str = Field(..., description='Estimation of time of implementation')
    created_at: datetime = Field(default_factory=datetime.now)

class AutoGPTAction(BaseModel):
    'AutoGPT Agent Action'
    action_type: AutoGPTActionType = Field(..., description='Type of action')
    description: str = Field(..., description='Description of action')
    reasoning: str = Field(..., description='Justification for action')
    tool_name: Optional[str] = Field(None, description='Tool used')
    tool_params: Optional[Dict[str, Any]] = Field(None, description='Tool Options')
    result: Optional[Dict[str, Any]] = Field(None, description='Result')
    timestamp: datetime = Field(default_factory=datetime.now)

class AutoGPTTaskStatus(BaseModel):
    'AutoGPT Task Status'
    task_id: str = Field(..., description='ID Tasks')
    status: AutoGPTTaskStatus = Field(..., description='Current status')
    current_action: str = Field(..., description='Current action of agent')
    agent_thoughts: List[str] = Field(default_factory=list, description="Agent's Thoughts")
    actions_taken: List[AutoGPTAction] = Field(default_factory=list, description='Actions implemented')
    created_at: datetime = Field(..., description='Time of creation')
    progress_percentage: Optional[float] = Field(None, description='Progress in implementation')

# ===== AGENT MODELS =====

class AutoGPTThought(BaseModel):
    "AutoGPT Agent's Thought"
    content: str = Field(..., description='Content of the thought')
    type: str = Field(..., description='Type of thought (analysis, planning, evaluation)')
    confidence: float = Field(..., description='Confidence in the mind (0-1)')
    timestamp: datetime = Field(default_factory=datetime.now)

class AutoGPTMemory(BaseModel):
    'Memory of the AutoGPT Agent'
    task_id: str = Field(..., description='ID Tasks')
    goal: str = Field(..., description='Objective')
    context: Dict[str, Any] = Field(default_factory=dict, description='Context')
    thoughts: List[AutoGPTThought] = Field(default_factory=list, description='The History of Thinking')
    actions: List[AutoGPTAction] = Field(default_factory=list, description='History of action')
    current_plan: Optional[List[str]] = Field(None, description='Current plan')
    learned_facts: List[str] = Field(default_factory=list, description='The facts studied')
    available_tools: List[str] = Field(default_factory=list, description='Affordable tools')

class AutoGPTPlan(BaseModel):
    'AutoGPT Agent Plan'
    goal: str = Field(..., description='Purpose of the plan')
    steps: List[str] = Field(..., description='Steps to be taken')
    reasoning: str = Field(..., description='Justification of the plan')
    estimated_steps: int = Field(..., description='Expected number of steps')
    success_criteria: List[str] = Field(..., description='Criteria for success')
    tools_needed: List[str] = Field(..., description='Necessary tools')
    created_at: datetime = Field(default_factory=datetime.now)

# ===== TOOL MODELS =====

class AutoGPTTool(BaseModel):
    'AutoGPT Agent tool'
    name: str = Field(..., description='Title of tool')
    description: str = Field(..., description='Description of possibilities')
    parameters: Dict[str, Any] = Field(..., description='Parameters diagram')
    service_url: str = Field(..., description='URL Microservice')
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description='HTTP Method')

class AutoGPTToolResult(BaseModel):
    'Result of the tool'
    tool_name: str = Field(..., description='Title of tool')
    success: bool = Field(..., description='Success')
    result_data: Dict[str, Any] = Field(..., description='Result')
    error: Optional[str] = Field(None, description='Error if there is')
    execution_time: float = Field(..., description='Implementation time')
    timestamp: datetime = Field(default_factory=datetime.now)

# ===== LLM INTERACTION MODELS =====

class AutoGPTPrompt(BaseModel):
    'Prompte for LLM'
    system_message: str = Field(..., description='System message')
    user_message: str = Field(..., description='User message')
    context: Dict[str, Any] = Field(default_factory=dict, description='Context')
    expected_format: str = Field(..., description='Expected format of response')

class AutoGPTLLMResponse(BaseModel):
    'Response from LLM'
    content: str = Field(..., description='Contents of the reply')
    parsed_data: Optional[Dict[str, Any]] = Field(None, description='Dissolved data')
    reasoning: Optional[str] = Field(None, description='Justification of the reply')
    confidence: Optional[float] = Field(None, description='LLM confidence')
    tokens_used: int = Field(0, description='Token use')
    processing_time: float = Field(0.0, description='Processing time')

# ===== DECISION MODELS =====

class AutoGPTDecision(BaseModel):
    'AutoGPT Agent &apos; s Decision'
    decision_type: str = Field(..., description='Type of solution')
    chosen_action: str = Field(..., description='Selected action')
    reasoning: str = Field(..., description='Justification of the decision')
    alternatives_considered: List[str] = Field(..., description='Alternatives considered')
    confidence: float = Field(..., description='Confidence in Decision')
    expected_outcome: str = Field(..., description='Output expected')
    timestamp: datetime = Field(default_factory=datetime.now)

class AutoGPTEvaluation(BaseModel):
    'Impact assessment'
    action_evaluated: str = Field(..., description='Measured action')
    success: bool = Field(..., description='Success')
    goal_progress: float = Field(..., description='Progress towards goal (0-1)')
    lessons_learned: List[str] = Field(..., description='The learned lessons')
    next_action_suggestion: Optional[str] = Field(None, description='Proposal for next action')
    timestamp: datetime = Field(default_factory=datetime.now)

# ===== RESULT MODELS =====

class AutoGPTTaskResult(BaseModel):
    'Outcome of AutoGPT Task'
    task_id: str = Field(..., description='ID Tasks')
    goal: str = Field(..., description='Objective')
    status: AutoGPTTaskStatus = Field(..., description='Final status')
    success: bool = Field(..., description='Success')
    result_data: Dict[str, Any] = Field(..., description='Implementation results')
    total_iterations: int = Field(..., description='Total number of iterations')
    actions_taken: List[AutoGPTAction] = Field(..., description='All actions carried out')
    agent_thoughts: List[AutoGPTThought] = Field(..., description="All Agent's Thoughts")
    lessons_learned: List[str] = Field(..., description='The learned lessons')
    execution_time: float = Field(..., description='Total implementation time')
    tools_used: List[str] = Field(..., description='Tools used')
    final_evaluation: str = Field(..., description='Final evaluation of results')
    created_at: datetime = Field(..., description='Time of creation')
    completed_at: datetime = Field(..., description='Completion time')
