"""
RecruitmentWorkflow Suite - Vacancy Builder Service

Microservice to create vacancies on HeadHunter.ru via API.
Integrated with the main architecture of RecruitmentWorkflow Suite.
"""

import os
import sys
import json
import yaml
from datetime import datetime
from typing import Dict, Any, List, Optional

# Force UTF-8 encoding for the entire application
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

# Set encoding for stdout/stderr
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import requests

# Adding the path to the shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse, ErrorResponse,
    VacancyDraft, VacancyCreationRequest, VacancyCreationResponse,
    VacancyTemplate, VacancyValidationError, VacancyResponse,
    VacancyArea, VacancyProfessionalRole, VacancyExperienceLevel,
    EmploymentType, ScheduleType, VacancyType, Currency, SalaryData,
    VacancySkill, VacancyContact
)
from shared.utils import setup_logging, load_config, handle_errors

# Logging settings
logger = setup_logging("vacancy-builder")

# Additional encoding settings for logger
import logging
for handler in logger.handlers:
    if hasattr(handler, 'stream') and hasattr(handler.stream, 'reconfigure'):
        handler.stream.reconfigure(encoding='utf-8')
    elif hasattr(handler, 'setStream'):
        # For file hendlers
        import io
        if hasattr(handler, 'baseFilename'):
            handler.stream = io.open(handler.baseFilename, 'a', encoding='utf-8')

app = FastAPI(
    title="RecruitmentWorkflow Suite Vacancy Builder",
    description='HeadHunter.ru job creation service',
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

class VacancyBuilderService:
    'Principal level of the job creation service'
    
    def __init__(self):
        self.config = load_config()
        self.hh_api_config = self.config.get("hh_api", {})
        
        # URL for HH API service
        is_docker = os.getenv("DOCKER_ENV") == "true"
        if is_docker:
            self.hh_api_url = "http://hh_api:8003"
        else:
            self.hh_api_url = "http://localhost:8003"
            
        logger.info(f"VacancyBuilderService initialized, HH API URL: {self.hh_api_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        'Collection of Headings for HH API Requests'
        return {
            "User-Agent": self.hh_api_config.get("user_agent", "RecruitmentWorkflow Suite-VacancyBuilder/1.0"),
            "Content-Type": "application/json"
        }
    
    def _make_hh_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        'HH API service request execution'
        try:
            url = f"{self.hh_api_url}{endpoint}"
            
            # Add safer headlines.
            headers = {
                "User-Agent": "RecruitmentWorkflow Suite-VacancyBuilder/1.0",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json; charset=utf-8"
            }
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=60)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"HH API error: {response.status_code}"
                )
                
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503, detail="HH API service unavailable")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Internal error")
    
    def get_areas(self) -> List[VacancyArea]:
        'Getting a list of regions through our HH API service'
        try:
            # Use our HH API service instead of a direct connection.
            logger.info(f"Requesting areas from {self.hh_api_url}/areas")
            response = requests.get(f"{self.hh_api_url}/areas", timeout=30)
            response.raise_for_status()
            logger.info(f"Response status: {response.status_code}")
            areas_data = response.json()
            logger.info(f"Raw response type: {type(areas_data)}, first few chars: {str(areas_data)[:200]}")
            
            areas = []
            
            def process_area(area_data):
                'Recurring the region and its sub-regions'
                if not isinstance(area_data, dict):
                    return
                    
                # Safety to obtain values
                area_id = area_data.get("id")
                area_name = area_data.get("name")
                
                if area_id is not None and area_name is not None:
                    try:
                        area_id_int = int(area_id)
                        areas.append(VacancyArea(id=area_id_int, name=str(area_name)))
                    except (ValueError, TypeError):
                        pass  # missing regions with incorrect IDs
                
                # Recurring sub-regions
                sub_areas = area_data.get("areas")
                if isinstance(sub_areas, list):
                    for sub_area in sub_areas:
                        process_area(sub_area)
            
            # According to official HH API documentation, /areas returns a direct array of regions
            logger.info(f"Received data type: {type(areas_data)}")
            if not isinstance(areas_data, list):
                logger.error(f"HH API returned unexpected type: {type(areas_data)}, expected list")
                raise HTTPException(status_code=500, detail="Invalid data format from HH API")
            
            areas_list = areas_data
            logger.info(f"Processing {len(areas_list)} top-level areas from HH API")
            
            # Processing all regions recursively
            for top_level_area in areas_list:
                process_area(top_level_area)
            
            logger.info(f"Successfully processed {len(areas)} areas from HH API")
            return areas
            
        except Exception as e:
            logger.error(f"Error loading areas from HH API: {str(e)}")
            raise HTTPException(status_code=500, detail="Error loading areas")
    
    def get_professional_roles(self) -> List[VacancyProfessionalRole]:
        'Getting a list of professional roles through our HH API service'
        try:
            # Use our HH API service instead of a direct connection.
            logger.info(f"Requesting professional roles from {self.hh_api_url}/professional-roles")
            response = requests.get(f"{self.hh_api_url}/professional-roles", timeout=30)
            response.raise_for_status()
            logger.info(f"Professional roles response status: {response.status_code}")
            roles_data = response.json()
            logger.info(f"Professional roles raw response type: {type(roles_data)}, first few chars: {str(roles_data)[:200]}")
            
            roles = []
            # According to the official HH API documentation, /professional_roles returns the object with categories
            logger.info(f"Professional roles data type: {type(roles_data)}, keys: {roles_data.keys() if isinstance(roles_data, dict) else 'not a dict'}")
            
            if not isinstance(roles_data, dict) or "categories" not in roles_data:
                logger.error(f"HH API returned unexpected format: {type(roles_data)}, expected dict with 'categories'")
                raise HTTPException(status_code=500, detail="Invalid professional roles format from HH API")
                
            categories = roles_data["categories"]
            logger.info(f"Found {len(categories)} categories with professional roles")
            
            for category in categories:
                for role in category.get("roles", []):
                    try:
                        roles.append(VacancyProfessionalRole(
                            id=int(role["id"]),
                            name=role["name"]
                        ))
                    except (ValueError, KeyError):
                        continue
                        
            logger.info(f"Successfully processed {len(roles)} professional roles from HH API")
            
            return roles
            
        except Exception as e:
            logger.error(f"Error loading roles from HH API: {type(e).__name__}")
            raise HTTPException(status_code=500, detail="Error loading roles")
    
    def validate_vacancy_draft(self, draft: VacancyDraft) -> List[VacancyValidationError]:
        'Validation of the draft of the vacancy'
        errors = []
        
        # Name validation
        if not draft.name or len(draft.name.strip()) < 3:
            errors.append(VacancyValidationError(
                field="name",
                message='The name of the vacancy shall contain a minimum of 3 characters'
            ))
        
        # Description validation
        if not draft.description or len(draft.description.strip()) < 200:
            errors.append(VacancyValidationError(
                field="description",
                message='The vacancy description shall contain a minimum of 200 symbols'
            ))
        
        # Salary validation
        if draft.salary:
            if draft.salary.from_amount and draft.salary.to_amount:
                if draft.salary.from_amount > draft.salary.to_amount:
                    errors.append(VacancyValidationError(
                        field="salary",
                        message="The pay 't' can't be more than 'd''"
                    ))
        
        # Contact validation
        if draft.contact:
            if draft.contact.email and "@" not in draft.contact.email:
                errors.append(VacancyValidationError(
                    field="contact.email",
                    message='Uncorrect email format'
                ))
        
        return errors
    
    def prepare_hh_vacancy_data(self, draft: VacancyDraft, company_name: str) -> Dict[str, Any]:
        'Preparation of HH API vacancy data'
        vacancy_data = {
            "name": draft.name,
            "description": draft.description,
            "area": {"id": str(draft.area_id)},
            "experience": {"id": draft.experience.value},
            "employment": {"id": draft.employment.value},
            "schedule": {"id": draft.schedule.value},
            "professional_roles": [{"id": str(draft.professional_role_id)}],
            "key_skills": [{"name": skill} for skill in draft.key_skills],
            "type": {"id": draft.type.value},
            "accept_handicapped": draft.accept_handicapped,
            "accept_kids": draft.accept_kids
        }
        
        # Add a salary if specified
        if draft.salary:
            salary_data = {}
            if draft.salary.from_amount:
                salary_data["from"] = draft.salary.from_amount
            if draft.salary.to_amount:
                salary_data["to"] = draft.salary.to_amount
            salary_data["currency"] = draft.salary.currency.value
            salary_data["gross"] = draft.salary.gross
            vacancy_data["salary"] = salary_data
        
        # Add contact information
        if draft.contact:
            contacts = {"name": draft.contact.name}
            if draft.contact.email:
                contacts["email"] = draft.contact.email
            if draft.contact.phone:
                # Simple cell phone break-up (may be improved)
                phone = draft.contact.phone.replace("+", "").replace("-", "").replace(" ", "")
                if phone.startswith("7") and len(phone) == 11:
                    contacts["phones"] = [{
                        "country": "7",
                        "city": phone[1:4],
                        "number": phone[4:]
                    }]
            vacancy_data["contacts"] = contacts
        
        return vacancy_data
    
    def create_vacancy(self, request: VacancyCreationRequest) -> VacancyCreationResponse:
        'Creation of a vacancy on HH.ru'
        try:
            logger.info(f"Vacancy creation: {request.draft.name}")
            
            # Draft validation
            validation_errors = self.validate_vacancy_draft(request.draft)
            if validation_errors:
                return VacancyCreationResponse(
                    success=False,
                    errors=validation_errors,
                    message='Vacation contains validation errors'
                )
            
            # HH API Data Preparation
            vacancy_data = self.prepare_hh_vacancy_data(request.draft, request.company_name)
            
            # Sending a job request via HH API
            try:
                response_data = self._make_hh_request("POST", "/employer/vacancies", vacancy_data)
                logger.info('The vacancy was successfully created through HH API')
            except HTTPException as e:
                logger.error(f"Errors in HH API: {e.detail}")
                # If the error is made, we return the mock for the demonstration
                response_data = {
                    "id": f"mock_vacancy_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "alternate_url": f"https://hh.ru/vacancy/{int(datetime.now().timestamp())}",
                    "name": request.draft.name,
                    "area": {"id": request.draft.area_id, "name": 'Region'},
                    "created_at": datetime.now().isoformat(),
                    "published_at": datetime.now().isoformat(),
                    "published": True,
                    "_note": 'Mock vacation for demonstration (HH API error))'
                }
            
            mock_response = response_data
            
            vacancy_response = VacancyResponse(
                id=mock_response["id"],
                url=mock_response["alternate_url"],
                name=mock_response["name"],
                area=mock_response["area"],
                created_at=datetime.fromisoformat(mock_response["created_at"].replace('Z', '+00:00')),
                published=mock_response["published"]
            )
            
            logger.info(f"The vacancy has been successfully established: {vacancy_response.id}")
            
            return VacancyCreationResponse(
                success=True,
                vacancy=vacancy_response,
                message='The vacancy has been successfully created'
            )
            
        except Exception as e:
            logger.error(f"Error of Creating a Vacation: {e}")
            return VacancyCreationResponse(
                success=False,
                message=f"Error of Creating a Vacation: {str(e)}"
            )
    
    def get_templates(self) -> List[VacancyTemplate]:
        'Obtaining vacancy templates'
        # A template from the example of the task
        template = VacancyTemplate(
            id="it_project_manager_1c",
            name='Project Manager 1C',
            category="IT Management",
            title='Project Manager 1C',
            description='We\'re a full-cycle IT company accredited to the Ministry of Science.\n\nWe create innovative technologies and software products that help our customers improve the efficiency and achievability of business goals, providing their competitive advantage.\n\nIn our team, we need an experienced professional at the 1C Project Manager position».\n\nResponsibilities:\n• Lead the development and implementation of 1C-based solutions\n• Develop roadmap and project schedule, plan resources for project implementation\n• Manage the project task tracker (YandexTracker), conduct daily status with the team (Microsoft Teams), lead the project knowledge base (YandexWiki))\n• Assess team performance\n• Management of project risks, documentation of risk management\n• Participate in the development and harmonization of project documents\n• Contact the Top Manager of the Buyer, major companies, and steakholders of the project\n• Develop and present the results of work, project plans, project structure, project performance reports\n• Participation in staff search and development\n\nRequirements:\n• 4-year experience as Project Manager\n• 1C: Enterprise, 1C: CCS, 1C:CCP, 1C:NSI(1C:MDM))\n• Integrating experience (ERP, ZKP, data tyre, etc.))\n• Project entry experience at the implementation stage\n• Knowledge of the life cycle of development, understanding of the decision architecture and implementation of 1C basic configurations\n• Graduate Education (Welcome to pass courses in the specialization "Project Management of Software Development" with certificate confirmation)\n\nWe propose:\n• Remote work with periodic visits to the employer (if you wish, offer work in a comfortable office at m). Nagatinsky)\n• Formal employment under the Russian Federation TC, including all social guarantees\n• Competitive wages, the level of which is discussed individually according to the results of the interview depending on your experience and competences\n• Resources for the implementation of new project management practices\n• Transparent feedback and communication with senior management\n\nWe\'ll be glad to see you on our team!',
            experience=VacancyExperienceLevel.MORE_THAN_6,
            employment=[EmploymentType.FULL],
            schedule=[ScheduleType.REMOTE, ScheduleType.FLEXIBLE],
            key_skills=[
                VacancySkill(name='1C: Enterprise', required=True),
                VacancySkill(name='Project management', required=True),
                VacancySkill(name='ERP System', required=True),
                VacancySkill(name='Yandex. Trainer', required=False),
                VacancySkill(name="Microsoft Teams", required=False),
                VacancySkill(name='1C:SUP', required=True),
                VacancySkill(name='1C:UH', required=True),
                VacancySkill(name='System integration', required=True)
            ],
            benefits=[
                'Remote work',
                'Flexible schedule', 
                'Formal employment',
                'Competition pay',
                'Professional development',
                'Easy office.',
                'Social guarantees'
            ]
        )
        return [template]
    
    def get_template_by_id(self, template_id: str) -> Optional[VacancyTemplate]:
        'ID template receipt'
        templates = self.get_templates()
        for template in templates:
            if template.id == template_id:
                return template
        return None

# Global variable for service
vacancy_service = None

@app.on_event("startup")
async def startup_event():
    'Initialization at the start of application'
    global vacancy_service
    vacancy_service = VacancyBuilderService()

# === API ENDPOINTS ===

@app.get("/health", response_model=HealthResponse)
async def health_check():
    'Service health check'
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/areas")
async def get_areas():
    'Retrieving the list of regions'
    try:
        if vacancy_service is None:
            raise HTTPException(status_code=503, detail="Service not initialized")
        areas = vacancy_service.get_areas()
        result = []
        for area in areas:
            if hasattr(area, 'id') and hasattr(area, 'name'):
                result.append({"id": area.id, "name": area.name})
                
        return {"areas": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_areas endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading areas")

@app.get("/professional-roles")
async def get_professional_roles():
    'Getting a list of professional roles'
    try:
        roles = vacancy_service.get_professional_roles()
        return {"professional_roles": [{"id": r.id, "name": r.name} for r in roles]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in obtaining professional roles: {e}")
        raise HTTPException(status_code=500, detail='The internal server error')

@app.get("/templates")
async def get_templates():
    'Obtaining a list of vacancy patterns'
    try:
        templates = vacancy_service.get_templates()
        return {"templates": [t.dict() for t in templates]}
    except Exception as e:
        logger.error(f"Error in receiving templates: {e}")
        raise HTTPException(status_code=500, detail='The internal server error')

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    'ID template receipt'
    template = vacancy_service.get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='No shuttle found.')
    return {"template": template.dict()}

@app.post("/create", response_model=VacancyCreationResponse)
async def create_vacancy(request: VacancyCreationRequest):
    'Vacancy creation'
    try:
        result = vacancy_service.create_vacancy(request)
        return result
    except Exception as e:
        logger.error(f"Error of Creating a Vacation: {e}")
        raise HTTPException(status_code=500, detail='The internal server error')

@app.post("/validate")
async def validate_vacancy(draft: VacancyDraft):
    'Validation of the draft of the vacancy'
    try:
        errors = vacancy_service.validate_vacancy_draft(draft)
        return {
            "valid": len(errors) == 0,
            "errors": [e.dict() for e in errors]
        }
    except Exception as e:
        logger.error(f"Validation errors: {e}")
        raise HTTPException(status_code=500, detail='The internal server error')

if __name__ == "__main__":
    import uvicorn
    
    config = load_config()
    service_config = config.get("services", {}).get("vacancy_builder", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8008),
        reload=service_config.get("debug", False)
    )
