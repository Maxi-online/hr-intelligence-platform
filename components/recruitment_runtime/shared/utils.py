"""
Candidate Analysis - Shared Utilities

Common utilities and helpers for all microservices of the Candidate Analisis system.

This module provides the basic infrastructure used by all components:
- File-backed logic and stdout
- Upload YAML configuration with redefinition through env vars
- HTTP customer with retry logic and error handling
- Data parsing facilities (dates, salaries, currencies)
- Decorators for Error Processing

Core Components:
- setup_logging(): Logging settings for microservices
- load_config(): Loading YAML configuration with env overrides
HTTPClient: HTTP client with exponential repetitions
- Data parsers: parse_date(), parse_salary(), calculate_average_salary()
- Error handlers: handle_errors() decorator for FastAPI endpoints

Key Features:
- Cross-platform logging: Works for Docer and Locally
- Environment overrides: Redefinition of configuration through env vars
- Robst HTTP: Retry logic for external API
- Data normalization: Parsing and Normalization of HH API Data
- Error Resilience: Graceful handling errors without service falls

Logging Strategy:
- Always in stdout for Docker logs.
- Additional to files (if available)
- Graceful degration with read-only file systems
- Structured messages for monitoring

HTTP Client Features:
- Explicit replications at network errors
- Adjustable timeouts and max_retries
- Automatic exponential backoff
- Combination with microservices architecture

Configuration Management:
- YAML as a primary source
- Environment variables for override (Docker-friendly)
- Default values for graceful demobilization
- UTF-8 support for Russian-language seizures

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



# Logging settings
def setup_logging(service_name: str, level: str = "INFO"):
    """Logging settings for microservices.
    We write to stdout ** forever** and to the file if possible.
    If the catalog is mounted as read-only (often on Windows), FileHandler
    Ignore that the app does not hang at the start.
    """
    log_format = f'%(asctime)s - {service_name} - %(levelname)s - %(message)s'

    # Create SteamHandler with Unicode support for Windows
    stream_handler = logging.StreamHandler()
    # Set UTF-8 encoding to correctly display emoji
    if hasattr(stream_handler.stream, 'reconfigure'):
        try:
            stream_handler.stream.reconfigure(encoding='utf-8')
        except (AttributeError, OSError):
            pass  # Ignore errors if reconfigure is not available
    
    handlers = [stream_handler]

    log_path = f'logs/{service_name}.log'
    try:
        # Create a catalogue if it's available and available for recording.
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        handlers.append(file_handler)
    except (OSError, IOError) as e:
        # You can't fall - just warn and continue without a file logger
        print(f"[setup_logging] Warning: cannot open log file {log_path}: {e}", file=sys.stderr)

    logging.basicConfig(level=getattr(logging, level), format=log_format, handlers=handlers)
    return logging.getLogger(service_name)

# Upload configuration
def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Uploading of the YAML file configuration (strict YAML-only for requirements)).

    IMPORTANT: No override of variable environments. All settings
    (Keys, Proxies, Ports) should only be supplied to YAML.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = _resolve_settings_env(yaml.safe_load(file)) or {}
        return config
    except FileNotFoundError:
        logging.warning(f"The configuration file {config_path} not found, default values used")
        return get_default_config()
    except Exception as e:
        logging.error(f"Configuration Error: {e}")
        return get_default_config()

def get_default_config() -> Dict[str, Any]:
    'default configuration'
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
            "max_completion_tokens": 3000,  # GPT-5 parameter
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
            "session_timeout_hours": int(os.getenv("SESSION_TIMEOUT", "8"))  # 8 hours &apos; workday
        }
    }

# HTTP customer with retry logic
class HTTPClient:
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        'GET request with retry logic'
        return self._request_with_retry('GET', endpoint, params=params, headers=headers)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        'POST Request with Retri logic'
        return self._request_with_retry('POST', endpoint, data=data, headers=headers)
    
    def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        'Follow-up of the request with repeated attempts'
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}{endpoint}"
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # Explicit delay
        raise requests.exceptions.RequestException("Max retries exceeded")

# Decorator for Error Processing
def handle_errors(func):
    'Errors in the endpoints API'
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

# Dating facilities
def parse_date(date_str: str) -> datetime:
    'Parsing the dates from the line'
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        return datetime.now()

def get_date_range(days: int) -> tuple:
    'Collection of the date range'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

# Text processing facilities
def normalize_text(text: str) -> str:
    'Normalization of search text'
    if not text:
        return ""
    return text.lower().strip()

def calculate_text_similarity(text1: str, text2: str) -> float:
    'A simple calculation of the similarity of the text'
    if not text1 or not text2:
        return 0.0
    
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

# Pay-as-you-go utilities
def parse_salary(salary_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    'Sparking of data on wages'
    if not salary_data:
        return None
    
    return {
        "from": salary_data.get("from"),
        "to": salary_data.get("to"),
        "currency": salary_data.get("currency", "RUR"),
        "gross": salary_data.get("gross", True)
    }

def calculate_average_salary(salary_data: Dict[str, Any]) -> Optional[int]:
    'Calculation of average salary'
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

# Utilities for validation
def validate_age_range(age_from: Optional[int], age_to: Optional[int]) -> bool:
    'Age range validation'
    if age_from is not None and (age_from < 14 or age_from > 100):
        return False
    if age_to is not None and (age_to < 14 or age_to > 100):
        return False
    if age_from is not None and age_to is not None and age_from > age_to:
        return False
    return True

def validate_salary_range(salary: Optional[int]) -> bool:
    'Salary validation'
    if salary is not None and (salary < 0 or salary > 10000000):
        return False
    return True