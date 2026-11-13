"""
Candidate Analysis - Multi-Agent Analysis System

Система специализированных AI агентов для глубокого анализа кандидатов.

Этот модуль реализует мультиагентную архитектуру, где каждый агент является экспертом
в определённой области анализа резюме. Все агенты работают параллельно с использованием
AsyncOpenAI и GPT-5-nano для максимальной производительности.

Architecture Overview:
    BaseAgent (ABC) 
    ├── TechnicalSkillsAgent      # Анализ технических навыков
    ├── ExperienceRelevanceAgent  # Оценка релевантности опыта  
    ├── CulturalFitAgent         # Анализ культурного соответствия
    ├── GrowthPotentialAgent     # Оценка потенциала роста
    ├── ResumeAnalysisAgent      # Анализ качества резюме
    └── AnomalyDetectionAgent    # Выявление несоответствий

Key Features:
- AsyncOpenAI для истинно параллельной работы всех агентов
- Конфигурируемые промпты через agent_prompts.yaml
- Настраиваемые параметры через agent_configs.yaml  
- Exponential backoff для устойчивости к ошибкам API
- Детальное логирование для debugging и мониторинга
- JSON-структурированные ответы для программной обработки

Agent Specializations:
- Technical: hard skills, технологии, инструменты
- Experience: релевантность опыта, карьерный путь
- Cultural: soft skills, коммуникация, teamwork
- Growth: потенциал, обучаемость, амбиции  
- Resume: структура, качество, полнота информации
- Anomaly: red flags, несоответствия, подозрительные моменты

Performance:
- Время анализа одного кандидата: ~4-6 секунд (6 агентов параллельно)
- Поддержка батчевой обработки до 10 кандидатов
- Graceful error handling с retry механизмами
- Минимальные затраты на OpenAI API (~$0.002-0.005 за кандидата)

Author: Candidate Analysis Team  
Version: 3.0.0 (AsyncOpenAI + True Parallelism)
Last Updated: 2025-01-04
"""

import time
import json
import re
import asyncio
import yaml
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import AgentReport, AgentStatus
from shared.utils import setup_logging, load_config

# СОВРЕМЕННЫЙ OPENAI КЛИЕНТ С ПРОКСИ
from openai import AsyncOpenAI
import httpx
import backoff

logger = setup_logging("agents")

class BaseAgent(ABC):
    """
    Базовый абстрактный класс для всех специализированных AI агентов.
    
    Предоставляет общую инфраструктуру для:
    - Загрузки конфигурации и промптов из YAML файлов
    - Инициализации AsyncOpenAI клиента с proxy поддержкой
    - Асинхронных вызовов GPT-5-nano с retry логикой
    - Логирования и мониторинга работы агентов
    - Стандартизированного формата ответов (JSON)
    
    Attributes:
        name (str): Уникальное имя агента (technical_skills, experience_relevance, etc.)
        config (dict): Полная конфигурация системы из settings.yaml
        ai_config (dict): Специфичная конфигурация AI из ai_analysis секции
        prompts (dict): Загруженные промпты из agent_prompts.yaml
        agent_configs (dict): Конфигурация агентов из agent_configs.yaml
        openai_client (AsyncOpenAI): Асинхронный клиент OpenAI
        
    Configuration Files:
        - agent_prompts.yaml: Промпты для каждого типа агента
        - agent_configs.yaml: Параметры модели (temperature, max_completion_tokens, etc.)
        - settings.yaml: Основная конфигурация (API ключи, proxy, etc.)
        
    Subclass Requirements:
        Каждый наследник должен реализовать:
        - analyze(candidate_data, requirements, context) -> AgentReport
        
    Error Handling:
        - Exponential backoff для OpenAI API вызовов
        - Graceful degradation при ошибках конфигурации
        - Детальное логирование всех операций
        
    Performance Features:
        - AsyncOpenAI для неблокирующих вызовов
        - httpx.AsyncClient для HTTP соединений
        - Настраиваемые timeouts и retry policies
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logger
        
        # ЗАГРУЖАЕМ КОНФИГУРАЦИЮ ЧЕРЕЗ load_config()
        self.config = load_config()
        self.ai_config = self.config.get("ai_analysis", {})
        
        # ЗАГРУЖАЕМ ПРОМПТЫ И НАСТРОЙКИ АГЕНТОВ
        self._load_prompts()
        self._load_agent_configs()
        
        # НАСТРАИВАЕМ СОВРЕМЕННЫЙ OPENAI КЛИЕНТ С ПРОКСИ
        self._setup_modern_openai_client()
    
    def _load_prompts(self):
        """Загружает промпты агентов из YAML с относительными путями"""
        try:
            # Пробуем несколько вариантов путей
            possible_paths = [
                "ai_analysis/agent_prompts.yaml",  # Локально
                "/app/ai_analysis/agent_prompts.yaml"  # Docker
            ]
            
            for prompts_path in possible_paths:
                if os.path.exists(prompts_path):
                    with open(prompts_path, 'r', encoding='utf-8') as f:
                        self.prompts = yaml.safe_load(f)
                        self.logger.info(f"✅ Промпты загружены для {self.name} из {prompts_path}")
                        return
            
            self.logger.warning(f"⚠️ Файл промптов не найден для {self.name}, используем значения по умолчанию")
            self.prompts = {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки промптов для {self.name}: {e}")
            self.prompts = {}
    
    def _load_agent_configs(self):
        """Загружает конфигурации агентов из agent_configs.yaml с относительными путями"""
        try:
            # Пробуем несколько вариантов путей
            possible_paths = [
                "ai_analysis/agent_configs.yaml",  # Локально
                "/app/ai_analysis/agent_configs.yaml"  # Docker
            ]
            
            for configs_path in possible_paths:
                if os.path.exists(configs_path):
                    with open(configs_path, 'r', encoding='utf-8') as f:
                        self.agent_configs = yaml.safe_load(f)
                        self.logger.info(f"✅ Конфигурации агентов загружены для {self.name} из {configs_path}")
                        return
            
            self.logger.warning(f"⚠️ Файл конфигураций агентов не найден для {self.name}, используем значения по умолчанию")
            self.agent_configs = {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки конфигураций агентов для {self.name}: {e}")
            self.agent_configs = {}
    

    
    def _setup_modern_openai_client(self):
        """Настраивает современный OpenAI клиент с правильной поддержкой прокси"""
        try:
            # Получаем API ключ
            api_key = self.ai_config.get("openai_api_key")
            if not api_key:
                self.logger.warning(f"⚠️ OPENAI_API_KEY не установлен для {self.name}")
            
            # Настройка HTTP прокси из конфигурации
            proxy_config = self.ai_config.get("proxy", {})
            proxy_enabled = proxy_config.get("enabled", False)
            
            if proxy_enabled:
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
                    
                    self.logger.info(f"🌐 OpenAI клиент с прокси инициализирован для {self.name}: {proxy_host}:{proxy_port}")
                else:
                    # Если настройки прокси неполные, используем обычный клиент
                    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                    self.logger.warning(f"⚠️ Прокси включен для {self.name}, но настройки неполные. Используется прямое соединение.")
            else:
                # Обычный httpx клиент без прокси для AsyncOpenAI
                http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                self.logger.info(f"🔗 OpenAI клиент без прокси инициализирован для {self.name}")
            
            # Инициализация AsyncOpenAI клиента для OpenRouter
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
                self.logger.info(f"🔄 OpenRouter AsyncOpenAI клиент для {self.name}: {base_url}")
                
                # Настройки для OpenRouter
                self.site_url = self.ai_config.get("site_url", "")
                self.site_name = self.ai_config.get("site_name", "CandidateRanking")
            else:
                # Старый OpenAI режим
                self.openai_client = AsyncOpenAI(
                    api_key=api_key,
                    http_client=http_client,
                    base_url=base_url if base_url != "https://openrouter.ai/api/v1" else None
                )
                self.site_url = ""
                self.site_name = ""
            
            # Параметры модели из конфигурации
            self.model = self.ai_config.get("model", "gpt-5-mini")
            self.max_completion_tokens = self.ai_config.get("max_completion_tokens", 3000)  # GPT-5 параметр для агентов
            self.temperature = self.ai_config.get("temperature", 0.0)
            
            # GPT-5 специфичные параметры
            gpt5_features = self.ai_config.get("gpt5_features", {})
            self.verbosity = gpt5_features.get("default_verbosity", "medium")
            self.reasoning_effort = gpt5_features.get("default_reasoning_effort", "medium")
            
            self.logger.info(f"✅ Современный AsyncOpenAI клиент настроен для {self.name} (модель: {self.model})")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка настройки современного AsyncOpenAI клиента для {self.name}: {e}")
            # Создаем базовый OpenRouter клиент как fallback
            openrouter_key = self.ai_config.get("openrouter_api_key", "")
            base_url = self.ai_config.get("base_url", "https://openrouter.ai/api/v1")
            
            self.openai_client = AsyncOpenAI(
                api_key=openrouter_key,
                base_url=base_url
            )
            self.model = self.ai_config.get("model", "openai/gpt-5-chat")
            self.max_tokens = self.ai_config.get("max_tokens", 16000)
            self.temperature = self.ai_config.get("temperature", 0.0)
            self.site_url = self.ai_config.get("site_url", "")
            self.site_name = self.ai_config.get("site_name", "CandidateRanking")
    
    def _get_agent_config(self, config_key: str, default_value: Any = None):
        """Получает конфигурацию агента по ключу"""
        agent_name = self.name.lower().replace('агент ', '').replace(' ', '_')
        
        # Пробуем разные варианты имени агента
        possible_names = [
            f"{agent_name}_agent",
            agent_name,
            f"agent_{agent_name}",
            self.name.lower().replace(' ', '_')
        ]
        
        for name in possible_names:
            if name in self.agent_configs.get('agents', {}):
                agent_config = self.agent_configs['agents'][name]
                return agent_config.get(config_key, default_value)
        
        return default_value
    
    def _get_agent_prompts(self, agent_key: str):
        """Получает промпты агента по ключу"""
        try:
            # DEBUG удалено: self.logger.error(f"🔍 DEBUG _get_agent_prompts: ищем ключ {agent_key}")
            # DEBUG удалено: self.logger.error(f"🔍 DEBUG _get_agent_prompts: доступные ключи в prompts: {list(self.prompts.keys())}")
            
            result = self.prompts.get(agent_key, {})
            # DEBUG удалено: self.logger.error(f"🔍 DEBUG _get_agent_prompts: возвращаем результат типа {type(result)}: {result}")
            
            if not isinstance(result, dict):
                self.logger.error(f"❌ ОШИБКА _get_agent_prompts: результат не словарь!")
                return {}
            
            return result
        except Exception as e:
            import traceback
            self.logger.error(f"❌ ОШИБКА в _get_agent_prompts: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            return {}
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3, base=1, max_value=5)
    async def _call_gpt(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Вызывает современный AsyncOpenAI клиент для анализа с retry логикой"""
        try:
            self.logger.info(f"🤖 {self.name} отправляет запрос к GPT...")
            
            # Подготавливаем параметры для OpenRouter
            extra_headers = {}
            if hasattr(self, 'site_url') and self.site_url:
                extra_headers["HTTP-Referer"] = self.site_url
            if hasattr(self, 'site_name') and self.site_name:
                extra_headers["X-Title"] = self.site_name

            # Используем AsyncOpenAI клиент с поддержкой OpenRouter и GPT-5
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
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,  # GPT-5 использует max_completion_tokens
                response_format={"type": "json_object"},
                extra_headers=extra_headers if extra_headers else {},
                # GPT-5 параметры передаются напрямую
                verbosity=gpt5_params.get("verbosity", "medium") if gpt5_params else "medium",
                reasoning_effort=gpt5_params.get("reasoning_effort", "medium") if gpt5_params else "medium"
            )
            
            content = response.choices[0].message.content
            self.logger.info(f"✅ {self.name} получил ответ от GPT (модель: {self.model})")
            
            # ПАРСИМ JSON ОТВЕТ
            try:
                result = json.loads(content)
                self.logger.info(f"✅ {self.name} успешно получил JSON ответ с оценкой {result.get('score', 'N/A')}")
                return result
            except json.JSONDecodeError:
                # Если не JSON, возвращаем как текст с подсказкой для парсинга
                self.logger.warning(f"⚠️ GPT вернул не JSON ответ для {self.name}, парсим как текст")
                return {
                    "analysis": content, 
                    "score": 50.0,
                    "summary": f"Анализ от {self.name}",
                    "details": [content[:200] + "..." if len(content) > 200 else content],
                    "red_flags": [],
                    "positive_points": [],
                    "recommendations": []
                }
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка вызова современного AsyncOpenAI клиента в {self.name}: {e}")
            return {
                "error": str(e), 
                "score": 0.0,
                "summary": f"Ошибка GPT в {self.name}",
                "details": [f"Техническая ошибка: {str(e)}"],
                "red_flags": ["Ошибка вызова GPT"],
                "positive_points": [],
                "recommendations": ["Требуется повторный анализ"]
            }
    
    @abstractmethod
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        """Анализирует кандидата и возвращает отчет"""
        pass
    
    def _create_report(self, score: float, status: AgentStatus, summary: str,
                      details: List[str] = None, red_flags: List[str] = None,
                      positive_points: List[str] = None, recommendations: List[str] = None,
                      processing_time: float = 0.0) -> AgentReport:
        """Создает стандартный отчет агента"""
        return AgentReport(
            agent_name=self.name,
            score=score,
            status=status,
            summary=summary,
            details=details or [],
            red_flags=red_flags or [],
            positive_points=positive_points or [],
            recommendations=recommendations or [],
            processing_time=processing_time,
            timestamp=datetime.now()
        )

    def _safe_get_experience_years(self, candidate_data: Dict[str, Any]) -> float:
        """Безопасно извлекает и суммирует опыт работы из структуры HH.ru API."""
        import re
        from datetime import datetime
        
        try:
            # 1. Проверяем основные поля опыта из HH.ru API
            # Поле total_experience может быть строкой "1 год 8 месяцев" или объектом {"months": N}
            if "total_experience" in candidate_data:
                exp = candidate_data["total_experience"]
                
                # ПОЛНЫЕ ДАННЫЕ HH.ru: total_experience = {"months": 18}
                if isinstance(exp, dict) and "months" in exp:
                    months = exp.get("months", 0)
                    if isinstance(months, (int, float)) and months > 0:
                        return round(months / 12, 1)
                
                elif isinstance(exp, str) and any(word in exp.lower() for word in ["год", "мес", "лет"]):
                    # Парсим строку типа "1 год 8 месяцев"
                    years = re.findall(r'(\d+)\s*(?:год|лет)', exp)
                    months = re.findall(r'(\d+)\s*мес', exp)
                    total_months = (int(years[0]) * 12 if years else 0) + (int(months[0]) if months else 0)
                    if total_months > 0:
                        return round(total_months / 12, 1)
                        
                elif isinstance(exp, (int, float)) and exp > 0:
                    return float(exp)
            
            # 2. БАЗОВЫЕ ДАННЫЕ HH.ru: experience может быть {'months': N}
            experience = candidate_data.get("experience", [])
            if isinstance(experience, dict) and "months" in experience:
                # Базовые данные HH.ru API: experience = {'months': 33}
                months = experience.get("months", 0)
                if isinstance(months, (int, float)) and months > 0:
                    return round(months / 12, 1)
            
            # 3. Проверяем массив experience (детальный опыт работы из полных данных)
            elif isinstance(experience, list) and experience:
                total_months = 0
                
                for job in experience:
                    if isinstance(job, dict):
                        # Попробуем извлечь даты начала и конца работы
                        start_date = job.get("start", "") or job.get("start_date", "")
                        end_date = job.get("end", "") or job.get("end_date", "")
                        
                        # Если есть период в виде строки (например, "Июл 2024 - сейчас 1 год 2 мес")
                        period_text = job.get("period", "") or str(job.get("description", ""))
                        if "год" in period_text or "мес" in period_text:
                            years = re.findall(r'(\d+)\s*(?:год|лет)', period_text)
                            months = re.findall(r'(\d+)\s*мес', period_text)
                            job_months = (int(years[0]) * 12 if years else 0) + (int(months[0]) if months else 0)
                            total_months += job_months
                            continue
                        
                        # Если есть четкие даты, вычисляем разность
                        if start_date and end_date:
                            try:
                                if end_date.lower() in ["сейчас", "настоящее время", "по настоящее время"]:
                                    end_date = datetime.now().strftime("%Y-%m")
                                
                                # Простой парсинг дат (без сложных библиотек)
                                start_parts = re.findall(r'\d+', str(start_date))
                                end_parts = re.findall(r'\d+', str(end_date))
                                
                                if len(start_parts) >= 2 and len(end_parts) >= 2:
                                    start_year, start_month = int(start_parts[-1]), int(start_parts[-2])
                                    end_year, end_month = int(end_parts[-1]), int(end_parts[-2])
                                    
                                    job_months = (end_year - start_year) * 12 + (end_month - start_month)
                                    total_months += max(0, job_months)
                                    
                            except Exception:
                                # Если не удалось парсить даты, пропускаем
                                pass
                
                if total_months > 0:
                    return round(total_months / 12, 1)
            
            # 4. Ищем в поле title указания на опыт
            title = candidate_data.get("title", "")
            if title and any(word in title.lower() for word in ["опыт", "год", "лет"]):
                years = re.findall(r'(\d+)\s*(?:год|лет)', title)
                months = re.findall(r'(\d+)\s*мес', title)
                if years or months:
                    total_months = (int(years[0]) * 12 if years else 0) + (int(months[0]) if months else 0)
                    return round(total_months / 12, 1)
            
            return 0.0
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ ОШИБКА в _safe_get_experience_years: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            return 0.0

    def _safe_get_languages(self, candidate_data: Dict[str, Any]) -> str:
        """Безопасно извлекает и форматирует языки из различных источников."""
        try:
            lang_list = []
            
            # 1. ОСНОВНОЙ ИСТОЧНИК: поле languages или language 
            languages = candidate_data.get("languages", candidate_data.get("language", []))
            
            if isinstance(languages, list) and languages:
                for lang in languages:
                    if isinstance(lang, dict):
                        name = lang.get("name", "")
                        level_data = lang.get("level", {})
                        if isinstance(level_data, dict):
                            level = level_data.get("name", "")
                        else:
                            level = str(level_data) if level_data else ""
                        lang_list.append(f"{name} ({level})" if level else name)
                    elif isinstance(lang, str):
                        lang_list.append(lang)
            
            # 2. БАЗОВЫЕ ДАННЫЕ: поиск языков в title и описании
            if not lang_list:
                title = candidate_data.get("title", "")
                about = candidate_data.get("about", "")
                
                # Простой поиск упоминаний языков
                language_keywords = ["русский", "английский", "немецкий", "французский", "испанский", "китайский", "japanese"]
                level_keywords = ["a1", "a2", "b1", "b2", "c1", "c2", "начинающий", "средний", "продвинутый", "свободно"]
                
                import re
                text_to_search = f"{title} {about}".lower()
                
                for lang_keyword in language_keywords:
                    if lang_keyword in text_to_search:
                        # Ищем уровень рядом с языком
                        pattern = f"{lang_keyword}[^a-zA-Zа-яё]*({'|'.join(level_keywords)})"
                        match = re.search(pattern, text_to_search, re.IGNORECASE)
                        if match:
                            lang_list.append(f"{lang_keyword.title()} ({match.group(1)})")
                        else:
                            lang_list.append(lang_keyword.title())
            
            result = ", ".join(filter(None, lang_list)) if lang_list else "Не указано"
            return result
        except Exception as e:
            import traceback
            self.logger.error(f"❌ ОШИБКА в _safe_get_languages: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            return "Не указано"

    def _prepare_raw_data_for_gpt(self, candidate_data: Dict[str, Any]) -> str:
        """Подготавливает чистые данные HH.ru для анализа GPT без хардкода."""
        try:
            import json
            return json.dumps(candidate_data, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Ошибка подготовки данных: {e}")
            return str(candidate_data)
    
    def _universal_agent_analyze(self, agent_type: str, candidate_data: Dict[str, Any], 
                                position_requirements: Dict[str, Any], 
                                additional_context: Optional[Dict[str, Any]] = None) -> str:
        """Универсальная функция анализа для всех агентов с сырым JSON."""
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts(agent_type)
            system_prompt = agent_prompts.get('system_prompt', f'Анализируй данные для {agent_type}.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - УНИВЕРСАЛЬНЫЙ ПОДХОД
            try:
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    search_query=search_query,
                    position_requirements_json=position_requirements_json
                )
            except KeyError:
                # Совместимость со старыми промптами - добавляем JSON в конец
                try:
                    # ИЗВЛЕКАЕМ РЕАЛЬНЫЕ ДАННЫЕ ИЗ JSON для старых промптов
                    import re
                    variables = re.findall(r'\{(\w+)\}', analysis_prompt_template)
                    format_dict = {}
                    
                    # Заполняем переменные РЕАЛЬНЫМИ данными из JSON
                    for var in variables:
                        if var == "candidate_skills":
                            skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                            format_dict[var] = ", ".join([s.get("name", str(s)) if isinstance(s, dict) else str(s) for s in skills]) if skills else "Не указано"
                        elif var == "experience_years":
                            exp = candidate_data.get("total_experience", {})
                            if isinstance(exp, dict) and "months" in exp:
                                format_dict[var] = f"{exp['months'] / 12:.1f}"
                            else:
                                format_dict[var] = str(exp) if exp else "0"
                        elif var == "required_experience":
                            min_exp = position_requirements.get("min_experience_years", 0)
                            max_exp = position_requirements.get("max_experience_years")
                            exp_desc = position_requirements.get("experience_description", "")
                            if max_exp and max_exp != min_exp:
                                format_dict[var] = f"{min_exp}-{max_exp} лет ({exp_desc})"
                            elif exp_desc:
                                format_dict[var] = f"{exp_desc} (мин. {min_exp} лет)"
                            else:
                                format_dict[var] = f"{min_exp} лет"
                        elif var == "required_skills":
                            skills = position_requirements.get("required_skills", [])
                            format_dict[var] = ", ".join(skills) if skills else "Не указано"
                        elif var == "total_experience":
                            exp = candidate_data.get("total_experience", {})
                            if isinstance(exp, dict) and "months" in exp:
                                format_dict[var] = f"{exp['months']} месяцев ({exp['months'] / 12:.1f} лет)"
                            else:
                                format_dict[var] = str(exp) if exp else "Не указано"
                        elif var == "min_experience_years":
                            min_exp = position_requirements.get("min_experience_years", 0)
                            max_exp = position_requirements.get("max_experience_years")
                            exp_desc = position_requirements.get("experience_description", "")
                            if max_exp and max_exp != min_exp:
                                format_dict[var] = f"{min_exp}-{max_exp}"
                            elif exp_desc and "до" in exp_desc:
                                format_dict[var] = exp_desc.replace("От ", "").replace(" лет", "")
                            else:
                                format_dict[var] = str(min_exp)
                            self.logger.info(f"🔍 ОТЛАДКА: min_experience_years = {format_dict[var]}, min={min_exp}, max={max_exp}, desc={exp_desc}")
                        elif var == "max_experience_years":
                            format_dict[var] = str(position_requirements.get("max_experience_years", "неограничен"))
                        elif var == "experience_description":
                            format_dict[var] = position_requirements.get("experience_description", "Требования не указаны")
                        elif var == "position_requirements_json":
                            format_dict[var] = position_requirements_json
                        elif var == "candidate_data_json":
                            format_dict[var] = candidate_data_json
                        else:
                            # Для остальных переменных - ищем в данных кандидата
                            value = candidate_data.get(var, f"НАЙТИ {var.upper()} В JSON")
                            format_dict[var] = str(value)
                    
                    user_prompt = analysis_prompt_template.format(**format_dict)
                except Exception as e:
                    user_prompt = analysis_prompt_template
                
                user_prompt += f"\n\nСЫРЫЕ ДАННЫЕ КАНДИДАТА (JSON):\n{candidate_data_json}"
                user_prompt += f"\n\nТРЕБОВАНИЯ (JSON):\n{position_requirements_json}"
            
            return system_prompt, user_prompt
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка универсального анализа: {e}")
            return "Анализируй данные кандидата.", f"ДАННЫЕ: {candidate_data_json}"
    
    def _safe_get_education(self, candidate_data: Dict[str, Any]) -> str:
        """Безопасно извлекает информацию об образовании из различных источников."""
        try:
            education_info = []
            
            # 1. ПОЛЕ education согласно HH.ru API (массив объектов образования)
            education = candidate_data.get("education", [])
            if isinstance(education, list):
                for edu_item in education:
                    if isinstance(edu_item, dict):
                        name = edu_item.get("name", "")  # Название учебного заведения
                        year = edu_item.get("year", "")   # Год окончания
                        level = edu_item.get("level", "")  # Уровень образования
                        
                        if name:
                            if year and level:
                                education_info.append(f"{level}: {name} ({year})")
                            elif year:
                                education_info.append(f"{name} ({year})")
                            elif level:
                                education_info.append(f"{level}: {name}")
                            else:
                                education_info.append(name)
            
            # 2. БАЗОВЫЕ ДАННЫЕ: поиск образования в title и других полях
            if not education_info:
                title = candidate_data.get("title", "")
                about = candidate_data.get("about", "")
                
                # Ищем уровни образования
                edu_keywords = ["bachelor", "master", "phd", "доктор", "магистр", "бакалавр", "специалист", 
                               "высшее", "среднее", "университет", "институт", "колледж", "техникум"]
                
                text_to_search = f"{title} {about}".lower()
                found_education = []
                
                for edu_word in edu_keywords:
                    if edu_word in text_to_search:
                        found_education.append(edu_word.title())
                
                if found_education:
                    education_info.append(f"Образование: {', '.join(set(found_education))}")
            
            # 3. Проверяем опыт работы на предмет упоминания образования
            last_work = candidate_data.get("last_work", {})
            if isinstance(last_work, dict):
                work_name = last_work.get("name", "")
                position = last_work.get("position", "")
                description = last_work.get("description", "")
                
                work_text = f"{work_name} {position} {description}".lower()
                if any(edu_word in work_text for edu_word in ["университет", "институт", "колледж", "вуз", "образование", "школа"]):
                    education_info.append(f"Связь с образовательными учреждениями в опыте работы")
            
            # Формируем результат
            if education_info:
                result = ". ".join(education_info)
                self.logger.info(f"✅ Найдена информация об образовании: {result}")
                return result
            else:
                return "Не указано"
                
        except Exception as e:
            import traceback
            self.logger.error(f"❌ ОШИБКА в _safe_get_education: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            return "Не указано"

    def _safe_get_last_work(self, candidate_data: Dict[str, Any]) -> tuple[str, str]:
        """Безопасно извлекает последнее место работы."""
        experience = candidate_data.get("experience", [])
        if isinstance(experience, list) and experience:
            last_job = experience[0]
            if isinstance(last_job, dict):
                position = last_job.get("position", "Не указано")
                company = last_job.get("name", "Не указано")  # В HH.ru API компания называется "name"
                return position, company
        return "Не указано", "Не указано"

    def _safe_get_experience_description(self, candidate_data: Dict[str, Any]) -> str:
        """Безопасно извлекает детальное описание опыта работы из поля experience."""
        try:
            experience = candidate_data.get("experience", [])
            if isinstance(experience, list) and experience:
                # Берем последнюю (первую в списке) работу
                last_job = experience[0]
                if isinstance(last_job, dict):
                    description = last_job.get("description", "")
                    position = last_job.get("position", "")
                    company = last_job.get("name", "")
                    
                    # Формируем полное описание опыта
                    full_description = f"Позиция: {position} в {company}. "
                    if description:
                        full_description += f"Описание: {description}"
                    return full_description
            
            return "Не указано"
        except Exception as e:
            import traceback
            self.logger.error(f"❌ ОШИБКА в _safe_get_experience_description: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            return "Не указано"

    def _safe_get_skills_with_levels(self, candidate_data: Dict[str, Any]) -> str:
        """Безопасно извлекает навыки с указанием уровней владения из различных полей резюме."""
        try:
            # Проверяем все возможные источники навыков
            all_skills = []
            
            # 1. Проверяем skills (список навыков из Candidate модели)
            skills = candidate_data.get("skills", [])
            if isinstance(skills, list) and skills:
                all_skills.extend([skill for skill in skills if skill])
                self.logger.info(f"✅ Найдены навыки в поле skills: {len(skills)} навыков")
            
            # 2. Проверяем verified_skills (подтвержденные навыки)
            verified_skills = candidate_data.get("verified_skills", [])
            if isinstance(verified_skills, list) and verified_skills:
                verified_skills_formatted = [f"{skill} (подтвержден)" for skill in verified_skills]
                all_skills.extend(verified_skills_formatted)
                self.logger.info(f"✅ Найдены подтвержденные навыки: {len(verified_skills)} навыков")
            
            # 3. ГЛАВНОЕ ПОЛЕ: skill_set (массив строк навыков согласно HH.ru API)
            skill_set = candidate_data.get("skill_set", [])
            if isinstance(skill_set, list):
                for skill in skill_set:
                    if isinstance(skill, str):
                        all_skills.append(skill)
                    elif isinstance(skill, dict) and "name" in skill:
                        all_skills.append(skill["name"])

            # 4. Проверяем поле skills как строку (альтернативный источник)
            if isinstance(candidate_data.get("skills"), str) and candidate_data.get("skills"):
                all_skills.append(f"Навыки: {candidate_data.get('skills')}")
            
            # 5. Ищем информацию в last_work description (технологии из последней работы)
            last_work = candidate_data.get("last_work", {})
            if isinstance(last_work, dict):
                description = last_work.get("description", "")
                if description and any(tech in description.lower() for tech in ["javascript", "react", "typescript", "python", "java", "php", "css", "html"]):
                    all_skills.append(f"Опыт работы с технологиями: {description[:200]}")

            # 6. Ищем информацию в experience (если есть детальное описание)
            experience = candidate_data.get("experience", {})
            if isinstance(experience, dict):
                # Проверяем поле description в опыте
                exp_description = experience.get("description", "")
                if exp_description and any(tech in exp_description.lower() for tech in ["javascript", "react", "typescript", "python", "java", "php"]):
                    all_skills.append(f"Технологии из опыта: {exp_description[:150]}")

            # Убираем дубликаты и формируем результат
            unique_skills = list(dict.fromkeys(all_skills))  # Сохраняем порядок, убираем дубликаты
            result = ". ".join(filter(None, unique_skills))
            
            if result:
                self.logger.info(f"✅ Итого извлечено навыков: {len(unique_skills)} из различных источников")
            
            return result if result else "Не указано"
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ ОШИБКА в _safe_get_skills_with_levels: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            return "Не указано"

    def _safe_get_about_me(self, candidate_data: Dict[str, Any]) -> str:
        """Безопасно извлекает информацию 'Обо мне' из различных источников."""
        try:
            about_info = []
            
            # 1. Проверяем поле about (основной источник)
            about = candidate_data.get("about", "")
            if about and isinstance(about, str):
                about_info.append(about)
                self.logger.info(f"✅ Найдена информация 'Обо мне': {len(about)} символов")
            
            # 2. Проверяем поле title как источник информации о кандидате
            title = candidate_data.get("title", "")
            if title:
                about_info.append(f"Позиция: {title}")
            
            # 3. Проверяем описание последней работы
            last_work = candidate_data.get("last_work", {})
            if isinstance(last_work, dict):
                description = last_work.get("description", "")
                if description:
                    about_info.append(f"Опыт работы: {description[:300]}...")
            
            # 4. Проверяем опыт работы на полезную информацию
            experience = candidate_data.get("experience", {})
            if isinstance(experience, dict):
                # Проверяем описание или название компании
                exp_description = experience.get("description", "")
                company = experience.get("company", "")
                if exp_description:
                    about_info.append(f"Профессиональный опыт: {exp_description[:200]}...")
                elif company:
                    about_info.append(f"Работал в: {company}")
            
            # 5. Проверяем навыки как источник информации о профиле
            skills = candidate_data.get("skills", [])
            if isinstance(skills, list) and skills:
                skills_summary = ", ".join(skills[:5])  # Первые 5 навыков
                if len(skills) > 5:
                    skills_summary += f" и еще {len(skills) - 5} навыков"
                about_info.append(f"Ключевые навыки: {skills_summary}")
            
            # Формируем результат
            if about_info:
                result = ". ".join(about_info)
                return result
            else:
                return "Информация отсутствует"
                
        except Exception as e:
            import traceback
            self.logger.error(f"❌ ОШИБКА в _safe_get_about_me: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            return "Информация отсутствует"
    
    def _get_status_by_score(self, score: float) -> AgentStatus:
        """Определяет статус на основе оценки"""
        if score >= 80:
            return AgentStatus.PASS
        elif score >= 60:
            return AgentStatus.WARNING
        else:
            return AgentStatus.FAIL
class RequirementsAgent(BaseAgent):
    """Агент анализа соответствия требованиям"""
    
    def __init__(self):
        super().__init__("Агент Анализа Требований")
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts('requirements_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Анализируй соответствие кандидатов требованиям.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ 
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - ПРАВИЛЬНО ИЗВЛЕКАЕМ ВСЕ НУЖНЫЕ ПЕРЕМЕННЫЕ
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ОТЛАДКА RequirementsAgent: промпт требует переменные: {required_vars}")
            
            # ПОДГОТАВЛИВАЕМ ВСЕ ВОЗМОЖНЫЕ ПЕРЕМЕННЫЕ ИЗ ДАННЫХ КАНДИДАТА
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Извлекаем дополнительные переменные из candidate_data
            if 'total_experience' in required_vars and 'total_experience' in candidate_data:
                format_vars['total_experience'] = json.dumps(candidate_data['total_experience'], ensure_ascii=False)
            
            if 'skills' in required_vars:
                skills = candidate_data.get('skill_set', []) or candidate_data.get('skills', [])
                format_vars['skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'about' in required_vars:
                format_vars['about'] = candidate_data.get('about', '')
            
            if 'experience' in required_vars:
                format_vars['experience'] = json.dumps(candidate_data.get('experience', []), ensure_ascii=False)
            
            if 'education' in required_vars:
                format_vars['education'] = json.dumps(candidate_data.get('education', []), ensure_ascii=False)
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ УСПЕШНО СФОРМИРОВАН ПОЛНЫЙ ПРОМПТ со всеми переменными: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось найти переменную {ke} в данных кандидата!")
                self.logger.error(f"🔍 Доступные ключи в candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Подготовленные переменные: {list(format_vars.keys())}")
                # Используем базовый промпт с JSON данными
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
            
            # ВЫЗЫВАЕМ GPT С ПРОМПТАМИ ИЗ ФАЙЛА
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # ОБРАБАТЫВАЕМ ОТВЕТ GPT
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", "Анализ соответствия требованиям")
            
            # БЕЗОПАСНАЯ ОБРАБОТКА details - конвертируем dict в string если нужно
            raw_details = gpt_result.get("details", [])
            details = []
            for item in raw_details:
                if isinstance(item, dict):
                    # Если GPT вернул объект, конвертируем в строку
                    details.append(f"{item.get('criterion', 'Критерий')}: {item.get('assessment', str(item))}")
                else:
                    details.append(str(item))
            
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка в {self.name}: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary="Ошибка анализа требований",
                details=[f"Техническая ошибка: {str(e)}"],
                processing_time=processing_time
            )

class ResumeAnalysisAgent(BaseAgent):
    """Агент анализа качества резюме как документа"""
    
    def __init__(self):
        super().__init__("Агент Анализа Резюме")
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts('resume_analysis_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Анализируй качество резюме как документа.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - ИЗВЛЕКАЕМ ВСЕ НУЖНЫЕ ПЕРЕМЕННЫЕ  
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ОТЛАДКА ResumeAnalysisAgent: промпт требует переменные: {required_vars}")
            
            # ПОДГОТАВЛИВАЕМ ВСЕ ВОЗМОЖНЫЕ ПЕРЕМЕННЫЕ ИЗ ДАННЫХ КАНДИДАТА
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Извлекаем дополнительные переменные из candidate_data для совместимости
            if 'about_section' in required_vars or 'about' in required_vars:
                about = candidate_data.get("about", "")
                format_vars['about_section'] = about or "Раздел 'О себе' не заполнен"
                format_vars['about'] = about
            
            if 'skills_list' in required_vars or 'skills' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                skills_text = ", ".join(skills) if isinstance(skills, list) else str(skills)
                format_vars['skills_list'] = skills_text or "Навыки не указаны"
                format_vars['skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'job_title' in required_vars:
                format_vars['job_title'] = candidate_data.get("title", "")
            
            if 'experience_description' in required_vars or 'experience' in required_vars:
                experience = candidate_data.get("experience", [])
                experience_text = ""
                if isinstance(experience, list) and experience:
                    experience_text = "; ".join([f"{exp.get('position', '')} в {exp.get('company', '')}" for exp in experience[:3]])
                elif isinstance(experience, dict):
                    experience_text = f"{experience.get('position', '')} в {experience.get('company', '')}"
                format_vars['experience_description'] = experience_text or "Опыт работы не указан"
                format_vars['experience'] = json.dumps(experience, ensure_ascii=False)
            
            if 'work_experience' in required_vars:
                total_exp = candidate_data.get("total_experience", {})
                work_exp_text = f"{total_exp.get('years', 0)} лет опыта" if total_exp else "Опыт не указан"
                format_vars['work_experience'] = work_exp_text
            
            if 'education_info' in required_vars or 'education' in required_vars:
                education = candidate_data.get("education", [])
                education_text = ""
                if isinstance(education, list) and education:
                    education_text = "; ".join([f"{edu.get('name', '')} ({edu.get('year', '')})" for edu in education[:2]])
                format_vars['education_info'] = education_text or "Образование не указано"
                format_vars['education'] = json.dumps(education, ensure_ascii=False)
            
            if 'contact_info' in required_vars:
                format_vars['contact_info'] = "НЕ АНАЛИЗИРУЙ КОНТАКТЫ"
            
            if 'position_requirements' in required_vars:
                format_vars['position_requirements'] = position_requirements.get("position_type", "general")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ УСПЕШНО СФОРМИРОВАН ПОЛНЫЙ ПРОМПТ ResumeAnalysisAgent со всеми переменными: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ResumeAnalysisAgent: Не удалось найти переменную {ke}!")
                self.logger.error(f"🔍 Доступные ключи в candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Подготовленные переменные: {list(format_vars.keys())}")
                # Используем старую логику только в крайнем случае
                # Совместимость со старыми промптами
                # Извлекаем реальные данные из candidate_data
                about = candidate_data.get("about", "")
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                experience = candidate_data.get("experience", [])
                total_exp = candidate_data.get("total_experience", {})
                education = candidate_data.get("education", [])
                
                # Форматируем данные для промпта
                skills_text = ", ".join(skills) if isinstance(skills, list) else str(skills)
                experience_text = ""
                if isinstance(experience, list) and experience:
                    experience_text = "; ".join([f"{exp.get('position', '')} в {exp.get('company', '')}" for exp in experience[:3]])
                elif isinstance(experience, dict):
                    experience_text = f"{experience.get('position', '')} в {experience.get('company', '')}"
                
                work_exp_text = f"{total_exp.get('years', 0)} лет опыта" if total_exp else "Опыт не указан"
                education_text = ""
                if isinstance(education, list) and education:
                    education_text = "; ".join([f"{edu.get('name', '')} ({edu.get('year', '')})" for edu in education[:2]])
                
                user_prompt = analysis_prompt_template.format(
                    job_title=candidate_data.get("title", ""),
                    about_section=about or "Раздел 'О себе' не заполнен",
                    skills_list=skills_text or "Навыки не указаны",
                    experience_description=experience_text or "Опыт работы не указан",
                    work_experience=work_exp_text,
                    education_info=education_text or "Образование не указано",
                    contact_info="НЕ АНАЛИЗИРУЙ КОНТАКТЫ",
                    position_requirements=position_requirements.get("position_type", "general")
                )
                user_prompt += f"\n\nСЫРЫЕ ДАННЫЕ КАНДИДАТА (JSON):\n{candidate_data_json}"
            
            # ВЫЗЫВАЕМ GPT С ПРОМПТАМИ ИЗ ФАЙЛА
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # ОБРАБАТЫВАЕМ ОТВЕТ GPT
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", "Анализ качества резюме")
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка в {self.name}: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary="Ошибка анализа резюме",
                details=[f"Техническая ошибка: {str(e)}"],
                processing_time=processing_time
            )

class ExperienceAgent(BaseAgent):
    """Агент анализа профессионального опыта"""
    
    def __init__(self):
        super().__init__("Агент Профессионального Опыта")
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts('experience_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Анализируй профессиональный опыт кандидатов.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - ИЗВЛЕКАЕМ ВСЕ НУЖНЫЕ ПЕРЕМЕННЫЕ
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ОТЛАДКА ExperienceAgent: промпт требует переменные: {required_vars}")
            
            # ПОДГОТАВЛИВАЕМ ВСЕ ВОЗМОЖНЫЕ ПЕРЕМЕННЫЕ ИЗ ДАННЫХ КАНДИДАТА
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Извлекаем дополнительные переменные из candidate_data для совместимости
            if 'experience' in required_vars:
                format_vars['experience'] = json.dumps(candidate_data.get("experience", []), ensure_ascii=False)
            
            if 'total_experience' in required_vars:
                format_vars['total_experience'] = json.dumps(candidate_data.get("total_experience", {}), ensure_ascii=False)
            
            if 'position_type' in required_vars:
                format_vars['position_type'] = position_requirements.get("position_type", "technical")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ УСПЕШНО СФОРМИРОВАН ПОЛНЫЙ ПРОМПТ ExperienceAgent со всеми переменными: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ExperienceAgent: Не удалось найти переменную {ke}!")
                self.logger.error(f"🔍 Доступные ключи в candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Подготовленные переменные: {list(format_vars.keys())}")
                # Используем базовый промпт с JSON данными
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\nСЫРЫЕ ДАННЫЕ КАНДИДАТА (JSON):\n{candidate_data_json}"
            
            # ВЫЗЫВАЕМ GPT С ПРОМПТАМИ ИЗ ФАЙЛА
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # ОБРАБАТЫВАЕМ ОТВЕТ GPT
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", "Анализ профессионального опыта кандидата")
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка в {self.name}: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary="Ошибка анализа опыта",
                details=[f"Техническая ошибка: {str(e)}"],
                processing_time=processing_time
            )

class FormattingAgent(BaseAgent):
    """Агент анализа качества оформления"""
    
    def __init__(self):
        super().__init__("Агент Качества Оформления")
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts('formatting_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Анализируй качество оформления резюме.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - ИЗВЛЕКАЕМ ВСЕ НУЖНЫЕ ПЕРЕМЕННЫЕ
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ОТЛАДКА FormattingAgent: промпт требует переменные: {required_vars}")
            
            # ПОДГОТАВЛИВАЕМ ВСЕ ВОЗМОЖНЫЕ ПЕРЕМЕННЫЕ ИЗ ДАННЫХ КАНДИДАТА
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Извлекаем дополнительные переменные из candidate_data для совместимости
            if 'title_quality' in required_vars:
                title = candidate_data.get("title", "")
                format_vars['title_quality'] = title if title else "Заголовок/специализация не указана"
            
            if 'about_section' in required_vars:
                about = candidate_data.get("about", "")
                format_vars['about_section'] = about if about else "Раздел 'О себе' отсутствует"
            
            if 'skills_section' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                if isinstance(skills, list) and skills:
                    skills_analysis = f"Список навыков: {', '.join(skills[:10])}" + ("..." if len(skills) > 10 else "")
                elif isinstance(skills, str) and skills:
                    skills_analysis = f"Навыки: {skills[:200]}" + ("..." if len(skills) > 200 else "")
                else:
                    skills_analysis = "Навыки не указаны"
                format_vars['skills_section'] = skills_analysis
            
            if 'experience_section' in required_vars:
                experience = candidate_data.get("experience", [])
                if isinstance(experience, list) and experience:
                    exp_items = []
                    for exp in experience[:3]:
                        position = exp.get('position', '')
                        company = exp.get('company', '')
                        if position or company:
                            exp_items.append(f"{position} в {company}")
                    experience_analysis = "; ".join(exp_items) if exp_items else "Опыт работы указан без деталей"
                else:
                    experience_analysis = "Опыт работы не указан"
                format_vars['experience_section'] = experience_analysis
            
            if 'education_section' in required_vars:
                education = candidate_data.get("education", [])
                if isinstance(education, list) and education:
                    edu_items = []
                    for edu in education[:2]:
                        name = edu.get('name', '')
                        year = edu.get('year', '')
                        if name:
                            edu_items.append(f"{name}" + (f" ({year})" if year else ""))
                    education_analysis = "; ".join(edu_items) if edu_items else "Образование указано без деталей"
                else:
                    education_analysis = "Образование не указано"
                format_vars['education_section'] = education_analysis
            
            if 'contacts_quality' in required_vars:
                format_vars['contacts_quality'] = "НЕ АНАЛИЗИРУЙ КОНТАКТЫ"
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ УСПЕШНО СФОРМИРОВАН ПОЛНЫЙ ПРОМПТ FormattingAgent со всеми переменными: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА FormattingAgent: Не удалось найти переменную {ke}!")
                self.logger.error(f"🔍 Доступные ключи в candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Подготовленные переменные: {list(format_vars.keys())}")
                # Используем старую логику только в крайнем случае
                title = candidate_data.get("title", "")
                about = candidate_data.get("about", "")
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                experience = candidate_data.get("experience", [])
                education = candidate_data.get("education", [])
                
                title_analysis = title if title else "Заголовок/специализация не указана"
                about_analysis = about if about else "Раздел 'О себе' отсутствует"
                
                skills_analysis = ""
                if isinstance(skills, list) and skills:
                    skills_analysis = f"Список навыков: {', '.join(skills[:10])}" + ("..." if len(skills) > 10 else "")
                elif isinstance(skills, str) and skills:
                    skills_analysis = f"Навыки: {skills[:200]}" + ("..." if len(skills) > 200 else "")
                else:
                    skills_analysis = "Навыки не указаны"
                
                experience_analysis = ""
                if isinstance(experience, list) and experience:
                    exp_items = []
                    for exp in experience[:3]:
                        position = exp.get('position', '')
                        company = exp.get('company', '')
                        if position or company:
                            exp_items.append(f"{position} в {company}")
                    experience_analysis = "; ".join(exp_items) if exp_items else "Опыт работы указан без деталей"
                else:
                    experience_analysis = "Опыт работы не указан"
                
                education_analysis = ""
                if isinstance(education, list) and education:
                    edu_items = []
                    for edu in education[:2]:
                        name = edu.get('name', '')
                        year = edu.get('year', '')
                        if name:
                            edu_items.append(f"{name}" + (f" ({year})" if year else ""))
                    education_analysis = "; ".join(edu_items) if edu_items else "Образование указано без деталей"
                else:
                    education_analysis = "Образование не указано"
                
                user_prompt = analysis_prompt_template.format(
                    title_quality=title_analysis,
                    contacts_quality="НЕ АНАЛИЗИРУЙ КОНТАКТЫ",
                    about_section=about_analysis,
                    skills_section=skills_analysis,
                    experience_section=experience_analysis,
                    education_section=education_analysis
                )
                user_prompt += f"\n\nСЫРЫЕ ДАННЫЕ КАНДИДАТА (JSON):\n{candidate_data_json}"
            
            # ВЫЗЫВАЕМ GPT С ПРОМПТАМИ ИЗ ФАЙЛА
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # ОБРАБАТЫВАЕМ ОТВЕТ GPT
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", "Анализ качества оформления резюме")
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка в {self.name}: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary="Ошибка анализа оформления",
                details=[f"Техническая ошибка: {str(e)}"],
                processing_time=processing_time
            )

class AnomalyDetectionAgent(BaseAgent):
    """Агент детекции аномалий"""
    
    def __init__(self):
        super().__init__("Агент Детекции Аномалий")
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts('anomaly_detection_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Выявляй аномалии в данных кандидатов.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ОТЛАДКА: выводим точное содержимое промпта
            self.logger.debug(f"🔍 ОТЛАДКА AnomalyDetectionAgent analysis_prompt_template (первые 500 символов):")
            self.logger.debug(f"{analysis_prompt_template[:500]}")
            if '"score"' in analysis_prompt_template:
                self.logger.warning(f"❌ НАЙДЕН ПРОБЛЕМНЫЙ \"score\" В ПРОМПТЕ!")
            if '{"score"' in analysis_prompt_template:
                self.logger.warning(f"❌ НАЙДЕН ПРОБЛЕМНЫЙ {{\"score\" В ПРОМПТЕ!")
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - ИЗВЛЕКАЕМ ВСЕ НУЖНЫЕ ПЕРЕМЕННЫЕ
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ОТЛАДКА AnomalyDetectionAgent: промпт требует переменные: {required_vars}")
            
            # ПОДГОТАВЛИВАЕМ ВСЕ ВОЗМОЖНЫЕ ПЕРЕМЕННЫЕ ИЗ ДАННЫХ КАНДИДАТА
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Извлекаем дополнительные переменные из candidate_data для совместимости
            if 'candidate_age' in required_vars:
                age = candidate_data.get("age")
                format_vars['candidate_age'] = str(age) if age else "Возраст не указан"
            
            if 'experience_years' in required_vars:
                total_exp = candidate_data.get("total_experience", {})
                months = total_exp.get("months", 0) if total_exp else 0
                years = months / 12 if months else 0
                format_vars['experience_years'] = f"{years:.1f} лет" if years else "Опыт не указан"
            
            if 'skills_list' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                format_vars['skills_list'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'career_progression' in required_vars:
                experience = candidate_data.get("experience", [])
                format_vars['career_progression'] = json.dumps(experience, ensure_ascii=False) if experience else "[]"
            
            if 'education_timeline' in required_vars:
                education = candidate_data.get("education", [])
                format_vars['education_timeline'] = json.dumps(education, ensure_ascii=False) if education else "[]"
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ УСПЕШНО СФОРМИРОВАН ПОЛНЫЙ ПРОМПТ AnomalyDetectionAgent со всеми переменными: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА AnomalyDetectionAgent: Не удалось найти переменную {ke}!")
                self.logger.error(f"🔍 Доступные ключи в candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Подготовленные переменные: {list(format_vars.keys())}")
                # Используем базовый промпт с JSON данными
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\nСЫРЫЕ ДАННЫЕ КАНДИДАТА (JSON):\n{candidate_data_json}"
            
            # ВЫЗЫВАЕМ GPT С ПРОМПТАМИ ИЗ ФАЙЛА
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # ОБРАБАТЫВАЕМ ОТВЕТ GPT
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", "Анализ аномалий в данных кандидата")
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка в {self.name}: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary="Ошибка детекции аномалий",
                details=[f"Техническая ошибка: {str(e)}"],
                processing_time=processing_time
            )

class TechnicalSkillsAgent(BaseAgent):
    """Агент анализа технических навыков"""
    
    def __init__(self):
        super().__init__("Агент Технических Навыков")
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts('technical_skills_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Анализируй технические навыки кандидатов.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - ИЗВЛЕКАЕМ ВСЕ НУЖНЫЕ ПЕРЕМЕННЫЕ
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ОТЛАДКА TechnicalSkillsAgent: промпт требует переменные: {required_vars}")
            
            # ПОДГОТАВЛИВАЕМ ВСЕ ВОЗМОЖНЫЕ ПЕРЕМЕННЫЕ ИЗ ДАННЫХ КАНДИДАТА
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Извлекаем дополнительные переменные из candidate_data для совместимости
            if 'candidate_skills' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                format_vars['candidate_skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'required_technologies' in required_vars:
                format_vars['required_technologies'] = json.dumps(position_requirements.get("skills", []), ensure_ascii=False)
            
            if 'experience_level' in required_vars:
                total_exp = candidate_data.get("total_experience", {})
                format_vars['experience_level'] = f"{total_exp.get('months', 0)} месяцев" if total_exp else "Опыт не указан"
            
            if 'position_level' in required_vars:
                format_vars['position_level'] = position_requirements.get("level", "middle")
            
            if 'specialization' in required_vars:
                format_vars['specialization'] = candidate_data.get("title", "")
            
            if 'experience_description' in required_vars:
                experience = candidate_data.get("experience", [])
                experience_descriptions = []
                if isinstance(experience, list):
                    for exp in experience:
                        if exp.get('description'):
                            experience_descriptions.append(exp['description'])
                format_vars['experience_description'] = "; ".join(experience_descriptions[:3]) if experience_descriptions else "Описание опыта не указано"
            
            if 'position_type' in required_vars:
                format_vars['position_type'] = position_requirements.get("position_type", "technical")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ УСПЕШНО СФОРМИРОВАН ПОЛНЫЙ ПРОМПТ TechnicalSkillsAgent со всеми переменными: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА TechnicalSkillsAgent: Не удалось найти переменную {ke}!")
                self.logger.error(f"🔍 Доступные ключи в candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Подготовленные переменные: {list(format_vars.keys())}")
                # Используем базовый промпт с JSON данными
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\nСЫРЫЕ ДАННЫЕ КАНДИДАТА (JSON):\n{candidate_data_json}"
            
            # ВЫЗЫВАЕМ GPT С ПРОМПТАМИ ИЗ ФАЙЛА
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # ОБРАБАТЫВАЕМ ОТВЕТ GPT
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", "Анализ технических навыков")
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка в {self.name}: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary="Ошибка анализа технических навыков",
                details=[f"Техническая ошибка: {str(e)}"],
                processing_time=processing_time
            )

class SkillLevelAgent(BaseAgent):
    """Агент строгой оценки уровней владения навыками по стандартам HH.ru"""
    
    def __init__(self):
        super().__init__("Агент Оценки Уровня Навыков")
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # ПОЛУЧАЕМ ПРОМПТЫ ИЗ ФАЙЛА
            agent_prompts = self._get_agent_prompts('skill_level_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Строго оценивай уровни владения навыками.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', 'Анализируй данные кандидата: {candidate_data_json}')
            
            # ПОДГОТАВЛИВАЕМ ЧИСТЫЕ JSON ДАННЫЕ
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # ФОРМАТИРУЕМ ПРОМПТ - ИЗВЛЕКАЕМ ВСЕ НУЖНЫЕ ПЕРЕМЕННЫЕ
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ОТЛАДКА SkillLevelAgent: промпт требует переменные: {required_vars}")
            
            # ПОДГОТАВЛИВАЕМ ВСЕ ВОЗМОЖНЫЕ ПЕРЕМЕННЫЕ ИЗ ДАННЫХ КАНДИДАТА
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Извлекаем дополнительные переменные из candidate_data для совместимости
            if 'skills' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                format_vars['skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'experience' in required_vars:
                format_vars['experience'] = json.dumps(candidate_data.get("experience", []), ensure_ascii=False)
            
            if 'total_experience' in required_vars:
                format_vars['total_experience'] = json.dumps(candidate_data.get("total_experience", {}), ensure_ascii=False)
            
            if 'position_type' in required_vars:
                format_vars['position_type'] = position_requirements.get("position_type", "technical")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ УСПЕШНО СФОРМИРОВАН ПОЛНЫЙ ПРОМПТ SkillLevelAgent со всеми переменными: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА SkillLevelAgent: Не удалось найти переменную {ke}!")
                self.logger.error(f"🔍 Доступные ключи в candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Подготовленные переменные: {list(format_vars.keys())}")
                # Используем базовый промпт с JSON данными
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\nСЫРЫЕ ДАННЫЕ КАНДИДАТА (JSON):\n{candidate_data_json}"
            
            # ВЫЗЫВАЕМ GPT С ПРОМПТАМИ ИЗ ФАЙЛА
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # ОБРАБАТЫВАЕМ ОТВЕТ GPT
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", "Оценка уровня навыков")
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка в {self.name}: {e}")
            self.logger.error(f"🔍 ПОЛНЫЙ TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary="Ошибка анализа уровня навыков",
                details=[f"Техническая ошибка: {str(e)}"],
                processing_time=processing_time
            )