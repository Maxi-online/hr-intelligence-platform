from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
import time

# Add the parent directory to the route to import the used modules
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
)
from shared.utils import setup_logging, load_config, parse_date, parse_salary

# Logging settings
logger = setup_logging("gateway-service")

app = FastAPI(
    title="API Gateway",
    description='Single entry point for all Candidate Analysis services',
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
        
        # Identify URL services according to environment
        is_docker = os.getenv("DOCKER_ENV") == "true"
        self.services = {
            name: f"http://{conf.get('docker_host', 'localhost')}:{conf.get('port')}" if is_docker 
                  else f"http://{conf.get('host', 'localhost')}:{conf.get('port')}"
            for name, conf in self.services_config.items()
        }
        
        self.rate_limit_requests = {}
        self.rate_limit_window = 60  # seconds
        self.max_requests_per_window = self.config.get("security", {}).get("rate_limit", 100)
    
    def check_rate_limit(self, client_ip: str) -> bool:
        'Rate limit check'
        current_time = time.time()
        
        if client_ip not in self.rate_limit_requests:
            self.rate_limit_requests[client_ip] = []
        
        # Removal of old requests
        self.rate_limit_requests[client_ip] = [
            req_time for req_time in self.rate_limit_requests[client_ip]
            if current_time - req_time < self.rate_limit_window
        ]
        
        # Control of limit
        if len(self.rate_limit_requests[client_ip]) >= self.max_requests_per_window:
            return False
        
        # Adding the current request
        self.rate_limit_requests[client_ip].append(current_time)
        return True
    
    def get_client_ip(self, request: Request) -> str:
        'Receive IP client'
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def make_service_request(self, service_name: str, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        'Response to microservice request'
        try:
            service_url = self.services.get(service_name)
            if not service_url:
                raise HTTPException(status_code=500, detail=f"Tools {service_name} not available")
            
            url = f"{service_url}{endpoint}"
            logger.info(f"Send a request to {service_name}: {method} {url}")
            
            if method.upper() == "GET":
                response = requests.get(url, **kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, **kwargs)
            elif method.upper() == "PUT":
                response = requests.put(url, **kwargs)
            elif method.upper() == "DELETE":
                response = requests.delete(url, **kwargs)
            else:
                raise HTTPException(status_code=400, detail='Non-supported method')
            
            logger.info(f"Response received from {service_name}: {response.status_code}")
            
            # HTTP error processing with correct coding
            if response.status_code >= 400:
                try:
                    error_detail = response.json().get("detail", response.text)
                except:
                    error_detail = response.text
                
                # Proxy the error code as it is
                logger.error(f"HTTP error {service_name}: {response.status_code} - {error_detail}")
                raise HTTPException(status_code=response.status_code, detail=error_detail)
            
            return response.json()
            
        except HTTPException:
            # Get HTTPExcept as it is.
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error of connection to the service {service_name}: {e}")
            raise HTTPException(status_code=503, detail=f"Tools {service_name} not available")
        except Exception as e:
            logger.error(f"an unexpected mistake: {e}")
            raise HTTPException(status_code=500, detail='The internal server error')
    
    def check_service_health(self, service_name: str) -> bool:
        'Service health check'
        try:
            health_response = self.make_service_request(service_name, "GET", "/health")
            return health_response.get("status") == "healthy"
        except Exception:
            return False
    
    def get_all_services_health(self) -> Dict[str, bool]:
        'Acquiring the status of all services'
        health_status = {}
        for service_name in self.services:
            health_status[service_name] = self.check_service_health(service_name)
        return health_status

# Initialization of API Gateway
gateway = APIGateway()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    'Middleware for rate limiting'
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
    'A simple test of access to the Gateway'
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    'Health check for gateway and all services'
    # Check only other services, excluding Gateway and Frontend
    services_health = {}
    for service_name, service_url in gateway.services.items():
        if service_name not in ["gateway", "frontend", "search"]:  # Remove self-checking, background and research
            services_health[service_name] = gateway.check_service_health(service_name)
    
    all_healthy = all(services_health.values()) if services_health else True
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/health/services")
async def get_services_health():
    'Acquiring the status of all services'
    services_health = {}
    for service_name, service_url in gateway.services.items():
        if service_name not in ["gateway", "frontend", "search"]:  # Remove self-checking, background and research
            services_health[service_name] = gateway.check_service_health(service_name)
    return {"services": services_health}

@app.get("/config")
async def get_config():
    'Catalyzing configuration'
    try:
        return gateway.make_service_request("config", "GET", "/config")
    except HTTPException:
        raise

@app.get("/config/{section}")
async def get_config_section(section: str):
    'Receive configuration section'
    try:
        return gateway.make_service_request("config", "GET", f"/config/{section}")
    except HTTPException:
        raise

@app.get("/filters")
async def get_search_filters():
    'Obtaining accessible search filters'
    # Return the basic filters without looking at the service
    return {
        "filters": {
            "area": {"name": 'Region', "type": "select", "options": []},
            "experience": {"name": 'Experience', "type": "select", "options": []},
            "salary": {"name": 'Wages', "type": "range", "min": 0, "max": 500000}
        }
    }

def create_search_request_gateway(
    text: Optional[str] = Query(None, description='Keywords for Search'),
    search_field: Optional[str] = Query("everywhere", description='Search Area'), 
    area: Optional[List[int]] = Query(None, description='ID of the regions'),
    salary: Optional[int] = Query(None, description='Maximum wage'),
    experience: Optional[str] = Query(None, description='Experience'),
    employment: Optional[List[str]] = Query(None, description='Type of employment'),
    schedule: Optional[List[str]] = Query(None, description='Time schedule'),
    professional_role: Optional[List[str]] = Query(None, description='Professional roles'),
    period: Optional[int] = Query(None, description='Days update period'),
    age_from: Optional[int] = Query(None, description='Age from'),
    age_to: Optional[int] = Query(None, description='Age before'), 
    gender: Optional[str] = Query(None, description='Gender'),
    language_id: Optional[str] = Query(None, description='ID Language'),
    language_level: Optional[str] = Query(None, description='Minimum language level'),
    page: int = Query(1, description='Page number'),
    per_page: int = Query(20, description='Number on page')
) -> SearchRequest:
    'Created SearchRequest from quary parameters in Gateway'
    
    # Processing of language requirements
    language_requirements = None
    if language_id and language_level:
        from shared.models import LanguageRequirement, LanguageLevel
        try:
            language_requirements = [LanguageRequirement(
                language_id=language_id,
                level=LanguageLevel(language_level)
            )]
        except ValueError:
            # If the language is wrong, ignore it.
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
    'Search for candidates via GET request'
    try:
        # Transform SearchRequest to GET Query Options
        params = search_request.model_dump(exclude_none=True)
        return gateway.make_service_request(
            "search", 
            "GET", 
            "/search", 
            params=params
        )
    except HTTPException:
        raise

@app.get("/candidates/{candidate_id}")
async def get_candidate_details(candidate_id: str):
    'Obtaining detailed information on the candidate through HH API'
    try:
        # Directly contact HH API for these summaries
        return gateway.make_service_request("hh_api", "GET", f"/resume/{candidate_id}")
    except HTTPException:
        raise

@app.post("/top-candidates")
async def get_top_candidates(search_request: SearchRequest, limit: int = 10):
    'To receive the top of the candidates'
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
    'Retrieving the list of regions'
    try:
        return gateway.make_service_request("hh_api", "GET", "/areas")
    except HTTPException:
        raise

@app.get("/professional-roles")
async def get_professional_roles():
    'Getting a list of professional roles'
    try:
        return gateway.make_service_request("hh_api", "GET", "/professional-roles")
    except HTTPException:
        raise

@app.get("/languages")
async def get_languages():
    'Getting a list of languages'
    try:
        return gateway.make_service_request("hh_api", "GET", "/languages")
    except HTTPException:
        raise

@app.get("/dictionaries")
async def get_dictionaries():
    'Collection of all handbooks'
    try:
        return gateway.make_service_request("hh_api", "GET", "/dictionaries")
    except HTTPException:
        raise

@app.get("/oauth/authorize-url")
async def get_authorize_url(redirect_uri: str, state: str = None):
    'Obtaining URL to authorise user in HH.ru'
    try:
        params = {"redirect_uri": redirect_uri}
        if state:
            params["state"] = state
        return gateway.make_service_request("hh_api", "GET", "/oauth/authorize-url", params=params)
    except HTTPException:
        raise

@app.post("/oauth/token")
async def exchange_code_for_token(code: str, redirect_uri: str):
    'Exchange of authoration code on access token'
    try:
        data = {"code": code, "redirect_uri": redirect_uri}
        return gateway.make_service_request("hh_api", "POST", "/oauth/token", data=data)
    except HTTPException:
        raise

@app.post("/oauth/refresh")
async def refresh_token():
    'Update access token via refresh token'
    try:
        return gateway.make_service_request("hh_api", "POST", "/oauth/refresh")
    except HTTPException:
        raise

@app.post("/settings/auth")
async def update_auth_settings(auth_settings: dict):
    'Update of authentication settings'
    try:
        # Update settings in HH API service
        hh_response = gateway.make_service_request("hh_api", "POST", "/settings/auth", json=auth_settings)
        
        # Update the settings in the AI Analysis service
        ai_response = gateway.make_service_request("ai_analysis", "POST", "/settings/auth", json=auth_settings)
        
        return {
            "status": "success",
            "message": 'Authentication settings updated',
            "hh_api_updated": hh_response.get("status") == "success",
            "ai_analysis_updated": ai_response.get("status") == "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error of Update: {e}")
        raise HTTPException(status_code=500, detail='Error of Update')

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
    'Collection of database statistics'
    try:
        stats = gateway.make_service_request("database", "GET", "/statistics")
        return {"statistics": stats}
    except HTTPException:
        raise

@app.post("/database/candidates")
async def create_candidate(candidate_data: Dict[str, Any]):
    'Establishment of a candidate in the database'
    try:
        return gateway.make_service_request("database", "POST", "/candidates", json=candidate_data)
    except HTTPException:
        raise

@app.get("/database/candidates/{candidate_id}")
async def get_candidate_from_db(candidate_id: str):
    'Retrieving a candidate from the database'
    try:
        return gateway.make_service_request("database", "GET", f"/candidates/{candidate_id}")
    except HTTPException:
        raise

@app.put("/database/candidates/{candidate_id}/searched")
async def update_candidate_search_count(candidate_id: str):
    'Update of the searcher'
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

# == sync, corrected by elderman == @elder_man
@app.post("/vacancy/top", response_model=VacancyTopResponse)
async def build_vacancy_top(req: VacancyTopRequest):
    'Building a TOP without a search service: Orchestra directly to Gateway.'
    try:
        # (1) Receive the details of the vacancy
        vacancy_details = gateway.make_service_request("hh_api", "POST", "/vacancy/details", json=req.model_dump())
        
        # (2) Reactions to the vacancy
        responses_data = gateway.make_service_request("hh_api", "POST", "/vacancy/responses", json=req.model_dump())
        vacancy_id = responses_data.get("vacancy_id", "")
        items = responses_data.get("items", [])

        # (3) Collecting candidates (convergence from executive summary)
        def resume_to_candidate(resume: Dict[str, Any]) -> Candidate:
            resume_id = resume.get("id", "")
            title = resume.get("title", "")
            area = resume.get("area", {})
            experience = resume.get("total_experience", {})
            salary_data = resume.get("salary")
            updated_at = parse_date(resume.get("updated_at", ""))
            name = 'Candidature'
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

        # (4) Prepare a multi-agent analysis booth with full vacancy information
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
            
            # We gain key skills from the vacation
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
        search_query = f"Vacancy: {vacancy_title}. Company: {vacancy_info.get('company', '')}. Requirements: {vacancy_info.get('description', '')[:500]}..."
        
        logger.info(f"Preparation of AI vacancy analysis: {vacancy_title}")
        logger.info(f"Vacancy requirements: {len(position_requirements.get('required_skills', []))} Skills, experience: {position_requirements.get('experience_required', 'Not specified')}")
        
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

        # (5) Send the boots to AI Analysis (maximum 10 at a time)
        batch_resp = []
        try:
            batch_size = 10
            for i in range(0, len(ma_requests), batch_size):
                batch = ma_requests[i:i + batch_size]
                batch_data = [r.model_dump(mode='json') for r in batch]
                logger.info(f"Sending the booth. {i//batch_size + 1}: {len(batch)} of candidates for the AI analisis")
                
                partial_resp = gateway.make_service_request(
                    "ai_analysis", "POST", "/multi-agent/batch",
                    json=batch_data
                )
                
                if isinstance(partial_resp, list):
                    batch_resp.extend(partial_resp)
                else:
                    # If you have a mistake, add empty answers
                    batch_resp.extend([{}] * len(batch))
                    
        except HTTPException as e:
            logger.error(f"The error of AI analysis: {e}")
            batch_resp = []

        # (6) Collecting final estimates and multi-agent data
        tops: List[Candidate] = []
        if isinstance(batch_resp, list) and len(batch_resp) == len(candidates):
            for i, br in enumerate(batch_resp):
                try:
                    if br and isinstance(br, dict):
                        ma = MultiAgentAnalysisResponse(**br)
                        candidates[i].score = float(ma.master_report.overall_score)
                        candidates[i].analysis_status = "completed"
                        candidates[i].multi_agent_data = br  # Save complete data.
                        candidates[i].analysis_summary = ma.master_report.recommendation
                    tops.append(candidates[i])
                except Exception as e:
                    logger.warning(f"Mistake of AI response for the candidate {i}: {e}")
                    candidates[i].score = 0.0
                    candidates[i].analysis_status = "error"
                    tops.append(candidates[i])
        else:
            logger.warning(f"Non-conformity: received {len(batch_resp)} responses to the {len(candidates)} Candidates")
            for candidate in candidates:
                candidate.score = 0.0
                candidate.analysis_status = "failed"
            tops = candidates

        # (7) Final sorting through the ringing (fallback))
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
        logger.error(f"The error of the top orchestra: {e}")
        raise HTTPException(status_code=500, detail='Error of building top')

# hh_api exclamation of vacancy details
@app.post("/vacancy/details")
async def vacancy_details(req: VacancyTopRequest):
    try:
        return gateway.make_service_request("hh_api", "POST", "/vacancy/details", json=req.model_dump())
    except HTTPException:
        raise

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    'HTTP exemption processor'
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.now().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    'General exemption processor'
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()}
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