from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
import time

# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse,
    SearchRequest,
    SearchResponse,
    Candidate,
    VacancyTopRequest,
    VacancyTopResponse,
    MultiAgentAnalysisRequest,
    MultiAgentAnalysisResponse,
    RankingRequest,
    ConfigSaveRequest,
    ConfigSaveResponse,
    VacancyCreationRequest,
    VacancyCreationResponse,
    VacancyDraft,
    VacancyTemplate,
    VacancyArea,
    VacancyProfessionalRole,
)
from shared.utils import setup_logging, load_config, parse_date, parse_salary

# Настройка логирования
logger = setup_logging("gateway-service")

app = FastAPI(
    title="API Gateway",
    description="Единая точка входа для всех сервисов Candidate Analysis",
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

class APIGateway:
    def __init__(self):
        self.config = load_config()
        self.services_config = self.config.get("services", {})
        
        # Определяем URL сервисов в зависимости от окружения
        is_docker = os.getenv("DOCKER_ENV") == "true"
        self.services = {
            name: f"http://{conf.get('docker_host', 'localhost')}:{conf.get('port')}" if is_docker 
                  else f"http://{conf.get('host', 'localhost')}:{conf.get('port')}"
            for name, conf in self.services_config.items()
        }
        
        self.rate_limit_requests = {}
        self.rate_limit_window = 60  # секунд
        self.max_requests_per_window = self.config.get("security", {}).get("rate_limit", 100)
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Проверка rate limit"""
        current_time = time.time()
        
        if client_ip not in self.rate_limit_requests:
            self.rate_limit_requests[client_ip] = []
        
        # Удаление старых запросов
        self.rate_limit_requests[client_ip] = [
            req_time for req_time in self.rate_limit_requests[client_ip]
            if current_time - req_time < self.rate_limit_window
        ]
        
        # Проверка лимита
        if len(self.rate_limit_requests[client_ip]) >= self.max_requests_per_window:
            return False
        
        # Добавление текущего запроса
        self.rate_limit_requests[client_ip].append(current_time)
        return True
    
    def get_client_ip(self, request: Request) -> str:
        """Получение IP клиента"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def make_service_request(self, service_name: str, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Выполнение запроса к микросервису"""
        try:
            service_url = self.services.get(service_name)
            if not service_url:
                raise HTTPException(status_code=500, detail=f"Сервис {service_name} недоступен")
            
            url = f"{service_url}{endpoint}"
            logger.info(f"Отправляем запрос к {service_name}: {method} {url}")
            
            if method.upper() == "GET":
                response = requests.get(url, **kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, **kwargs)
            elif method.upper() == "PUT":
                response = requests.put(url, **kwargs)
            elif method.upper() == "DELETE":
                response = requests.delete(url, **kwargs)
            else:
                raise HTTPException(status_code=400, detail="Неподдерживаемый метод")
            
            logger.info(f"Получен ответ от {service_name}: {response.status_code}")
            
            # Обработка HTTP ошибок с правильным проксированием кодов
            if response.status_code >= 400:
                try:
                    error_detail = response.json().get("detail", response.text)
                except:
                    error_detail = response.text
                
                # Проксируем код ошибки как есть
                logger.error(f"HTTP ошибка от {service_name}: {response.status_code} - {error_detail}")
                raise HTTPException(status_code=response.status_code, detail=error_detail)
            
            return response.json()
            
        except HTTPException:
            # Проксируем HTTPException как есть
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка соединения с сервисом {service_name}: {e}")
            raise HTTPException(status_code=503, detail=f"Сервис {service_name} недоступен")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
    
    def check_service_health(self, service_name: str) -> bool:
        """Проверка здоровья сервиса"""
        try:
            health_response = self.make_service_request(service_name, "GET", "/health")
            return health_response.get("status") == "healthy"
        except Exception:
            return False
    
    def get_all_services_health(self) -> Dict[str, bool]:
        """Получение статуса всех сервисов"""
        health_status = {}
        for service_name in self.services:
            health_status[service_name] = self.check_service_health(service_name)
        return health_status

# Инициализация API Gateway
gateway = APIGateway()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Middleware для rate limiting"""
    client_ip = gateway.get_client_ip(request)
    
    if not gateway.check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "retry_after": gateway.rate_limit_window}
        )
    
    response = await call_next(request)
    return response

@app.get("/ping")
async def ping():
    """Простая проверка доступности gateway"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья gateway и всех сервисов"""
    # Проверяем только другие сервисы, исключая gateway и frontend
    services_health = {}
    for service_name, service_url in gateway.services.items():
        if service_name not in ["gateway", "frontend", "search"]:  # Исключаем самопроверку, frontend и search
            services_health[service_name] = gateway.check_service_health(service_name)
    
    all_healthy = all(services_health.values()) if services_health else True
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/health/services")
async def get_services_health():
    """Получение статуса всех сервисов"""
    services_health = {}
    for service_name, service_url in gateway.services.items():
        if service_name not in ["gateway", "frontend", "search"]:  # Исключаем самопроверку, frontend и search
            services_health[service_name] = gateway.check_service_health(service_name)
    return {"services": services_health}

@app.get("/config")
async def get_config():
    """Получение конфигурации"""
    try:
        return gateway.make_service_request("config", "GET", "/config")
    except HTTPException:
        raise

@app.get("/config/{section}")
async def get_config_section(section: str):
    """Получение секции конфигурации"""
    try:
        return gateway.make_service_request("config", "GET", f"/config/{section}")
    except HTTPException:
        raise

@app.get("/filters")
async def get_search_filters():
    """Получение доступных фильтров для поиска"""
    # Возвращаем базовые фильтры без обращения к search service
    return {
        "filters": {
            "area": {"name": "Регион", "type": "select", "options": []},
            "experience": {"name": "Опыт работы", "type": "select", "options": []},
            "salary": {"name": "Зарплата", "type": "range", "min": 0, "max": 500000}
        }
    }

def create_search_request_gateway(
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
    """Создание SearchRequest из query параметров в Gateway"""
    
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
async def search_candidates(search_request: SearchRequest = Depends(create_search_request_gateway)):
    """Поиск кандидатов через HH API напрямую"""
    try:
        # Преобразуем SearchRequest в параметры для GET запроса
        params = search_request.model_dump(exclude_none=True)
        return gateway.make_service_request(
            "hh_api", 
            "GET", 
            "/search", 
            params=params
        )
    except HTTPException:
        raise

@app.get("/candidates/{candidate_id}")
async def get_candidate_details(candidate_id: str):
    """Получение детальной информации о кандидате через HH API"""
    try:
        # Обращаемся напрямую к HH API за данными резюме
        return gateway.make_service_request("hh_api", "GET", f"/resume/{candidate_id}")
    except HTTPException:
        raise

@app.post("/top-candidates")
async def get_top_candidates(search_request: SearchRequest, limit: int = 10):
    """Получение топ кандидатов"""
    try:
        return gateway.make_service_request(
            "search",
            "POST",
            f"/top-candidates?limit={limit}",
            json=search_request.model_dump()
        )
    except HTTPException:
        raise

@app.get("/areas")
async def get_areas():
    """Получение списка регионов"""
    try:
        return gateway.make_service_request("hh_api", "GET", "/areas")
    except HTTPException:
        raise

@app.get("/professional-roles")
async def get_professional_roles():
    """Получение списка профессиональных ролей"""
    try:
        return gateway.make_service_request("hh_api", "GET", "/professional-roles")
    except HTTPException:
        raise

@app.get("/languages")
async def get_languages():
    """Получение списка языков"""
    try:
        return gateway.make_service_request("hh_api", "GET", "/languages")
    except HTTPException:
        raise

@app.get("/dictionaries")
async def get_dictionaries():
    """Получение всех справочников"""
    try:
        return gateway.make_service_request("hh_api", "GET", "/dictionaries")
    except HTTPException:
        raise

@app.get("/hh-api/me")
async def get_current_user():
    """Получение информации о текущем пользователе/работодателе через HH API"""
    try:
        return gateway.make_service_request("hh_api", "GET", "/me")
    except HTTPException:
        raise

@app.get("/hh-api/employer/managers")
async def get_employer_managers():
    """Получение списка менеджеров работодателя через HH API"""
    try:
        return gateway.make_service_request("hh_api", "GET", "/employer/managers")
    except HTTPException:
        raise

@app.get("/oauth/authorize-url")
async def get_authorize_url(redirect_uri: str, state: str = None):
    """Получение URL для авторизации пользователя в HH.ru"""
    try:
        params = {"redirect_uri": redirect_uri}
        if state:
            params["state"] = state
        return gateway.make_service_request("hh_api", "GET", "/oauth/authorize-url", params=params)
    except HTTPException:
        raise

@app.post("/oauth/token")
async def exchange_code_for_token(code: str, redirect_uri: str):
    """Обмен authorization code на access token"""
    try:
        data = {"code": code, "redirect_uri": redirect_uri}
        return gateway.make_service_request("hh_api", "POST", "/oauth/token", data=data)
    except HTTPException:
        raise

@app.post("/oauth/refresh")
async def refresh_token():
    """Обновление access token через refresh token"""
    try:
        return gateway.make_service_request("hh_api", "POST", "/oauth/refresh")
    except HTTPException:
        raise

@app.post("/settings/auth")
async def update_auth_settings(auth_settings: dict):
    """Обновление настроек аутентификации"""
    try:
        # Обновляем настройки в HH API сервисе
        hh_response = gateway.make_service_request("hh_api", "POST", "/settings/auth", json=auth_settings)
        
        # Обновляем настройки в AI Analysis сервисе
        ai_response = gateway.make_service_request("ai_analysis", "POST", "/settings/auth", json=auth_settings)
        
        return {
            "status": "success",
            "message": "Настройки аутентификации обновлены",
            "hh_api_updated": hh_response.get("status") == "success",
            "ai_analysis_updated": ai_response.get("status") == "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обновления настроек: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления настроек")

@app.get("/ranking/weights")
async def get_ranking_weights():
    try:
        return gateway.make_service_request("ranking", "GET", "/weights")
    except HTTPException:
        raise

@app.put("/ranking/weights")
async def update_ranking_weights(weights: Dict[str, Any]):
    try:
        return gateway.make_service_request("ranking", "PUT", "/weights", json=weights)
    except HTTPException:
        raise

@app.get("/database/statistics")
async def get_database_statistics():
    """Получение статистики базы данных"""
    try:
        stats = gateway.make_service_request("database", "GET", "/statistics")
        return {"statistics": stats}
    except HTTPException:
        raise

@app.post("/database/candidates")
async def create_candidate(candidate_data: Dict[str, Any]):
    """Создание кандидата в базе данных"""
    try:
        return gateway.make_service_request("database", "POST", "/candidates", json=candidate_data)
    except HTTPException:
        raise

@app.get("/database/candidates/{candidate_id}")
async def get_candidate_from_db(candidate_id: str):
    """Получение кандидата из базы данных"""
    try:
        return gateway.make_service_request("database", "GET", f"/candidates/{candidate_id}")
    except HTTPException:
        raise

@app.put("/database/candidates/{candidate_id}/searched")
async def update_candidate_search_count(candidate_id: str):
    """Обновление счетчика поиска кандидата"""
    try:
        return gateway.make_service_request("database", "PUT", f"/candidates/{candidate_id}/searched")
    except HTTPException:
        raise

@app.post("/ranking/calculate-scores")
async def calculate_scores(request: Dict[str, Any]):
    try:
        return gateway.make_service_request("ranking", "POST", "/calculate-scores", json=request)
    except HTTPException:
        raise

# ===== НОВОЕ: Топ кандидатов по ссылке вакансии =====
@app.post("/vacancy/top", response_model=VacancyTopResponse)
async def build_vacancy_top(req: VacancyTopRequest):
    """Построение ТОПа без сервиса search: оркестрация прямо в gateway."""
    try:
        # 1) Получаем детали вакансии
        vacancy_details = gateway.make_service_request("hh_api", "POST", "/vacancy/details", json=req.model_dump())
        
        # 2) Получаем отклики на вакансию
        responses_data = gateway.make_service_request("hh_api", "POST", "/vacancy/responses", json=req.model_dump())
        vacancy_id = responses_data.get("vacancy_id", "")
        items = responses_data.get("items", [])

        # 3) Собираем кандидатов (конвертация из резюме)
        def resume_to_candidate(resume: Dict[str, Any]) -> Candidate:
            resume_id = resume.get("id", "")
            title = resume.get("title", "")
            area = resume.get("area", {})
            experience = resume.get("total_experience", {})
            salary_data = resume.get("salary")
            updated_at = parse_date(resume.get("updated_at", ""))
            name = "Кандидат"
            age = resume.get("age")
            skills: List[str] = []
            if isinstance(resume.get("skill_set"), list):
                skills.extend([s for s in resume["skill_set"] if isinstance(s, str)])
            if isinstance(resume.get("key_skills"), list):
                skills.extend([s.get("name", "") for s in resume["key_skills"] if isinstance(s, dict)])
            last_work = {}
            exp_list = resume.get("experience")
            if isinstance(exp_list, list) and exp_list:
                last = exp_list[0]
                last_work = {
                    "name": last.get("company", ""),
                    "position": last.get("position", ""),
                    "description": last.get("description", ""),
                }
            salary = parse_salary(salary_data) if salary_data else None
            resume_url = f"https://hh.ru/resume/{resume_id}" if resume_id else None
            photo_url = None
            if resume.get("photo"):
                photo_url = resume["photo"].get("medium", resume["photo"].get("small"))
            has_cover_letter = resume.get("has_cover_letter", False)
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
                verified_skills=[],
                updated_at=updated_at,
                url=resume_url,
                photo_url=photo_url,
                has_cover_letter=has_cover_letter,
            )

        candidates: List[Candidate] = []
        for it in items:
            try:
                resume_obj = it.get("resume") if isinstance(it, dict) else None
                resume_id = None
                if isinstance(resume_obj, dict):
                    candidates.append(resume_to_candidate(resume_obj))
                    continue
                if isinstance(it, dict):
                    resume_id = it.get("resume_id")
                if not resume_id and isinstance(it, dict):
                    for l in it.get("links", []) or []:
                        if isinstance(l, dict) and l.get("rel") == "resume" and isinstance(l.get("href"), str):
                            import re
                            m = re.search(r"resumes/(\w+)", l["href"]) 
                            if m:
                                resume_id = m.group(1)
                                break
                if resume_id:
                    resume_data = gateway.make_service_request("hh_api", "GET", f"/resume/{resume_id}")
                    resume_payload = resume_data.get("resume", resume_data)
                    candidates.append(resume_to_candidate(resume_payload))
            except Exception:
                continue

        if not candidates:
            return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=0, candidates=[])

        # 4) Готовим батч мульти‑агентного анализа с полной информацией о вакансии
        vacancy_info = {}
        position_requirements = {"required_skills": []}
        
        if isinstance(vacancy_details, dict):
            vacancy_info = {
                "title": vacancy_details.get("name", ""),
                "description": vacancy_details.get("description", ""),
                "company": (vacancy_details.get("employer", {}) or {}).get("name", ""),
                "experience": (vacancy_details.get("experience", {}) or {}).get("name", ""),
                "employment": (vacancy_details.get("employment", {}) or {}).get("name", ""),
                "schedule": (vacancy_details.get("schedule", {}) or {}).get("name", ""),
                "salary": vacancy_details.get("salary", {}),
                "area": (vacancy_details.get("area", {}) or {}).get("name", ""),
            }
            
            # Извлекаем ключевые навыки из вакансии
            key_skills = vacancy_details.get("key_skills", [])
            if isinstance(key_skills, list):
                required_skills = [skill.get("name", "") for skill in key_skills if isinstance(skill, dict)]
                position_requirements = {
                    "required_skills": required_skills,
                    "experience_required": vacancy_info["experience"],
                    "employment_type": vacancy_info["employment"],
                    "schedule_type": vacancy_info["schedule"],
                    "description": vacancy_info["description"],
                }
        
        vacancy_title = vacancy_info.get("title", "")
        search_query = f"Вакансия: {vacancy_title}. Компания: {vacancy_info.get('company', '')}. Требования: {vacancy_info.get('description', '')[:500]}..."
        
        logger.info(f"Подготовка AI анализа для вакансии: {vacancy_title}")
        logger.info(f"Требования вакансии: {len(position_requirements.get('required_skills', []))} навыков, опыт: {position_requirements.get('experience_required', 'не указан')}")
        
        ma_requests: List[MultiAgentAnalysisRequest] = []
        for c in candidates:
            candidate_data = c.model_dump()
            ma_requests.append(MultiAgentAnalysisRequest(
                candidate_id=c.id,
                position_type="specific_vacancy",
                search_query=search_query,
                position_requirements=position_requirements,
                candidate_data=candidate_data,
                search_filters=vacancy_info,
            ))

        # 5) Отправляем батчи в AI Analysis (максимум 10 за раз)
        batch_resp = []
        try:
            batch_size = 10
            for i in range(0, len(ma_requests), batch_size):
                batch = ma_requests[i:i + batch_size]
                batch_data = [r.model_dump(mode='json') for r in batch]
                logger.info(f"Отправляем батч {i//batch_size + 1}: {len(batch)} кандидатов в AI analysis")
                
                partial_resp = gateway.make_service_request(
                    "ai_analysis", "POST", "/multi-agent/batch",
                    json=batch_data
                )
                
                if isinstance(partial_resp, list):
                    batch_resp.extend(partial_resp)
                else:
                    # Если ошибка в батче, добавляем пустые ответы
                    batch_resp.extend([{}] * len(batch))
                    
        except HTTPException as e:
            logger.error(f"Ошибка AI analysis: {e}")
            batch_resp = []

        # 6) Собираем итоговые оценки и мульти-агентные данные
        tops: List[Candidate] = []
        if isinstance(batch_resp, list) and len(batch_resp) == len(candidates):
            for i, br in enumerate(batch_resp):
                try:
                    if br and isinstance(br, dict):
                        ma = MultiAgentAnalysisResponse(**br)
                        candidates[i].score = float(ma.master_report.overall_score)
                        candidates[i].analysis_status = "completed"
                        candidates[i].multi_agent_data = br  # Сохраняем полные данные
                        candidates[i].analysis_summary = ma.master_report.recommendation
                    tops.append(candidates[i])
                except Exception as e:
                    logger.warning(f"Ошибка обработки AI ответа для кандидата {i}: {e}")
                    candidates[i].score = 0.0
                    candidates[i].analysis_status = "error"
                    tops.append(candidates[i])
        else:
            logger.warning(f"Несоответствие: получено {len(batch_resp)} ответов для {len(candidates)} кандидатов")
            for candidate in candidates:
                candidate.score = 0.0
                candidate.analysis_status = "failed"
            tops = candidates

        # 7) Финальная сортировка через ranking (fallback — локальная)
        try:
            rank_payload = RankingRequest(
                candidates=tops,
                search_request=SearchRequest(text=vacancy_title or "", page=1, per_page=len(tops))
            )
            ranked = gateway.make_service_request("ranking", "POST", "/rank", json=rank_payload.model_dump(mode='json'))
            ranked_candidates = ranked.get("ranked_candidates", []) if isinstance(ranked, dict) else []
            result_list: List[Candidate] = [Candidate(**c) if isinstance(c, dict) else c for c in ranked_candidates]
        except Exception:
            result_list = sorted(tops, key=lambda c: c.score or 0, reverse=True)

        if req.limit:
            result_list = result_list[: req.limit]

        return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=len(candidates), candidates=result_list)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка оркестрации ТОПа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка построения ТОПа")

# Проксирование получения откликов в hh_api
@app.post("/vacancy/responses")
async def vacancy_responses(req: VacancyTopRequest):
    """Получение откликов на вакансию через HH API"""
    try:
        return gateway.make_service_request("hh_api", "POST", "/vacancy/responses", json=req.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения откликов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения откликов")

# Проксирование деталей вакансии в hh_api
@app.post("/vacancy/details")
async def vacancy_details(req: VacancyTopRequest):
    try:
        return gateway.make_service_request("hh_api", "POST", "/vacancy/details", json=req.model_dump())
    except HTTPException:
        raise

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.now().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик общих исключений"""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()}
    )

@app.post("/config/save", response_model=ConfigSaveResponse)
async def save_config(request: ConfigSaveRequest):
    """Автоматическое сохранение конфигурации пользователя"""
    try:
        logger.info("🛠️ Получен запрос на сохранение конфигурации")
        
        # Проверяем валидность ключей
        if not request.hh_client_id or not request.hh_client_secret:
            return ConfigSaveResponse(
                success=False,
                message="❌ HH API Client ID и Client Secret обязательны"
            )
        
        if not request.openrouter_api_key or not request.openrouter_api_key.startswith("sk-or-v1-"):
            return ConfigSaveResponse(
                success=False,
                message="❌ OpenRouter API ключ должен начинаться с 'sk-or-v1-'"
            )
        
        # Пытаемся сохранить конфигурацию
        try:
            config_path = "/app/config/settings.yaml"
            
            # Создаем резервную копию если файл существует
            if os.path.exists(config_path):
                import shutil
                shutil.copy(config_path, f"{config_path}.backup")
            
            # Формируем новую конфигурацию
            config_content = f"""# Настройки AI-анализа (GPT-5)
ai_analysis:
  openrouter_api_key: "{request.openrouter_api_key}"
  base_url: "https://openrouter.ai/api/v1"
  model: "gpt-5-mini"
  site_url: "https://example.org"
  site_name: "RecruitmentWorkflow Suite"
  max_completion_tokens: 3000  # GPT-5 параметр
  temperature: 0.0
  retry_attempts: 3
  gpt5_features:
    default_verbosity: "medium"
    default_reasoning_effort: "medium"
  multi_agent:
    enabled: true
    parallel_processing: true
    agents:
      - "technical_skills"
      - "experience_relevance" 
      - "cultural_fit"
      - "growth_potential"
      - "resume_analysis"
      - "anomaly_detection"
  master_coordinator:
    enabled: true
    model: "gpt-5-mini"
    max_completion_tokens: 4000  # GPT-5 параметр
    verbosity: "high"
    reasoning_effort: "medium"
  proxy:
    enabled: false

cache:
  enabled: true
  max_size: 1000
  ttl: 3600

hh_api:
  base_url: "https://api.hh.ru"
  client_id: "{request.hh_client_id}"
  client_secret: "{request.hh_client_secret}"
  user_tokens:
    access_token: "{request.hh_access_token or 'ЗАМЕНИТЕ_НА_ВАШ_ACCESS_TOKEN'}"
    refresh_token: "{request.hh_refresh_token or 'ЗАМЕНИТЕ_НА_ВАШ_REFRESH_TOKEN'}"
    expires_at: "2025-12-31T23:59:59Z"

clickhouse:
  host: "hrhelp-clickhouse"
  port: 8123
  database: "hrhelp"
  connection:
    client_name: "hrhelp-app"

services:
  config:
    host: "0.0.0.0"
    port: 8004
  hh_api:
    host: "0.0.0.0"
    port: 8003
  ranking:
    host: "0.0.0.0"
    port: 8002
  ai_analysis:
    host: "0.0.0.0"
    port: 8005
  database:
    host: "0.0.0.0"
    port: 8006
  gateway:
    host: "0.0.0.0"
    port: 8088
"""
            
            # Сохраняем новую конфигурацию
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            logger.info("✅ Конфигурация успешно сохранена")
            
            return ConfigSaveResponse(
                success=True,
                message="✅ Готово! Настройки сохранены и применены автоматически.",
                config_applied=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения конфигурации: {e}")
            return ConfigSaveResponse(
                success=False,
                message=f"❌ Ошибка сохранения: {str(e)}"
            )
    
    except Exception as e:
        logger.error(f"❌ Общая ошибка при обработке запроса: {e}")
        return ConfigSaveResponse(
            success=False,
            message=f"❌ Внутренняя ошибка сервера: {str(e)}"
        )

# ===== ЭНДПОИНТЫ ДЛЯ СОЗДАНИЯ ВАКАНСИЙ =====

@app.get("/vacancy-builder/areas")
async def get_vacancy_areas():
    """Получение списка регионов для создания вакансий"""
    try:
        response = gateway.make_service_request("vacancy_builder", "GET", "/areas")
        return response
    except Exception as e:
        logger.error(f"Ошибка получения регионов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения списка регионов")

@app.get("/vacancy-builder/professional-roles")
async def get_vacancy_professional_roles():
    """Получение списка профессиональных ролей для создания вакансий"""
    try:
        response = gateway.make_service_request("vacancy_builder", "GET", "/professional-roles")
        return response
    except Exception as e:
        logger.error(f"Ошибка получения профессиональных ролей: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения профессиональных ролей")

@app.get("/vacancy-builder/templates")
async def get_vacancy_templates():
    """Получение списка шаблонов вакансий"""
    try:
        response = gateway.make_service_request("vacancy_builder", "GET", "/templates")
        return response
    except Exception as e:
        logger.error(f"Ошибка получения шаблонов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения шаблонов вакансий")

@app.get("/vacancy-builder/templates/{template_id}")
async def get_vacancy_template(template_id: str):
    """Получение шаблона вакансии по ID"""
    try:
        response = gateway.make_service_request("vacancy_builder", "GET", f"/templates/{template_id}")
        return response
    except Exception as e:
        logger.error(f"Ошибка получения шаблона {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения шаблона")

@app.post("/vacancy-builder/validate")
async def validate_vacancy_draft(draft: VacancyDraft):
    """Валидация черновика вакансии"""
    try:
        response = gateway.make_service_request("vacancy_builder", "POST", "/validate", json=draft.dict())
        return response
    except Exception as e:
        logger.error(f"Ошибка валидации вакансии: {e}")
        raise HTTPException(status_code=500, detail="Ошибка валидации вакансии")

@app.post("/vacancy-builder/create", response_model=VacancyCreationResponse)
async def create_vacancy(request: VacancyCreationRequest):
    """Создание вакансии на HeadHunter.ru"""
    try:
        logger.info(f"Gateway: Создание вакансии '{request.draft.name}'")
        
        # Отправляем запрос в сервис vacancy_builder
        response = gateway.make_service_request("vacancy_builder", "POST", "/create", json=request.dict())
        
        if response:
            logger.info(f"Gateway: Вакансия создана успешно")
            return VacancyCreationResponse(**response)
        else:
            logger.error("Gateway: Не удалось создать вакансию")
            return VacancyCreationResponse(
                success=False,
                message="Не удалось создать вакансию"
            )
            
    except Exception as e:
        logger.error(f"Gateway: Ошибка создания вакансии: {e}")
        return VacancyCreationResponse(
            success=False,
            message=f"Ошибка создания вакансии: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("gateway", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8000),
        reload=service_config.get("debug", False)
    )