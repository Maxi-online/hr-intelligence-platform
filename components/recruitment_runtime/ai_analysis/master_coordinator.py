"""
Candidate Analysis - Master Coordinator for Multi-Agent System

Мастер-координатор мульти-агентной системы анализа кандидатов.

Этот модуль представляет собой "мозг" всей системы AI анализа, который:
- Управляет оркестрацией 6 специализированных агентов
- Агрегирует результаты всех агентов в единое заключение
- Генерирует профессиональные рекомендации в стиле топ-менеджера
- Обеспечивает истинно параллельную обработку через AsyncOpenAI

Core Functionality:
- Agent Orchestration: координация работы всех специализированных агентов
- Results Aggregation: объединение отчётов агентов в единую картину
- Master Analysis: финальный анализ через GPT-5-nano
- Professional Recommendations: бизнес-заключения для HR отделов

Architecture:
    MasterCoordinator
    ├── Agent Selection (by position type)
    ├── Parallel Agent Execution (true async)
    ├── Results Aggregation & Scoring
    ├── Master GPT Analysis 
    └── Professional Recommendation Generation

Key Features:
- AsyncOpenAI для параллельных вызовов мастер-анализа
- Настраиваемые наборы агентов под тип позиции
- Интеллектуальное агрегирование оценок
- Профессиональные рекомендации (РЕКОМЕНДУЮ/НЕ РЕКОМЕНДУЮ/УСЛОВНО)
- Детальная диагностика ошибок и performance metrics

Performance:
- Время мастер-анализа: ~3-5 секунд на кандидата
- Поддержка батчевой параллельной обработки
- Экспоненциальные повторы при ошибках OpenAI
- Graceful degradation при недоступности агентов

Master Report Structure:
- overall_score: Итоговая оценка (0-100)
- recommendation: РЕКОМЕНДУЮ/НЕ РЕКОМЕНДУЮ/УСЛОВНО РЕКОМЕНДУЮ
- master_assessment: Развёрнутое профессиональное заключение
- individual_scores: Детальные оценки по каждому критерию
- strengths/weaknesses: Сильные и слабые стороны кандидата

Author: Candidate Analysis Team
Version: 3.0.0 (AsyncOpenAI + True Parallelism)
Last Updated: 2025-01-04
"""

import time
import statistics
import asyncio
import json
import random
from typing import Dict, Any, List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем AsyncOpenAI для GPT анализа
try:
    import openai
    from openai import AsyncOpenAI
    import httpx
    import backoff
except ImportError:
    openai = None
    httpx = None
    backoff = None

from shared.models import (
    MultiAgentAnalysisRequest, MultiAgentAnalysisResponse, 
    MasterCoordinatorReport, AgentReport, AgentStatus
)
from shared.utils import setup_logging

# ПРОСТОЙ ИМПОРТ АГЕНТОВ БЕЗ ОТНОСИТЕЛЬНЫХ ПУТЕЙ
import sys
import os

# В Docker контейнере все файлы находятся в /app
# Добавляем ai_analysis в PYTHONPATH если нужно
if '/app/ai_analysis' not in sys.path:
    sys.path.insert(0, '/app/ai_analysis')
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

# Простой импорт без относительных путей
from agents import RequirementsAgent, ResumeAnalysisAgent, ExperienceAgent
from agents import FormattingAgent, AnomalyDetectionAgent
from agents import TechnicalSkillsAgent, SkillLevelAgent

logger = setup_logging("master-coordinator")

class MasterCoordinator:
    """Мастер-координатор мульти-агентной системы"""
    
    def __init__(self):
        self.logger = logger
        
        # ЗАГРУЖАЕМ КОНФИГУРАЦИЮ ЧЕРЕЗ load_config()
        from shared.utils import load_config
        self.config = load_config()
        
        # ИСПРАВЛЕНИЕ: Загружаем отдельную конфигурацию мастер-координатора
        self._load_coordinator_config()
        self.ai_config = self.config.get("ai_analysis", {})
        
        # ИСПОЛЬЗУЕМ PROMPT MANAGER ВМЕСТО САМОДЕЛЬНОЙ ЗАГРУЗКИ
        from prompt_manager import get_prompt_manager
        self.prompt_manager = get_prompt_manager()
        
        # НАСТРАИВАЕМ OPENAI КЛИЕНТ С ПРОКСИ (как в BaseAgent)
        self._setup_openai_with_proxy()
        
        # Инициализируем всех доступных агентов
        self.agents = {
            "requirements": RequirementsAgent(),
            "resume_analysis": ResumeAnalysisAgent(), 
            "technical_skills": TechnicalSkillsAgent(),
            "skill_level": SkillLevelAgent(),
            "experience": ExperienceAgent(),
            "formatting": FormattingAgent(),
            "anomaly_detection": AnomalyDetectionAgent()
        }
        
        # Конфигурация агентов для разных типов позиций
        self.position_agent_config = {
            "technical": ["requirements", "technical_skills", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"],
            "management": ["requirements", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"],
            "sales": ["requirements", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"],
            "general": ["requirements", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"]
        }
    
    async def analyze_candidate(self, request: MultiAgentAnalysisRequest) -> MultiAgentAnalysisResponse:
        """Главная функция анализа кандидата через всех агентов"""
        start_time = time.time()
        
        try:
            # 1. Определяем активных агентов
            active_agents = self._get_active_agents(request.position_type, request.active_agents)
            self.logger.info(f"Активируем агентов для анализа кандидата {request.candidate_id}: {active_agents}")
            
            # 2. Запускаем анализ всех активных агентов ПАРАЛЛЕЛЬНО
            agent_reports = await self._run_agents_analysis(
                active_agents, request.candidate_data, request.position_requirements, 
                {"search_query": request.search_query, "search_filters": request.search_filters}
            )
            
            # 3. Генерируем итоговый отчет мастера
            self.logger.info(f"🔥 ОТЛАДКА: Переходим к генерации отчета мастера, получено {len(agent_reports)} отчетов агентов")
            master_report = await self._generate_master_report(agent_reports, request)
            self.logger.info(f"🔥 ОТЛАДКА: Отчет мастера сгенерирован успешно")
            
            # 4. Формируем финальный ответ
            total_processing_time = time.time() - start_time
            
            return MultiAgentAnalysisResponse(
                candidate_id=request.candidate_id,
                master_report=master_report,
                agent_reports=agent_reports,
                active_agents=active_agents,
                total_processing_time=total_processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка в мастер-координаторе для кандидата {request.candidate_id}: {e}")
            raise e
    
    def _get_active_agents(self, position_type: str, requested_agents: Optional[List[str]]) -> List[str]:
        """Определяет список активных агентов"""
        if requested_agents:
            # Используем явно указанных агентов
            return [agent for agent in requested_agents if agent in self.agents]
        
        # Автоматическое определение по типу позиции
        return self.position_agent_config.get(position_type, self.position_agent_config["general"])
    
    async def _run_agents_analysis(self, active_agents: List[str], candidate_data: Dict[str, Any], 
                                 position_requirements: Dict[str, Any], additional_context: Dict[str, Any]) -> List[AgentReport]:
        """Запускает анализ всех активных агентов ПАРАЛЛЕЛЬНО"""
        
        # Создаем задачи для всех агентов
        tasks = []
        for agent_name in active_agents:
            agent = self.agents[agent_name]
            task = self._run_single_agent(agent_name, agent, candidate_data, position_requirements, additional_context)
            tasks.append(task)
        
        self.logger.info(f"🚀 Запускаем {len(tasks)} агентов ПАРАЛЛЕЛЬНО")
        
        # Выполняем все задачи параллельно
        agent_reports = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты и ошибки
        processed_reports = []
        for i, result in enumerate(agent_reports):
            agent_name = active_agents[i]
            
            if isinstance(result, Exception):
                self.logger.error(f"❌ Ошибка в агенте {agent_name}: {result}")
                # Создаем отчет об ошибке
                error_report = AgentReport(
                    agent_name=agent_name,
                    score=0.0,
                    status=AgentStatus.ERROR,
                    summary=f"Ошибка выполнения агента {agent_name}",
                    details=[f"Техническая ошибка: {str(result)}"],
                    red_flags=["Агент не смог выполнить анализ"],
                    positive_points=[],
                    recommendations=["Требуется ручная проверка"],
                    processing_time=0.0
                )
                processed_reports.append(error_report)
            else:
                processed_reports.append(result)
                self.logger.info(f"✅ Агент {agent_name} завершил анализ с оценкой {result.score:.1f}%")
        
        self.logger.info(f"🏁 Все {len(processed_reports)} агентов завершили работу")
        return processed_reports
    
    async def _run_single_agent(self, agent_name: str, agent, candidate_data: Dict[str, Any], 
                              position_requirements: Dict[str, Any], additional_context: Dict[str, Any]) -> AgentReport:
        """Запускает одного агента с обработкой ошибок"""
        try:
            self.logger.info(f"⚡ Запускаем агента: {agent_name}")
            report = await agent.analyze(candidate_data, position_requirements, additional_context)
            return report
        except Exception as e:
            self.logger.error(f"💥 Критическая ошибка в агенте {agent_name}: {e}")
            raise e
    
    async def _generate_master_report(self, agent_reports: List[AgentReport], 
                               request: MultiAgentAnalysisRequest) -> MasterCoordinatorReport:
        """Генерирует итоговый отчет мастер-координатора"""
        start_time = time.time()
        
        # 1. Вычисляем среднее арифметическое оценок
        valid_scores = [report.score for report in agent_reports if report.status != AgentStatus.ERROR]
        overall_score = statistics.mean(valid_scores) if valid_scores else 0.0
        
        # 2. Собираем индивидуальные оценки
        individual_scores = {report.agent_name: report.score for report in agent_reports}
        
        # 3. Анализируем статусы агентов
        agents_with_warnings = [r.agent_name for r in agent_reports if r.status == AgentStatus.WARNING]
        agents_with_failures = [r.agent_name for r in agent_reports if r.status == AgentStatus.FAIL]
        
        # 4. Подсчитываем красные флаги и плюсы
        total_red_flags = sum(len(report.red_flags) for report in agent_reports)
        total_positive_points = sum(len(report.positive_points) for report in agent_reports)
        
        # 5. Генерируем текстовую оценку мастера
        self.logger.info(f"🤖 МАСТЕР-КООРДИНАТОР: Начинаем генерацию анализа для кандидата")
        master_assessment = await self._generate_master_assessment(
            agent_reports, overall_score, total_red_flags, total_positive_points, 
            agents_with_warnings, agents_with_failures, request
        )
        self.logger.info(f"🤖 МАСТЕР-КООРДИНАТОР: Анализ сгенерирован, длина: {len(master_assessment)} символов")
        
        # 6. Определяем финальную рекомендацию
        recommendation = self._get_final_recommendation(overall_score, total_red_flags, len(agents_with_failures))
        
        processing_time = time.time() - start_time
        
        return MasterCoordinatorReport(
            overall_score=round(overall_score, 1),
            individual_scores=individual_scores,
            master_assessment=master_assessment,
            recommendation=recommendation,
            total_red_flags=total_red_flags,
            total_positive_points=total_positive_points,
            agents_with_warnings=agents_with_warnings,
            agents_with_failures=agents_with_failures,
            processing_time=processing_time
        )
    
    async def _generate_master_assessment(self, agent_reports: List[AgentReport], overall_score: float,
                                   total_red_flags: int, total_positive_points: int,
                                   agents_with_warnings: List[str], agents_with_failures: List[str],
                                   request: MultiAgentAnalysisRequest) -> str:
        """Генерирует качественную текстовую оценку мастера через GPT"""
        self.logger.info(f"🔥 ОТЛАДКА _generate_master_assessment: Начинаем генерацию, OpenAI клиент: {self.openai_client is not None}")
        
        # Собираем все данные от агентов для анализа мастера
        agent_data = []
        for report in agent_reports:
            agent_info = {
                "name": report.agent_name,
                "score": report.score,
                "status": report.status.value,
                "summary": report.summary,
                "details": report.details,
                "red_flags": report.red_flags,
                "positive_points": report.positive_points,
                "recommendations": report.recommendations
            }
            agent_data.append(agent_info)
        
        # Генерируем качественный анализ через AsyncOpenAI
        return await self._call_gpt_for_master_analysis(
            agent_data, overall_score, request.candidate_data, 
            request.position_requirements, request.search_query
        )
    

    
    def _load_coordinator_config(self):
        """Загружает конфигурацию мастер-координатора из agent_configs.yaml"""
        try:
            import yaml
            # Пробуем несколько вариантов путей
            possible_paths = [
                "ai_analysis/agent_configs.yaml",  # Локально
                "/app/ai_analysis/agent_configs.yaml"  # Docker
            ]
            
            for config_path in possible_paths:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        full_config = yaml.safe_load(f)
                        self.coordinator_config = full_config.get('master_coordinator', {})
                        self.logger.info(f"✅ Конфигурация мастер-координатора загружена из {config_path}")
                        return
            
            self.logger.warning(f"⚠️ Файл agent_configs.yaml не найден для мастер-координатора")
            self.coordinator_config = {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки конфигурации мастер-координатора: {e}")
            self.coordinator_config = {}
    
    def _setup_openai_with_proxy(self):
        """Настраивает OpenAI клиент с прокси (копия логики из BaseAgent)"""
        try:
            # Получаем API ключ
            api_key = self.ai_config.get("openai_api_key")
            if not api_key:
                self.logger.warning(f"⚠️ OPENAI_API_KEY не установлен для мастер-координатора")
            
            # Настройка HTTP прокси из конфигурации
            proxy_config = self.ai_config.get("proxy", {})
            proxy_enabled = proxy_config.get("enabled", False)
            
            if proxy_enabled and httpx:
                # Получаем настройки прокси из конфигурации или переменных окружения
                proxy_host = proxy_config.get("host", "")
                proxy_port = proxy_config.get("port", "")
                proxy_username = proxy_config.get("username", "")
                proxy_password = proxy_config.get("password", "")
                proxy_protocol = proxy_config.get("protocol", "http")
                
                if proxy_host and proxy_port:
                    # Формируем URL прокси
                    if proxy_username and proxy_password:
                        proxy_url = f"{proxy_protocol}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                    else:
                        proxy_url = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
                    
                    # Создаем httpx клиент с прокси для AsyncOpenAI
                    http_client = httpx.AsyncClient(
                        proxy=proxy_url,
                        timeout=httpx.Timeout(60.0)
                    )
                    
                    self.logger.info(f"🌐 OpenAI клиент с прокси инициализирован для мастер-координатора: {proxy_host}:{proxy_port}")
                else:
                    # Если настройки прокси неполные, используем обычный клиент
                    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                    self.logger.warning(f"⚠️ Прокси включен для мастер-координатора, но настройки неполные. Используется прямое соединение.")
            else:
                # Обычный httpx клиент без прокси для AsyncOpenAI
                if httpx:
                    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                    self.logger.info(f"🔗 OpenAI клиент без прокси инициализирован для мастер-координатора")
                else:
                    http_client = None
                    self.logger.warning(f"⚠️ httpx недоступен для мастер-координатора")
            
            # Инициализация OpenRouter клиента
            if openai:
                base_url = self.ai_config.get("base_url", "https://openrouter.ai/api/v1")
                
                if "openrouter.ai" in base_url:
                    # OpenRouter режим
                    openrouter_key = self.ai_config.get("openrouter_api_key")
                    if not openrouter_key:
                        raise ValueError("Для OpenRouter требуется openrouter_api_key в конфигурации")
                    
                    # Создаем клиент без прокси для OpenRouter
                    self.openai_client = AsyncOpenAI(
                        api_key=openrouter_key,
                        base_url=base_url
                    )
                    self.logger.info(f"🔄 OpenRouter AsyncOpenAI клиент для мастер-координатора: {base_url}")
                    
                    # Настройки для OpenRouter
                    self.site_url = self.ai_config.get("site_url", "")
                    self.site_name = self.ai_config.get("site_name", "CandidateRanking")
                else:
                    # Старый OpenAI режим
                    if http_client:
                        self.openai_client = AsyncOpenAI(
                            api_key=api_key,
                            http_client=http_client,
                            base_url=base_url if base_url != "https://openrouter.ai/api/v1" else None
                        )
                    else:
                        self.openai_client = AsyncOpenAI(
                            api_key=api_key,
                            base_url=base_url if base_url != "https://openrouter.ai/api/v1" else None
                        )
                    self.site_url = ""
                    self.site_name = ""
                
                # Параметры модели из конфигурации
                self.model = self.ai_config.get("model", "gpt-5-mini")
                self.max_completion_tokens = self.ai_config.get("max_completion_tokens", 5000)  # GPT-5 параметр для координатора
                
                # GPT-5 параметры для координатора
                coordinator_config = self.config.get("ai_analysis", {}).get("multi_agent", {}).get("master_coordinator", {})
                self.verbosity = coordinator_config.get("verbosity", "high")
                self.reasoning_effort = coordinator_config.get("reasoning_effort", "medium")
                self.temperature = self.ai_config.get("temperature", 0.0)
                
                self.logger.info(f"✅ AsyncOpenAI клиент мастер-координатора настроен (модель: {self.model})")
            else:
                self.openai_client = None
                self.logger.warning(f"⚠️ AsyncOpenAI недоступен для мастер-координатора")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка настройки AsyncOpenAI клиента для мастер-координатора: {e}")
            self.openai_client = None
    
    async def _call_gpt_for_master_analysis(self, agent_data: List[Dict], overall_score: float, 
                                     candidate_data: Dict, position_requirements: Dict, search_query: str) -> str:
        """Вызывает GPT для качественного анализа всех данных мастер-координатором"""
        
        self.logger.info(f"🤖 МАСТЕР-КООРДИНАТОР: Вызов GPT анализа начинается")
        self.logger.info(f"🤖 МАСТЕР-КООРДИНАТОР: OpenAI клиент доступен: {self.openai_client is not None}")
        
        if not self.openai_client:
            # Fallback: если OpenAI недоступен, генерируем простой текст
            self.logger.warning(f"⚠️ МАСТЕР-КООРДИНАТОР: OpenAI недоступен, используем fallback")
            return self._generate_fallback_assessment(agent_data, overall_score, search_query)
        
        try:
            # Проверяем тип candidate_data и обрабатываем правильно
            if isinstance(candidate_data, list):
                # Если это список, берем первый элемент
                candidate_dict = candidate_data[0] if candidate_data else {}
                self.logger.warning(f"🤖 МАСТЕР-КООРДИНАТОР: candidate_data является списком, используем первый элемент")
            elif isinstance(candidate_data, dict):
                candidate_dict = candidate_data
            else:
                self.logger.error(f"🤖 МАСТЕР-КООРДИНАТОР: Неожиданный тип candidate_data: {type(candidate_data)}")
                candidate_dict = {}
            
            # Подготавливаем данные для GPT
            candidate_summary = {
                "name": candidate_dict.get("name", "Не указано"),
                "title": candidate_dict.get("title", "Не указано"),
                "experience_months": candidate_dict.get("experience", {}).get("total_months", 0) if isinstance(candidate_dict.get("experience"), dict) else 0,
                "area": candidate_dict.get("area", {}).get("name", "Не указано") if isinstance(candidate_dict.get("area"), dict) else "Не указано",
                "salary": candidate_dict.get("salary", {}),
                "skills": candidate_dict.get("skills", []),
                "education": candidate_dict.get("education", []),
                "about": candidate_dict.get("about", "")
            }
            
            # Получаем промпты из PromptManager
            self.logger.info(f"🤖 МАСТЕР-КООРДИНАТОР: Загружаем промпты из PromptManager")
            system_prompt = self.prompt_manager.get_prompt("master_coordinator", "system_prompt")
            analysis_prompt = self.prompt_manager.get_prompt("master_coordinator", "analysis_prompt")
            
            self.logger.info(f"🤖 МАСТЕР-КООРДИНАТОР: system_prompt найден: {system_prompt is not None}")
            self.logger.info(f"🤖 МАСТЕР-КООРДИНАТОР: analysis_prompt найден: {analysis_prompt is not None}")
            
            if not system_prompt or not analysis_prompt:
                self.logger.warning("⚠️ МАСТЕР-КООРДИНАТОР: Промпты не найдены, используем fallback")
                return self._generate_fallback_assessment(agent_data, overall_score, search_query)
            
            # Форматируем analysis_prompt с данными
            formatted_analysis_prompt = analysis_prompt.format(
                candidate_summary=json.dumps(candidate_summary, ensure_ascii=False, indent=2),
                search_query=search_query,
                position_requirements=json.dumps(position_requirements, ensure_ascii=False, indent=2),
                agent_data=json.dumps(agent_data, ensure_ascii=False, indent=2),
                overall_score=overall_score
            )
            
            # Подготавливаем параметры для OpenRouter
            extra_headers = {}
            if hasattr(self, 'site_url') and self.site_url:
                extra_headers["HTTP-Referer"] = self.site_url
            if hasattr(self, 'site_name') and self.site_name:
                extra_headers["X-Title"] = self.site_name

            # ИСТИННАЯ АСИНХРОННОСТЬ с поддержкой OpenRouter и GPT-5
            gpt5_params = {}
            if hasattr(self, 'verbosity') and hasattr(self, 'reasoning_effort'):
                gpt5_params.update({
                    "verbosity": self.verbosity,
                    "reasoning_effort": self.reasoning_effort
                })
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_analysis_prompt}
                ],
                max_completion_tokens=self.max_completion_tokens,  # GPT-5 параметр
                temperature=self.temperature,
                extra_headers=extra_headers if extra_headers else {},
                # GPT-5 параметры передаются напрямую
                verbosity=gpt5_params.get("verbosity", "high") if gpt5_params else "high",
                reasoning_effort=gpt5_params.get("reasoning_effort", "medium") if gpt5_params else "medium"
            )
            
            gpt_analysis = response.choices[0].message.content.strip()
            self.logger.info("✅ GPT мастер-анализ успешно сгенерирован")
            return gpt_analysis
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка GPT анализа мастера: {e}")
            return self._generate_fallback_assessment(agent_data, overall_score, search_query)
    
    def _generate_fallback_assessment(self, agent_data: List[Dict], overall_score: float, search_query: str) -> str:
        """Генерирует упрощенный анализ когда GPT недоступен"""
        
        high_scores = [agent for agent in agent_data if agent["score"] >= 70]
        low_scores = [agent for agent in agent_data if agent["score"] < 50]
        
        assessment = f"**Автоматический анализ кандидата** (GPT недоступен)\n\n"
        assessment += f"Общая оценка: {overall_score:.1f}%\n\n"
        
        if overall_score >= 70:
            assessment += f"Кандидат демонстрирует хорошее соответствие позиции '{search_query}'. "
        elif overall_score >= 50:
            assessment += f"Кандидат частично соответствует требованиям позиции '{search_query}'. "
        else:
            assessment += f"Кандидат слабо соответствует требованиям позиции '{search_query}'. "
        
        if high_scores:
            assessment += f"Сильные стороны показали {len(high_scores)} агентов. "
        
        if low_scores:
            assessment += f"Выявлены проблемы в {len(low_scores)} областях анализа. "
        
        assessment += "\n\nДля полного анализа требуется активация GPT мастер-координатора."
        
        return assessment
    
    def _generate_conclusion(self, score: float, red_flags: int, failures: int, 
                           request: MultiAgentAnalysisRequest) -> str:
        """Генерирует итоговое заключение"""
        if score >= 85 and red_flags <= 2:
            return f"Отличный кандидат для позиции '{request.search_query}'. Высокое соответствие требованиям и минимум рисков. Рекомендуется для дальнейшего рассмотрения."
        
        elif score >= 70 and failures == 0:
            return f"Хороший кандидат для позиции '{request.search_query}'. Соответствует основным требованиям с незначительными замечаниями. Подходит для собеседования."
        
        elif score >= 60:
            return f"Кандидат может подойти для позиции '{request.search_query}' при дополнительной проверке. Есть области для обсуждения на собеседовании."
        
        elif score >= 40:
            return f"Кандидат частично соответствует требованиям позиции '{request.search_query}'. Требуется тщательная оценка на собеседовании."
        
        else:
            return f"Кандидат слабо соответствует требованиям позиции '{request.search_query}'. Высокие риски, рекомендуется поиск более подходящих кандидатов."
    
    def _get_final_recommendation(self, score: float, red_flags: int, failures: int) -> str:
        """Определяет финальную рекомендацию"""
        if score >= 80 and failures == 0:
            return "РЕКОМЕНДУЕТСЯ к собеседованию"
        elif score >= 65 and failures <= 1:
            return "РАССМОТРЕТЬ с осторожностью"
        elif score >= 50:
            return "ТРЕБУЕТ дополнительной проверки"
        else:
            return "НЕ РЕКОМЕНДУЕТСЯ"
    
    def _get_status_emoji(self, status: AgentStatus) -> str:
        """Возвращает эмодзи для статуса"""
        emoji_map = {
            AgentStatus.PASS: "✅",
            AgentStatus.WARNING: "⚠️", 
            AgentStatus.FAIL: "❌",
            AgentStatus.ERROR: "🔥"
        }
        return emoji_map.get(status, "❓")
    
    def get_available_agents(self) -> Dict[str, str]:
        """Возвращает список доступных агентов"""
        return {name: agent.name for name, agent in self.agents.items()}
    
    def get_position_config(self) -> Dict[str, List[str]]:
        """Возвращает конфигурацию агентов для разных типов позиций"""
        return self.position_agent_config.copy()