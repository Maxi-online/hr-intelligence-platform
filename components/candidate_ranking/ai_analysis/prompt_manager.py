"""
Менеджер промптов для мульти-агентной системы
Загружает промпты из YAML файлов и предоставляет их агентам
"""

import yaml
import os
from typing import Dict, Any, Optional
from shared.utils import setup_logging


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



logger = setup_logging("prompt-manager")

class PromptManager:
    """Менеджер промптов для агентов"""
    
    def __init__(self, prompts_file: str = "agent_prompts.yaml", configs_file: str = "agent_configs.yaml"):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.prompts_file = os.path.join(self.current_dir, prompts_file)
        self.configs_file = os.path.join(self.current_dir, configs_file)
        
        self.prompts = {}
        self.configs = {}
        
        self._load_prompts()
        self._load_configs()
    
    def _load_prompts(self):
        """Загружает промпты из YAML файла"""
        try:
            if os.path.exists(self.prompts_file):
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    self.prompts = yaml.safe_load(f)
                logger.info(f"✅ Промпты загружены из {self.prompts_file}")
            else:
                logger.warning(f"⚠️ Файл промптов не найден: {self.prompts_file}")
                self.prompts = {}
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки промптов: {e}")
            self.prompts = {}
    
    def _load_configs(self):
        """Загружает конфигурации из YAML файла"""
        try:
            if os.path.exists(self.configs_file):
                with open(self.configs_file, 'r', encoding='utf-8') as f:
                    self.configs = _resolve_settings_env(yaml.safe_load(f))
                logger.info(f"✅ Конфигурации загружены из {self.configs_file}")
            else:
                logger.warning(f"⚠️ Файл конфигураций не найден: {self.configs_file}")
                self.configs = {}
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигураций: {e}")
            self.configs = {}
    
    def get_prompt(self, agent_name: str, prompt_type: str = "system_prompt") -> Optional[str]:
        """Получает промпт для указанного агента"""
        try:
            # Сначала ищем точное имя (для master_coordinator)
            agent_prompts = self.prompts.get(agent_name, {})
            if prompt_type in agent_prompts:
                return agent_prompts[prompt_type]
            
            # Потом ищем с суффиксом _agent (для обычных агентов)
            agent_prompts = self.prompts.get(f"{agent_name}_agent", {})
            if prompt_type in agent_prompts:
                return agent_prompts[prompt_type]
            
            logger.warning(f"⚠️ Промпт {prompt_type} не найден для агента {agent_name}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения промпта для {agent_name}: {e}")
            return None
    
    def get_config(self, config_path: str) -> Any:
        """Получает конфигурацию по пути (например: 'agents.requirements_agent.timeout')"""
        try:
            keys = config_path.split('.')
            current = self.configs
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    logger.warning(f"⚠️ Конфигурация не найдена: {config_path}")
                    return None
            
            return current
        except Exception as e:
            logger.error(f"❌ Ошибка получения конфигурации {config_path}: {e}")
            return None
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Получает полную конфигурацию агента"""
        agent_config = self.get_config(f"agents.{agent_name}_agent")
        return agent_config if agent_config else {}
    
    def get_position_config(self, position_type: str) -> Dict[str, Any]:
        """Получает конфигурацию для типа позиции"""
        position_config = self.get_config(f"position_configs.{position_type}")
        return position_config if position_config else {}
    
    def get_common_settings(self) -> Dict[str, Any]:
        """Получает общие настройки"""
        return self.prompts.get("common_settings", {})
    
    def get_industry_focus(self, industry: str) -> Optional[Dict[str, Any]]:
        """Получает фокусные области для индустрии"""
        industry_config = self.prompts.get("industry_specific", {}).get(industry)
        return industry_config
    
    def format_analysis_prompt(self, agent_name: str, **kwargs) -> Optional[str]:
        """Форматирует analysis_prompt с переданными параметрами"""
        try:
            analysis_prompt = self.get_prompt(agent_name, "analysis_prompt")
            if analysis_prompt:
                return analysis_prompt.format(**kwargs)
            return None
        except KeyError as e:
            logger.error(f"❌ Отсутствует параметр для форматирования промпта {agent_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования промпта {agent_name}: {e}")
            return None
    
    def reload_prompts(self):
        """Перезагружает промпты и конфигурации"""
        logger.info("🔄 Перезагрузка промптов и конфигураций...")
        self._load_prompts()
        self._load_configs()
    
    def get_master_coordinator_config(self) -> Dict[str, Any]:
        """Получает конфигурацию мастер-координатора"""
        return self.get_config("master_coordinator") or {}
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Получает конфигурацию мониторинга"""
        return self.get_config("monitoring") or {}
    
    def validate_config(self) -> Dict[str, Any]:
        """Валидирует конфигурацию и возвращает отчет"""
        validation_report = {
            "status": "healthy",
            "issues": [],
            "warnings": [],
            "loaded_agents": 0,
            "loaded_prompts": 0
        }
        
        try:
            # Проверяем агентов
            agents_config = self.get_config("agents")
            if agents_config:
                validation_report["loaded_agents"] = len(agents_config)
            else:
                validation_report["issues"].append("Конфигурация агентов не найдена")
                validation_report["status"] = "unhealthy"
            
            # Проверяем промпты
            agent_prompts = [key for key in self.prompts.keys() if key.endswith("_agent")]
            validation_report["loaded_prompts"] = len(agent_prompts)
            
            if validation_report["loaded_prompts"] == 0:
                validation_report["issues"].append("Промпты агентов не найдены")
                validation_report["status"] = "unhealthy"
            
            # Проверяем соответствие промптов и конфигураций
            if agents_config:
                for agent_name in agents_config.keys():
                    if f"{agent_name}" not in self.prompts:
                        validation_report["warnings"].append(f"Промпт для {agent_name} не найден")
            
            logger.info(f"✅ Валидация конфигурации завершена: {validation_report['status']}")
            
        except Exception as e:
            validation_report["status"] = "error"
            validation_report["issues"].append(f"Ошибка валидации: {str(e)}")
            logger.error(f"❌ Ошибка валидации конфигурации: {e}")
        
        return validation_report

# Глобальный экземпляр промпт-менеджера
prompt_manager = PromptManager()

def get_prompt_manager() -> PromptManager:
    """Возвращает глобальный экземпляр промпт-менеджера"""
    return prompt_manager