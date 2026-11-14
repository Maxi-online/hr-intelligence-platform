"""
Models for Master Agency (REX)

Identify data structures for interaction with master agent,
management, organization and communication context.

Author: Candidate Analysis Team  
Version: 1.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class MasterTaskStatus(str, Enum):
    'Status of the master agent &apos; s task'
    RECEIVED = "received"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    DELEGATING = "delegating"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class TaskPriority(str, Enum):
    'Priority of the task'
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class ToolType(str, Enum):
    'Types of tools (Neuro staff + systems)'
    # HR tools
    PASSIVE_RECRUITER = "recruitment_runtime"
    ACTIVE_RECRUITER = "active_recruiter"
    SCREENER = "screener"
    ONBOARDER = "onboarder"
    
    # Technical tools
    DATA_ANALYST = "data_analyst"
    CODE_REVIEWER = "code_reviewer"
    
    # Marketing instruments
    CONTENT_GENERATOR = "content_generator"
    
    # Service tools
    CUSTOMER_SUPPORT = "customer_support"
    
    # Financial instruments
    FINANCE_HELPER = "finance_helper"
    
    # Universal Instrument
    GENERIC_TOOL = "generic_tool"


class MasterTaskRequest(BaseModel):
    'Request task for master agent'
    goal: str = Field(..., description='High-level goal in natural language')
    context: Dict[str, Any] = Field(default_factory=dict, description='Context of the task')
    priority: TaskPriority = Field(TaskPriority.NORMAL, description='Priority of the task')
    deadline: Optional[datetime] = Field(None, description='Performance dedline')
    requester: str = Field(..., description='Who has set the task')
    channel: str = Field("api", description='Channel of reception (teams/telegram/api)')
    constraints: List[str] = Field(default_factory=list, description='Limitations')
    expected_tools: Optional[List[ToolType]] = Field(None, description='Expected instruments')
    human_assignees: Optional[List[str]] = Field(None, description='Designated persons (email/username)')
    departments: Optional[List[str]] = Field(None, description='Divisions involved')


class MasterTaskResponse(BaseModel):
    'Response to the task of the master agent'
    task_id: str = Field(..., description='Unique ID task')
    status: MasterTaskStatus = Field(..., description='Status of acceptance of task')
    message: str = Field(..., description='Message from the master agent')
    estimated_duration: str = Field(..., description='Estimation of time of implementation')
    assigned_tools: List[ToolType] = Field(default_factory=list, description='Designated instruments')
    assigned_humans: List[str] = Field(default_factory=list, description='Designated persons')
    created_at: datetime = Field(default_factory=datetime.now)


class TaskAssignment(BaseModel):
    'Designation of task (tool or person)'
    task_id: str = Field(..., description='ID core task')
    assignment_type: str = Field(..., description="Type of assignment: 'tool' or 'human'")
    
    # For tools
    tool_type: Optional[ToolType] = Field(None, description='Type of tool')
    tool_config: Dict[str, Any] = Field(default_factory=dict, description='Instrument configuration')
    
    # For people.
    human_assignee: Optional[str] = Field(None, description='Designated person')
    department: Optional[str] = Field(None, description='Division of Designated')
    role: Optional[str] = Field(None, description='Role of the designated')
    
    # General fields
    goal: str = Field(..., description='Specific objective')
    context: Dict[str, Any] = Field(default_factory=dict, description='Context of the task')
    priority: TaskPriority = Field(..., description='Priority')
    dependencies: List[str] = Field(default_factory=list, description='Dependence')
    estimated_time: str = Field(..., description='Time evaluation')
    status: str = Field("pending", description='Status')
    deadline: Optional[datetime] = Field(None, description='Deadline')
    
    # Supplementary information
    instructions: str = Field("", description='Additional instructions')
    expected_format: str = Field("", description='Expected outcome format')
    approval_required: bool = Field(False, description='Approval required')


class ConversationMessage(BaseModel):
    'Communication in dialogue'
    message_id: str = Field(..., description='Message ID')
    sender: str = Field(..., description='Sender (human/master_agent/agent_name)')
    recipient: str = Field(..., description='Beneficiary')
    content: str = Field(..., description='Contents of the communication')
    message_type: str = Field("text", description='Message type (text/file/action)')
    channel: str = Field(..., description='Channel (teams/telegram/email)')
    conversation_id: str = Field(..., description='ID Dialogues')
    task_id: Optional[str] = Field(None, description='Related task')
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict, description='Metadata')


class OrganizationContext(BaseModel):
    'Context of the organization'
    company_name: str = Field(..., description='Company name')
    industry: str = Field(..., description='Industry')
    company_size: str = Field(..., description='Company size')
    
    # Structure of the company
    departments: List[Dict[str, Any]] = Field(default_factory=list, description='Divisions')
    roles: Dict[str, Any] = Field(default_factory=dict, description='Roles and rights')
    hierarchy: Dict[str, Any] = Field(default_factory=dict, description='Hierarchy')
    
    # Business processes
    hiring_process: Dict[str, Any] = Field(default_factory=dict, description='Recruitment process')
    approval_chains: Dict[str, Any] = Field(default_factory=dict, description='Agreed loops')
    sla_requirements: Dict[str, Any] = Field(default_factory=dict, description='SLA Requirements')
    
    # Culture and values
    company_values: List[str] = Field(default_factory=list, description='Company values')
    culture_description: str = Field("", description='Description of culture')
    communication_style: str = Field("professional", description='Communication style')
    
    # Specifications
    tech_stack: List[str] = Field(default_factory=list, description='Technology latch')
    tools_used: List[str] = Field(default_factory=list, description='Tools used')
    
    last_updated: datetime = Field(default_factory=datetime.now)


class ToolStatus(BaseModel):
    'Status of the instrument'
    tool_type: ToolType = Field(..., description='Type of tool')
    status: str = Field(..., description='Current status')
    current_task: Optional[str] = Field(None, description='Current challenge')
    workload: float = Field(0.0, description='Loading (0-1)')
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    last_activity: datetime = Field(default_factory=datetime.now)
    capabilities: List[str] = Field(default_factory=list, description='Opportunities of the tool')
    endpoint: Optional[str] = Field(None, description="API endpoint")
    
class HumanAssignee(BaseModel):
    'Information on the person appointed'
    email: str = Field(..., description='Email employee')
    name: str = Field(..., description='Full name')
    department: str = Field(..., description='Division')
    role: str = Field(..., description='Role')
    permissions: List[str] = Field(default_factory=list, description='Permits')
    availability: str = Field("available", description='Accessibility')
    current_workload: float = Field(0.0, description='Current upload')
    preferred_contact: str = Field("email", description='Preferenced mode of communication')
    timezone: str = Field("UTC+3", description='Clock belt')


class WorkflowRule(BaseModel):
    'Rule of business'
    rule_id: str = Field(..., description='ID rules')
    name: str = Field(..., description='Title of the rule')
    condition: Dict[str, Any] = Field(..., description='Activation condition')
    action: Dict[str, Any] = Field(..., description='Action')
    priority: int = Field(1, description='Priority of the rule')
    active: bool = Field(True, description='Whether the rule is active')
    created_by: str = Field(..., description='Who created')
    created_at: datetime = Field(default_factory=datetime.now)


class MasterMemory(BaseModel):
    'Memory of Master Agent'
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
    'Performance-quality metrics'
    task_id: str = Field(..., description='ID Tasks')
    completion_time: float = Field(..., description='Implementation time (seconds)')
    success_rate: float = Field(..., description='Success indicator (0-1)')
    user_satisfaction: Optional[float] = Field(None, description='User satisfaction')
    quality_score: float = Field(..., description='Overall quality assessment')
    errors_count: int = Field(0, description='Number of errors')
    escalations_count: int = Field(0, description='Number of escalations')
    feedback: List[str] = Field(default_factory=list, description='Retaliation')
    timestamp: datetime = Field(default_factory=datetime.now)


class EscalationEvent(BaseModel):
    'The Event of Explosion'
    event_id: str = Field(..., description='ID Events')
    task_id: str = Field(..., description='ID Tasks')
    assignment_type: str = Field(..., description="Type of assignment: 'tool' or 'human'")
    assignee: str = Field(..., description='Designated (tool or person)')
    reason: str = Field(..., description='Reason for escalation')
    severity: str = Field(..., description='Seriousity (low/medium/high/critical)')
    escalated_to: str = Field(..., description='Whose escalation')
    escalation_type: str = Field("manual", description='Type of escalation (automatic/manual)')
    resolved: bool = Field(False, description='Has it been decided?')
    resolution: Optional[str] = Field(None, description='Method of solution')
    timestamp: datetime = Field(default_factory=datetime.now)


class MasterTaskStatusUpdate(BaseModel):
    'Updating the status of the task'
    task_id: str = Field(..., description='ID Tasks')
    status: MasterTaskStatus = Field(..., description='New status')
    progress: float = Field(..., description='Progress (0-1)')
    current_action: str = Field(..., description='Current action')
    agent_updates: List[Dict[str, Any]] = Field(default_factory=list, description='Updates from agents')
    estimated_completion: Optional[datetime] = Field(None, description='Estimate completion time')
    blockers: List[str] = Field(default_factory=list, description='Blocks')
    next_steps: List[str] = Field(default_factory=list, description='Next steps')
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolCapability(BaseModel):
    'Opportunity of the tool'
    name: str = Field(..., description='Name of possibility')
    description: str = Field(..., description='Description')
    category: str = Field(..., description='Category (analysis/creation/communication/etc)')
    complexity: str = Field("medium", description='Complexity (low/medium/high)')
    estimated_time: str = Field(..., description='Tentative timing')
    required_inputs: List[str] = Field(default_factory=list, description='Necessary input data')
    output_format: str = Field("", description='Output format')
    
class ToolRegistration(BaseModel):
    'Registration of the tool in the system'
    tool_id: str = Field(..., description='Unique ID tool')
    tool_type: ToolType = Field(..., description='Type of tool')
    name: str = Field(..., description='Title of tool')
    description: str = Field(..., description='Description')
    version: str = Field("1.0.0", description='Version')
    
    # Technical parameters
    endpoint: Optional[str] = Field(None, description="API endpoint")
    health_check_url: Optional[str] = Field(None, description='URL Health Testing')
    authentication: Dict[str, Any] = Field(default_factory=dict, description='Authentication Options')
    
    # Opportunities
    capabilities: List[ToolCapability] = Field(default_factory=list)
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description='Search tags')
    department_affinity: List[str] = Field(default_factory=list, description='Preference divisions')
    priority_level: int = Field(1, description='Priority of choice (1-5)')
    max_concurrent_tasks: int = Field(5, description='Maximum simultaneous tasks')
    
    # Status
    active: bool = Field(True, description='Activity')
    registered_at: datetime = Field(default_factory=datetime.now)
    last_health_check: Optional[datetime] = Field(None)
    
class HumanTaskNotification(BaseModel):
    'Notification of a human task'
    notification_id: str = Field(..., description='ID notifications')
    task_id: str = Field(..., description='ID related task')
    recipient: HumanAssignee = Field(..., description='Beneficiary')
    
    # Contents
    subject: str = Field(..., description='Subject of notification')
    message: str = Field(..., description='Text of the communication')
    task_description: str = Field(..., description='Task description')
    priority: TaskPriority = Field(..., description='Priority')
    deadline: Optional[datetime] = Field(None, description='Deadline')
    
    # Metadata
    channel: str = Field(..., description='Channel of delivery (email/teams/telegram)')
    format_type: str = Field("text", description='Format (text/html/markdown)')
    attachments: List[str] = Field(default_factory=list, description='Annexes')
    
    # Status
    status: str = Field("pending", description='Delivery status')
    sent_at: Optional[datetime] = Field(None)
    read_at: Optional[datetime] = Field(None)
    responded_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.now)
    
class DirectorDecision(BaseModel):
    'Director &apos; s Decision (REX)'
    decision_id: str = Field(..., description='ID Decisions')
    task_id: str = Field(..., description='ID related task')
    
    # Information on the decision
    decision_type: str = Field(..., description='Type of solution (approve/reject/delegate/escalate/request_info))')
    reasoning: str = Field(..., description='Justification of the decision')
    confidence: float = Field(..., description='Confidence in decision (0-1)')
    
    # Actions
    actions: List[Dict[str, Any]] = Field(default_factory=list, description='Action plan')
    assignments: List[TaskAssignment] = Field(default_factory=list, description='New appointments')
    
    # Monitoring
    review_required: bool = Field(False, description='Whether verification is required')
    escalation_path: Optional[str] = Field(None, description='The Way of Explosion')
    
    # Status
    status: str = Field("active", description='Status of decision')
    created_at: datetime = Field(default_factory=datetime.now)
    executed_at: Optional[datetime] = Field(None)
    
class CommunicationChannel(BaseModel):
    'Channel of communication'
    channel_id: str = Field(..., description='Channel ID')
    channel_type: str = Field(..., description='Channel type (teams/telegram/email)')
    name: str = Field(..., description='Channel Name')
    participants: List[str] = Field(default_factory=list, description='Participants')
    active: bool = Field(True, description='Is the channel active')
    bot_enabled: bool = Field(False, description='Whether the bot is on.')
    settings: Dict[str, Any] = Field(default_factory=dict, description='Channel settings')
    created_at: datetime = Field(default_factory=datetime.now)
