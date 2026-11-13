"""
Quality Controller - Контроллер качества выполнения задач

Отвечает за оценку качества работы агентов, выявление проблем,
улучшение процессов и обучение системы.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from openai import AsyncOpenAI
import httpx

from .models import QualityMetrics, EscalationEvent, MasterTaskStatus

if TYPE_CHECKING:
    from .master_agent import MasterAgent

logger = logging.getLogger("quality-controller")


class QualityController:
    """
    Контроллер качества выполнения
    
    Функции:
    - Оценка качества выполнения задач
    - Выявление паттернов ошибок
    - Автоматическое улучшение процессов
    - Эскалация критических проблем
    - Обучение на основе опыта
    - Мониторинг производительности агентов
    """
    
    def __init__(self, config: Dict[str, Any], master_agent: "MasterAgent"):
        self.config = config
        self.master_agent = master_agent
        self.logger = logger
        
        # Конфигурация качества
        self.quality_config = config.get("quality_control", {})
        
        # LLM для анализа качества
        self.llm_client = None
        self._setup_llm()
        
        # Пороговые значения
        self.thresholds = {
            "min_success_rate": self.quality_config.get("min_success_rate", 0.8),
            "max_response_time": self.quality_config.get("max_response_time", 300),  # 5 минут
            "min_user_satisfaction": self.quality_config.get("min_user_satisfaction", 0.7),
            "escalation_failure_rate": self.quality_config.get("escalation_failure_rate", 0.3)
        }
        
        # История метрик
        self.quality_history: List[QualityMetrics] = []
        self.escalation_events: List[EscalationEvent] = []
        
        # Паттерны проблем
        self.problem_patterns: Dict[str, List[Dict[str, Any]]] = {}
        
        # Статистика
        self.stats = {
            "total_evaluations": 0,
            "quality_issues_detected": 0,
            "escalations_created": 0,
            "improvements_suggested": 0,
            "average_quality_score": 0.0
        }
    
    def _setup_llm(self):
        """Настройка LLM для анализа качества"""
        try:
            ai_config = self.config.get("master_agent", {})
            
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
            
            # Параметры для анализа качества
            self.model = ai_config.get("fast_model", "gpt-5-mini")
            self.max_tokens = ai_config.get("max_completion_tokens", 2000)
            self.temperature = 0.1  # Низкая температура для объективного анализа
            
            logger.info("✅ LLM для Quality Controller настроен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки LLM: {e}")
    
    async def initialize(self):
        """Инициализация контроллера качества"""
        try:
            # Загрузка истории качества
            await self._load_quality_history()
            
            # Анализ существующих паттернов
            await self._analyze_existing_patterns()
            
            self.logger.info("✅ Quality Controller инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Quality Controller: {e}")
            raise
    
    async def evaluate_task_quality(self, task_data: Dict[str, Any], agent_results: List[Dict[str, Any]]) -> QualityMetrics:
        """Оценка качества выполнения задачи"""
        try:
            task_id = task_data.get("id", "unknown")
            start_time = task_data.get("start_time", datetime.now())
            completion_time = (datetime.now() - start_time).total_seconds()
            
            # Базовые метрики
            success_count = sum(1 for result in agent_results if result.get("success", False))
            total_agents = len(agent_results) if agent_results else 1
            success_rate = success_count / total_agents if total_agents > 0 else 0.0
            
            errors_count = sum(1 for result in agent_results if "error" in result)
            
            # Анализ качества через LLM
            quality_analysis = await self._analyze_task_quality_with_llm(task_data, agent_results)
            
            # Расчет общей оценки качества
            quality_score = await self._calculate_quality_score(
                success_rate, completion_time, errors_count, quality_analysis
            )
            
            # Создание метрик
            metrics = QualityMetrics(
                task_id=task_id,
                completion_time=completion_time,
                success_rate=success_rate,
                quality_score=quality_score,
                errors_count=errors_count,
                feedback=quality_analysis.get("feedback", [])
            )
            
            # Сохранение в историю
            self.quality_history.append(metrics)
            
            # Проверка на проблемы
            await self._check_for_quality_issues(metrics, task_data, agent_results)
            
            # Обновление статистики
            self.stats["total_evaluations"] += 1
            self._update_average_quality_score(quality_score)
            
            self.logger.info(f"✅ Качество задачи {task_id} оценено: {quality_score:.2f}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка оценки качества задачи: {e}")
            # Возвращаем базовые метрики в случае ошибки
            return QualityMetrics(
                task_id=task_data.get("id", "unknown"),
                completion_time=0.0,
                success_rate=0.0,
                quality_score=0.0,
                errors_count=1
            )
    
    async def _analyze_task_quality_with_llm(self, task_data: Dict[str, Any], agent_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализ качества задачи с помощью LLM"""
        try:
            if not self.llm_client:
                return {"feedback": ["LLM недоступен для анализа качества"]}
            
            # Подготовка данных для анализа
            analysis_prompt = f"""
Проанализируй качество выполнения задачи HR мастер-агентом.

ЗАДАЧА:
Цель: {task_data.get('request', {}).get('goal', 'Неизвестно')}
Приоритет: {task_data.get('request', {}).get('priority', 'normal')}
Ожидаемые агенты: {task_data.get('analysis', {}).get('required_agents', [])}

ПЛАН ВЫПОЛНЕНИЯ:
{json.dumps(task_data.get('plan', {}), ensure_ascii=False, indent=2)}

РЕЗУЛЬТАТЫ ОТ АГЕНТОВ:
{json.dumps(agent_results, ensure_ascii=False, indent=2)}

ОЦЕНИ:
1. Соответствие результатов поставленной цели
2. Качество планирования и координации
3. Эффективность использования агентов
4. Выявленные проблемы и ошибки
5. Соответствие ожиданиям пользователя

КРИТЕРИИ КАЧЕСТВА:
- Полнота выполнения задачи
- Своевременность
- Точность результатов
- Пользовательский опыт
- Эффективность ресурсов

Ответь в формате JSON:
{{
    "goal_achievement": 0.0-1.0,
    "planning_quality": 0.0-1.0,
    "agent_coordination": 0.0-1.0,
    "error_handling": 0.0-1.0,
    "user_experience": 0.0-1.0,
    "overall_assessment": 0.0-1.0,
    "strengths": ["сила 1", "сила 2"],
    "weaknesses": ["слабость 1", "слабость 2"],
    "feedback": ["рекомендация 1", "рекомендация 2"],
    "improvement_suggestions": ["улучшение 1", "улучшение 2"]
}}
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт по оценке качества работы AI-агентов в HR."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка LLM анализа качества: {e}")
            return {
                "overall_assessment": 0.5,
                "feedback": [f"Ошибка анализа: {e}"]
            }
    
    async def _calculate_quality_score(self, success_rate: float, completion_time: float, 
                                     errors_count: int, llm_analysis: Dict[str, Any]) -> float:
        """Расчет общей оценки качества"""
        try:
            # Базовые компоненты оценки
            success_component = success_rate * 0.3
            
            # Оценка времени (штраф за превышение лимита)
            time_component = 0.2
            if completion_time > self.thresholds["max_response_time"]:
                time_component *= max(0.1, 1 - (completion_time / self.thresholds["max_response_time"] - 1))
            
            # Оценка ошибок (штраф за ошибки)
            error_component = max(0.0, 0.2 - (errors_count * 0.05))
            
            # LLM оценка
            llm_component = llm_analysis.get("overall_assessment", 0.5) * 0.3
            
            # Общая оценка
            quality_score = success_component + time_component + error_component + llm_component
            
            return min(1.0, max(0.0, quality_score))
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета качества: {e}")
            return 0.5
    
    async def _check_for_quality_issues(self, metrics: QualityMetrics, task_data: Dict[str, Any], 
                                      agent_results: List[Dict[str, Any]]):
        """Проверка на проблемы качества"""
        try:
            issues_detected = []
            
            # Проверка успешности
            if metrics.success_rate < self.thresholds["min_success_rate"]:
                issues_detected.append({
                    "type": "low_success_rate",
                    "severity": "high" if metrics.success_rate < 0.5 else "medium",
                    "description": f"Низкий процент успеха: {metrics.success_rate:.2f}",
                    "recommendation": "Пересмотреть планирование и выбор агентов"
                })
            
            # Проверка времени выполнения
            if metrics.completion_time > self.thresholds["max_response_time"]:
                issues_detected.append({
                    "type": "slow_completion",
                    "severity": "medium",
                    "description": f"Медленное выполнение: {metrics.completion_time:.1f}с",
                    "recommendation": "Оптимизировать процессы или распараллелить задачи"
                })
            
            # Проверка количества ошибок
            if metrics.errors_count > 2:
                issues_detected.append({
                    "type": "high_error_rate",
                    "severity": "high",
                    "description": f"Много ошибок: {metrics.errors_count}",
                    "recommendation": "Улучшить обработку ошибок и валидацию"
                })
            
            # Проверка общего качества
            if metrics.quality_score < 0.6:
                issues_detected.append({
                    "type": "low_quality_score",
                    "severity": "medium",
                    "description": f"Низкая оценка качества: {metrics.quality_score:.2f}",
                    "recommendation": "Общее улучшение процессов"
                })
            
            if issues_detected:
                self.stats["quality_issues_detected"] += len(issues_detected)
                
                # Эскалация критических проблем
                critical_issues = [issue for issue in issues_detected if issue["severity"] == "high"]
                if critical_issues:
                    await self._escalate_quality_issues(metrics.task_id, critical_issues, task_data)
                
                # Сохранение паттернов проблем
                await self._record_problem_patterns(issues_detected, task_data, agent_results)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки качества: {e}")
    
    async def _escalate_quality_issues(self, task_id: str, critical_issues: List[Dict[str, Any]], 
                                     task_data: Dict[str, Any]):
        """Эскалация критических проблем качества"""
        try:
            escalation = EscalationEvent(
                event_id=f"esc_{task_id}_{len(self.escalation_events)}",
                task_id=task_id,
                agent_type="master_agent",
                reason=f"Критические проблемы качества: {', '.join([issue['type'] for issue in critical_issues])}",
                severity="high",
                escalated_to="hr_manager"
            )
            
            self.escalation_events.append(escalation)
            self.stats["escalations_created"] += 1
            
            # Уведомление через messenger interface (если доступен)
            if hasattr(self.master_agent, 'messenger'):
                await self._notify_escalation(escalation, critical_issues)
            
            self.logger.warning(f"⚠️ Эскалация создана: {escalation.event_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка эскалации: {e}")
    
    async def _notify_escalation(self, escalation: EscalationEvent, issues: List[Dict[str, Any]]):
        """Уведомление об эскалации"""
        try:
            message_content = f"""
🚨 ЭСКАЛАЦИЯ КАЧЕСТВА

Задача: {escalation.task_id}
Причина: {escalation.reason}

Проблемы:
{chr(10).join([f"• {issue['description']}" for issue in issues])}

Рекомендации:
{chr(10).join([f"• {issue['recommendation']}" for issue in issues])}

Время: {escalation.timestamp}
"""
            
            # Здесь была бы отправка уведомления
            self.logger.info(f"📧 Уведомление об эскалации подготовлено: {escalation.event_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка уведомления об эскалации: {e}")
    
    async def _record_problem_patterns(self, issues: List[Dict[str, Any]], task_data: Dict[str, Any], 
                                     agent_results: List[Dict[str, Any]]):
        """Запись паттернов проблем для обучения"""
        try:
            for issue in issues:
                issue_type = issue["type"]
                
                if issue_type not in self.problem_patterns:
                    self.problem_patterns[issue_type] = []
                
                pattern_record = {
                    "issue": issue,
                    "task_type": task_data.get("analysis", {}).get("task_type", "unknown"),
                    "complexity": task_data.get("analysis", {}).get("complexity", "medium"),
                    "agents_used": task_data.get("plan", {}).get("agents", []),
                    "timestamp": datetime.now().isoformat(),
                    "context": {
                        "goal": task_data.get("request", {}).get("goal", ""),
                        "priority": task_data.get("request", {}).get("priority", "normal")
                    }
                }
                
                self.problem_patterns[issue_type].append(pattern_record)
                
                # Ограничение размера истории паттернов
                if len(self.problem_patterns[issue_type]) > 100:
                    self.problem_patterns[issue_type] = self.problem_patterns[issue_type][-100:]
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка записи паттернов проблем: {e}")
    
    async def generate_quality_report(self, period_days: int = 7) -> Dict[str, Any]:
        """Генерация отчета о качестве"""
        try:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            
            # Фильтрация метрик за период
            period_metrics = [
                metric for metric in self.quality_history
                if metric.timestamp >= cutoff_date
            ]
            
            if not period_metrics:
                return {"error": "Нет данных за указанный период"}
            
            # Расчет агрегированных метрик
            avg_quality_score = statistics.mean([m.quality_score for m in period_metrics])
            avg_success_rate = statistics.mean([m.success_rate for m in period_metrics])
            avg_completion_time = statistics.mean([m.completion_time for m in period_metrics])
            total_errors = sum([m.errors_count for m in period_metrics])
            
            # Анализ трендов
            quality_trend = await self._analyze_quality_trend(period_metrics)
            
            # Топ проблем
            top_problems = await self._identify_top_problems(period_days)
            
            # Рекомендации по улучшению
            recommendations = await self._generate_improvement_recommendations(period_metrics)
            
            report = {
                "period": f"{period_days} дней",
                "total_tasks": len(period_metrics),
                "metrics": {
                    "average_quality_score": round(avg_quality_score, 2),
                    "average_success_rate": round(avg_success_rate, 2),
                    "average_completion_time": round(avg_completion_time, 1),
                    "total_errors": total_errors,
                    "escalations": len([e for e in self.escalation_events if e.timestamp >= cutoff_date])
                },
                "trends": quality_trend,
                "top_problems": top_problems,
                "recommendations": recommendations,
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации отчета качества: {e}")
            return {"error": str(e)}
    
    async def _analyze_quality_trend(self, metrics: List[QualityMetrics]) -> Dict[str, Any]:
        """Анализ тренда качества"""
        try:
            if len(metrics) < 2:
                return {"trend": "insufficient_data"}
            
            # Сортировка по времени
            sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
            
            # Сравнение первой и второй половины периода
            mid_point = len(sorted_metrics) // 2
            first_half = sorted_metrics[:mid_point]
            second_half = sorted_metrics[mid_point:]
            
            first_avg = statistics.mean([m.quality_score for m in first_half])
            second_avg = statistics.mean([m.quality_score for m in second_half])
            
            change = second_avg - first_avg
            
            if abs(change) < 0.05:
                trend = "stable"
            elif change > 0:
                trend = "improving"
            else:
                trend = "declining"
            
            return {
                "trend": trend,
                "change": round(change, 3),
                "first_half_avg": round(first_avg, 2),
                "second_half_avg": round(second_avg, 2)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа тренда: {e}")
            return {"trend": "error", "error": str(e)}
    
    async def _identify_top_problems(self, period_days: int) -> List[Dict[str, Any]]:
        """Выявление топ проблем"""
        try:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            
            problem_counts = {}
            
            for problem_type, patterns in self.problem_patterns.items():
                recent_patterns = [
                    p for p in patterns
                    if datetime.fromisoformat(p["timestamp"]) >= cutoff_date
                ]
                
                if recent_patterns:
                    problem_counts[problem_type] = {
                        "count": len(recent_patterns),
                        "severity_distribution": {},
                        "recent_example": recent_patterns[-1]["issue"]["description"]
                    }
                    
                    # Подсчет по серьезности
                    for pattern in recent_patterns:
                        severity = pattern["issue"]["severity"]
                        problem_counts[problem_type]["severity_distribution"][severity] = (
                            problem_counts[problem_type]["severity_distribution"].get(severity, 0) + 1
                        )
            
            # Сортировка по количеству
            top_problems = sorted(
                problem_counts.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:5]
            
            return [
                {
                    "problem_type": problem_type,
                    "count": data["count"],
                    "severity_distribution": data["severity_distribution"],
                    "recent_example": data["recent_example"]
                }
                for problem_type, data in top_problems
            ]
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка выявления топ проблем: {e}")
            return []
    
    async def _generate_improvement_recommendations(self, metrics: List[QualityMetrics]) -> List[str]:
        """Генерация рекомендаций по улучшению"""
        try:
            recommendations = []
            
            # Анализ на основе метрик
            avg_success_rate = statistics.mean([m.success_rate for m in metrics])
            avg_quality_score = statistics.mean([m.quality_score for m in metrics])
            avg_completion_time = statistics.mean([m.completion_time for m in metrics])
            
            if avg_success_rate < 0.8:
                recommendations.append("Улучшить планирование задач и выбор агентов")
            
            if avg_quality_score < 0.7:
                recommendations.append("Внедрить дополнительные проверки качества")
            
            if avg_completion_time > 180:  # 3 минуты
                recommendations.append("Оптимизировать производительность и распараллеливание")
            
            # Анализ паттернов проблем
            if "high_error_rate" in self.problem_patterns:
                recommendations.append("Улучшить обработку ошибок и валидацию входных данных")
            
            if "low_success_rate" in self.problem_patterns:
                recommendations.append("Пересмотреть алгоритмы распределения задач")
            
            return recommendations if recommendations else ["Общее качество работы удовлетворительное"]
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации рекомендаций: {e}")
            return ["Ошибка анализа качества"]
    
    async def _load_quality_history(self):
        """Загрузка истории качества"""
        try:
            # В реальной реализации здесь была бы загрузка из памяти или файлов
            self.logger.info("✅ История качества загружена")
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки истории качества: {e}")
    
    async def _analyze_existing_patterns(self):
        """Анализ существующих паттернов"""
        try:
            # В реальной реализации здесь был бы анализ сохраненных паттернов
            self.logger.info("✅ Паттерны проблем проанализированы")
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа паттернов: {e}")
    
    def _update_average_quality_score(self, new_score: float):
        """Обновление средней оценки качества"""
        current_avg = self.stats["average_quality_score"]
        total_evaluations = self.stats["total_evaluations"]
        
        if total_evaluations == 1:
            self.stats["average_quality_score"] = new_score
        else:
            self.stats["average_quality_score"] = (
                (current_avg * (total_evaluations - 1) + new_score) / total_evaluations
            )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики Quality Controller"""
        return {
            "stats": self.stats,
            "thresholds": self.thresholds,
            "quality_history_size": len(self.quality_history),
            "escalation_events_count": len(self.escalation_events),
            "problem_patterns_count": len(self.problem_patterns),
            "recent_quality_scores": [
                m.quality_score for m in self.quality_history[-10:]
            ] if self.quality_history else []
        }
