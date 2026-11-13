"""
Task Distributor - Распределитель задач между нейросотрудниками

Отвечает за анализ задач, выбор подходящих агентов, делегирование
и координацию выполнения между всеми нейросотрудниками.

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
    Универсальный оркестратор задач для директора
    
    Функции:
    - Распределение задач по всем доступным инструментам
    - Гибкая система подбора инструментов
    - Мониторинг выполнения по всем отделам
    - Балансировка нагрузки ресурсов
    - Координация межотдельных процессов
    """
    
    def __init__(self, config: Dict[str, Any], master_agent: "MasterAgent"):
        self.config = config
        self.master_agent = master_agent
        self.logger = logger
        
        # Конфигурация агентов
        self.services_config = config.get("services", {})
        
        # Состояние инструментов
        self.tool_statuses: Dict[str, ToolStatus] = {}
        self.tool_endpoints: Dict[str, str] = {}
        self.active_assignments: Dict[str, TaskAssignment] = {}
        
        # Очереди задач по типам инструментов
        self.task_queues: Dict[str, List[TaskAssignment]] = {
            tool_type.value: [] for tool_type in ToolType
        }
        
        # Метрики производительности по всем отделам
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Статистика директорского управления
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
        """Инициализация endpoints всех доступных инструментов"""
        # HR инструменты
        recruitment_runtime_config = self.services_config.get("recruitment_runtime", {})
        self.tool_endpoints["recruitment_runtime"] = (
            f"http://{recruitment_runtime_config.get('host', 'localhost')}:"
            f"{recruitment_runtime_config.get('port', 8010)}"
        )
        
        # Развиваемые инструменты (пока заглушки)
        self.tool_endpoints["active_recruiter"] = "http://localhost:8011"
        self.tool_endpoints["screener"] = "http://localhost:8012"
        self.tool_endpoints["onboarder"] = "http://localhost:8013"
        
        # Новые универсальные инструменты
        self.tool_endpoints["data_analyst"] = "http://localhost:8015"
        self.tool_endpoints["content_generator"] = "http://localhost:8016"
        self.tool_endpoints["code_reviewer"] = "http://localhost:8017"
        self.tool_endpoints["customer_support"] = "http://localhost:8018"
        self.tool_endpoints["finance_helper"] = "http://localhost:8019"
        self.tool_endpoints["generic_tool"] = "http://localhost:8021"
    
    async def initialize(self):
        """Инициализация Task Distributor"""
        try:
            # Проверка доступности инструментов
            await self.check_tool_availability()
            
            # Инициализация метрик
            await self._initialize_performance_metrics()
            
            self.logger.info("✅ Task Distributor инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Task Distributor: {e}")
            raise
    
    async def check_tool_availability(self) -> Dict[str, Dict[str, Any]]:
        """Проверка доступности всех инструментов"""
        availability = {}
        
        for tool_type, endpoint in self.tool_endpoints.items():
            try:
                # Проверка health endpoint
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
        """Универсальное делегирование задачи"""
        try:
            if assignment.assignment_type == "tool":
                return await self._delegate_to_tool(assignment)
            elif assignment.assignment_type == "human":
                return await self._delegate_to_human(assignment)
            else:
                return {
                    "success": False,
                    "error": f"Неизвестный тип назначения: {assignment.assignment_type}"
                }
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка делегирования задачи: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _delegate_to_tool(self, assignment: TaskAssignment) -> Dict[str, Any]:
        """Делегирование задачи ИИ-инструменту"""
        try:
            tool_type = assignment.tool_type.value
            
            # Проверка доступности инструмента
            availability = await self.check_tool_availability()
            if not availability.get(tool_type, {}).get("available", False):
                return {
                    "success": False,
                    "error": f"Инструмент {tool_type} недоступен",
                    "tool_type": tool_type
                }
            
            # Отправка задачи инструменту
            result = await self._send_task_to_tool(assignment)
            
            if result.get("success", False):
                # Сохранение назначения в активных
                self.active_assignments[assignment.task_id] = assignment
                self.task_queues[tool_type].append(assignment)
                self.stats["tasks_distributed"] += 1
                
                self.logger.info(f"✅ Задача {assignment.task_id} делегирована инструменту {tool_type}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка делегирования инструменту: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_type": tool_type
            }
    
    async def _delegate_to_human(self, assignment: TaskAssignment) -> Dict[str, Any]:
        """Делегирование задачи человеку"""
        try:
            # Пока заглушка - в реальной реализации здесь будет
            # отправка уведомлений через Teams/Telegram/Email
            self.logger.info(f"📝 Задача для {assignment.human_assignee} в отделе {assignment.department} создана")
            
            self.stats["tasks_distributed"] += 1
            
            return {
                "success": True,
                "assignment_type": "human",
                "assignee": assignment.human_assignee,
                "department": assignment.department,
                "message": f"Задача направлена {assignment.human_assignee}",
                "notification_sent": True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка делегирования человеку: {e}")
            return {
                "success": False,
                "error": str(e),
                "assignee": assignment.human_assignee or "неизвестен"
            }
    
    async def _send_task_to_tool(self, assignment: TaskAssignment) -> Dict[str, Any]:
        """Отправка задачи конкретному инструменту"""
        try:
            tool_type = assignment.tool_type.value
            endpoint = self.tool_endpoints.get(tool_type)
            
            if not endpoint:
                return {"success": False, "error": f"Endpoint для {tool_type} не найден"}
            
            # Подготовка данных для инструмента
            if tool_type == "recruitment_runtime":
                return await self._send_to_recruitment_runtime(assignment, endpoint)
            elif tool_type in ["active_recruiter", "screener", "onboarder"]:
                return await self._send_to_hr_tool(assignment, tool_type, endpoint)
            elif tool_type in ["data_analyst", "content_generator", "code_reviewer", "customer_support", "finance_helper"]:
                return await self._send_to_universal_tool(assignment, tool_type, endpoint)
            elif tool_type == "generic_tool":
                return await self._send_to_generic_tool(assignment, endpoint)
            else:
                return {"success": False, "error": f"Неизвестный тип инструмента: {tool_type}"}
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки задачи инструменту: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_to_recruitment_runtime(self, assignment: TaskAssignment, endpoint: str) -> Dict[str, Any]:
        """Отправка задачи существующему Recruitment Runtime"""
        try:
            # Формат запроса для существующего autorecruiter API
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
            
            # URL для создания задачи в autorecruiter
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
            self.logger.error(f"❌ Ошибка отправки в Recruitment Runtime: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_to_hr_tool(self, assignment: TaskAssignment, tool_type: str, endpoint: str) -> Dict[str, Any]:
        """Отправка задачи HR инструментам (заглушка)"""
        # Пока эти инструменты не реализованы
        self.logger.info(f"📝 Задача для HR инструмента {tool_type} добавлена в очередь")
        
        return {
            "success": True,
            "tool_type": tool_type,
            "tool_task_id": f"hr_mock_{uuid.uuid4().hex[:8]}",
            "estimated_duration": assignment.estimated_time,
            "message": f"Задача принята HR инструментом {tool_type} (в разработке)",
            "endpoint": endpoint,
            "mock": True
        }
    
    async def collect_results(self, master_task_id: str) -> List[Dict[str, Any]]:
        """Сбор результатов от всех агентов по задаче"""
        try:
            results = []
            
            # Поиск всех назначений задач
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
            self.logger.error(f"❌ Ошибка сбора результатов: {e}")
            return []
    
    async def _get_recruitment_runtime_result(self, assignment: TaskAssignment) -> Optional[Dict[str, Any]]:
        """Получение результата от Recruitment Runtime"""
        try:
            endpoint = self.agent_endpoints["recruitment_runtime"]
            
            # Предполагаем что у autorecruiter есть endpoint для получения результата
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
                        self.logger.warning(f"⚠️ Не удалось получить результат от Recruitment Runtime: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения результата от Recruitment Runtime: {e}")
            return None
    
    async def _get_tool_result(self, assignment: TaskAssignment, tool_type: str) -> Dict[str, Any]:
        """Получение результата от инструментов (заглушка)"""
        return {
            "tool_type": tool_type,
            "task_id": assignment.task_id,
            "success": True,
            "result_data": {"mock_result": f"Результат от {tool_type}"},
            "message": f"Задача выполнена инструментом {tool_type} (заглушка)",
            "execution_time": 60,
            "mock": True
        }
    
    async def monitor_task_progress(self, task_id: str) -> Dict[str, Any]:
        """Мониторинг прогресса выполнения задачи"""
        try:
            if task_id not in self.active_tasks:
                return {"error": "Задача не найдена"}
            
            task = self.active_tasks[task_id]
            agent_type = task.agent_type.value
            
            if agent_type == "recruitment_runtime":
                return await self._monitor_recruitment_runtime_progress(task)
            else:
                return await self._monitor_future_agent_progress(task, agent_type)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка мониторинга задачи: {e}")
            return {"error": str(e)}
    
    async def _monitor_recruitment_runtime_progress(self, assignment: TaskAssignment) -> Dict[str, Any]:
        """Мониторинг прогресса Recruitment Runtime"""
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
        """Мониторинг прогресса инструментов (заглушка)"""
        return {
            "task_id": assignment.task_id,
            "tool_type": tool_type,
            "status": "in_progress",
            "progress": 0.5,
            "current_action": f"Выполняется инструментом {tool_type}",
            "mock": True
        }
    
    def _get_agent_workload(self, agent_type: str) -> float:
        """Получение текущей загрузки агента"""
        if agent_type not in self.task_queues:
            return 0.0
        
        active_tasks = len([
            task for task in self.task_queues[agent_type]
            if task.status in ["pending", "in_progress"]
        ])
        
        # Предполагаем максимум 5 одновременных задач на агента
        max_concurrent_tasks = 5
        return min(active_tasks / max_concurrent_tasks, 1.0)
    
    async def _check_agent_availability(self):
        """Проверка доступности агентов при инициализации"""
        availability = await self.check_agent_availability()
        
        available_agents = [
            agent for agent, status in availability.items()
            if status.get("available", False)
        ]
        
        if not available_agents:
            self.logger.warning("⚠️ Ни один агент не доступен!")
        else:
            self.logger.info(f"✅ Доступные агенты: {', '.join(available_agents)}")
    
    async def _initialize_performance_metrics(self):
        """Инициализация метрик производительности"""
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
        """Получение статистики Task Distributor"""
        # Обновление статистики загрузки инструментов
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
        """Балансировка нагрузки между агентами"""
        try:
            # Анализ загрузки инструментов
            workloads = {}
            for tool_type in ToolType:
                workloads[tool_type.value] = self._get_tool_workload(tool_type.value)
            
            # Поиск перегруженных агентов
            overloaded_agents = [
                agent for agent, workload in workloads.items()
                if workload > 0.8
            ]
            
            # Поиск недогруженных агентов
            underloaded_agents = [
                agent for agent, workload in workloads.items()
                if workload < 0.5
            ]
            
            # Логика перераспределения задач (пока базовая)
            rebalanced_tasks = 0
            
            # В реальной реализации здесь была бы логика перемещения задач
            # между очередями агентов одного типа
            
            return {
                "rebalanced_tasks": rebalanced_tasks,
                "overloaded_agents": overloaded_agents,
                "underloaded_agents": underloaded_agents,
                "current_workloads": workloads
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка балансировки нагрузки: {e}")
            return {"error": str(e)}
