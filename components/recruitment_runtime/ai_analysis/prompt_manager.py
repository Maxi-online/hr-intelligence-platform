"""
Project Manager for the Multi-Agent System
Uploads prompts from YAML files and provides them to agents
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
    'Representative Manager for Agents'
    
    def __init__(self, prompts_file: str = "agent_prompts.yaml", configs_file: str = "agent_configs.yaml"):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.prompts_file = os.path.join(self.current_dir, prompts_file)
        self.configs_file = os.path.join(self.current_dir, configs_file)
        
        self.prompts = {}
        self.configs = {}
        
        self._load_prompts()
        self._load_configs()
    
    def _load_prompts(self):
        'Uploads prompts from YAML file'
        try:
            if os.path.exists(self.prompts_file):
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    self.prompts = yaml.safe_load(f)
                logger.info(f"✅ Prompts loaded from {self.prompts_file}")
            else:
                logger.warning(f"⚠️ No props file found: {self.prompts_file}")
                self.prompts = {}
        except Exception as e:
            logger.error(f"❌ Error of Prometheus Loading: {e}")
            self.prompts = {}
    
    def _load_configs(self):
        'Uploads configuration from YAML file'
        try:
            if os.path.exists(self.configs_file):
                with open(self.configs_file, 'r', encoding='utf-8') as f:
                    self.configs = _resolve_settings_env(yaml.safe_load(f))
                logger.info(f"✅ The configurations are downloaded from {self.configs_file}")
            else:
                logger.warning(f"⚠️ No configuration file found: {self.configs_file}")
                self.configs = {}
        except Exception as e:
            logger.error(f"❌ Configuration Error: {e}")
            self.configs = {}
    
    def get_prompt(self, agent_name: str, prompt_type: str = "system_prompt") -> Optional[str]:
        'Receives a prop for the specified agent'
        try:
            # First we look for the exact name (for master_coordinator)
            agent_prompts = self.prompts.get(agent_name, {})
            if prompt_type in agent_prompts:
                return agent_prompts[prompt_type]
            
            # Then we're looking for a souffix.
            agent_prompts = self.prompts.get(f"{agent_name}_agent", {})
            if prompt_type in agent_prompts:
                return agent_prompts[prompt_type]
            
            logger.warning(f"⚠️ Prompte {prompt_type} not found for an agent {agent_name}")
            return None
        except Exception as e:
            logger.error(f"❌ Error in receiving a proof for {agent_name}: {e}")
            return None
    
    def get_config(self, config_path: str) -> Any:
        "Receives configuration along the way (e.g.: 'agents.requirements_agent.timeout')"
        try:
            keys = config_path.split('.')
            current = self.configs
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    logger.warning(f"⚠️ No configuration found: {config_path}")
                    return None
            
            return current
        except Exception as e:
            logger.error(f"❌ Error of Configuration {config_path}: {e}")
            return None
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        'Receives full agent configuration'
        agent_config = self.get_config(f"agents.{agent_name}_agent")
        return agent_config if agent_config else {}
    
    def get_position_config(self, position_type: str) -> Dict[str, Any]:
        'Receives configuration for type of position'
        position_config = self.get_config(f"position_configs.{position_type}")
        return position_config if position_config else {}
    
    def get_common_settings(self) -> Dict[str, Any]:
        'Receives general settings'
        return self.prompts.get("common_settings", {})
    
    def get_industry_focus(self, industry: str) -> Optional[Dict[str, Any]]:
        'Receives focus areas for industry'
        industry_config = self.prompts.get("industry_specific", {}).get(industry)
        return industry_config
    
    def format_analysis_prompt(self, agent_name: str, **kwargs) -> Optional[str]:
        'Formats analysis_prompt with transmitted parameters'
        try:
            analysis_prompt = self.get_prompt(agent_name, "analysis_prompt")
            if analysis_prompt:
                return analysis_prompt.format(**kwargs)
            return None
        except KeyError as e:
            logger.error(f"❌ No option for prompt formatting {agent_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Errors in Prometheus Formatting {agent_name}: {e}")
            return None
    
    def reload_prompts(self):
        'Reloading Prompts and configurations'
        logger.info('🔄 Rebooting Prompts and configurations...')
        self._load_prompts()
        self._load_configs()
    
    def get_master_coordinator_config(self) -> Dict[str, Any]:
        'Receives Master Coordinator configuration'
        return self.get_config("master_coordinator") or {}
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        'Receives monitoring configuration'
        return self.get_config("monitoring") or {}
    
    def validate_config(self) -> Dict[str, Any]:
        'Validate configuration and return report'
        validation_report = {
            "status": "healthy",
            "issues": [],
            "warnings": [],
            "loaded_agents": 0,
            "loaded_prompts": 0
        }
        
        try:
            # Checking agents.
            agents_config = self.get_config("agents")
            if agents_config:
                validation_report["loaded_agents"] = len(agents_config)
            else:
                validation_report["issues"].append('No agent configuration found')
                validation_report["status"] = "unhealthy"
            
            # Checking prompts.
            agent_prompts = [key for key in self.prompts.keys() if key.endswith("_agent")]
            validation_report["loaded_prompts"] = len(agent_prompts)
            
            if validation_report["loaded_prompts"] == 0:
                validation_report["issues"].append('No agent proms found.')
                validation_report["status"] = "unhealthy"
            
            # Checking to match prompts and configurations
            if agents_config:
                for agent_name in agents_config.keys():
                    if f"{agent_name}" not in self.prompts:
                        validation_report["warnings"].append(f"Prompt for {agent_name} not found")
            
            logger.info(f"✅ The configuration validation has been completed: {validation_report['status']}")
            
        except Exception as e:
            validation_report["status"] = "error"
            validation_report["issues"].append(f"Validation errors: {str(e)}")
            logger.error(f"❌ Configuration errors: {e}")
        
        return validation_report

# Global copy of the assistant manager
prompt_manager = PromptManager()

def get_prompt_manager() -> PromptManager:
    'Returns a global copy of the prompt manager'
    return prompt_manager