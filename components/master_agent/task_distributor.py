"""
Tsk Distributor - Task manager between Neuro staff

Responsible for task analysis, selection of suitable agents, delegation
and coordination of implementation among all Neuro staff.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import uuid
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from .models import TaskAssignment, ToolType, TaskPriority, ToolStatus

if TYPE_CHECKING:
    from .master_agent import MasterAgent

logger = logging.getLogger("task-distributor")


class TaskDistributor:
    """
    Universal Tasks Orchestra for the Director
    
    Functions:
    - Distribution of tasks across all available tools
    - Flexible tool selection system
    - Monitoring of implementation across all divisions
    - Balance of resources
    - Coordination of inter-divisional processes
    """
    
    def __init__(self, config: Dict[str, Any], master_agent: "MasterAgent"):
        self.config = config
        self.master_agent = master_agent
        self.logger = logger
        
        # Agent configuration
        self.services_config = config.get("services", {})
        
        # Status of tools
        self.tool_statuses: Dict[str, ToolStatus] = {}
        self.tool_endpoints: Dict[str, str] = {}
        self.active_assignments: Dict[str, TaskAssignment] = {}
        
        # Sets of tasks by type of tool
        self.task_queues: Dict[str, List[TaskAssignment]] = {
            tool_type.value: [] for tool_type in ToolType
        }
        
        # Productivity metrics across all divisions
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Directors &apos; statistics
        self.stats = {
            "tasks_distributed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_response_time": 0.0,
            "tool_utilization": {},
            "department_engagement": {},
            "cross_department_tasks": 0
        }
        
        self._initialize_tool_endpoints()
    
    def _initialize_tool_endpoints(self):
        'Initialization of endpoints of all available tools'
        # HR tools
        recruitment_runtime_config = self.services_config.get("recruitment_runtime", {})
        self.tool_endpoints["recruitment_runtime"] = (
            f"http://{recruitment_runtime_config.get('host', 'localhost')}:"
            f"{recruitment_runtime_config.get('port', 8010)}"
        )
        
        # Developing instruments (while plugging)
        self.tool_endpoints["active_recruiter"] = "http://localhost:8011"
        self.tool_endpoints["screener"] = "http://localhost:8012"
        self.tool_endpoints["onboarder"] = "http://localhost:8013"
        
        # New universal instruments
        self.tool_endpoints["data_analyst"] = "http://localhost:8015"
        self.tool_endpoints["content_generator"] = "http://localhost:8016"
        self.tool_endpoints["code_reviewer"] = "http://localhost:8017"
        self.tool_endpoints["customer_support"] = "http://localhost:8018"
        self.tool_endpoints["finance_helper"] = "http://localhost:8019"
        self.tool_endpoints["generic_tool"] = "http://localhost:8021"
    
    async def initialize(self):
        'Initialization of Task Distributor'
        try:
            # Checking the availability of tools
            await self.check_tool_availability()
            
            # Initialization of metric
            await self._initialize_performance_metrics()
            
            self.logger.info('✅ Tsk Distributor initialized')
            
        except Exception as e:
            self.logger.error(f"Error: ❌ Initialization of Task Distributor: {e}")
            raise
    
    async def check_tool_availability(self) -> Dict[str, Dict[str, Any]]:
        'Checking the availability of all tools'
        availability = {}
        
        for tool_type, endpoint in self.tool_endpoints.items():
            try:
                # Checking Health Endpoint
                health_url = f"{endpoint}/health"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            availability[tool_type] = {
                                "available": True,
                                "status": "healthy",
                                "response_time": data.get("response_time", 0),
                                "workload": self._get_tool_workload(tool_type),
                                "endpoint": endpoint,
                                "capabilities": data.get("capabilities", [])
                            }
                        else:
                            availability[tool_type] = {
                                "available": False,
                                "status": "unhealthy",
                                "endpoint": endpoint
                            }
            except asyncio.TimeoutError:
                availability[tool_type] = {
                    "available": False,
                    "status": "timeout",
                    "endpoint": endpoint
                }
            except Exception as e:
                availability[tool_type] = {
                    "available": False,
                    "status": "error",
                    "error": str(e),
                    "endpoint": endpoint
                }
        
        return availability
    
    async def delegate_task(self, assignment: TaskAssignment) -> Dict[str, Any]:
        'Universal delegation of tasks'
        try:
            if assignment.assignment_type == "tool":
                return await self._delegate_to_tool(assignment)
            elif assignment.assignment_type == "human":
                return await self._delegate_to_human(assignment)
            else:
                return {
                    "success": False,
                    "error": f"Unknown type of destination: {assignment.assignment_type}"
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error of Delegation of Task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _delegate_to_tool(self, assignment: TaskAssignment) -> Dict[str, Any]:
        'Delegation of the IE tool task'
        try:
            tool_type = assignment.tool_type.value
            
            # Checking the accessibility of the tool
            availability = await self.check_tool_availability()
            if not availability.get(tool_type, {}).get("available", False):
                return {
                    "success": False,
                    "error": f"Instrument {tool_type} not available",
                    "tool_type": tool_type
                }
            
            # Send task to tool
            result = await self._send_task_to_tool(assignment)
            
            if result.get("success", False):
                # Maintaining appointment in active service
                self.active_assignments[assignment.task_id] = assignment
                self.task_queues[tool_type].append(assignment)
                self.stats["tasks_distributed"] += 1
                
                self.logger.info(f"✅ Objective {assignment.task_id} delegated to tool {tool_type}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error of Delegation of the Instrument: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_type": tool_type
            }
    
    async def _delegate_to_human(self, assignment: TaskAssignment) -> Dict[str, Any]:
        'Delegation of the task to the human being'
        try:
            # As long as the plug goes, there's gonna be a real implementation here.
            # Send notifications via Teams/Telegram/Email
            self.logger.info(f"📝 Task for {assignment.human_assignee} in the Division {assignment.department} established")
            
            self.stats["tasks_distributed"] += 1
            
            return {
                "success": True,
                "assignment_type": "human",
                "assignee": assignment.human_assignee,
                "department": assignment.department,
                "message": f"Objective {assignment.human_assignee}",
                "notification_sent": True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error of Delegation to Man: {e}")
            return {
                "success": False,
                "error": str(e),
                "assignee": assignment.human_assignee or 'unknown'
            }
    
    async def _send_task_to_tool(self, assignment: TaskAssignment) -> Dict[str, Any]:
        'Sending a task to a specific tool'
        try:
            tool_type = assignment.tool_type.value
            endpoint = self.tool_endpoints.get(tool_type)
            
            if not endpoint:
                return {"success": False, "error": f"Endpoint for {tool_type} not found"}
            
            # Preparation of data for the tool
            if tool_type == "recruitment_runtime":
                return await self._send_to_recruitment_runtime(assignment, endpoint)
            elif tool_type in ["active_recruiter", "screener", "onboarder"]:
                return await self._send_to_hr_tool(assignment, tool_type, endpoint)
            elif tool_type in ["data_analyst", "content_generator", "code_reviewer", "customer_support", "finance_helper"]:
                return await self._send_to_universal_tool(assignment, tool_type, endpoint)
            elif tool_type == "generic_tool":
                return await self._send_to_generic_tool(assignment, endpoint)
            else:
                return {"success": False, "error": f"Unknown type of tool: {tool_type}"}
                
        except Exception as e:
            self.logger.error(f"❌ Error in sending the tool task: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_to_recruitment_runtime(self, assignment: TaskAssignment, endpoint: str) -> Dict[str, Any]:
        'Send a task to the existing Recruitment Runtime'
        try:
            # Request Format for the Existing Auto-Procruiter API
            request_data = {
                "goal": assignment.goal,
                "context": assignment.context,
                "requirements": {
                    "priority": assignment.priority.value,
                    "estimated_time": assignment.estimated_time
                },
                "constraints": [],
                "max_iterations": 10,
                "tools_allowed": ["vacancy_builder", "vacancy_processor", "ranking", "ai_analysis"]
            }
            
            # URL to create a task in autorecruiter
            task_url = f"{endpoint}/api/autorecruiter/tasks"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(task_url, json=request_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        
                        return {
                            "success": True,
                            "agent_type": "recruitment_runtime",
                            "agent_task_id": result_data.get("task_id"),
                            "estimated_duration": result_data.get("estimated_duration"),
                            "message": result_data.get("message"),
                            "endpoint": endpoint
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "endpoint": endpoint
                        }
                        
        except Exception as e:
            self.logger.error(f"❌ Errors in Recruitment Runtime: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_to_hr_tool(self, assignment: TaskAssignment, tool_type: str, endpoint: str) -> Dict[str, Any]:
        'Send HR to Tools (Silencing)'
        # So far, these instruments have not been implemented
        self.logger.info(f"📝 A challenge for the HR tool {tool_type} added in line")
        
        return {
            "success": True,
            "tool_type": tool_type,
            "tool_task_id": f"hr_mock_{uuid.uuid4().hex[:8]}",
            "estimated_duration": assignment.estimated_time,
            "message": f"Target accepted by HR tool {tool_type} (in development)",
            "endpoint": endpoint,
            "mock": True
        }
    
    async def collect_results(self, master_task_id: str) -> List[Dict[str, Any]]:
        'Collection of results from all task agents'
        try:
            results = []
            
            # Searching for all mission assignments
            related_assignments = [
                assignment for assignment in self.active_assignments.values()
                if assignment.task_id == master_task_id
            ]
            
            for assignment in related_assignments:
                tool_type = assignment.tool_type.value
                
                if tool_type == "recruitment_runtime":
                    result = await self._get_recruitment_runtime_result(assignment)
                else:
                    result = await self._get_tool_result(assignment, tool_type)
                
                if result:
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error in collecting results: {e}")
            return []
    
    async def _get_recruitment_runtime_result(self, assignment: TaskAssignment) -> Optional[Dict[str, Any]]:
        'Recruitation Runtime'
        try:
            endpoint = self.agent_endpoints["recruitment_runtime"]
            
            # We assume that autorecruiter has an endpoint to produce a result
            result_url = f"{endpoint}/api/autorecruiter/tasks/{assignment.task_id}/result"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        return {
                            "agent_type": "recruitment_runtime",
                            "task_id": assignment.task_id,
                            "success": result_data.get("success", False),
                            "result_data": result_data.get("result_data", {}),
                            "message": result_data.get("final_evaluation", ""),
                            "execution_time": result_data.get("execution_time", 0)
                        }
                    else:
                        self.logger.warning(f"⚠️ Unable to obtain results from Recruitation Runtime: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error: ❌ Results from Recruitment Runtime: {e}")
            return None
    
    async def _get_tool_result(self, assignment: TaskAssignment, tool_type: str) -> Dict[str, Any]:
        'The result from the instruments (shuffle)'
        return {
            "tool_type": tool_type,
            "task_id": assignment.task_id,
            "success": True,
            "result_data": {"mock_result": f"Result from {tool_type}"},
            "message": f"Objective accomplished by tool {tool_type} (shuffles)",
            "execution_time": 60,
            "mock": True
        }
    
    async def monitor_task_progress(self, task_id: str) -> Dict[str, Any]:
        'Monitoring progress towards the goal'
        try:
            if task_id not in self.active_tasks:
                return {"error": 'The task is not found.'}
            
            task = self.active_tasks[task_id]
            agent_type = task.agent_type.value
            
            if agent_type == "recruitment_runtime":
                return await self._monitor_recruitment_runtime_progress(task)
            else:
                return await self._monitor_future_agent_progress(task, agent_type)
                
        except Exception as e:
            self.logger.error(f"❌ Error of task monitoring: {e}")
            return {"error": str(e)}
    
    async def _monitor_recruitment_runtime_progress(self, assignment: TaskAssignment) -> Dict[str, Any]:
        'Monitoring progress'
        try:
            endpoint = self.agent_endpoints["recruitment_runtime"]
            status_url = f"{endpoint}/api/autorecruiter/tasks/{assignment.task_id}/status"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(status_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        return {
                            "task_id": assignment.task_id,
                            "agent_type": "recruitment_runtime",
                            "status": status_data.get("status"),
                            "progress": status_data.get("progress_percentage", 0),
                            "current_action": status_data.get("current_action"),
                            "actions_taken": len(status_data.get("actions_taken", [])),
                            "agent_thoughts": status_data.get("agent_thoughts", [])
                        }
                    else:
                        return {"task_id": assignment.task_id, "error": f"HTTP {response.status}"}
                        
        except Exception as e:
            return {"task_id": assignment.task_id, "error": str(e)}
    
    async def _monitor_tool_progress(self, assignment: TaskAssignment, tool_type: str) -> Dict[str, Any]:
        'Monitoring of progress of instruments (shuffle)'
        return {
            "task_id": assignment.task_id,
            "tool_type": tool_type,
            "status": "in_progress",
            "progress": 0.5,
            "current_action": f"Implemented by tool {tool_type}",
            "mock": True
        }
    
    def _get_agent_workload(self, agent_type: str) -> float:
        'Receiving the current loading of the agent'
        if agent_type not in self.task_queues:
            return 0.0
        
        active_tasks = len([
            task for task in self.task_queues[agent_type]
            if task.status in ["pending", "in_progress"]
        ])
        
        # We're assuming a maximum of five simultaneous tasks on the agent.
        max_concurrent_tasks = 5
        return min(active_tasks / max_concurrent_tasks, 1.0)
    
    async def _check_agent_availability(self):
        'Check the availability of agents during initialization'
        availability = await self.check_agent_availability()
        
        available_agents = [
            agent for agent, status in availability.items()
            if status.get("available", False)
        ]
        
        if not available_agents:
            self.logger.warning('⚠️ No agent is available!')
        else:
            self.logger.info(f"✅ Affordable agents: {', '.join(available_agents)}")
    
    async def _initialize_performance_metrics(self):
        'Initialization of productivity metrics'
        for tool_type in ToolType:
            self.performance_metrics[tool_type.value] = {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "average_response_time": 0.0,
                "success_rate": 0.0,
                "last_active": None
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        'Getting Tsk Distributor statistics'
        # Update tools download statistics
        for tool_type in ToolType:
            self.stats["tool_utilization"][tool_type.value] = self._get_tool_workload(tool_type.value)
        
        return {
            "stats": self.stats,
            "active_assignments_count": len(self.active_assignments),
            "task_queues_sizes": {
                tool_type: len(queue) for tool_type, queue in self.task_queues.items()
            },
            "tool_endpoints": self.tool_endpoints,
            "performance_metrics": self.performance_metrics
        }
    
    async def balance_workload(self) -> Dict[str, Any]:
        'Load balance between agents'
        try:
            # Analysis of tool downloads
            workloads = {}
            for tool_type in ToolType:
                workloads[tool_type.value] = self._get_tool_workload(tool_type.value)
            
            # Search for overloaded agents
            overloaded_agents = [
                agent for agent, workload in workloads.items()
                if workload > 0.8
            ]
            
            # Search for underworked agents
            underloaded_agents = [
                agent for agent, workload in workloads.items()
                if workload < 0.5
            ]
            
            # Logic of redeployment of tasks (as long as basic)
            rebalanced_tasks = 0
            
            # In real terms, there would be a logic of moving tasks
            # between numbers of agents of the same type
            
            return {
                "rebalanced_tasks": rebalanced_tasks,
                "overloaded_agents": overloaded_agents,
                "underloaded_agents": underloaded_agents,
                "current_workloads": workloads
            }
            
        except Exception as e:
            self.logger.error(f"Error: ❌ Balance of load: {e}")
            return {"error": str(e)}
