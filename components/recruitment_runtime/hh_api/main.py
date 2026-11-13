"""
Candidate Analysis - HeadHunter API Integration Service

Сервис интеграции с HeadHunter.ru API для поиска и получения данных кандидатов.

Этот модуль обеспечивает надёжную интеграцию с внешним API HeadHunter, включая:
- OAuth 2.0 авторизацию с автоматическим обновлением токенов
- Устойчивые запросы с exponential backoff при ошибках
- Правильную обработку rate limiting (429, 503) 
- Детальную диагностику проблем для мониторинга
- Получение как базовых, так и детальных данных резюме

Key Features:
- OAuth 2.0 Flow: Полная поддержка авторизации HeadHunter
- Smart Retry Logic: Экспоненциальные повторы при 429/503 ошибках
- Token Management: Автоматическое обновление access_token
- Error Propagation: Корректная передача HTTP статусов
- Rate Limit Handling: Умная обработка лимитов API

API Endpoints:
- /search: Поиск кандидатов с фильтрами
- /resume/{id}: Получение детальных данных резюме
- /areas: Справочник регионов
- /oauth/authorize: Авторизация пользователя
- /oauth/refresh: Обновление access_token

Error Handling Strategy:
- 429 Too Many Requests: Retry с экспоненциальной задержкой
- 503 Service Unavailable: Retry + флаг rate_limit_exceeded
- 500 Internal Server Error: Прямая передача ошибки
- 401/403: Авторизационные ошибки
- Network errors: Graceful degradation

Performance & Reliability:
- Максимум 3 попытки для каждого запроса
- Jitter в задержках для избежания thundering herd
- Детальное логирование всех операций
- Правильная обработка timeouts

Author: Candidate Analysis Team
Version: 2.0.0 (Improved Error Handling & Token Management)
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import time

# Принудительно устанавливаем UTF-8 кодировку для всего приложения
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

# Устанавливаем кодировку для stdout/stderr
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import HealthResponse, SearchRequest, Candidate, VacancyTopRequest, VacancyTopResponse
from shared.utils import setup_logging, HTTPClient, parse_date, parse_salary, calculate_average_salary, load_config

# Настройка логирования
logger = setup_logging("hh-api-service")

app = FastAPI(
    title="HH API Service",
    description="Сервис интеграции с HeadHunter API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HHAPIClient:
    def __init__(self):
        # Загружаем конфигурацию из settings.yaml
        self.config = load_config()
        hh_config = self.config.get("hh_api", {})
        
        self.base_url = hh_config.get("base_url", "https://api.hh.ru")
        self.user_agent = hh_config.get("user_agent", "")
        self.http_client = HTTPClient(self.base_url)
        
        # OAuth credentials из конфигурации
        self.client_id = hh_config.get("client_id", "")
        self.client_secret = hh_config.get("client_secret", "")
        
        # Пользовательские токены из конфигурации  
        user_tokens = hh_config.get("user_tokens", {})
        self.access_token = user_tokens.get("access_token")
        self.refresh_token = user_tokens.get("refresh_token")
        self.token_expires_at = user_tokens.get("expires_at")
    
    def _get_headers(self) -> Dict[str, str]:
        """Получение заголовков для запросов"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json"
        }
        
        # Добавляем токен если есть
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        return headers
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Получение URL для авторизации пользователя"""
        auth_url = "https://hh.ru/oauth/authorize"
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri
        }
        if state:
            params["state"] = state
            
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"
    
    def get_token_from_code(self, authorization_code: str, redirect_uri: str):
        """Получение токена доступа через Authorization Code"""
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": authorization_code,
                "redirect_uri": redirect_uri
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                logger.info("Токен доступа получен через authorization code")
                return token_data
            else:
                logger.error(f"Ошибка получения токена: {response.status_code} - {response.text}")
                raise HTTPException(status_code=400, detail=f"Ошибка авторизации: {response.text}")
                    
        except Exception as e:
            logger.error(f"Ошибка при запросе токена: {e}")
            raise HTTPException(status_code=500, detail="Ошибка аутентификации")
    
    def refresh_access_token(self):
        """Обновление токена доступа через refresh token"""
        if not self.refresh_token:
            raise HTTPException(status_code=401, detail="Нет refresh token для обновления")
            
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                if token_data.get("refresh_token"):
                    self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                logger.info("Токен обновлен успешно")
                return token_data
            else:
                logger.error(f"Ошибка обновления токена: {response.status_code} - {response.text}")
                raise HTTPException(status_code=401, detail="Ошибка обновления токена")
                    
        except Exception as e:
            logger.error(f"Ошибка при обновлении токена: {e}")
            raise HTTPException(status_code=500, detail="Ошибка аутентификации")
    
    def _force_refresh_token(self):
        """Принудительное обновление токена (игнорирует срок действия)"""
        if not self.refresh_token:
            raise Exception("Нет refresh token для принудительного обновления")
            
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                old_token = self.access_token[:20] + "..." if self.access_token else "None"
                
                self.access_token = token_data.get("access_token")
                if token_data.get("refresh_token"):
                    self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                
                new_token = self.access_token[:20] + "..." if self.access_token else "None"
                logger.info(f"🔄 Токен принудительно обновлен: {old_token} → {new_token}")
                return token_data
            elif response.status_code == 400:
                error_data = response.json()
                if error_data.get("error") == "invalid_grant" and "not expired" in error_data.get("error_description", ""):
                    logger.warning("⚠️ HH API не разрешает обновление токена (еще не истек)")
                    raise Exception("Токен еще действителен, HH API блокирует обновление")
                else:
                    logger.error(f"❌ Ошибка обновления токена: {response.status_code} - {response.text}")
                    raise Exception(f"Ошибка HH API: {response.text}")
            else:
                logger.error(f"❌ Неожиданный статус при обновлении токена: {response.status_code}")
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Принудительное обновление токена не удалось: {e}")
            raise
    
    def get_application_token(self):
        """Получение токена приложения через Client Credentials Grant"""
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                # Для client_credentials обычно нет refresh_token
                self.refresh_token = None
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                logger.info("Токен приложения получен успешно через Client Credentials Grant")
                return token_data
            else:
                logger.error(f"Ошибка получения токена приложения: {response.status_code} - {response.text}")
                # Если Client Credentials не поддерживается, выбрасываем исключение о необходимости пользовательской авторизации
                if response.status_code == 400:
                    raise HTTPException(status_code=401, detail="Требуется авторизация пользователя для доступа к резюме.")
                raise HTTPException(status_code=500, detail=f"Ошибка получения токена приложения: {response.text}")
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка при запросе токена приложения: {e}")
            raise HTTPException(status_code=500, detail="Ошибка аутентификации приложения")
    
    def _ensure_token(self):
        """Проверка токена доступа"""
        if not self.access_token:
            # Пытаемся получить токен приложения с помощью Client Credentials Grant
            logger.info("Получаем токен приложения через Client Credentials Grant...")
            self.get_application_token()
            return
        
        # Проверяем, не истек ли токен
        if self.token_expires_at and time.time() >= self.token_expires_at - 300:  # 5 минут буфера
            if self.refresh_token:
                logger.info("Токен истекает, обновляем...")
                self.refresh_access_token()
            else:
                # Если refresh токена нет, пытаемся получить новый токен приложения
                logger.info("Токен истек, получаем новый токен приложения...")
                self.get_application_token()
    
    def _make_authenticated_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Выполнение аутентифицированного запроса"""
        # Для публичных эндпоинтов не нужен токен
        public_endpoints = ["/areas", "/professional_roles", "/languages"]
        
        if endpoint in public_endpoints:
            # Публичные эндпоинты работают без токена
            try:
                logger.info(f"Выполняем публичный запрос к {endpoint} с параметрами: {params}")
                
                # Используем requests напрямую для публичных эндпоинтов
                url = f"{self.base_url}{endpoint}"
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "application/json"
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=self.http_client.timeout)
                logger.info(f"Получен ответ от {endpoint}: статус {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.error(f"🚫 Превышен лимит запросов для публичного endpoint {endpoint}")
                    raise HTTPException(status_code=429, detail="Превышен лимит запросов к HH API. Попробуйте позже.")
                else:
                    logger.error(f"⚠️ HH API ошибка {response.status_code} для {endpoint}: {response.text}")
                    raise HTTPException(status_code=response.status_code, detail=f"Ошибка HH API: {response.text}")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Сетевая ошибка публичного запроса к {endpoint}: {e}")
                raise HTTPException(status_code=503, detail=f"Сетевая ошибка при обращении к HH API: {e}")
        
        # Для остальных эндпоинтов нужен токен
        # Проверяем/получаем токен
        if not self.access_token or (self.token_expires_at and time.time() > self.token_expires_at):
            self._ensure_token()
        
        # Retry логика для 429 ошибок
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Выполняем аутентифицированный запрос к {endpoint} с параметрами: {params} (попытка {attempt + 1})")
                
                # Используем requests напрямую, чтобы контролировать обработку ошибок
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self._get_headers(), params=params)
                logger.info(f"Получен ответ от {endpoint}: статус {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        # При первой 429 ошибке пытаемся принудительно обновить токен
                        logger.warning(f"🔍 DEBUG: 429 ошибка для {endpoint}, attempt={attempt}, refresh_token={bool(self.refresh_token)}")
                        
                        if attempt == 0 and self.refresh_token:
                            try:
                                logger.warning(f"🔄 Попытка принудительного обновления токена из-за 429 для {endpoint}")
                                self._force_refresh_token()
                                logger.info(f"✅ Токен обновлен, повторяем запрос к {endpoint}")
                                continue
                            except Exception as refresh_error:
                                logger.warning(f"⚠️ Не удалось обновить токен: {refresh_error}")
                        
                        import random
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except Exception:
                                delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                        else:
                            delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                        logger.warning(f"🚫 HH API лимит для {endpoint} (429), retry через {delay:.1f}s")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"💥 Превышен лимит запросов HH API для {endpoint} после {max_retries} попыток")
                        raise HTTPException(status_code=429, detail="Превышен лимит запросов к HH API. Попробуйте позже.")
                elif response.status_code == 401:
                    logger.error(f"🔐 Ошибка авторизации HH API для {endpoint}")
                    raise HTTPException(status_code=401, detail="Ошибка авторизации HH API. Проверьте токен доступа работодателя (OAuth).")
                elif response.status_code == 403:
                    logger.error(f"🚫 Доступ запрещен HH API для {endpoint}")
                    raise HTTPException(status_code=403, detail="Доступ запрещен. Недостаточно прав (требуются права работодателя для переговоров/откликов).")
                elif response.status_code == 404:
                    logger.error(f"📭 Ресурс не найден HH API для {endpoint}")
                    raise HTTPException(status_code=404, detail="Запрашиваемый ресурс не найден.")
                else:
                    logger.error(f"⚠️ HH API ошибка {response.status_code} для {endpoint}: {response.text}")
                    raise HTTPException(status_code=response.status_code, detail=f"Ошибка HH API: {response.text}")
                    
            except HTTPException:
                # Проксируем HTTP ошибки как есть
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"🔄 Сетевая ошибка для {endpoint}, retry через {delay}s: {e}")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Критическая сетевая ошибка для {endpoint}: {e}")
                    raise HTTPException(status_code=503, detail=f"Сетевая ошибка при обращении к HH API: {e}")
    
    def get_areas(self) -> List[Dict[str, Any]]:
        """Получение списка регионов"""
        try:
            response = self._make_authenticated_request("/areas")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения списка регионов: {e}")
            raise HTTPException(status_code=500, detail="Ошибка получения списка регионов")

    # ===== НОВОЕ: Получение откликов на вакансию по ссылке =====
    def _extract_vacancy_id(self, vacancy_url: str) -> Optional[str]:
        try:
            # Простейший парсер ID: ожидаем /vacancy/<id>
            import re
            match = re.search(r"vacancy/(\d+)", vacancy_url)
            return match.group(1) if match else None
        except Exception:
            return None

    def get_vacancy_details(self, vacancy_url: str) -> Dict[str, Any]:
        """Получение подробностей вакансии по ссылке (публичный эндпоинт вакансий)."""
        vacancy_id = self._extract_vacancy_id(vacancy_url)
        if not vacancy_id:
            raise HTTPException(status_code=400, detail="Некорректная ссылка на вакансию")
        try:
            url = f"{self.base_url}/vacancies/{vacancy_id}"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                data = response.json()
                data["vacancy_id"] = vacancy_id
                return data
            else:
                logger.error(f"Ошибка получения вакансии: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Ошибка получения вакансии")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка получения вакансии {vacancy_id}: {e}")
            raise HTTPException(status_code=500, detail="Ошибка получения вакансии")

    def get_vacancy_responses(self, vacancy_url: str, per_page: int = 50, max_pages: int = 20) -> Dict[str, Any]:
        """Получение откликов (переписок) на вакансию. Требуется OAuth работодателя и права переговоров.

        Реализовано через negotiations/response: GET /negotiations/response?vacancy_id=<id>
        Возвращает унифицированный список с resume_id для дальнейшего получения резюме.
        """
        vacancy_id = self._extract_vacancy_id(vacancy_url)
        if not vacancy_id:
            raise HTTPException(status_code=400, detail="Некорректная ссылка на вакансию")

        try:
            collected: List[Dict[str, Any]] = []
            page = 0
            while page < max_pages:
                params = {"vacancy_id": vacancy_id, "page": page, "per_page": per_page}
                # Используем правильный эндпоинт для получения откликов
                data = self._make_authenticated_request("/negotiations/response", params=params)
                logger.info(f"🔥 ПРАВИЛЬНЫЙ ЗАПРОС К /negotiations/response: {params}")
                items = data.get("items", []) if isinstance(data, dict) else []
                
                logger.info(f"Получено {len(items)} откликов на странице {page}")
                
                for it in items:
                    resume_obj = it.get("resume") if isinstance(it, dict) else None
                    resume_id = None
                    if isinstance(resume_obj, dict):
                        resume_id = resume_obj.get("id")
                    if not resume_id:
                        # fallback: иногда в item могут быть поля links
                        links = it.get("links", []) if isinstance(it, dict) else []
                        for l in links:
                            if isinstance(l, dict) and l.get("rel") == "resume":
                                href = l.get("href", "")
                                # ожидаем /resumes/<id>
                                import re
                                m = re.search(r"resumes/(\w+)", href)
                                if m:
                                    resume_id = m.group(1)
                                    break
                    if resume_id:
                        collected.append({"resume_id": resume_id, "raw": it})

                pages_total = data.get("pages") if isinstance(data, dict) else None
                page += 1
                if pages_total is not None and page >= pages_total:
                    break
                if not items:  # Если пустая страница - прекращаем
                    break

            logger.info(f"Всего собрано {len(collected)} откликов с resume_id для вакансии {vacancy_id}")
            return {"vacancy_id": vacancy_id, "items": collected, "total": len(collected)}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка получения откликов на вакансию {vacancy_id}: {e}")
            raise HTTPException(status_code=500, detail="Ошибка получения откликов на вакансию")
    
    def get_professional_roles(self) -> Dict[str, Any]:
        """Получение списка профессиональных ролей"""
        try:
            response = self._make_authenticated_request("/professional_roles")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения профессиональных ролей: {e}")
            raise HTTPException(status_code=500, detail="Ошибка получения профессиональных ролей")
    
    def get_languages(self) -> List[Dict[str, Any]]:
        """Получение списка языков (публичный эндпоинт)"""
        try:
            response = self._make_authenticated_request("/languages")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения списка языков: {e}")
            # Fallback к базовому списку языков если API недоступен
            return [
                {"id": "1", "name": "Русский"},
                {"id": "2", "name": "Английский"},
                {"id": "3", "name": "Немецкий"},
                {"id": "4", "name": "Французский"},
                {"id": "5", "name": "Испанский"},
                {"id": "6", "name": "Китайский"},
                {"id": "7", "name": "Японский"},
                {"id": "8", "name": "Корейский"},
                {"id": "9", "name": "Итальянский"},
                {"id": "10", "name": "Португальский"}
            ]
    
    def get_dictionaries(self) -> Dict[str, Any]:
        """Получение всех доступных справочников"""
        try:
            # Объединяем несколько анонимных эндпоинтов
            result = {}
            
            # Языки
            try:
                languages_response = self._make_authenticated_request("/languages")
                result["language"] = languages_response
            except:
                result["language"] = [
                    {"id": "1", "name": "Русский"},
                    {"id": "2", "name": "Английский"},
                    {"id": "3", "name": "Немецкий"},
                    {"id": "4", "name": "Французский"},
                    {"id": "5", "name": "Испанский"}
                ]
            
            # Опыт работы - захардкоженные значения (соответствуют HH API)
            result["experience"] = [
                {"id": "noExperience", "name": "Нет опыта"},
                {"id": "between1And3", "name": "От 1 года до 3 лет"},
                {"id": "between3And6", "name": "От 3 до 6 лет"},
                {"id": "moreThan6", "name": "Более 6 лет"}
            ]
            
            # Тип занятости
            result["employment"] = [
                {"id": "full", "name": "Полная занятость"},
                {"id": "part", "name": "Частичная занятость"},
                {"id": "project", "name": "Проектная работа"},
                {"id": "volunteer", "name": "Волонтерство"},
                {"id": "probation", "name": "Стажировка"}
            ]
            
            # График работы
            result["schedule"] = [
                {"id": "fullDay", "name": "Полный день"},
                {"id": "shift", "name": "Сменный график"},
                {"id": "flexible", "name": "Гибкий график"},
                {"id": "remote", "name": "Удаленная работа"},
                {"id": "flyInFlyOut", "name": "Вахтовый метод"}
            ]
            
            # Уровни языков
            result["language_level"] = [
                {"id": "a1", "name": "A1 — Начальный"},
                {"id": "a2", "name": "A2 — Элементарный"},
                {"id": "b1", "name": "B1 — Средний"},
                {"id": "b2", "name": "B2 — Средне-продвинутый"},
                {"id": "c1", "name": "C1 — Продвинутый"},
                {"id": "c2", "name": "C2 — Профессиональный"},
                {"id": "native", "name": "Родной"}
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения справочников: {e}")
            raise HTTPException(status_code=500, detail="Ошибка получения справочников")
    
    def search_resumes(self, search_request: SearchRequest) -> Dict[str, Any]:
        """Поиск резюме кандидатов"""
        try:
            # Формирование параметров запроса для резюме
            params = {
                "per_page": search_request.per_page,
                "page": search_request.page - 1  # HH API использует 0-based индексацию
            }
            
            if search_request.text:
                params["text"] = search_request.text
            
            # Для резюме поддерживается search_field
            if search_request.search_field:
                params["search_field"] = search_request.search_field.value
            
            if search_request.area:
                # Для резюме area должен быть одним значением
                if isinstance(search_request.area, list):
                    params["area"] = search_request.area[0] if search_request.area else None
                else:
                    params["area"] = search_request.area
            
            if search_request.salary:
                params["salary"] = search_request.salary
            
            if search_request.experience:
                params["experience"] = search_request.experience.value
            
            if search_request.employment:
                # HH API ожидает строку, а не список
                params["employment"] = search_request.employment[0].value if search_request.employment else None
            
            if search_request.schedule:
                # HH API ожидает строку, а не список
                params["schedule"] = search_request.schedule[0].value if search_request.schedule else None
            
            if search_request.professional_role:
                params["professional_role"] = search_request.professional_role
            
            if search_request.period:
                params["period"] = search_request.period
            
            if search_request.age_from:
                params["age_from"] = search_request.age_from
            
            if search_request.age_to:
                params["age_to"] = search_request.age_to
            
            if search_request.gender:
                params["gender"] = search_request.gender.value
            
            if search_request.language:
                # Преобразование языков в формат HH API
                language_params = []
                for lang_req in search_request.language:
                    language_params.append(f"{lang_req.language_id}.{lang_req.level.value}")
                params["language"] = language_params
            
            # Удаляем None значения
            params = {k: v for k, v in params.items() if v is not None}
            
            # Добавляем детальное логирование
            logger.info(f"Параметры запроса к HH API (резюме): {params}")
            
            # Используем эндпоинт резюме
            response = self._make_authenticated_request("/resumes", params=params)
            
            # Логируем ответ
            logger.info(f"Получен ответ от HH API (вакансии): {response}")
            
            return response
        except HTTPException:
            # Проксируем HTTP ошибки как есть (включая 401 Unauthorized) 
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка поиска: {e}")
            raise HTTPException(status_code=500, detail="Внутренняя ошибка поиска резюме")
    
    def get_resume_details(self, resume_id: str) -> Dict[str, Any]:
        """Получение детальной информации о резюме"""
        try:
            response = self._make_authenticated_request(f"/resumes/{resume_id}")
            return response
        except HTTPException:
            # Проксируем HTTP ошибки как есть (включая 401 Unauthorized)
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка получения деталей резюме: {e}")
            raise HTTPException(status_code=500, detail="Внутренняя ошибка получения деталей резюме")
    
    def _parse_candidate(self, resume_data: Dict[str, Any]) -> Candidate:
        """Парсинг данных кандидата из ответа HH API (резюме)"""
        try:
            # Извлечение основной информации из резюме
            resume_id = resume_data.get("id", "")
            title = resume_data.get("title", "")
            area = resume_data.get("area", {})
            experience = resume_data.get("total_experience", {})
            salary_data = resume_data.get("salary")
            updated_at = parse_date(resume_data.get("updated_at", ""))
            
            # Извлечение информации о кандидате
            name = "Кандидат"  # HH API скрывает ФИО для анонимности
            age = resume_data.get("age")
            
            # Извлечение навыков из резюме
            skills = []
            verified_skills = []
            
            # Навыки могут быть в разных полях
            if "skill_set" in resume_data:
                skills = resume_data["skill_set"]
            
            if "key_skills" in resume_data:
                key_skills = resume_data["key_skills"]
                if isinstance(key_skills, list):
                    skills.extend([skill.get("name", "") for skill in key_skills if isinstance(skill, dict)])
            
            # Извлечение информации о последнем месте работы
            last_work = {}
            if "experience" in resume_data and resume_data["experience"]:
                last_exp = resume_data["experience"][0] if isinstance(resume_data["experience"], list) else {}
                last_work = {
                    "name": last_exp.get("company", ""),
                    "position": last_exp.get("position", ""),
                    "description": last_exp.get("description", "")
                }
            
            # Парсинг зарплаты
            salary = None
            if salary_data:
                salary = parse_salary(salary_data)
            
            # Формирование URL резюме
            resume_url = f"https://hh.ru/resume/{resume_id}"
            
            # Извлечение фотографии кандидата
            photo_url = None
            if "photo" in resume_data and resume_data["photo"]:
                photo_url = resume_data["photo"].get("medium", resume_data["photo"].get("small"))
            
            # Проверка наличия сопроводительного письма
            has_cover_letter = resume_data.get("has_cover_letter", False)
            
            return Candidate(
                id=resume_id,
                name=name,
                age=age,
                title=title,
                area=area,
                experience=experience,
                salary=salary,
                last_work=last_work,
                skills=skills,
                verified_skills=verified_skills,
                updated_at=updated_at,
                url=resume_url,
                photo_url=photo_url,
                has_cover_letter=has_cover_letter
            )
            
        except Exception as e:
            logger.error(f"Ошибка парсинга резюме: {e}")
            raise

# Инициализация клиента HH API
hh_client = HHAPIClient()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/areas")
async def get_areas():
    """Получение списка регионов"""
    try:
        areas = hh_client.get_areas()
        # Возвращаем прямой массив регионов согласно официальной документации HH API
        return areas
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения регионов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения регионов")

@app.get("/professional-roles")
async def get_professional_roles():
    """Получение списка профессиональных ролей"""
    try:
        roles = hh_client.get_professional_roles()
        # Возвращаем объект с categories согласно официальной документации HH API
        return roles
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения профессиональных ролей: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения профессиональных ролей")

@app.get("/languages")
async def get_languages():
    """Получение списка языков"""
    try:
        languages = hh_client.get_languages()
        return {"languages": languages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения языков: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения языков")

@app.get("/dictionaries")
async def get_dictionaries():
    """Получение всех справочников"""
    try:
        dictionaries = hh_client.get_dictionaries()
        return {"dictionaries": dictionaries}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения справочников: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения справочников")

# ===== НОВОЕ: HTTP endpoint для откликов по ссылке на вакансию =====
@app.post("/vacancy/details", response_model=Dict[str, Any])
async def get_vacancy_details_endpoint(payload: VacancyTopRequest):
    try:
        data = hh_client.get_vacancy_details(payload.vacancy_url)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обработки запроса вакансии: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения вакансии")

@app.post("/vacancy/responses", response_model=Dict[str, Any])
async def get_vacancy_responses_endpoint(payload: VacancyTopRequest):
    try:
        # Получаем ВСЕ отклики - увеличиваем max_pages для полного сбора
        max_pages = 100  # Достаточно для получения тысяч откликов (100 страниц x 50 = 5000 откликов)
        data = hh_client.get_vacancy_responses(payload.vacancy_url, per_page=50, max_pages=max_pages)
        logger.info(f"🎯 Получено ВСЕГО откликов: {data.get('total', 0)}")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обработки запроса откликов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения откликов")

def create_search_request(
    text: Optional[str] = Query(None, description="Ключевые слова для поиска"),
    search_field: Optional[str] = Query("everywhere", description="Область поиска"), 
    area: Optional[List[int]] = Query(None, description="ID регионов"),
    salary: Optional[int] = Query(None, description="Максимальная зарплата"),
    experience: Optional[str] = Query(None, description="Опыт работы"),
    employment: Optional[List[str]] = Query(None, description="Тип занятости"),
    schedule: Optional[List[str]] = Query(None, description="График работы"),
    professional_role: Optional[List[str]] = Query(None, description="Профессиональные роли"),
    period: Optional[int] = Query(None, description="Период обновления в днях"),
    age_from: Optional[int] = Query(None, description="Возраст от"),
    age_to: Optional[int] = Query(None, description="Возраст до"), 
    gender: Optional[str] = Query(None, description="Пол"),
    language_id: Optional[str] = Query(None, description="ID языка"),
    language_level: Optional[str] = Query(None, description="Минимальный уровень языка"),
    page: int = Query(1, description="Номер страницы"),
    per_page: int = Query(20, description="Количество на странице")
) -> SearchRequest:
    """Создание SearchRequest из query параметров"""
    
    # Обработка языковых требований
    language_requirements = None
    if language_id and language_level:
        from shared.models import LanguageRequirement, LanguageLevel
        try:
            language_requirements = [LanguageRequirement(
                language_id=language_id,
                level=LanguageLevel(language_level)
            )]
        except ValueError:
            # Если неверный уровень языка, игнорируем
            language_requirements = None
    
    return SearchRequest(
        text=text,
        search_field=search_field,
        area=area,
        salary=salary,
        experience=experience,
        employment=employment,
        schedule=schedule,
        professional_role=professional_role,
        period=period,
        age_from=age_from,
        age_to=age_to,
        gender=gender,
        language=language_requirements,
        page=page,
        per_page=per_page
    )

@app.get("/search")
async def search_resumes(search_request: SearchRequest = Depends(create_search_request)):
    """Поиск резюме через GET запрос"""
    try:
        # Выполнение поиска вакансий
        search_results = hh_client.search_resumes(search_request)
        
        # Парсинг результатов
        candidates = []
        for item in search_results.get("items", []):
            try:
                candidate = hh_client._parse_candidate(item)
                candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Ошибка парсинга вакансии: {e}")
                continue
        
        # Формирование ответа
        total_count = search_results.get("found", 0)
        pages = search_results.get("pages", 0)
        
        return {
            "candidates": [candidate.model_dump() for candidate in candidates],
            "total_count": total_count,
            "page": search_request.page,
            "pages": pages
        }
        
    except HTTPException as he:
        # Проксируем HTTP ошибки как есть (включая 401 Unauthorized)
        logger.error(f"HTTP ошибка при поиске: {he.status_code} - {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Неожиданная ошибка поиска: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервиса поиска")

@app.get("/resume/{resume_id}")
async def get_resume_details(resume_id: str):
    """Получение детальной информации о резюме"""
    try:
        resume_data = hh_client.get_resume_details(resume_id)
        return {"resume": resume_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения деталей резюме: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения деталей резюме")

@app.get("/oauth/authorize-url")
async def get_authorize_url(redirect_uri: str, state: str = None):
    """Получение URL для авторизации пользователя в HH.ru"""
    try:
        auth_url = hh_client.get_authorization_url(redirect_uri, state)
        return {"authorization_url": auth_url}
    except Exception as e:
        logger.error(f"Ошибка формирования URL авторизации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка формирования URL авторизации")

@app.post("/oauth/token")
async def exchange_code_for_token(code: str, redirect_uri: str):
    """Обмен authorization code на access token"""
    try:
        token_data = hh_client.get_token_from_code(code, redirect_uri)
        return {
            "access_token": token_data.get("access_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обмена кода на токен: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения токена")

@app.post("/oauth/refresh")
async def refresh_token():
    """Обновление access token через refresh token"""
    try:
        token_data = hh_client.refresh_access_token()
        return {
            "access_token": token_data.get("access_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обновления токена: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления токена")

@app.post("/settings/auth")
async def update_auth_settings(auth_settings: dict):
    """Обновление настроек аутентификации"""
    try:
        # Обновляем настройки клиента HH API
        if "hh_client_id" in auth_settings:
            hh_client.client_id = auth_settings["hh_client_id"]
        
        if "hh_client_secret" in auth_settings:
            hh_client.client_secret = auth_settings["hh_client_secret"]
        
        if "hh_user_agent" in auth_settings:
            hh_client.user_agent = auth_settings["hh_user_agent"]
        
        logger.info("Настройки HH API обновлены")
        return {
            "status": "success", 
            "message": "Настройки HH API обновлены",
            "client_id": hh_client.client_id[:10] + "..." if hh_client.client_id else None,
            "user_agent": hh_client.user_agent
        }
    except Exception as e:
        logger.error(f"Ошибка обновления настроек HH API: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления настроек HH API")

# ===== ФУНКЦИОНАЛ СОЗДАНИЯ ВАКАНСИЙ =====

@app.post("/employer/vacancies")
async def create_vacancy(vacancy_data: Dict[str, Any]):
    """Создание вакансии через HH API"""
    try:
        logger.info(f"HH API: Создание вакансии '{vacancy_data.get('name', 'Неизвестная')}'")
        
        # Проверяем, что у нас есть токен
        if not hh_client.access_token:
            logger.error("Нет токена доступа для создания вакансии")
            raise HTTPException(status_code=401, detail="Не настроен токен доступа работодателя")
        
        # Формируем заголовки
        headers = hh_client._get_headers()
        headers["Content-Type"] = "application/json"
        
        # Отправляем запрос на создание вакансии
        url = f"{hh_client.base_url}/employer/vacancies"
        response = requests.post(url, json=vacancy_data, headers=headers, timeout=30)
        
        if response.status_code == 201:
            # Вакансия создана успешно
            vacancy_response = response.json()
            logger.info(f"HH API: Вакансия создана, ID: {vacancy_response.get('id')}")
            return vacancy_response
        
        elif response.status_code in [400, 422]:
            # Ошибки валидации
            logger.warning(f"HH API: Ошибка валидации при создании вакансии: {response.text}")
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Ошибка валидации данных вакансии",
                    "errors": error_data.get("errors", []),
                    "description": error_data.get("description", response.text)
                }
            )
        
        elif response.status_code == 401:
            logger.error("HH API: Ошибка авторизации при создании вакансии")
            raise HTTPException(status_code=401, detail="Ошибка авторизации. Проверьте токен работодателя")
        
        elif response.status_code == 403:
            logger.error("HH API: Нет прав для создания вакансий")
            raise HTTPException(status_code=403, detail="Нет прав для создания вакансий. Обратитесь к администратору")
        
        else:
            # Другие ошибки
            logger.error(f"HH API: Неожиданная ошибка создания вакансии: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ошибка HH API: {response.text}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HH API: Общая ошибка создания вакансии: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка при создании вакансии")

@app.get("/me")
async def get_current_user():
    """Получение информации о текущем пользователе/работодателе"""
    try:
        if not hh_client.access_token:
            raise HTTPException(status_code=401, detail="Access token не найден")
        
        headers = hh_client._get_headers()
        url = f"{hh_client.base_url}/me"
        
        logger.info(f"Запрос информации о пользователе: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Получены данные пользователя: {user_data.get('email', 'N/A')}")
            return user_data
        else:
            logger.error(f"Ошибка HH API /me: {response.status_code} - {response.text}")
            # Возвращаем детальную информацию об ошибке для отладки
            try:
                error_data = response.json()
                error_detail = f"HH API Error {response.status_code}: {error_data}"
            except:
                error_detail = f"HH API Error {response.status_code}: {response.text}"
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except HTTPException as he:
        # Проксируем HTTP ошибки как есть (включая 403)
        raise he
    except requests.exceptions.RequestException as e:
        logger.error(f"Сетевая ошибка при получении данных пользователя: {str(e)}")
        raise HTTPException(status_code=503, detail="Сервис временно недоступен")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении данных пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка при получении данных пользователя")

@app.get("/employer/managers")
async def get_employer_managers():
    """Получение списка менеджеров работодателя"""
    try:
        if not hh_client.access_token:
            raise HTTPException(status_code=401, detail="Access token не найден")
        
        # Сначала получаем информацию о текущем пользователе для получения employer_id
        headers = hh_client._get_headers()
        me_url = f"{hh_client.base_url}/me"
        
        logger.info(f"Получение информации о пользователе: {me_url}")
        me_response = requests.get(me_url, headers=headers, timeout=30)
        
        if me_response.status_code != 200:
            logger.error(f"Ошибка получения информации о пользователе: {me_response.status_code}")
            raise HTTPException(status_code=me_response.status_code, detail="Не удалось получить информацию о пользователе")
        
        me_data = me_response.json()
        employer_id = me_data.get("employer", {}).get("id")
        
        if not employer_id:
            logger.error("Employer ID не найден в данных пользователя")
            raise HTTPException(status_code=400, detail="Employer ID не найден")
        
        # Теперь запрашиваем менеджеров согласно официальной документации
        managers_url = f"{hh_client.base_url}/employers/{employer_id}/managers"
        
        logger.info(f"Запрос списка менеджеров: {managers_url}")
        response = requests.get(managers_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            managers_data = response.json()
            logger.info(f"Получено менеджеров: {len(managers_data.get('items', []))}")
            return managers_data
        else:
            logger.error(f"Ошибка HH API /employers/{employer_id}/managers: {response.status_code} - {response.text}")
            try:
                error_data = response.json()
                error_detail = f"HH API Error {response.status_code}: {error_data}"
            except:
                error_detail = f"HH API Error {response.status_code}: {response.text}"
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except HTTPException as he:
        raise he
    except requests.exceptions.RequestException as e:
        logger.error(f"Сетевая ошибка при получении менеджеров: {str(e)}")
        raise HTTPException(status_code=503, detail="Сервис временно недоступен")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении менеджеров: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка при получении менеджеров")

@app.get("/employer/vacancies")
async def get_employer_vacancies(page: int = 0, per_page: int = 20):
    """Получение списка вакансий работодателя"""
    try:
        if not hh_client.access_token:
            raise HTTPException(status_code=401, detail="Не настроен токен доступа работодателя")
        
        headers = hh_client._get_headers()
        url = f"{hh_client.base_url}/employer/vacancies"
        params = {"page": page, "per_page": per_page}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"HH API: Ошибка получения вакансий работодателя: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HH API: Ошибка получения вакансий работодателя: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения списка вакансий")

if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("hh_api", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8003),
        reload=service_config.get("debug", False)
    )