"""
Master Agent (REX) - Chief Coordinator of Neuro Officers

Autonomous AI Agent uses GPT-5 to manage all Neuro staff
AutoGPT planning and decision-making logic.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from openai import AsyncOpenAI
import httpx

from .models import (
    MasterTaskRequest, MasterTaskResponse, MasterTaskStatus, TaskAssignment,
    ConversationMessage, OrganizationContext, MasterMemory, QualityMetrics,
    EscalationEvent, ToolType, TaskPriority
)
from .messenger_interface import MessengerInterface
from .task_distributor import TaskDistributor
from .organization_context import OrganizationContextManager
from .memory_manager import MasterMemoryManager
from .quality_controller import QualityController

logger = logging.getLogger("master-agent")


class MasterAgent:
    """
    Chief Coordinator of Neuro Officers (REX)
    
    Key opportunities:
    - 🧠 GPT-5 for strategic planning
    - 💬 Natural communication with people through Teams/Telegram
    - 🎯 Autonomous task sharing among agents
    - 🏛️ Understanding the context of the organization
    - ✅ Quality control and learning
    - 📊 Monitoring and Analyst
    - ⚙️ Business processes management
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger
        
        # A unique I.D. Agent
        self.agent_id = f"master_agent_{uuid.uuid4().hex[:8]}"
        
        # LLM Settings
        self._setup_llm()
        
        # Initialization of components
        self.messenger = MessengerInterface(config)
        self.task_distributor = TaskDistributor(config, self)
        self.org_context = OrganizationContextManager(config)
        self.memory_manager = MasterMemoryManager(config)
        self.quality_controller = QualityController(config, self)
        
        # Active tasks and status
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.agent_statuses: Dict[str, Dict[str, Any]] = {}
        self.conversation_contexts: Dict[str, List[ConversationMessage]] = {}
        
        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "escalated_tasks": 0,
            "average_completion_time": 0.0,
            "user_satisfaction": 0.0,
            "uptime_start": datetime.now()
        }
        
        logger.info(f"💼 REX-AI Director initialized: {self.agent_id}")
    
    def _setup_llm(self):
        'LLM client settings'
        try:
            ai_config = self.config.get("master_agent", {})
            
            # Core GPT-5 for strategic planning
            self.main_model = ai_config.get("main_model", "gpt-5-mini")
            self.fast_model = ai_config.get("fast_model", "gpt-5-mini")
            
            # Settings of Proxi
            proxy_config = ai_config.get("proxy", {})
            proxy_enabled = proxy_config.get("enabled", False)
            
            http_client = None
            if proxy_enabled:
                proxy_host = proxy_config.get("host", "")
                proxy_port = proxy_config.get("port", "")
                if proxy_host and proxy_port:
                    proxy_url = f"http://{proxy_host}:{proxy_port}"
                    http_client = httpx.AsyncClient(proxy=proxy_url, timeout=httpx.Timeout(60.0))
            
            if not http_client:
                http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
            
            # OpenRouter or OpenAI client
            base_url = ai_config.get("base_url", "https://openrouter.ai/api/v1")
            api_key = ai_config.get("openrouter_api_key") or ai_config.get("openai_api_key")
            
            self.llm_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
            
            # GPT-5 Options
            self.max_completion_tokens = ai_config.get("max_completion_tokens", 4000)
            self.temperature = ai_config.get("temperature", 0.2)
            
            # GPT-5 Specific Settings
            gpt5_features = ai_config.get("gpt5_features", {})
            self.verbosity = gpt5_features.get("default_verbosity", "medium")
            self.reasoning_effort = gpt5_features.get("default_reasoning_effort", "medium")
            
            logger.info(f"✅ LLM is set: {self.main_model}")
            
        except Exception as e:
            logger.error(f"❌ Configuration of LLM errors: {e}")
            raise
    
    async def initialize(self):
        'Initialization of all components'
        try:
            # Initialization of subsystems
            await self.messenger.initialize()
            await self.task_distributor.initialize()
            await self.org_context.initialize()
            await self.memory_manager.initialize()
            await self.quality_controller.initialize()
            
            # Restoration of memory
            await self._restore_state()
            
            logger.info('🚀 Master Agent fully initialized')
            
        except Exception as e:
            logger.error(f"Error: ❌ Initialization of Master Agent: {e}")
            raise
    
    async def process_task(self, request: MasterTaskRequest, progress_callback: Optional[Callable] = None) -> MasterTaskResponse:
        """
        Main task processing cycle (AutuGPT logic)
        
        Steps:
        1. ANALYZE - In-depth analysis of the challenge and context
        2. PLAN - Strategic planning and selection of agents  
        3. ACT - Delegation of tasks and coordination
        4. EVALUATE - Evaluation of results and quality
        5. DECIDE - Decision-making on next steps
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()
        
        try:
            # Creation of the task
            task_data = {
                "id": task_id,
                "request": request,
                "status": MasterTaskStatus.RECEIVED,
                "start_time": start_time,
                "progress": 0.0,
                "assigned_agents": [],
                "messages": [],
                "iterations": 0
            }
            
            self.active_tasks[task_id] = task_data
            self.stats["total_tasks"] += 1
            
            # Notification of acceptance of task
            response = MasterTaskResponse(
                task_id=task_id,
                status=MasterTaskStatus.ANALYZING,
                message=f"Target accepted. Commencing goal analysis: '{request.goal}'",
                estimated_duration="I'm analyzing...",
                assigned_agents=[]
            )
            
            if progress_callback:
                await progress_callback(task_id, "received", ['Objective received', 'Commence processing'])
            
            # === 1. ANALYZE - In-depth analysis ===
            analysis_result = await self._deep_analysis(task_data)
            task_data["analysis"] = analysis_result
            task_data["progress"] = 0.2
            
            if progress_callback:
                await progress_callback(task_id, "analyzing", [
                    'Analysis completed',
                    f"Type of task: {analysis_result.get('task_type', 'general')}",
                    f"Complexity: {analysis_result.get('complexity', 'medium')}"
                ])
            
            # === 2. PLAN - Strategic planning ===
            task_data["status"] = MasterTaskStatus.PLANNING
            planning_result = await self._strategic_planning(task_data)
            task_data["plan"] = planning_result
            task_data["progress"] = 0.4
            
            if progress_callback:
                await progress_callback(task_id, "planning", [
                    'Plan established',
                    f"Agents: {', '.join(planning_result.get('agents', []))}",
                    f"Steps: {len(planning_result.get('steps', []))}"
                ])
            
            # === 3. ACT - Delegation and coordination ===
            task_data["status"] = MasterTaskStatus.DELEGATING
            execution_result = await self._coordinate_execution(task_data)
            task_data["execution"] = execution_result
            task_data["progress"] = 0.8
            
            if progress_callback:
                await progress_callback(task_id, "executing", [
                    'Tasks delegated',
                    'Coordinated implementation',
                    f"Active agents: {len(execution_result.get('active_agents', []))}"
                ])
            
            # === 4. EVALUATE - Evaluation of results ===
            task_data["status"] = MasterTaskStatus.MONITORING
            evaluation_result = await self._evaluate_results(task_data)
            task_data["evaluation"] = evaluation_result
            task_data["progress"] = 0.95
            
            # === 5. DECIDE - Decision-making ===
            decision_result = await self._make_final_decision(task_data)
            task_data["decision"] = decision_result
            task_data["progress"] = 1.0
            
            # Conclusion
            if decision_result.get("success", False):
                task_data["status"] = MasterTaskStatus.COMPLETED
                self.stats["completed_tasks"] += 1
                
                completion_time = (datetime.now() - start_time).total_seconds()
                self._update_performance_metrics(completion_time, True)
                
                # Maintaining a successful strategy
                await self._save_successful_strategy(task_data)
                
                response.status = MasterTaskStatus.COMPLETED
                response.message = decision_result.get("message", 'Achieved successfully')
                response.assigned_agents = planning_result.get("agents", [])
                
            else:
                task_data["status"] = MasterTaskStatus.FAILED
                self.stats["failed_tasks"] += 1
                
                response.status = MasterTaskStatus.FAILED
                response.message = decision_result.get("message", 'Mission not achieved')
            
            if progress_callback:
                await progress_callback(task_id, "completed", [
                    decision_result.get("message", 'Completed'),
                    f"Time frame: {(datetime.now() - start_time).total_seconds():.1f}c"
                ])
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error of task processing {task_id}: {e}")
            self.stats["failed_tasks"] += 1
            
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = MasterTaskStatus.FAILED
                self.active_tasks[task_id]["error"] = str(e)
            
            return MasterTaskResponse(
                task_id=task_id,
                status=MasterTaskStatus.FAILED,
                message=f"Error of execution: {str(e)}",
                estimated_duration="N/A",
                assigned_agents=[]
            )
    
    async def _deep_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        'In-depth GPT-5 task analysis'
        try:
            request = task_data["request"]
            
            # Getting the context of the organization
            org_context = await self.org_context.get_context()
            
            # Analysis of the history of similar tasks
            similar_tasks = await self.memory_manager.find_similar_tasks(request.goal)
            
            # Prompt for Director Analysis
            analysis_prompt = f"""
You're REX, AI's director of the company.{org_context.company_name}\".
You run every department and make strategic decisions.

ANALYSIS'S OBJECTIVE:
Objective: {request.goal}
Context: {json.dumps(request.context, ensure_ascii=False, indent=2)}
Priority: {request.priority}
Divisions: {request.departments or 'Not specified'}
Limitations: {request.constraints}

CONTEXT OF THE UNITED NATIONS:
- Industry: {org_context.industry}
- Size: {org_context.company_size}
- Divisions managed by: {[dept.get('name', '') for dept in org_context.departments]}
- Control style: {org_context.communication_style}

ELEVABLE RESOURCES:
People in the department:
{self._format_human_resources(org_context)}

INSTRUMENTS:
1. Recruitment Runtime - HR: job creation, feedback analysis
2. Active Recruiter - HR: Active Search, Headhunting
3. Data Analyst - Analysis: Business metrics, reports
4. Content Generator - Marketing: Content, social media
5. Code Reviewer - Development: code analysis, review
6. Computer Support - Services: client support
7. Finance Help - Finance: Budget Analysis, Reports
8. Generic Tool - Universal Setup Tool

EXPERIENCE SOLUTIONS:
{json.dumps(similar_tasks, ensure_ascii=False, indent=2)}

PROANALIZATION AS DIRECTOR:
1. Nature and scope of the task (which divisions are affected))
2. Strategic importance for the company
3. Whether information is required from people
4. What tools can help
5. Which people to attract and why
6. Synergies and coordination
7. Risks and business opportunities
8. Impact on the general objectives of the company

Answer JSON:
{{
    \"task_nature\": \"Description of the nature of the task\",
    \"domain\": \"Main area (hr/tech/marketing/finance/management/universal)\",
    \"scope\": \"Scope (departmental/cross_departmental/company_wide)\",
    \"complexity\": \"Complexity (low/medium/high/strategic)\",
    \"affected_departments\": [\"List of affected divisions\"],
    \"required_human_input\": [\"What people need to know\"],
    \"recommended_tools\": [\"List of recommended tools\"],
    \"human_assignments\": [\"Someone to attract\"],
    \"strategic_importance\": \"low/medium/high/critical\",
    \"business_impact\": \"Description of the impact on business\",
    \"key_stages\": [\"Phase 1\", \"Phase 2\", ...],
    \"risks\": [\"Risk 1\", \"Risk 2\", ...],
    \"estimated_hours\": number,
    \"confidence\": 0.95,
    \"director_insights\": [\"Director &apos; s key websites\"]
}}
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.main_model,
                messages=[
                    {"role": "system", "content": "You're the director of a company with full authority to run all departments."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,
                verbosity=self.verbosity,
                reasoning_effort=self.reasoning_effort,
                response_format={"type": "json_object"}
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            
            logger.info(f"✅ Analysis completed: {analysis_result.get('domain')} ({analysis_result.get('complexity')})")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Error of analysis: {e}")
            return {
                "task_nature": "standard",
                "domain": "universal",
                "complexity": "medium",
                "scope": "departmental",
                "affected_departments": ["management"],
                "recommended_tools": ["generic_tool"],
                "strategic_importance": "medium",
                "business_impact": 'Needs attention.',
                "estimated_hours": 2,
                "confidence": 0.5,
                "director_insights": ['Further analysis required'],
                "error": str(e)
            }
    
    def _format_human_resources(self, org_context: OrganizationContext) -> str:
        'Formatting information on human resources'
        resources = []
        for dept in org_context.departments:
            dept_name = dept.get('name', 'Unknown Division')
            dept_head = dept.get('head', 'Not designated')
            dept_size = dept.get('size', 0)
            
            resources.append(f"- {dept_name}: {dept_head} (command) {dept_size} (number of persons)")
        
        return "\n".join(resources)
    
    async def _strategic_planning(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        'Strategic implementation planning'
        try:
            analysis = task_data["analysis"]
            request = task_data["request"]
            
            # Checking the availability of agents
            agent_availability = await self.task_distributor.check_agent_availability()
            
            planning_prompt = f"""
On the basis of the task analysis, establish a detailed implementation plan.

ANALYSIS OF THE PROBLEMS:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

ACCESS TO AGENCIES:
{json.dumps(agent_availability, ensure_ascii=False, indent=2)}

ESTABLISH THE PLAN:
1. Step sequence
2. Agent distribution  
3. Relationships between tasks
4. Time frame
5. Control and sync points
6. Plan B for malfunctions

JSON response format:
{{
    \"agents\": [\"List of selected agents\"],
    \"steps\": [
        {{
            \"step\": 1,
            \"description\": \"Description\",
            \"agent\": \"Type of agent\",
            \"estimated_time\": \"time\",
            \"dependencies\": [\"Dependency\"],
            \"deliverables\": [\"results\"]
        }}
    ],
    \"coordination_points\": [\"Synchronization points\"],
    \"quality_checks\": [\"Quality assurance\"], 
    \"contingency_plans\": [\"Malfunction plans\"],
    \"total_estimated_time\": \"Total time\"
}}
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.main_model,
                messages=[
                    {"role": "system", "content": "You're a strategic task planner for an I.I.A. team."},
                    {"role": "user", "content": planning_prompt}
                ],
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,
                verbosity=self.verbosity,
                reasoning_effort=self.reasoning_effort,
                response_format={"type": "json_object"}
            )
            
            plan = json.loads(response.choices[0].message.content)
            
            # Plan validation
            if not plan.get("agents") or not plan.get("steps"):
                raise ValueError('The plan should contain agents and steps')
            
            logger.info(f"✅ Plan established: {len(plan.get('steps', []))} Steps, {len(plan.get('agents', []))} Agents")
            return plan
            
        except Exception as e:
            logger.error(f"❌ Error of planning: {e}")
            # Basic plan
            return {
                "approach": "standard",
                "strategy_type": "delegation", 
                "execution_sequence": ['Analysis', 'Planning', 'Implementation'],
                "human_assignments": [],
                "tool_assignments": [{"tool_type": "generic_tool", "task": 'Do the task', "priority": "medium"}],
                "estimated_timeline": '2-4 hours',
                "error": str(e)
            }
    
    async def _coordinate_execution(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        'Coordination of implementation through Task Distributor'
        try:
            plan = task_data["plan"]
            request = task_data["request"]
            
            # Delegation of tasks to agents
            execution_results = []
            active_agents = []
            
            for step in plan.get("steps", []):
                agent_type = step.get("agent")
                if agent_type:
                    # Creation of a tool appointment
                    subtask = TaskAssignment(
                        task_id=task_data["id"],
                        assignment_type="tool",
                        tool_type=ToolType(agent_type),
                        goal=step.get("description", request.goal),
                        context=request.context,
                        priority=request.priority,
                        estimated_time=step.get("estimated_time", '1 hour')
                    )
                    
                    # Sending a task to an agent
                    result = await self.task_distributor.delegate_task(subtask)
                    execution_results.append(result)
                    
                    if result.get("success"):
                        active_agents.append(agent_type)
            
            return {
                "active_agents": active_agents,
                "execution_results": execution_results,
                "coordination_status": "active"
            }
            
        except Exception as e:
            logger.error(f"❌ Error of coordination: {e}")
            return {"error": str(e), "active_agents": []}
    
    async def _evaluate_results(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        'Performance evaluation'
        try:
            # Collection of results from all agents
            task_id = task_data["id"]
            agent_results = await self.task_distributor.collect_results(task_id)
            
            # Quality analysis
            quality_metrics = await self.quality_controller.evaluate_task_quality(task_data, agent_results)
            
            return {
                "agent_results": agent_results,
                "quality_metrics": quality_metrics,
                "overall_success": quality_metrics.success_rate > 0.7
            }
            
        except Exception as e:
            logger.error(f"❌ Error of assessment: {e}")
            return {"error": str(e), "overall_success": False}
    
    async def _make_final_decision(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        'Final decision'
        try:
            evaluation = task_data.get("evaluation", {})
            
            if evaluation.get("overall_success", False):
                return {
                    "success": True,
                    "message": 'Achieved successfully',
                    "next_actions": ['Notify customer', 'Save Results']
                }
            else:
                return {
                    "success": False,
                    "message": 'The task is done with errors',
                    "next_actions": ['Escalation', 'Retry']
                }
                
        except Exception as e:
            logger.error(f"❌ Error in decision making: {e}")
            return {"success": False, "message": f"mistake: {e}"}
    
    async def _restore_state(self):
        'Restoration of memory'
        try:
            saved_state = await self.memory_manager.get_master_memory()
            if saved_state:
                self.active_tasks = saved_state.active_tasks
                self.agent_statuses = saved_state.agent_statuses
                logger.info('✅ Restored from memory')
        except Exception as e:
            logger.warning(f"⚠️ Unable to recover: {e}")
    
    async def _save_successful_strategy(self, task_data: Dict[str, Any]):
        'Keeping a successful strategy in memory'
        try:
            strategy = {
                "goal_pattern": task_data["request"].goal,
                "analysis": task_data["analysis"],
                "plan": task_data["plan"],
                "success_metrics": task_data.get("evaluation", {}),
                "timestamp": datetime.now()
            }
            await self.memory_manager.save_successful_strategy(strategy)
        except Exception as e:
            logger.error(f"❌ Mistake of Strategy Maintenance: {e}")
    
    def _update_performance_metrics(self, completion_time: float, success: bool):
        'Update productivity metrics'
        # Update of average implementation time
        total_completed = self.stats["completed_tasks"]
        if total_completed > 0:
            current_avg = self.stats["average_completion_time"]
            self.stats["average_completion_time"] = (
                (current_avg * (total_completed - 1) + completion_time) / total_completed
            )
        else:
            self.stats["average_completion_time"] = completion_time
    
    async def get_status(self) -> Dict[str, Any]:
        'Taking Master Agency status'
        uptime = (datetime.now() - self.stats["uptime_start"]).total_seconds()
        
        return {
            "agent_id": self.agent_id,
            "status": "active",
            "uptime_seconds": uptime,
            "active_tasks_count": len(self.active_tasks),
            "stats": self.stats,
            "agent_statuses": self.agent_statuses,
            "memory_stats": await self.memory_manager.get_stats()
        }
    
    async def handle_conversation(self, message: ConversationMessage) -> ConversationMessage:
        'Processing of communication in dialogue'
        try:
            # Updating the dialogue context
            conversation_id = message.conversation_id
            if conversation_id not in self.conversation_contexts:
                self.conversation_contexts[conversation_id] = []
            
            self.conversation_contexts[conversation_id].append(message)
            
            # Response generation
            response_content = await self._generate_conversation_response(message)
            
            # Establishment of a response message
            response = ConversationMessage(
                message_id=f"msg_{uuid.uuid4().hex[:8]}",
                sender="master_agent",
                recipient=message.sender,
                content=response_content,
                channel=message.channel,
                conversation_id=conversation_id,
                task_id=message.task_id
            )
            
            self.conversation_contexts[conversation_id].append(response)
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in dialogue processing: {e}")
            return ConversationMessage(
                message_id=f"msg_error_{uuid.uuid4().hex[:8]}",
                sender="master_agent",
                recipient=message.sender,
                content=f"Sorry, there was an error: {e}",
                channel=message.channel,
                conversation_id=message.conversation_id
            )
    
    async def _generate_conversation_response(self, message: ConversationMessage) -> str:
        'Generating the response in the dialogue'
        try:
            # Context of the dialogue
            conversation_history = self.conversation_contexts.get(message.conversation_id, [])
            history_text = "\n".join([
                f"{msg.sender}: {msg.content}" 
                for msg in conversation_history[-10:]  # Last 10 communications
            ])
            
            # Context of the organization
            org_context = await self.org_context.get_context()
            
            conversation_prompt = f"""
You're REX, AI's director of the company.{org_context.company_name}\".
You run all departments and make strategic decisions.

CONTEXT OF THE UNITED NATIONS:
- Industry: {org_context.industry}
- Size: {org_context.company_size}
- Control style: {org_context.communication_style}
- Divisions managed by: {', '.join([dept.get('name', '') for dept in org_context.departments])}

HISTORY OF THE DIALOGUE:
{history_text}

NEW COMMUNICATION FROM {message.sender}:
{message.content}

Answer as an experienced director:
1. Authoritative, but friendly
2. Offer concrete solutions and actions
3. Use the right divisions if required
4. Set challenges for people or tools if you need them
5. Request additional information if unclear

The answer should be as a manager with full authority.
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.fast_model,
                messages=[
                    {"role": "system", "content": "You're the director of a company with full authority to run all departments."},
                    {"role": "user", "content": conversation_prompt}
                ],
                temperature=0.7,
                max_completion_tokens=500,
                verbosity="low",
                reasoning_effort="low"
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Error of Generation of Answer: {e}")
            return f"Got your request. I'm gonna figure this out and answer it. Possible technical complexities: {e}"
