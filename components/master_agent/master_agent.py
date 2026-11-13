"""
Master Agent (РЕКС) - Главный координатор нейросотрудников

Автономный AI агент использующий GPT-5 для управления всеми нейросотрудниками
организации с AutoGPT логикой планирования и принятия решений.

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
    Главный координатор нейросотрудников (РЕКС)
    
    Ключевые возможности:
    - 🧠 GPT-5 для стратегического планирования
    - 💬 Естественное общение с людьми через Teams/Telegram
    - 🎯 Автономное распределение задач между агентами
    - 🏛️ Понимание контекста организации
    - ✅ Контроль качества и обучение
    - 📊 Мониторинг и аналитика
    - ⚙️ Управление рабочими процессами
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger
        
        # Уникальный ID агента
        self.agent_id = f"master_agent_{uuid.uuid4().hex[:8]}"
        
        # Настройка LLM
        self._setup_llm()
        
        # Инициализация компонентов
        self.messenger = MessengerInterface(config)
        self.task_distributor = TaskDistributor(config, self)
        self.org_context = OrganizationContextManager(config)
        self.memory_manager = MasterMemoryManager(config)
        self.quality_controller = QualityController(config, self)
        
        # Активные задачи и состояние
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.agent_statuses: Dict[str, Dict[str, Any]] = {}
        self.conversation_contexts: Dict[str, List[ConversationMessage]] = {}
        
        # Статистика
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "escalated_tasks": 0,
            "average_completion_time": 0.0,
            "user_satisfaction": 0.0,
            "uptime_start": datetime.now()
        }
        
        logger.info(f"💼 РЕКС - AI Директор инициализирован: {self.agent_id}")
    
    def _setup_llm(self):
        """Настройка LLM клиентов"""
        try:
            ai_config = self.config.get("master_agent", {})
            
            # Основной GPT-5 для стратегического планирования
            self.main_model = ai_config.get("main_model", "gpt-5-mini")
            self.fast_model = ai_config.get("fast_model", "gpt-5-mini")
            
            # Настройка прокси
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
            
            # OpenRouter или OpenAI клиент
            base_url = ai_config.get("base_url", "https://openrouter.ai/api/v1")
            api_key = ai_config.get("openrouter_api_key") or ai_config.get("openai_api_key")
            
            self.llm_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
            
            # Параметры GPT-5
            self.max_completion_tokens = ai_config.get("max_completion_tokens", 4000)
            self.temperature = ai_config.get("temperature", 0.2)
            
            # GPT-5 специфичные настройки
            gpt5_features = ai_config.get("gpt5_features", {})
            self.verbosity = gpt5_features.get("default_verbosity", "medium")
            self.reasoning_effort = gpt5_features.get("default_reasoning_effort", "medium")
            
            logger.info(f"✅ LLM настроен: {self.main_model}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки LLM: {e}")
            raise
    
    async def initialize(self):
        """Инициализация всех компонентов"""
        try:
            # Инициализация подсистем
            await self.messenger.initialize()
            await self.task_distributor.initialize()
            await self.org_context.initialize()
            await self.memory_manager.initialize()
            await self.quality_controller.initialize()
            
            # Восстановление состояния из памяти
            await self._restore_state()
            
            logger.info("🚀 Master Agent полностью инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Master Agent: {e}")
            raise
    
    async def process_task(self, request: MasterTaskRequest, progress_callback: Optional[Callable] = None) -> MasterTaskResponse:
        """
        Основной цикл обработки задачи (AutoGPT логика)
        
        Этапы:
        1. ANALYZE - Глубокий анализ задачи и контекста
        2. PLAN - Стратегическое планирование и выбор агентов  
        3. ACT - Делегирование задач и координация
        4. EVALUATE - Оценка результатов и качества
        5. DECIDE - Принятие решений о следующих шагах
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()
        
        try:
            # Создание задачи
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
            
            # Уведомление о принятии задачи
            response = MasterTaskResponse(
                task_id=task_id,
                status=MasterTaskStatus.ANALYZING,
                message=f"Задача принята к выполнению. Начинаю анализ цели: '{request.goal}'",
                estimated_duration="Анализирую...",
                assigned_agents=[]
            )
            
            if progress_callback:
                await progress_callback(task_id, "received", ["Задача получена", "Начинаю обработку"])
            
            # === 1. ANALYZE - Глубокий анализ ===
            analysis_result = await self._deep_analysis(task_data)
            task_data["analysis"] = analysis_result
            task_data["progress"] = 0.2
            
            if progress_callback:
                await progress_callback(task_id, "analyzing", [
                    "Анализ завершен",
                    f"Тип задачи: {analysis_result.get('task_type', 'general')}",
                    f"Сложность: {analysis_result.get('complexity', 'medium')}"
                ])
            
            # === 2. PLAN - Стратегическое планирование ===
            task_data["status"] = MasterTaskStatus.PLANNING
            planning_result = await self._strategic_planning(task_data)
            task_data["plan"] = planning_result
            task_data["progress"] = 0.4
            
            if progress_callback:
                await progress_callback(task_id, "planning", [
                    "План создан",
                    f"Агенты: {', '.join(planning_result.get('agents', []))}",
                    f"Этапы: {len(planning_result.get('steps', []))}"
                ])
            
            # === 3. ACT - Делегирование и координация ===
            task_data["status"] = MasterTaskStatus.DELEGATING
            execution_result = await self._coordinate_execution(task_data)
            task_data["execution"] = execution_result
            task_data["progress"] = 0.8
            
            if progress_callback:
                await progress_callback(task_id, "executing", [
                    "Задачи делегированы",
                    "Координирую выполнение",
                    f"Активных агентов: {len(execution_result.get('active_agents', []))}"
                ])
            
            # === 4. EVALUATE - Оценка результатов ===
            task_data["status"] = MasterTaskStatus.MONITORING
            evaluation_result = await self._evaluate_results(task_data)
            task_data["evaluation"] = evaluation_result
            task_data["progress"] = 0.95
            
            # === 5. DECIDE - Принятие решений ===
            decision_result = await self._make_final_decision(task_data)
            task_data["decision"] = decision_result
            task_data["progress"] = 1.0
            
            # Завершение
            if decision_result.get("success", False):
                task_data["status"] = MasterTaskStatus.COMPLETED
                self.stats["completed_tasks"] += 1
                
                completion_time = (datetime.now() - start_time).total_seconds()
                self._update_performance_metrics(completion_time, True)
                
                # Сохранение успешной стратегии
                await self._save_successful_strategy(task_data)
                
                response.status = MasterTaskStatus.COMPLETED
                response.message = decision_result.get("message", "Задача выполнена успешно")
                response.assigned_agents = planning_result.get("agents", [])
                
            else:
                task_data["status"] = MasterTaskStatus.FAILED
                self.stats["failed_tasks"] += 1
                
                response.status = MasterTaskStatus.FAILED
                response.message = decision_result.get("message", "Задача не выполнена")
            
            if progress_callback:
                await progress_callback(task_id, "completed", [
                    decision_result.get("message", "Задача завершена"),
                    f"Время выполнения: {(datetime.now() - start_time).total_seconds():.1f}с"
                ])
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки задачи {task_id}: {e}")
            self.stats["failed_tasks"] += 1
            
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = MasterTaskStatus.FAILED
                self.active_tasks[task_id]["error"] = str(e)
            
            return MasterTaskResponse(
                task_id=task_id,
                status=MasterTaskStatus.FAILED,
                message=f"Ошибка выполнения: {str(e)}",
                estimated_duration="N/A",
                assigned_agents=[]
            )
    
    async def _deep_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Глубокий анализ задачи с использованием GPT-5"""
        try:
            request = task_data["request"]
            
            # Получение контекста организации
            org_context = await self.org_context.get_context()
            
            # Анализ истории похожих задач
            similar_tasks = await self.memory_manager.find_similar_tasks(request.goal)
            
            # Промпт для директорского анализа
            analysis_prompt = f"""
Ты - РЕКС, AI директор компании "{org_context.company_name}".
Ты управляешь ВСЕМИ отделами и принимаешь стратегические решения.

ЗАДАЧА ДЛЯ АНАЛИЗА:
Цель: {request.goal}
Контекст: {json.dumps(request.context, ensure_ascii=False, indent=2)}
Приоритет: {request.priority}
Отделы: {request.departments or 'не указаны'}
Ограничения: {request.constraints}

КОНТЕКСТ ОРГАНИЗАЦИИ:
- Отрасль: {org_context.industry}
- Размер: {org_context.company_size}
- Отделы под управлением: {[dept.get('name', '') for dept in org_context.departments]}
- Стиль управления: {org_context.communication_style}

ДОСТУПНЫЕ РЕСУРСЫ:
ЛЮДИ ПО ОТДЕЛАМ:
{self._format_human_resources(org_context)}

ИИ-ИНСТРУМЕНТЫ:
1. Recruitment Runtime - HR: создание вакансий, анализ откликов
2. Active Recruiter - HR: активный поиск, headhunting
3. Data Analyst - Аналитика: бизнес-метрики, отчеты
4. Content Generator - Маркетинг: контент, соцсети
5. Code Reviewer - Разработка: анализ кода, ревью
6. Customer Support - Сервис: поддержка клиентов
7. Finance Helper - Финансы: анализ бюджета, отчеты
8. Generic Tool - Универсальный настраиваемый инструмент

ПОХОЖИЕ РЕШЕНИЯ ИЗ ОПЫТА:
{json.dumps(similar_tasks, ensure_ascii=False, indent=2)}

ПРОАНАЛИЗИРУЙ КАК ДИРЕКТОР:
1. Природа и масштаб задачи (какие отделы затронуты)
2. Стратегическая важность для компании
3. Требуется ли информация от людей
4. Какие инструменты могут помочь
5. Кого из людей привлечь и почему
6. Последовательность действий и координация
7. Риски и возможности для бизнеса
8. Влияние на общие цели компании

Ответь в формате JSON:
{{
    "task_nature": "описание природы задачи",
    "domain": "основная область (hr/tech/marketing/finance/management/universal)",
    "scope": "масштаб (departmental/cross_departmental/company_wide)",
    "complexity": "сложность (low/medium/high/strategic)",
    "affected_departments": ["список затронутых отделов"],
    "required_human_input": ["что нужно узнать у людей"],
    "recommended_tools": ["список рекомендуемых инструментов"],
    "human_assignments": ["кого из людей привлечь"],
    "strategic_importance": "low/medium/high/critical",
    "business_impact": "описание влияния на бизнес",
    "key_stages": ["этап 1", "этап 2", ...],
    "risks": ["риск 1", "риск 2", ...],
    "estimated_hours": число,
    "confidence": 0.95,
    "director_insights": ["ключевые инсайты директора"]
}}
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.main_model,
                messages=[
                    {"role": "system", "content": "Ты директор компании с полными полномочиями управления всеми отделами."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,
                verbosity=self.verbosity,
                reasoning_effort=self.reasoning_effort,
                response_format={"type": "json_object"}
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            
            logger.info(f"✅ Анализ завершен: {analysis_result.get('domain')} ({analysis_result.get('complexity')})")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
            return {
                "task_nature": "standard",
                "domain": "universal",
                "complexity": "medium",
                "scope": "departmental",
                "affected_departments": ["management"],
                "recommended_tools": ["generic_tool"],
                "strategic_importance": "medium",
                "business_impact": "Требует внимания",
                "estimated_hours": 2,
                "confidence": 0.5,
                "director_insights": ["Необходим дополнительный анализ"],
                "error": str(e)
            }
    
    def _format_human_resources(self, org_context: OrganizationContext) -> str:
        """Форматирование информации о человеческих ресурсах"""
        resources = []
        for dept in org_context.departments:
            dept_name = dept.get('name', 'Неизвестный отдел')
            dept_head = dept.get('head', 'Не назначен')
            dept_size = dept.get('size', 0)
            
            resources.append(f"- {dept_name}: {dept_head} (команда {dept_size} чел.)")
        
        return "\n".join(resources)
    
    async def _strategic_planning(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Стратегическое планирование выполнения"""
        try:
            analysis = task_data["analysis"]
            request = task_data["request"]
            
            # Проверка доступности агентов
            agent_availability = await self.task_distributor.check_agent_availability()
            
            planning_prompt = f"""
На основе анализа задачи создай детальный план выполнения.

АНАЛИЗ ЗАДАЧИ:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

ДОСТУПНОСТЬ АГЕНТОВ:
{json.dumps(agent_availability, ensure_ascii=False, indent=2)}

СОЗДАЙ ПЛАН:
1. Последовательность шагов
2. Распределение по агентам  
3. Зависимости между задачами
4. Временные рамки
5. Точки контроля и синхронизации
6. Plan B при сбоях

Формат ответа JSON:
{{
    "agents": ["список выбранных агентов"],
    "steps": [
        {{
            "step": 1,
            "description": "описание",
            "agent": "тип агента",
            "estimated_time": "время",
            "dependencies": ["зависимости"],
            "deliverables": ["результаты"]
        }}
    ],
    "coordination_points": ["точки синхронизации"],
    "quality_checks": ["проверки качества"], 
    "contingency_plans": ["планы на случай сбоев"],
    "total_estimated_time": "общее время"
}}
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.main_model,
                messages=[
                    {"role": "system", "content": "Ты стратегический планировщик задач для команды ИИ-агентов."},
                    {"role": "user", "content": planning_prompt}
                ],
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,
                verbosity=self.verbosity,
                reasoning_effort=self.reasoning_effort,
                response_format={"type": "json_object"}
            )
            
            plan = json.loads(response.choices[0].message.content)
            
            # Валидация плана
            if not plan.get("agents") or not plan.get("steps"):
                raise ValueError("План должен содержать агентов и шаги")
            
            logger.info(f"✅ План создан: {len(plan.get('steps', []))} шагов, {len(plan.get('agents', []))} агентов")
            return plan
            
        except Exception as e:
            logger.error(f"❌ Ошибка планирования: {e}")
            # Базовый план
            return {
                "approach": "standard",
                "strategy_type": "delegation", 
                "execution_sequence": ["Анализ", "Планирование", "Выполнение"],
                "human_assignments": [],
                "tool_assignments": [{"tool_type": "generic_tool", "task": "Выполнить задачу", "priority": "medium"}],
                "estimated_timeline": "2-4 часа",
                "error": str(e)
            }
    
    async def _coordinate_execution(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Координация выполнения через Task Distributor"""
        try:
            plan = task_data["plan"]
            request = task_data["request"]
            
            # Делегирование задач агентам
            execution_results = []
            active_agents = []
            
            for step in plan.get("steps", []):
                agent_type = step.get("agent")
                if agent_type:
                    # Создание назначения инструменту
                    subtask = TaskAssignment(
                        task_id=task_data["id"],
                        assignment_type="tool",
                        tool_type=ToolType(agent_type),
                        goal=step.get("description", request.goal),
                        context=request.context,
                        priority=request.priority,
                        estimated_time=step.get("estimated_time", "1 час")
                    )
                    
                    # Отправка задачи агенту
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
            logger.error(f"❌ Ошибка координации: {e}")
            return {"error": str(e), "active_agents": []}
    
    async def _evaluate_results(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Оценка результатов выполнения"""
        try:
            # Сбор результатов от всех агентов
            task_id = task_data["id"]
            agent_results = await self.task_distributor.collect_results(task_id)
            
            # Анализ качества
            quality_metrics = await self.quality_controller.evaluate_task_quality(task_data, agent_results)
            
            return {
                "agent_results": agent_results,
                "quality_metrics": quality_metrics,
                "overall_success": quality_metrics.success_rate > 0.7
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка оценки: {e}")
            return {"error": str(e), "overall_success": False}
    
    async def _make_final_decision(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Принятие финального решения"""
        try:
            evaluation = task_data.get("evaluation", {})
            
            if evaluation.get("overall_success", False):
                return {
                    "success": True,
                    "message": "Задача выполнена успешно",
                    "next_actions": ["Уведомить заказчика", "Сохранить результаты"]
                }
            else:
                return {
                    "success": False,
                    "message": "Задача выполнена с ошибками",
                    "next_actions": ["Эскалация", "Повторная попытка"]
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка принятия решения: {e}")
            return {"success": False, "message": f"Ошибка: {e}"}
    
    async def _restore_state(self):
        """Восстановление состояния из памяти"""
        try:
            saved_state = await self.memory_manager.get_master_memory()
            if saved_state:
                self.active_tasks = saved_state.active_tasks
                self.agent_statuses = saved_state.agent_statuses
                logger.info("✅ Состояние восстановлено из памяти")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось восстановить состояние: {e}")
    
    async def _save_successful_strategy(self, task_data: Dict[str, Any]):
        """Сохранение успешной стратегии в память"""
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
            logger.error(f"❌ Ошибка сохранения стратегии: {e}")
    
    def _update_performance_metrics(self, completion_time: float, success: bool):
        """Обновление метрик производительности"""
        # Обновление среднего времени выполнения
        total_completed = self.stats["completed_tasks"]
        if total_completed > 0:
            current_avg = self.stats["average_completion_time"]
            self.stats["average_completion_time"] = (
                (current_avg * (total_completed - 1) + completion_time) / total_completed
            )
        else:
            self.stats["average_completion_time"] = completion_time
    
    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса Master Agent"""
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
        """Обработка сообщения в диалоге"""
        try:
            # Обновление контекста диалога
            conversation_id = message.conversation_id
            if conversation_id not in self.conversation_contexts:
                self.conversation_contexts[conversation_id] = []
            
            self.conversation_contexts[conversation_id].append(message)
            
            # Генерация ответа
            response_content = await self._generate_conversation_response(message)
            
            # Создание ответного сообщения
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
            logger.error(f"❌ Ошибка обработки диалога: {e}")
            return ConversationMessage(
                message_id=f"msg_error_{uuid.uuid4().hex[:8]}",
                sender="master_agent",
                recipient=message.sender,
                content=f"Извините, произошла ошибка: {e}",
                channel=message.channel,
                conversation_id=message.conversation_id
            )
    
    async def _generate_conversation_response(self, message: ConversationMessage) -> str:
        """Генерация ответа в диалоге"""
        try:
            # Контекст диалога
            conversation_history = self.conversation_contexts.get(message.conversation_id, [])
            history_text = "\n".join([
                f"{msg.sender}: {msg.content}" 
                for msg in conversation_history[-10:]  # Последние 10 сообщений
            ])
            
            # Контекст организации
            org_context = await self.org_context.get_context()
            
            conversation_prompt = f"""
Ты - РЕКС, AI директор компании "{org_context.company_name}".
Ты управляешь всеми отделами и принимаешь стратегические решения.

КОНТЕКСТ ОРГАНИЗАЦИИ:
- Отрасль: {org_context.industry}
- Размер: {org_context.company_size}
- Стиль управления: {org_context.communication_style}
- Отделы под управлением: {', '.join([dept.get('name', '') for dept in org_context.departments])}

ИСТОРИЯ ДИАЛОГА:
{history_text}

НОВОЕ СООБЩЕНИЕ ОТ {message.sender}:
{message.content}

Ответь как опытный директор:
1. Авторитетно, но дружелюбно
2. Предложи конкретные решения и действия
3. Задействуй нужные отделы если требуется
4. Поставь задачи людям или инструментам если нужно
5. Запроси дополнительную информацию если неясно

Ответ должен быть как от руководителя с полными полномочиями.
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.fast_model,
                messages=[
                    {"role": "system", "content": "Ты директор компании с полными полномочиями управления всеми отделами."},
                    {"role": "user", "content": conversation_prompt}
                ],
                temperature=0.7,
                max_completion_tokens=500,
                verbosity="low",
                reasoning_effort="low"
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа: {e}")
            return f"Понял ваш запрос. Сейчас разберусь и отвечу. Возможны технические сложности: {e}"
