"""
Candidate Analysis - Shared Utilities

Общие утилиты и хелперы для всех микросервисов системы Candidate Analysis.

Этот модуль предоставляет базовую инфраструктуру, используемую всеми компонентами:
- Логирование с поддержкой файлов и stdout
- Загрузка конфигурации из YAML с переопределением через env vars
- HTTP клиент с retry логикой и error handling
- Утилиты парсинга данных (даты, зарплаты, валюты)
- Декораторы для обработки ошибок

Core Components:
- setup_logging(): Настройка логирования для микросервисов
- load_config(): Загрузка YAML конфигурации с env overrides
- HTTPClient: HTTP клиент с экспоненциальными повторами
- Data parsers: parse_date(), parse_salary(), calculate_average_salary()
- Error handlers: handle_errors() декоратор для FastAPI endpoints

Key Features:
- Cross-platform logging: Работает в Docker и локально
- Environment overrides: Переопределение конфигурации через env vars
- Robust HTTP: Retry логика для внешних API
- Data normalization: Парсинг и нормализация данных HH API
- Error resilience: Graceful handling ошибок без падения сервисов

Logging Strategy:
- Всегда в stdout для Docker logs
- Дополнительно в файлы (если доступно)
- Graceful degradation при read-only файловых системах
- Структурированные сообщения для monitoring

HTTP Client Features:
- Экспоненциальные повторы при network errors
- Настраиваемые timeouts и max_retries
- Автоматический exponential backoff
- Совместимость с microservices architecture

Configuration Management:
- YAML как primary source
- Environment variables для override (Docker-friendly)
- Default values для graceful degradation
- UTF-8 support для русскоязычных конфигов

Author: Candidate Analysis Team
Version: 2.0.0 (Enhanced HTTP Client + Improved Config)
Last Updated: 2025-01-04
"""

import os
import yaml
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from functools import wraps
import time


def _resolve_settings_env(value):
    """Resolve required environment references in already parsed configuration."""
    import os
    import re
    if isinstance(value, dict):
        return {key: _resolve_settings_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_settings_env(item) for item in value]
    if not isinstance(value, str):
        return value
    match = re.fullmatch(r"\$\{([A-Z_][A-Z0-9_]*)(?::(int|float|bool))?\}", value)
    if match is None:
        return value
    name, kind = match.groups()
    content = os.environ.get(name)
    if content is None or not content.strip():
        raise RuntimeError(f"Required configuration variable is missing: {name}")
    if kind == "int":
        return int(content)
    if kind == "float":
        return float(content)
    if kind == "bool":
        if content.lower() not in {"true", "false", "1", "0"}:
            raise ValueError(f"Expected a boolean configuration variable: {name}")
        return content.lower() in {"true", "1"}
    return content



# Настройка логирования
def setup_logging(service_name: str, level: str = "INFO"):
    """Настройка логирования для микросервиса.
    Пишем в stdout **всегда** и в файл, если это возможно.
    Если каталог смонтирован как read-only (часто на Windows), то FileHandler
    игнорируется, чтобы приложение не зависало на старте.
    """
    log_format = f'%(asctime)s - {service_name} - %(levelname)s - %(message)s'

    # Создаем StreamHandler с поддержкой Unicode для Windows
    stream_handler = logging.StreamHandler()
    # Устанавливаем кодировку UTF-8 для корректного отображения эмодзи
    if hasattr(stream_handler.stream, 'reconfigure'):
        try:
            stream_handler.stream.reconfigure(encoding='utf-8')
        except (AttributeError, OSError):
            pass  # Игнорируем ошибки, если reconfigure недоступен
    
    handlers = [stream_handler]

    log_path = f'logs/{service_name}.log'
    try:
        # Создаём каталог, если он есть и доступен на запись
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        handlers.append(file_handler)
    except (OSError, IOError) as e:
        # Падать нельзя – просто предупреждаем и продолжаем без файлового логгера
        print(f"[setup_logging] Warning: cannot open log file {log_path}: {e}", file=sys.stderr)

    logging.basicConfig(level=getattr(logging, level), format=log_format, handlers=handlers)
    return logging.getLogger(service_name)

# Загрузка конфигурации
def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Загрузка конфигурации из YAML файла (строго YAML-only по требованиям).

    ВАЖНО: никаких override из переменных окружения. Все настройки
    (ключи, прокси, порты) должны задаваться исключительно в YAML.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = _resolve_settings_env(yaml.safe_load(file)) or {}
        return config
    except FileNotFoundError:
        logging.warning(f"Конфигурационный файл {config_path} не найден, используются значения по умолчанию")
        return get_default_config()
    except Exception as e:
        logging.error(f"Ошибка загрузки конфигурации: {e}")
        return get_default_config()

def get_default_config() -> Dict[str, Any]:
    """Конфигурация по умолчанию"""
    return {
        "hh_api": {
            "base_url": "https://api.hh.ru",
            "client_id": os.getenv("HH_CLIENT_ID", "M2RQEGT97Q1KF0L10IGDV1C6J88NJ8L2I3CEGJICLTDDKS1KEKG7LB5UD2A5Q3F7"),
            "client_secret": os.getenv("HH_CLIENT_SECRET", ""),
            "user_agent": os.environ["USER_AGENT"]
        },
        "services": {
            "gateway": {"port": 8000, "host": "0.0.0.0"},
            "search": {"port": 8001, "host": "0.0.0.0"},
            "ranking": {"port": 8002, "host": "0.0.0.0"},
            "hh_api": {"port": 8003, "host": "0.0.0.0"},
            "config": {"port": 8004, "host": "0.0.0.0"},
            "frontend": {"port": 8501, "host": "0.0.0.0"}
        },
        "ranking": {
            "weights": {
                "keyword_relevance": 0.4,
                "filter_match": 0.3,
                "recency": 0.2,
                "profile_completeness": 0.1
            }
        },
        "search": {
            "max_results": 100,
            "default_per_page": 20
        },
        "ai_analysis": {
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "base_url": "https://openrouter.ai/api/v1",
            "model": "gpt-5-mini",
            "max_completion_tokens": 3000,  # GPT-5 параметр
            "temperature": 0.0,
            "gpt5_features": {
                "default_verbosity": "medium",
                "default_reasoning_effort": "medium"
            }
        },
        "authentication": {
            "enabled": os.getenv("AUTH_ENABLED", "true").lower() == "true",
            "passwords": {
                "hr_manager": os.getenv("HR_MANAGER_PASSWORD", ""),
                "recruiter": os.getenv("RECRUITER_PASSWORD", ""),
                "admin": os.getenv("ADMIN_PASSWORD", "")
            },
            "session_timeout_hours": int(os.getenv("SESSION_TIMEOUT", "8"))  # 8 часов рабочий день
        }
    }

# HTTP клиент с retry логикой
class HTTPClient:
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """GET запрос с retry логикой"""
        return self._request_with_retry('GET', endpoint, params=params, headers=headers)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """POST запрос с retry логикой"""
        return self._request_with_retry('POST', endpoint, data=data, headers=headers)
    
    def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Выполнение запроса с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}{endpoint}"
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
        raise requests.exceptions.RequestException("Max retries exceeded")

# Декоратор для обработки ошибок
def handle_errors(func):
    """Декоратор для обработки ошибок в API endpoints"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Ошибка в {func.__name__}: {str(e)}")
            raise
    return wrapper

# Утилиты для работы с датами
def parse_date(date_str: str) -> datetime:
    """Парсинг даты из строки"""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        return datetime.now()

def get_date_range(days: int) -> tuple:
    """Получение диапазона дат"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

# Утилиты для работы с текстом
def normalize_text(text: str) -> str:
    """Нормализация текста для поиска"""
    if not text:
        return ""
    return text.lower().strip()

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Простой расчет схожести текста"""
    if not text1 or not text2:
        return 0.0
    
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

# Утилиты для работы с зарплатой
def parse_salary(salary_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Парсинг данных о зарплате"""
    if not salary_data:
        return None
    
    return {
        "from": salary_data.get("from"),
        "to": salary_data.get("to"),
        "currency": salary_data.get("currency", "RUR"),
        "gross": salary_data.get("gross", True)
    }

def calculate_average_salary(salary_data: Dict[str, Any]) -> Optional[int]:
    """Расчет средней зарплаты"""
    if not salary_data:
        return None
    
    salary_from = salary_data.get("from")
    salary_to = salary_data.get("to")
    
    if salary_from and salary_to:
        return (salary_from + salary_to) // 2
    elif salary_from:
        return salary_from
    elif salary_to:
        return salary_to
    
    return None

# Утилиты для валидации
def validate_age_range(age_from: Optional[int], age_to: Optional[int]) -> bool:
    """Валидация диапазона возраста"""
    if age_from is not None and (age_from < 14 or age_from > 100):
        return False
    if age_to is not None and (age_to < 14 or age_to > 100):
        return False
    if age_from is not None and age_to is not None and age_from > age_to:
        return False
    return True

def validate_salary_range(salary: Optional[int]) -> bool:
    """Валидация зарплаты"""
    if salary is not None and (salary < 0 or salary > 10000000):
        return False
    return True