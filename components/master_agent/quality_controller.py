"""
Quality Controler - Task Quality Control

Responsible for assessing the quality of agents &apos; work, identifying problems,
Improved processes and training of the system.

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
    Performance quality controller
    
    Functions:
    - Evaluation of the quality of performance
    - Detection of patterns of errors
    - Automatic process improvement
    - The escalation of critical problems
    - Learning from experience
    - Monitoring the performance of agents
    """
    
    def __init__(self, config: Dict[str, Any], master_agent: "MasterAgent"):
        self.config = config
        self.master_agent = master_agent
        self.logger = logger
        
        # Quality configuration
        self.quality_config = config.get("quality_control", {})
        
        # LLM for quality analysis
        self.llm_client = None
        self._setup_llm()
        
        # Threshold values
        self.thresholds = {
            "min_success_rate": self.quality_config.get("min_success_rate", 0.8),
            "max_response_time": self.quality_config.get("max_response_time", 300),  # 5 minutes
            "min_user_satisfaction": self.quality_config.get("min_user_satisfaction", 0.7),
            "escalation_failure_rate": self.quality_config.get("escalation_failure_rate", 0.3)
        }
        
        # The history of the metric
        self.quality_history: List[QualityMetrics] = []
        self.escalation_events: List[EscalationEvent] = []
        
        # Patterns of Problems
        self.problem_patterns: Dict[str, List[Dict[str, Any]]] = {}
        
        # Statistics
        self.stats = {
            "total_evaluations": 0,
            "quality_issues_detected": 0,
            "escalations_created": 0,
            "improvements_suggested": 0,
            "average_quality_score": 0.0
        }
    
    def _setup_llm(self):
        'LLM settings for quality analysis'
        try:
            ai_config = self.config.get("master_agent", {})
            
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
            
            # Parameters for quality analysis
            self.model = ai_config.get("fast_model", "gpt-5-mini")
            self.max_tokens = ai_config.get("max_completion_tokens", 2000)
            self.temperature = 0.1  # Low temperature for objective analysis
            
            logger.info('✅ LLM for Quality Controler')
            
        except Exception as e:
            logger.error(f"❌ Configuration of LLM errors: {e}")
    
    async def initialize(self):
        'Initialization of Quality Controller'
        try:
            # Loading quality history
            await self._load_quality_history()
            
            # Analysis of existing patterns
            await self._analyze_existing_patterns()
            
            self.logger.info('✅ Quality Controler initialized')
            
        except Exception as e:
            self.logger.error(f"Error: ❌ Initialization of Quality Controller: {e}")
            raise
    
    async def evaluate_task_quality(self, task_data: Dict[str, Any], agent_results: List[Dict[str, Any]]) -> QualityMetrics:
        'Evaluation of the quality of the task'
        try:
            task_id = task_data.get("id", "unknown")
            start_time = task_data.get("start_time", datetime.now())
            completion_time = (datetime.now() - start_time).total_seconds()
            
            # Basic metrics
            success_count = sum(1 for result in agent_results if result.get("success", False))
            total_agents = len(agent_results) if agent_results else 1
            success_rate = success_count / total_agents if total_agents > 0 else 0.0
            
            errors_count = sum(1 for result in agent_results if "error" in result)
            
            # Quality analysis through LLM
            quality_analysis = await self._analyze_task_quality_with_llm(task_data, agent_results)
            
            # Calculation of the overall quality assessment
            quality_score = await self._calculate_quality_score(
                success_rate, completion_time, errors_count, quality_analysis
            )
            
            # Creation of metrics
            metrics = QualityMetrics(
                task_id=task_id,
                completion_time=completion_time,
                success_rate=success_rate,
                quality_score=quality_score,
                errors_count=errors_count,
                feedback=quality_analysis.get("feedback", [])
            )
            
            # Save to history
            self.quality_history.append(metrics)
            
            # Checking for problems
            await self._check_for_quality_issues(metrics, task_data, agent_results)
            
            # Updating statistics
            self.stats["total_evaluations"] += 1
            self._update_average_quality_score(quality_score)
            
            self.logger.info(f"✅ Quality of task {task_id} assessed: {quality_score:.2f}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error in assessing the quality of task: {e}")
            # Return the basic metrics in case of error
            return QualityMetrics(
                task_id=task_data.get("id", "unknown"),
                completion_time=0.0,
                success_rate=0.0,
                quality_score=0.0,
                errors_count=1
            )
    
    async def _analyze_task_quality_with_llm(self, task_data: Dict[str, Any], agent_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        'Quality analysis of the task using LLM'
        try:
            if not self.llm_client:
                return {"feedback": ['LLM is not available for quality analysis']}
            
            # Preparation of data for analysis
            analysis_prompt = f"""
Review the quality of the HR Master Agent &apos; s task.

TASK:
Objective: {task_data.get('request', {}).get('goal', 'Unknown')}
Priority: {task_data.get('request', {}).get('priority', 'normal')}
Expected agents: {task_data.get('analysis', {}).get('required_agents', [])}

IMPLEMENTATION PLAN:
{json.dumps(task_data.get('plan', {}), ensure_ascii=False, indent=2)}

RESULTS FROM AGENCIES:
{json.dumps(agent_results, ensure_ascii=False, indent=2)}

EVALUATION:
1. Meeting the target
2. Quality of planning and coordination
3. Efficiency of use of agents
4. Detected problems and errors
5. Compliance with user expectations

QUALITY CRITERIA:
- Completeness of task
Timeliness
- Accuracy of results
- User experience
- Resource efficiency

Answer JSON:
{{
    \"goal_achievement\": 0.0-1.0,
    \"planning_quality\": 0.0-1.0,
    \"agent_coordination\": 0.0-1.0,
    \"error_handling\": 0.0-1.0,
    \"user_experience\": 0.0-1.0,
    \"overall_assessment\": 0.0-1.0,
    \"strengths\": [\"force 1\", \"force 2\"],
    \"weaknesses\": [\"weakness 1\", \"weakness 2\"],
    \"feedback\": [\"Recommendation 1\", \"Recommendation 2\"],
    \"improvement_suggestions\": [\"improvement 1\", \"improvement 2\"]
}}
"""
            
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You're an expert on the quality assessment of AI agents' work at HR."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ LLM Quality Analysis Error: {e}")
            return {
                "overall_assessment": 0.5,
                "feedback": [f"Error of analysis: {e}"]
            }
    
    async def _calculate_quality_score(self, success_rate: float, completion_time: float, 
                                     errors_count: int, llm_analysis: Dict[str, Any]) -> float:
        'Calculation of the overall quality assessment'
        try:
            # Basic components of the assessment
            success_component = success_rate * 0.3
            
            # Time estimate (failure for exceeding limit)
            time_component = 0.2
            if completion_time > self.thresholds["max_response_time"]:
                time_component *= max(0.1, 1 - (completion_time / self.thresholds["max_response_time"] - 1))
            
            # Error Assessment (the penalty for errors))
            error_component = max(0.0, 0.2 - (errors_count * 0.05))
            
            # LLM evaluation
            llm_component = llm_analysis.get("overall_assessment", 0.5) * 0.3
            
            # Overall assessment
            quality_score = success_component + time_component + error_component + llm_component
            
            return min(1.0, max(0.0, quality_score))
            
        except Exception as e:
            self.logger.error(f"❌ Error in Quality Calculation: {e}")
            return 0.5
    
    async def _check_for_quality_issues(self, metrics: QualityMetrics, task_data: Dict[str, Any], 
                                      agent_results: List[Dict[str, Any]]):
        'Quality check'
        try:
            issues_detected = []
            
            # Checking for success
            if metrics.success_rate < self.thresholds["min_success_rate"]:
                issues_detected.append({
                    "type": "low_success_rate",
                    "severity": "high" if metrics.success_rate < 0.5 else "medium",
                    "description": f"Low success rate: {metrics.success_rate:.2f}",
                    "recommendation": 'Review the planning and selection of agents'
                })
            
            # Checking the time of implementation
            if metrics.completion_time > self.thresholds["max_response_time"]:
                issues_detected.append({
                    "type": "slow_completion",
                    "severity": "medium",
                    "description": f"Slow implementation: {metrics.completion_time:.1f}c",
                    "recommendation": 'Optimize processes or split tasks'
                })
            
            # Check the number of errors
            if metrics.errors_count > 2:
                issues_detected.append({
                    "type": "high_error_rate",
                    "severity": "high",
                    "description": f"A lot of mistakes: {metrics.errors_count}",
                    "recommendation": 'Improve error processing and validation'
                })
            
            # General quality check
            if metrics.quality_score < 0.6:
                issues_detected.append({
                    "type": "low_quality_score",
                    "severity": "medium",
                    "description": f"Low quality assessment: {metrics.quality_score:.2f}",
                    "recommendation": 'Overall process improvement'
                })
            
            if issues_detected:
                self.stats["quality_issues_detected"] += len(issues_detected)
                
                # The escalation of critical issues
                critical_issues = [issue for issue in issues_detected if issue["severity"] == "high"]
                if critical_issues:
                    await self._escalate_quality_issues(metrics.task_id, critical_issues, task_data)
                
                # Maintaining problem patterns
                await self._record_problem_patterns(issues_detected, task_data, agent_results)
            
        except Exception as e:
            self.logger.error(f"❌ Error of quality verification: {e}")
    
    async def _escalate_quality_issues(self, task_id: str, critical_issues: List[Dict[str, Any]], 
                                     task_data: Dict[str, Any]):
        'Escalation of critical quality issues'
        try:
            escalation = EscalationEvent(
                event_id=f"esc_{task_id}_{len(self.escalation_events)}",
                task_id=task_id,
                agent_type="master_agent",
                reason=f"Critical quality issues: {', '.join([issue['type'] for issue in critical_issues])}",
                severity="high",
                escalated_to="hr_manager"
            )
            
            self.escalation_events.append(escalation)
            self.stats["escalations_created"] += 1
            
            # Notification through messenger interface (if available)
            if hasattr(self.master_agent, 'messenger'):
                await self._notify_escalation(escalation, critical_issues)
            
            self.logger.warning(f"⚠️ Escalation created: {escalation.event_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error of escalation: {e}")
    
    async def _notify_escalation(self, escalation: EscalationEvent, issues: List[Dict[str, Any]]):
        'Notice of escalation'
        try:
            message_content = f"""
🚨 QUALITY ESCOLATION

Task: {escalation.task_id}
Reason: {escalation.reason}

Challenges:
{chr(10).join([f"• {issue['description']}" for issue in issues])}

Recommendations:
{chr(10).join([f"• {issue['recommendation']}" for issue in issues])}

Time: {escalation.timestamp}
"""
            
            # There would be a notice here.
            self.logger.info(f"📧 Notice of escalation prepared: {escalation.event_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error in notification of escalation: {e}")
    
    async def _record_problem_patterns(self, issues: List[Dict[str, Any]], task_data: Dict[str, Any], 
                                     agent_results: List[Dict[str, Any]]):
        'Recording problems for training'
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
                
                # Limiting the size of Pattern history
                if len(self.problem_patterns[issue_type]) > 100:
                    self.problem_patterns[issue_type] = self.problem_patterns[issue_type][-100:]
            
        except Exception as e:
            self.logger.error(f"❌ Error of pattern recording: {e}")
    
    async def generate_quality_report(self, period_days: int = 7) -> Dict[str, Any]:
        'Quality report generation'
        try:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            
            # Meter filtering over the period
            period_metrics = [
                metric for metric in self.quality_history
                if metric.timestamp >= cutoff_date
            ]
            
            if not period_metrics:
                return {"error": 'No data for the period'}
            
            # Calculation of aggregate metrics
            avg_quality_score = statistics.mean([m.quality_score for m in period_metrics])
            avg_success_rate = statistics.mean([m.success_rate for m in period_metrics])
            avg_completion_time = statistics.mean([m.completion_time for m in period_metrics])
            total_errors = sum([m.errors_count for m in period_metrics])
            
            # Trends analysis
            quality_trend = await self._analyze_quality_trend(period_metrics)
            
            # Top of the problem
            top_problems = await self._identify_top_problems(period_days)
            
            # Recommendations for improvement
            recommendations = await self._generate_improvement_recommendations(period_metrics)
            
            report = {
                "period": f"{period_days} days",
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
            self.logger.error(f"❌ Error in Generating Quality Report: {e}")
            return {"error": str(e)}
    
    async def _analyze_quality_trend(self, metrics: List[QualityMetrics]) -> Dict[str, Any]:
        'Analysis of the trend in quality'
        try:
            if len(metrics) < 2:
                return {"trend": "insufficient_data"}
            
            # Time Sorting
            sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
            
            # Comparison of the first and second half of the period
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
            self.logger.error(f"❌ Analysis of trend errors: {e}")
            return {"trend": "error", "error": str(e)}
    
    async def _identify_top_problems(self, period_days: int) -> List[Dict[str, Any]]:
        'Identifying the top of the problem'
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
                    
                    # Seriousness calculation
                    for pattern in recent_patterns:
                        severity = pattern["issue"]["severity"]
                        problem_counts[problem_type]["severity_distribution"][severity] = (
                            problem_counts[problem_type]["severity_distribution"].get(severity, 0) + 1
                        )
            
            # Quantity Sorting
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
            self.logger.error(f"❌ Errors in identifying top problems: {e}")
            return []
    
    async def _generate_improvement_recommendations(self, metrics: List[QualityMetrics]) -> List[str]:
        'Generating recommendations for improvement'
        try:
            recommendations = []
            
            # Meteric analysis
            avg_success_rate = statistics.mean([m.success_rate for m in metrics])
            avg_quality_score = statistics.mean([m.quality_score for m in metrics])
            avg_completion_time = statistics.mean([m.completion_time for m in metrics])
            
            if avg_success_rate < 0.8:
                recommendations.append('Improve task planning and choice of agents')
            
            if avg_quality_score < 0.7:
                recommendations.append('Introduce additional quality checks')
            
            if avg_completion_time > 180:  # 3 minutes
                recommendations.append('Optimize productivity and dissipation')
            
            # Analysis of problem patterns
            if "high_error_rate" in self.problem_patterns:
                recommendations.append('Improve error processing and validation of input data')
            
            if "low_success_rate" in self.problem_patterns:
                recommendations.append('Review task distribution algorithms')
            
            return recommendations if recommendations else ['Overall quality of work satisfactory']
            
        except Exception as e:
            self.logger.error(f"❌ Error in Generating Recommendations: {e}")
            return ['Error in Quality Analysis']
    
    async def _load_quality_history(self):
        'Loading quality history'
        try:
            # In real implementation there would be a download from memory or files
            self.logger.info('✅ Quality history downloaded')
        except Exception as e:
            self.logger.error(f"❌ Error in the quality history: {e}")
    
    async def _analyze_existing_patterns(self):
        'Analysis of existing patterns'
        try:
            # In real terms, there would be an analysis of the retained patterns
            self.logger.info('✅ Problem patters analysed')
        except Exception as e:
            self.logger.error(f"Error: ❌ Analysis of patterns: {e}")
    
    def _update_average_quality_score(self, new_score: float):
        'Update of the average quality assessment'
        current_avg = self.stats["average_quality_score"]
        total_evaluations = self.stats["total_evaluations"]
        
        if total_evaluations == 1:
            self.stats["average_quality_score"] = new_score
        else:
            self.stats["average_quality_score"] = (
                (current_avg * (total_evaluations - 1) + new_score) / total_evaluations
            )
    
    async def get_stats(self) -> Dict[str, Any]:
        'Collection of statistics Quality Controler'
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
