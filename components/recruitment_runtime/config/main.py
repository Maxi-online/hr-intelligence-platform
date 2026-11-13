from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yaml
import os
import sys
from datetime import datetime
from typing import Dict, Any


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



# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import HealthResponse, ErrorResponse
from shared.utils import setup_logging

# Настройка логирования
logger = setup_logging("config-service")

app = FastAPI(
    title="Config Service",
    description="Сервис управления конфигурацией для Candidate Analysis",
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

class ConfigManager:
    def __init__(self):
        self.config_file = "config/settings.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации из файла"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as file:
                config = _resolve_settings_env(yaml.safe_load(file))
            logger.info("Конфигурация успешно загружена")
            return config
        except FileNotFoundError:
            logger.error(f"Файл конфигурации {self.config_file} не найден")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            "hh_api": {
                "base_url": "https://api.hh.ru",
                "client_id": os.getenv("HH_CLIENT_ID", ""),
                "client_secret": os.getenv("HH_CLIENT_SECRET", ""),
                "user_agent": "HR-Help/1.0"
            },
            "services": {
                "gateway": {"port": 8000, "host": "0.0.0.0"},
                "search": {"port": 8001, "host": "0.0.0.0"},
                "ranking": {"port": 8002, "host": "0.0.0.0"},
                "hh_api": {"port": 8003, "host": "0.0.0.0"},
                "config": {"port": 8004, "host": "0.0.0.0"},
                "frontend": {"port": 8501, "host": "0.0.0.0"}
            }
        }
    
    def get_config(self, section: str = None) -> Dict[str, Any]:
        """Получение конфигурации или её секции"""
        if section:
            return self.config.get(section, {})
        return self.config
    
    def update_config(self, section: str, data: Dict[str, Any]) -> bool:
        """Обновление секции конфигурации"""
        try:
            self.config[section] = data
            self._save_config()
            logger.info(f"Конфигурация секции {section} обновлена")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации: {e}")
            return False
    
    def _save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            raise

# Инициализация менеджера конфигурации
config_manager = ConfigManager()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/config")
async def get_config(section: str = None):
    """Получение конфигурации"""
    try:
        config = config_manager.get_config(section)
        return {"config": config}
    except Exception as e:
        logger.error(f"Ошибка получения конфигурации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения конфигурации")

@app.get("/config/{section}")
async def get_config_section(section: str):
    """Получение конкретной секции конфигурации"""
    try:
        config = config_manager.get_config(section)
        if not config:
            raise HTTPException(status_code=404, detail=f"Секция {section} не найдена")
        return {"config": config}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения секции конфигурации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения конфигурации")

@app.put("/config/{section}")
async def update_config_section(section: str, data: Dict[str, Any]):
    """Обновление секции конфигурации"""
    try:
        success = config_manager.update_config(section, data)
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка обновления конфигурации")
        return {"message": f"Секция {section} успешно обновлена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обновления конфигурации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления конфигурации")

@app.get("/services")
async def get_services_config():
    """Получение конфигурации всех сервисов"""
    try:
        services = config_manager.get_config("services")
        return {"services": services}
    except Exception as e:
        logger.error(f"Ошибка получения конфигурации сервисов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения конфигурации сервисов")

@app.get("/services/{service_name}")
async def get_service_config(service_name: str):
    """Получение конфигурации конкретного сервиса"""
    try:
        services = config_manager.get_config("services")
        service_config = services.get(service_name)
        if not service_config:
            raise HTTPException(status_code=404, detail=f"Сервис {service_name} не найден")
        return {"service": service_config}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения конфигурации сервиса: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения конфигурации сервиса")

@app.get("/hh-api")
async def get_hh_api_config():
    """Получение конфигурации HH API"""
    try:
        hh_config = config_manager.get_config("hh_api")
        return {"hh_api": hh_config}
    except Exception as e:
        logger.error(f"Ошибка получения конфигурации HH API: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения конфигурации HH API")

if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("config", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8004),
        reload=service_config.get("debug", False)
    )