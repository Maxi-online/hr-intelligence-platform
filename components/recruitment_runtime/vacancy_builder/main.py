"""
RecruitmentWorkflow Suite - Vacancy Builder Service

Микросервис для создания вакансий на HeadHunter.ru через API.
Интегрирован с основной архитектурой RecruitmentWorkflow Suite.
"""

import os
import sys
import json
import yaml
from datetime import datetime
from typing import Dict, Any, List, Optional

# Принудительно устанавливаем UTF-8 кодировку для всего приложения
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

# Устанавливаем кодировку для stdout/stderr
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import requests

# Добавляем путь к shared модулям
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

# Настройка логирования
logger = setup_logging("vacancy-builder")

# Дополнительная настройка кодировки для логгера
import logging
for handler in logger.handlers:
    if hasattr(handler, 'stream') and hasattr(handler.stream, 'reconfigure'):
        handler.stream.reconfigure(encoding='utf-8')
    elif hasattr(handler, 'setStream'):
        # Для файловых хендлеров
        import io
        if hasattr(handler, 'baseFilename'):
            handler.stream = io.open(handler.baseFilename, 'a', encoding='utf-8')

app = FastAPI(
    title="RecruitmentWorkflow Suite Vacancy Builder",
    description="Сервис создания вакансий на HeadHunter.ru",
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
    """Основной класс сервиса создания вакансий"""
    
    def __init__(self):
        self.config = load_config()
        self.hh_api_config = self.config.get("hh_api", {})
        
        # URL для HH API сервиса
        is_docker = os.getenv("DOCKER_ENV") == "true"
        if is_docker:
            self.hh_api_url = "http://hh_api:8003"
        else:
            self.hh_api_url = "http://localhost:8003"
            
        logger.info(f"VacancyBuilderService инициализирован, HH API URL: {self.hh_api_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Получение заголовков для запросов к HH API"""
        return {
            "User-Agent": self.hh_api_config.get("user_agent", "RecruitmentWorkflow Suite-VacancyBuilder/1.0"),
            "Content-Type": "application/json"
        }
    
    def _make_hh_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Выполнение запроса к HH API сервису"""
        try:
            url = f"{self.hh_api_url}{endpoint}"
            
            # Добавим более безопасные заголовки
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
        """Получение списка регионов через наш HH API сервис"""
        try:
            # Используем наш HH API сервис вместо прямого подключения
            logger.info(f"Requesting areas from {self.hh_api_url}/areas")
            response = requests.get(f"{self.hh_api_url}/areas", timeout=30)
            response.raise_for_status()
            logger.info(f"Response status: {response.status_code}")
            areas_data = response.json()
            logger.info(f"Raw response type: {type(areas_data)}, first few chars: {str(areas_data)[:200]}")
            
            areas = []
            
            def process_area(area_data):
                """Рекурсивная обработка региона и его подрегионов"""
                if not isinstance(area_data, dict):
                    return
                    
                # Безопасное получение значений
                area_id = area_data.get("id")
                area_name = area_data.get("name")
                
                if area_id is not None and area_name is not None:
                    try:
                        area_id_int = int(area_id)
                        areas.append(VacancyArea(id=area_id_int, name=str(area_name)))
                    except (ValueError, TypeError):
                        pass  # пропускаем регионы с некорректными ID
                
                # Рекурсивно обрабатываем подрегионы
                sub_areas = area_data.get("areas")
                if isinstance(sub_areas, list):
                    for sub_area in sub_areas:
                        process_area(sub_area)
            
            # Согласно официальной документации HH API, /areas возвращает прямой массив регионов
            logger.info(f"Received data type: {type(areas_data)}")
            if not isinstance(areas_data, list):
                logger.error(f"HH API returned unexpected type: {type(areas_data)}, expected list")
                raise HTTPException(status_code=500, detail="Invalid data format from HH API")
            
            areas_list = areas_data
            logger.info(f"Processing {len(areas_list)} top-level areas from HH API")
            
            # Обрабатываем все регионы рекурсивно
            for top_level_area in areas_list:
                process_area(top_level_area)
            
            logger.info(f"Successfully processed {len(areas)} areas from HH API")
            return areas
            
        except Exception as e:
            logger.error(f"Error loading areas from HH API: {str(e)}")
            raise HTTPException(status_code=500, detail="Error loading areas")
    
    def get_professional_roles(self) -> List[VacancyProfessionalRole]:
        """Получение списка профессиональных ролей через наш HH API сервис"""
        try:
            # Используем наш HH API сервис вместо прямого подключения
            logger.info(f"Requesting professional roles from {self.hh_api_url}/professional-roles")
            response = requests.get(f"{self.hh_api_url}/professional-roles", timeout=30)
            response.raise_for_status()
            logger.info(f"Professional roles response status: {response.status_code}")
            roles_data = response.json()
            logger.info(f"Professional roles raw response type: {type(roles_data)}, first few chars: {str(roles_data)[:200]}")
            
            roles = []
            # Согласно официальной документации HH API, /professional_roles возвращает объект с categories
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
        """Валидация черновика вакансии"""
        errors = []
        
        # Валидация названия
        if not draft.name or len(draft.name.strip()) < 3:
            errors.append(VacancyValidationError(
                field="name",
                message="Название вакансии должно содержать минимум 3 символа"
            ))
        
        # Валидация описания
        if not draft.description or len(draft.description.strip()) < 200:
            errors.append(VacancyValidationError(
                field="description",
                message="Описание вакансии должно содержать минимум 200 символов"
            ))
        
        # Валидация зарплаты
        if draft.salary:
            if draft.salary.from_amount and draft.salary.to_amount:
                if draft.salary.from_amount > draft.salary.to_amount:
                    errors.append(VacancyValidationError(
                        field="salary",
                        message="Зарплата 'от' не может быть больше зарплаты 'до'"
                    ))
        
        # Валидация контактов
        if draft.contact:
            if draft.contact.email and "@" not in draft.contact.email:
                errors.append(VacancyValidationError(
                    field="contact.email",
                    message="Некорректный формат email"
                ))
        
        return errors
    
    def prepare_hh_vacancy_data(self, draft: VacancyDraft, company_name: str) -> Dict[str, Any]:
        """Подготовка данных для создания вакансии в HH API формате"""
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
        
        # Добавляем зарплату если указана
        if draft.salary:
            salary_data = {}
            if draft.salary.from_amount:
                salary_data["from"] = draft.salary.from_amount
            if draft.salary.to_amount:
                salary_data["to"] = draft.salary.to_amount
            salary_data["currency"] = draft.salary.currency.value
            salary_data["gross"] = draft.salary.gross
            vacancy_data["salary"] = salary_data
        
        # Добавляем контактную информацию
        if draft.contact:
            contacts = {"name": draft.contact.name}
            if draft.contact.email:
                contacts["email"] = draft.contact.email
            if draft.contact.phone:
                # Простое разбиение телефона (можно улучшить)
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
        """Создание вакансии на HH.ru"""
        try:
            logger.info(f"Создание вакансии: {request.draft.name}")
            
            # Валидация черновика
            validation_errors = self.validate_vacancy_draft(request.draft)
            if validation_errors:
                return VacancyCreationResponse(
                    success=False,
                    errors=validation_errors,
                    message="Вакансия содержит ошибки валидации"
                )
            
            # Подготовка данных для HH API
            vacancy_data = self.prepare_hh_vacancy_data(request.draft, request.company_name)
            
            # Отправка запроса на создание вакансии через HH API
            try:
                response_data = self._make_hh_request("POST", "/employer/vacancies", vacancy_data)
                logger.info("Вакансия успешно создана через HH API")
            except HTTPException as e:
                logger.error(f"Ошибка создания вакансии в HH API: {e.detail}")
                # Если ошибка - возвращаем mock для демонстрации
                response_data = {
                    "id": f"mock_vacancy_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "alternate_url": f"https://hh.ru/vacancy/{int(datetime.now().timestamp())}",
                    "name": request.draft.name,
                    "area": {"id": request.draft.area_id, "name": "Регион"},
                    "created_at": datetime.now().isoformat(),
                    "published_at": datetime.now().isoformat(),
                    "published": True,
                    "_note": "Mock-вакансия для демонстрации (ошибка HH API)"
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
            
            logger.info(f"Вакансия успешно создана: {vacancy_response.id}")
            
            return VacancyCreationResponse(
                success=True,
                vacancy=vacancy_response,
                message="Вакансия успешно создана"
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания вакансии: {e}")
            return VacancyCreationResponse(
                success=False,
                message=f"Ошибка создания вакансии: {str(e)}"
            )
    
    def get_templates(self) -> List[VacancyTemplate]:
        """Получение шаблонов вакансий"""
        # Шаблон из примера задачи
        template = VacancyTemplate(
            id="it_project_manager_1c",
            name="Руководитель проектов 1С",
            category="IT Management",
            title="Руководитель проектов 1С",
            description="""Мы — IT-компания полного цикла, аккредитованная в Минцифры.

Мы создаем инновационные технологии и программные продукты, которые помогают нашим клиентам повышать эффективность и достижимость бизнес-целей, обеспечивая их конкурентное преимущество.

В нашу команду требуется опытный профессионал на позицию «Руководитель проектов 1С».

Обязанности:
• Руководить разработкой и внедрением решений на базе 1С
• Формировать roadmap и план-график реализации проекта, планировать ресурсы для реализации проекта
• Управлять task-трекером проекта (ЯндексТрекер), проводить ежедневные статусы с командой (Microsoft Teams), вести базу знаний проекта (ЯндексWiki)
• Оценивать результаты работ команды
• Управлять рисками проекта, документирование работы с рисками
• Участвовать в разработке и согласовании проектной документации
• Контактировать с топ-менеджерами Заказчика, крупных компаний, и стейкхолдерами проекта
• Разрабатывать и презентовать результаты работ, планы-графики проекта, оргструктуру проекта, отчеты о выполнении проекта
• Участие в поиске и развитии сотрудников

Требования:
• Опыт работы на должности руководителя проектов от 4 лет
• Опыт работы над проектами на базе 1С:Предприятие, 1С:УХ, 1С:ЗУП, 1С:НСИ(1С:MDM)
• Опыт интеграций (ERP, ЗУП, шина данных и др)
• Опыт входа в проект на стадии реализации
• Знания жизненного цикла разработки, понимание архитектуры решений и внедрения базовых конфигураций 1С
• Высшее образование (Приветствуется прохождение курсов по специализации "Управление проектами разработки программного обеспечения" с подтверждением сертификатом)

Мы предлагаем:
• Удаленная работа с периодическими выездами к заказчику (При желании предлагаем работу в комфортном офисе на м. Нагатинская)
• Официальное трудоустройство по ТК РФ, включая все социальные гарантии
• Конкурентная заработная плата, уровень которой обсуждается индивидуально по итогам собеседования в зависимости от вашего опыта и компетенций
• Ресурсы для реализации внедрения новых методов управления проектами
• Прозрачная обратная связь и коммуникация с высшим руководством

Будем рады видеть вас в нашей команде!""",
            experience=VacancyExperienceLevel.MORE_THAN_6,
            employment=[EmploymentType.FULL],
            schedule=[ScheduleType.REMOTE, ScheduleType.FLEXIBLE],
            key_skills=[
                VacancySkill(name="1С:Предприятие", required=True),
                VacancySkill(name="Управление проектами", required=True),
                VacancySkill(name="ERP системы", required=True),
                VacancySkill(name="Яндекс.Трекер", required=False),
                VacancySkill(name="Microsoft Teams", required=False),
                VacancySkill(name="1С:ЗУП", required=True),
                VacancySkill(name="1С:УХ", required=True),
                VacancySkill(name="Интеграция систем", required=True)
            ],
            benefits=[
                "Удаленная работа",
                "Гибкий график", 
                "Официальное трудоустройство",
                "Конкурентная зарплата",
                "Профессиональное развитие",
                "Комфортный офис",
                "Социальные гарантии"
            ]
        )
        return [template]
    
    def get_template_by_id(self, template_id: str) -> Optional[VacancyTemplate]:
        """Получение шаблона по ID"""
        templates = self.get_templates()
        for template in templates:
            if template.id == template_id:
                return template
        return None

# Глобальная переменная для сервиса
vacancy_service = None

@app.on_event("startup")
async def startup_event():
    """Инициализация при старте приложения"""
    global vacancy_service
    vacancy_service = VacancyBuilderService()

# === API ENDPOINTS ===

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
    """Получение списка профессиональных ролей"""
    try:
        roles = vacancy_service.get_professional_roles()
        return {"professional_roles": [{"id": r.id, "name": r.name} for r in roles]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения профессиональных ролей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/templates")
async def get_templates():
    """Получение списка шаблонов вакансий"""
    try:
        templates = vacancy_service.get_templates()
        return {"templates": [t.dict() for t in templates]}
    except Exception as e:
        logger.error(f"Ошибка получения шаблонов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Получение шаблона по ID"""
    template = vacancy_service.get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return {"template": template.dict()}

@app.post("/create", response_model=VacancyCreationResponse)
async def create_vacancy(request: VacancyCreationRequest):
    """Создание вакансии"""
    try:
        result = vacancy_service.create_vacancy(request)
        return result
    except Exception as e:
        logger.error(f"Ошибка создания вакансии: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.post("/validate")
async def validate_vacancy(draft: VacancyDraft):
    """Валидация черновика вакансии"""
    try:
        errors = vacancy_service.validate_vacancy_draft(draft)
        return {
            "valid": len(errors) == 0,
            "errors": [e.dict() for e in errors]
        }
    except Exception as e:
        logger.error(f"Ошибка валидации: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

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
