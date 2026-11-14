"""
Format for Universal LLM Service Microservice
"""

import json
import os
import logging


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



logger = logging.getLogger(__name__)

def load_settings():
    'Loading settings from settings.json'
    settings_file = "settings.json"
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = _resolve_settings_env(json.load(f))
                logger.info('✅ The settings are loaded from settings.json')
                return settings
        except Exception as e:
            logger.error(f"❌ Download error settings.json: {e}")
    
    # Fallback on environment variables
    logger.warning('⚠️ settings.json not found, use environment variables')
    
    return {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "proxy_url": os.getenv("OPENAI_PROXY_URL"),
            "model": os.getenv("OPENAI_MODEL", "gpt-5-mini")
        },
        "database": {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "office_services_agents"),
            "username": os.getenv("DB_USER", "office_services_user"),
            "password": os.getenv("DB_PASS", "")
        },
        "llm_service": {
            "port": int(os.getenv("LLM_SERVICE_PORT", "8102")),
            "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
        }
    }

# Upload settings
settings = load_settings()
