"""
Candidate Analysis - Multi-Agent Analysis System

Specialized AI agents system for in-depth analysis of candidates.

This module implements a multi-agent architecture where each agent is an expert
in a particular area of analysis of the executive summary. All agents operate in parallel using
AsyncOpenAI and GPT-5-nano for maximum productivity.

Architecture Overview:
    BaseAgent (ABC) 
    ├── TechnicalSkillsAgent # Technical Skills Analysis
    ├── ExperienceRelevanceAgent # Assessing the relevance of experiences  
    ├── CulturalFitAgent # Cultural Conformity Analysis
    ├── GrowthPotentialAgent # Growth potential assessment
    ├── ResumeAnalysisAgent #Quality analysis of the summary
    └── AnomalyDetectionAgent #Inconformance identification

Key Features:
- AsyncOpenAI for the true parallel work of all agents
- Transformable prompts via agent_prompts.yaml
- Adjustable parameters via agent_configs.yaml  
- Exponential backoff for API error resistance
- Detailed logic for debugging and monitoring
- JSON structured responses for software processing

Agent Specializations:
- Technical: hard scills, technology, tools
Experience: relevance of experience, career path
- Cultural: software scills, communication, teamwork
- Growth: potential, learning, ambition  
- Resume: structure, quality, completeness of information
- Analy: Red flags, inconsistencies, suspicious moments

Performance:
- One candidate time: ~4-6 seconds (6 agents in parallel))
- Support for the Batchev processing of up to 10 candidates
- Graceful error handling with retrie mechanisms
- Minimum cost of OpenAI API (~$0.002-0.005 for candidate))

Author: Candidate Analysis Team  
Version: 3.0.0 (AsyncOpenAI + True Parallelism)
Last Updated: 2025-01-04
"""

import time
import json
import re
import asyncio
import yaml
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import AgentReport, AgentStatus
from shared.utils import setup_logging, load_config

# CONTEMPORARY OPENAI CLICENT WITH PROCESS
from openai import AsyncOpenAI
import httpx
import backoff

logger = setup_logging("agents")

class BaseAgent(ABC):
    """
    Basic abstract class for all specialized AI agents.
    
    Provides a common infrastructure for:
    - Upload configuration and prompts from YAML files
    - AsyncOpenAI client initialization with proxy support
    - Asynchronous GPT-5-nano calls with retry logic
    - Logging and monitoring agents &apos; work
    - Standardized Response Format (JSON)
    
    Attributes:
        name (str): unique agent name (technical_skills, experience_relevance, etc.)
        config (dict): complete system configuration from settings.yaml
        ai_config (dict): Section specific configuration AI from ai_analysis
        prompts (dict): Upload prompts from agent_prompts.yaml
        agent_configs (dict): Actors configuration from agent_configs.yaml
        openai_client (AsyncOpenAI): OpenAI asynchronous client
        
    Configuration Files:
        - agent_prompts.yaml: Prompts for each type of agent
        - agent_configs.yaml: Model Options(temperature, max_completion_tokens, etc.)
        - settings.yaml: Main configuration (API keys, proxie, etc.).)
        
    Subclass Requirements:
        Each heir must realize:
        - analyze(candidate_data, requirements, context) -> AgentReport
        
    Error Handling:
        - Exponential backoff for OpenAI API calls
        - Graceful degradation for configuration errors
        - Detailed logic of all operations
        
    Performance Features:
        - AsyncOpenAI for non-locking calls
        - httpx.AsyncClient for HTTP compounds
        - Adjustable timeouts and retry policies
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logger
        
        # FACILITATION OF load_config()
        self.config = load_config()
        self.ai_config = self.config.get("ai_analysis", {})
        
        # FREEDOMS AND AGENCIES
        self._load_prompts()
        self._load_agent_configs()
        
        # FACILITATION OF THE CONTEMPORARY OPENAI CLICENT WITH A PROCESS
        self._setup_modern_openai_client()
    
    def _load_prompts(self):
        'Uploads YAML agents prompts with relative routes'
        try:
            # We're gonna try out a few ways.
            possible_paths = [
                "ai_analysis/agent_prompts.yaml",  # Local
                "/app/ai_analysis/agent_prompts.yaml"  # Docker
            ]
            
            for prompts_path in possible_paths:
                if os.path.exists(prompts_path):
                    with open(prompts_path, 'r', encoding='utf-8') as f:
                        self.prompts = yaml.safe_load(f)
                        self.logger.info(f"✅ Prompts loaded for {self.name} from {prompts_path}")
                        return
            
            self.logger.warning(f"⚠️ Prompt file not found for {self.name}using default values")
            self.prompts = {}
        except Exception as e:
            self.logger.error(f"❌ Errors in charging for {self.name}: {e}")
            self.prompts = {}
    
    def _load_agent_configs(self):
        'Uploads agent_configs.yaml agent configurations with relative routes'
        try:
            # We're gonna try out a few ways.
            possible_paths = [
                "ai_analysis/agent_configs.yaml",  # Local
                "/app/ai_analysis/agent_configs.yaml"  # Docker
            ]
            
            for configs_path in possible_paths:
                if os.path.exists(configs_path):
                    with open(configs_path, 'r', encoding='utf-8') as f:
                        self.agent_configs = yaml.safe_load(f)
                        self.logger.info(f"✅ The agent configurations are loaded for {self.name} from {configs_path}")
                        return
            
            self.logger.warning(f"⚠️ Agent configuration file not found for {self.name}using default values")
            self.agent_configs = {}
        except Exception as e:
            self.logger.error(f"❌ Configuration errors of agents for {self.name}: {e}")
            self.agent_configs = {}
    

    
    def _setup_modern_openai_client(self):
        'Sets up a modern OpenAI client with the right support for a proxie'
        try:
            # Get an API key.
            api_key = self.ai_config.get("openai_api_key")
            if not api_key:
                self.logger.warning(f"⚠️ OPENAI_API_KEY not fitted for {self.name}")
            
            # Settings HTTP Proxi from configuration
            proxy_config = self.ai_config.get("proxy", {})
            proxy_enabled = proxy_config.get("enabled", False)
            
            if proxy_enabled:
                # We're going to get proxie settings from configuration or variable environments
                proxy_host = proxy_config.get("host", "")
                proxy_port = proxy_config.get("port", "")
                proxy_username = proxy_config.get("username", "")
                proxy_password = proxy_config.get("password", "")
                proxy_protocol = proxy_config.get("protocol", "http")
                
                if proxy_host and proxy_port:
                    # Form an uRL proxie
                    if proxy_username and proxy_password:
                        proxy_url = f"{proxy_protocol}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                    else:
                        proxy_url = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
                    
                    # Create httpx client proxie for AsyncOpenAI
                    http_client = httpx.AsyncClient(
                        proxy=proxy_url,
                        timeout=httpx.Timeout(60.0)
                    )
                    
                    self.logger.info(f"🌐 OpenAI Proxi client initialized for {self.name}: {proxy_host}:{proxy_port}")
                else:
                    # If Proxi settings are incomplete, the normal customer is used
                    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                    self.logger.warning(f"⚠️ Proxie included for {self.name}, But the settings are incomplete. Direct connection used.")
            else:
                # Normal httpx client with no proxie for AsyncOpenAI
                http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                self.logger.info(f"🔗 OpenAI client without proxie initialized for {self.name}")
            
            # Initialization of modern AsyncOpenAI client
            self.openai_client = AsyncOpenAI(
                api_key=api_key,
                http_client=http_client
            )
            
            # common_settings model parameters in agent_prompts.yaml
            common_settings = self.prompts.get('common_settings', {})
            self.model = common_settings.get("model", "gpt-5-nano")
            self.max_completion_tokens = common_settings.get("max_completion_tokens", 2000)
            # self.temperature = common_settings.get("temperature", 0.3)
            
            self.logger.info(f"✅ Today's AsyncOpenAI client is set for {self.name} (model: {self.model})")
            
        except Exception as e:
            self.logger.error(f"❌ Configuration error of the modern AsyncOpenAI client for {self.name}: {e}")
            # Create a base client as a fallback, YAML parameters
            self.openai_client = AsyncOpenAI(api_key=self.ai_config.get("openai_api_key", ""))
            common_settings = self.prompts.get('common_settings', {})
            self.model = common_settings.get("model", "gpt-5-nano")
            self.max_completion_tokens = common_settings.get("max_completion_tokens", 2000)
            # self.temperature = common_settings.get("temperature", 0.3)
    
    def _get_agent_config(self, config_key: str, default_value: Any = None):
        'Receives the key agent configuration'
        agent_name = self.name.lower().replace('агент ', '').replace(' ', '_')
        
        # We're going to try out a different version of the agent's name.
        config_name = re.sub(r"(?<!^)(?=[A-Z])", "_", type(self).__name__).lower()
        possible_names = [
            config_name,
            f"{agent_name}_agent",
            agent_name,
            f"agent_{agent_name}",
            self.name.lower().replace(' ', '_')
        ]
        
        for name in possible_names:
            if name in self.agent_configs.get('agents', {}):
                agent_config = self.agent_configs['agents'][name]
                return agent_config.get(config_key, default_value)
        
        return default_value
    
    def _get_agent_prompts(self, agent_key: str):
        "Gets the agent's key prompts."
        try:
            # DEBUG Deleted:self.logger.error(f"🔍 DEBUG _get_agent_prompts: We're looking for a key.{agent_key}")
            # DEBUG Deleted:self.logger.error(f"🔍 DEBUG _get_agent_prompts: available keys toprompts: {list(self.prompts.keys())}")
            
            result = self.prompts.get(agent_key, {})
            # DEBUG Deleted:self.logger.error(f"🔍 DEBUG _get_agent_prompts: We're returning the result of the type{type(result)}: {result}")
            
            if not isinstance(result, dict):
                self.logger.error(f"❌ Error _get_agent_prompts: the result is not a dictionary!")
                return {}
            
            return result
        except Exception as e:
            import traceback
            self.logger.error(f"❌ The error in _get_agent_prompts: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            return {}
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3, base=1, max_value=5)
    async def _call_gpt(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        'Call a modern AsyncOpenAI client to analyze with retry logic'
        try:
            self.logger.info(f"🤖 {self.name} Sends a request to GPT...")
            
            # Using the modern AsyncOpenAI client with the JSON mode - SUSTAINABLE ASYNCHRONY
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                # temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            self.logger.info(f"✅ {self.name} received a reply from GPT (model: {self.model})")
            
            # JSON ANSWERS
            try:
                result = json.loads(content)
                self.logger.info(f"✅ {self.name} JSON has successfully received an evaluation response {result.get('score', 'N/A')}")
                return result
            except json.JSONDecodeError:
                # If not JSON, let's return as a text with a hint for parsing
                self.logger.warning(f"⚠️ GPT returned not JSON's answer for {self.name}, parsim as text")
                return {
                    "analysis": content, 
                    "score": 50.0,
                    "summary": f"Analysis from {self.name}",
                    "details": [content[:200] + "..." if len(content) > 200 else content],
                    "red_flags": [],
                    "positive_points": [],
                    "recommendations": []
                }
                
        except Exception as e:
            self.logger.error(f"❌ The error of calling the modern AsyncOpenAI client {self.name}: {e}")
            return {
                "error": str(e), 
                "score": 0.0,
                "summary": f"Error of GPT in {self.name}",
                "details": [f"Technical errors: {str(e)}"],
                "red_flags": ['Mistake of GPT'],
                "positive_points": [],
                "recommendations": ['Re-examination required']
            }
    
    @abstractmethod
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        'Analyses the candidate and returns the report'
        pass
    
    def _create_report(self, score: float, status: AgentStatus, summary: str,
                      details: List[str] = None, red_flags: List[str] = None,
                      positive_points: List[str] = None, recommendations: List[str] = None,
                      processing_time: float = 0.0) -> AgentReport:
        'Creates a standard agent report'
        return AgentReport(
            agent_name=self.name,
            score=score,
            status=status,
            summary=summary,
            details=details or [],
            red_flags=red_flags or [],
            positive_points=positive_points or [],
            recommendations=recommendations or [],
            processing_time=processing_time,
            timestamp=datetime.now()
        )

    def _safe_get_experience_years(self, candidate_data: Dict[str, Any]) -> float:
        'Safe to extract and summarize work experience from the HH.ru API structure.'
        import re
        from datetime import datetime
        
        try:
            # 1. Check the main fields of experience from HH.ru API
            # The total_experience field may be a line "1 year 8 months" or an object {"months": N}
            if "total_experience" in candidate_data:
                exp = candidate_data["total_experience"]
                
                # COMPLETE DATA HH.ru: total_experience = {"months": 18}
                if isinstance(exp, dict) and "months" in exp:
                    months = exp.get("months", 0)
                    if isinstance(months, (int, float)) and months > 0:
                        return round(months / 12, 1)
                
                elif isinstance(exp, str) and any(word in exp.lower() for word in ["год", "мес", 'years']):
                    # We're gonna parade a line like 1 year 8 months.
                    years = re.findall(r'(\d+)\s*(?:год|лет)', exp)
                    months = re.findall(r'(\d+)\s*мес', exp)
                    total_months = (int(years[0]) * 12 if years else 0) + (int(months[0]) if months else 0)
                    if total_months > 0:
                        return round(total_months / 12, 1)
                        
                elif isinstance(exp, (int, float)) and exp > 0:
                    return float(exp)
            
            # 2. BASIC DATA HH.ru: Experience may be {'months':N}
            experience = candidate_data.get("experience", [])
            if isinstance(experience, dict) and "months" in experience:
                # Baseline data HH.ru API: experience = {'months': 33}
                months = experience.get("months", 0)
                if isinstance(months, (int, float)) and months > 0:
                    return round(months / 12, 1)
            
            # 3. Checking the full-data array)
            elif isinstance(experience, list) and experience:
                total_months = 0
                
                for job in experience:
                    if isinstance(job, dict):
                        # Find the start and end dates of the work
                        start_date = job.get("start", "") or job.get("start_date", "")
                        end_date = job.get("end", "") or job.get("end_date", "")
                        
                        # If there is a line period (e.g. July 2024 - now 1 year 2 months)")
                        period_text = job.get("period", "") or str(job.get("description", ""))
                        if "год" in period_text or "мес" in period_text:
                            years = re.findall(r'(\d+)\s*(?:год|лет)', period_text)
                            months = re.findall(r'(\d+)\s*мес', period_text)
                            job_months = (int(years[0]) * 12 if years else 0) + (int(months[0]) if months else 0)
                            total_months += job_months
                            continue
                        
                        # If there are clear dates, we calculate the difference.
                        if start_date and end_date:
                            try:
                                if end_date.lower() in ["сейчас", "настоящее время", "по настоящее время"]:
                                    end_date = datetime.now().strftime("%Y-%m")
                                
                                # Simple parsing of dates (without complex libraries)
                                start_parts = re.findall(r'\d+', str(start_date))
                                end_parts = re.findall(r'\d+', str(end_date))
                                
                                if len(start_parts) >= 2 and len(end_parts) >= 2:
                                    start_year, start_month = int(start_parts[-1]), int(start_parts[-2])
                                    end_year, end_month = int(end_parts[-1]), int(end_parts[-2])
                                    
                                    job_months = (end_year - start_year) * 12 + (end_month - start_month)
                                    total_months += max(0, job_months)
                                    
                            except Exception:
                                # If you couldn't pass the dates, we'll skip.
                                pass
                
                if total_months > 0:
                    return round(total_months / 12, 1)
            
            # 4. Looking for experience in the field
            title = candidate_data.get("title", "")
            if title and any(word in title.lower() for word in ['Experience', "год", 'years']):
                years = re.findall(r'(\d+)\s*(?:год|лет)', title)
                months = re.findall(r'(\d+)\s*мес', title)
                if years or months:
                    total_months = (int(years[0]) * 12 if years else 0) + (int(months[0]) if months else 0)
                    return round(total_months / 12, 1)
            
            return 0.0
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error: ❌ Feil in _safe_get_experience_years: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            return 0.0

    def _safe_get_languages(self, candidate_data: Dict[str, Any]) -> str:
        'Safe to extract and format languages from different sources.'
        try:
            lang_list = []
            
            # 1. BASIC SOURCE: languages or language field 
            languages = candidate_data.get("languages", candidate_data.get("language", []))
            
            if isinstance(languages, list) and languages:
                for lang in languages:
                    if isinstance(lang, dict):
                        name = lang.get("name", "")
                        level_data = lang.get("level", {})
                        if isinstance(level_data, dict):
                            level = level_data.get("name", "")
                        else:
                            level = str(level_data) if level_data else ""
                        lang_list.append(f"{name} ({level})" if level else name)
                    elif isinstance(lang, str):
                        lang_list.append(lang)
            
            # 2. BASIC DATA: Language search and description
            if not lang_list:
                title = candidate_data.get("title", "")
                about = candidate_data.get("about", "")
                
                # A simple search for references to languages
                language_keywords = ["русский", "английский", "немецкий", "французский", "испанский", "китайский", "japanese"]
                level_keywords = ["a1", "a2", "b1", "b2", "c1", "c2", "начинающий", "средний", "продвинутый", "свободно"]
                
                import re
                text_to_search = f"{title} {about}".lower()
                
                for lang_keyword in language_keywords:
                    if lang_keyword in text_to_search:
                        # Looking for a level next to the language
                        pattern = f"{lang_keyword}[A-ZA-Za-Yao]{'|'.join(level_keywords)})"
                        match = re.search(pattern, text_to_search, re.IGNORECASE)
                        if match:
                            lang_list.append(f"{lang_keyword.title()} ({match.group(1)})")
                        else:
                            lang_list.append(lang_keyword.title())
            
            result = ", ".join(filter(None, lang_list)) if lang_list else 'Not specified'
            return result
        except Exception as e:
            import traceback
            self.logger.error(f"❌ The error in _safe_get_languages: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            return 'Not specified'

    def _prepare_raw_data_for_gpt(self, candidate_data: Dict[str, Any]) -> str:
        'Prepares clean HH.ru data for GPT analysis without hard code.'
        try:
            import json
            return json.dumps(candidate_data, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Error in data preparation: {e}")
            return str(candidate_data)
    
    def _universal_agent_analyze(self, agent_type: str, candidate_data: Dict[str, Any], 
                                position_requirements: Dict[str, Any], 
                                additional_context: Optional[Dict[str, Any]] = None) -> str:
        'Universal analysis function for all raw JSON agents.'
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts(agent_type)
            system_prompt = agent_prompts.get('system_prompt', f'Analyze data for {agent_type}.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # PURPOSE NET JSON DATA
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # FORMATURE PROMPT - UNIVERSAL APPROACH
            try:
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    search_query=search_query,
                    position_requirements_json=position_requirements_json
                )
            except KeyError:
                # Combination with old prompts - add JSON to the end
                try:
                    # We extract real data from JSON for old prompt
                    import re
                    variables = re.findall(r'\{(\w+)\}', analysis_prompt_template)
                    format_dict = {}
                    
                    # Filling in the variables with real data from JSON
                    for var in variables:
                        if var == "candidate_skills":
                            skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                            format_dict[var] = ", ".join([s.get("name", str(s)) if isinstance(s, dict) else str(s) for s in skills]) if skills else 'Not specified'
                        elif var == "experience_years":
                            exp = candidate_data.get("total_experience", {})
                            if isinstance(exp, dict) and "months" in exp:
                                format_dict[var] = f"{exp['months'] / 12:.1f}"
                            else:
                                format_dict[var] = str(exp) if exp else "0"
                        elif var == "required_experience":
                            min_exp = position_requirements.get("min_experience_years", 0)
                            max_exp = position_requirements.get("max_experience_years")
                            exp_desc = position_requirements.get("experience_description", "")
                            if max_exp and max_exp != min_exp:
                                format_dict[var] = f"{min_exp}-{max_exp} years (years){exp_desc})"
                            elif exp_desc:
                                format_dict[var] = f"{exp_desc} (Min. {min_exp} (years)"
                            else:
                                format_dict[var] = f"{min_exp} years"
                        elif var == "required_skills":
                            skills = position_requirements.get("required_skills", [])
                            format_dict[var] = ", ".join(skills) if skills else 'Not specified'
                        elif var == "total_experience":
                            exp = candidate_data.get("total_experience", {})
                            if isinstance(exp, dict) and "months" in exp:
                                format_dict[var] = f"{exp['months']} months{exp['months'] / 12:.1f} (years)"
                            else:
                                format_dict[var] = str(exp) if exp else 'Not specified'
                        elif var == "min_experience_years":
                            min_exp = position_requirements.get("min_experience_years", 0)
                            max_exp = position_requirements.get("max_experience_years")
                            exp_desc = position_requirements.get("experience_description", "")
                            if max_exp and max_exp != min_exp:
                                format_dict[var] = f"{min_exp}-{max_exp}"
                            elif exp_desc and "до" in exp_desc:
                                format_dict[var] = exp_desc.replace("От ", "").replace(" лет", "")
                            else:
                                format_dict[var] = str(min_exp)
                            self.logger.info(f"🔍 min_experience_years = {format_dict[var]}, min={min_exp}, max={max_exp}, desc={exp_desc}")
                        elif var == "max_experience_years":
                            format_dict[var] = str(position_requirements.get("max_experience_years", 'unlimited'))
                        elif var == "experience_description":
                            format_dict[var] = position_requirements.get("experience_description", 'Requirements not specified')
                        elif var == "position_requirements_json":
                            format_dict[var] = position_requirements_json
                        elif var == "candidate_data_json":
                            format_dict[var] = candidate_data_json
                        else:
                            # For the rest of the variables, we're looking for a candidate in the data.
                            value = candidate_data.get(var, f"Find it. {var.upper()} To JSON")
                            format_dict[var] = str(value)
                    
                    user_prompt = analysis_prompt_template.format(**format_dict)
                except Exception as e:
                    user_prompt = analysis_prompt_template
                
                user_prompt += f"\n\n CANDIDATE DATA (JSON):\n{candidate_data_json}"
                user_prompt += f"\n\nSTRUCTION (JSON):\n{position_requirements_json}"
            
            return system_prompt, user_prompt
            
        except Exception as e:
            self.logger.error(f"❌ The Universal Analysis Error: {e}")
            return "Analyse the candidate's data.", f"DATA: {candidate_data_json}"
    
    def _safe_get_education(self, candidate_data: Dict[str, Any]) -> str:
        'Safe information about education from various sources.'
        try:
            education_info = []
            
            # 1. Field of education according to HH.ru API)
            education = candidate_data.get("education", [])
            if isinstance(education, list):
                for edu_item in education:
                    if isinstance(edu_item, dict):
                        name = edu_item.get("name", "")  # Name of educational institution
                        year = edu_item.get("year", "")   # Year of end
                        level = edu_item.get("level", "")  # Level of education
                        
                        if name:
                            if year and level:
                                education_info.append(f"{level}: {name} ({year})")
                            elif year:
                                education_info.append(f"{name} ({year})")
                            elif level:
                                education_info.append(f"{level}: {name}")
                            else:
                                education_info.append(name)
            
            # 2. BASIC DATA: Searching for education in title and other fields
            if not education_info:
                title = candidate_data.get("title", "")
                about = candidate_data.get("about", "")
                
                # Looking for levels of education
                edu_keywords = ["bachelor", "master", "phd", "доктор", "магистр", "бакалавр", "специалист", 
                               "высшее", "среднее", "университет", "институт", "колледж", "техникум"]
                
                text_to_search = f"{title} {about}".lower()
                found_education = []
                
                for edu_word in edu_keywords:
                    if edu_word in text_to_search:
                        found_education.append(edu_word.title())
                
                if found_education:
                    education_info.append(f"Education: {', '.join(set(found_education))}")
            
            # 3. Checking work experience for reference to education
            last_work = candidate_data.get("last_work", {})
            if isinstance(last_work, dict):
                work_name = last_work.get("name", "")
                position = last_work.get("position", "")
                description = last_work.get("description", "")
                
                work_text = f"{work_name} {position} {description}".lower()
                if any(edu_word in work_text for edu_word in ["университет", "институт", "колледж", 'University', 'Education', 'School']):
                    education_info.append(f"Relationship with educational institutions in working experience")
            
            # Form the result
            if education_info:
                result = ". ".join(education_info)
                self.logger.info(f"✅ Information on education found: {result}")
                return result
            else:
                return 'Not specified'
                
        except Exception as e:
            import traceback
            self.logger.error(f"❌ The error in _safe_get_education: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            return 'Not specified'

    def _safe_get_last_work(self, candidate_data: Dict[str, Any]) -> tuple[str, str]:
        'Safe to get the last job.'
        experience = candidate_data.get("experience", [])
        if isinstance(experience, list) and experience:
            last_job = experience[0]
            if isinstance(last_job, dict):
                position = last_job.get("position", 'Not specified')
                company = last_job.get("name", 'Not specified')  # In HH.ru API, the company is called "name"
                return position, company
        return 'Not specified', 'Not specified'

    def _safe_get_experience_description(self, candidate_data: Dict[str, Any]) -> str:
        'Safe extract a detailed description of work experience from the experience field.'
        try:
            experience = candidate_data.get("experience", [])
            if isinstance(experience, list) and experience:
                # Take the last job (first job on the list)
                last_job = experience[0]
                if isinstance(last_job, dict):
                    description = last_job.get("description", "")
                    position = last_job.get("position", "")
                    company = last_job.get("name", "")
                    
                    # Form a full description of experience
                    full_description = f"Position: {position} in {company}. "
                    if description:
                        full_description += f"Description: {description}"
                    return full_description
            
            return 'Not specified'
        except Exception as e:
            import traceback
            self.logger.error(f"❌ The error in _safe_get_experience_description: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            return 'Not specified'

    def _safe_get_skills_with_levels(self, candidate_data: Dict[str, Any]) -> str:
        'Safe to extract skills with indication of ownership levels from different fields.'
        try:
            # Checking all possible sources of skills
            all_skills = []
            
            # 1. Checking the scills)
            skills = candidate_data.get("skills", [])
            if isinstance(skills, list) and skills:
                all_skills.extend([skill for skill in skills if skill])
                self.logger.info(f"✅ Skills found in the scills field: {len(skills)} skills")
            
            # 2. Check verified_skills)
            verified_skills = candidate_data.get("verified_skills", [])
            if isinstance(verified_skills, list) and verified_skills:
                verified_skills_formatted = [f"{skill} (confirmed)" for skill in verified_skills]
                all_skills.extend(verified_skills_formatted)
                self.logger.info(f"✅ Reconfirmed skills found: {len(verified_skills)} skills")
            
            # 3. Heading field: skill_set (HH.ru API line mass))
            skill_set = candidate_data.get("skill_set", [])
            if isinstance(skill_set, list):
                for skill in skill_set:
                    if isinstance(skill, str):
                        all_skills.append(skill)
                    elif isinstance(skill, dict) and "name" in skill:
                        all_skills.append(skill["name"])

            # 4. Checking the field scills as a string)
            if isinstance(candidate_data.get("skills"), str) and candidate_data.get("skills"):
                all_skills.append(f"Skills: {candidate_data.get('skills')}")
            
            # 5. Looking for information in last_work release)
            last_work = candidate_data.get("last_work", {})
            if isinstance(last_work, dict):
                description = last_work.get("description", "")
                if description and any(tech in description.lower() for tech in ["javascript", "react", "typescript", "python", "java", "php", "css", "html"]):
                    all_skills.append(f"Experience with technology: {description[:200]}")

            # 6. Looking for information in experience (if you have a detailed description))
            experience = candidate_data.get("experience", {})
            if isinstance(experience, dict):
                # Checking descript field in experience
                exp_description = experience.get("description", "")
                if exp_description and any(tech in exp_description.lower() for tech in ["javascript", "react", "typescript", "python", "java", "php"]):
                    all_skills.append(f"Technology from experience: {exp_description[:150]}")

            # Remove duplicates and form the result
            unique_skills = list(dict.fromkeys(all_skills))  # Keep order, take out the duplicates.
            result = ". ".join(filter(None, unique_skills))
            
            if result:
                self.logger.info(f"✅ The result is the skills: {len(unique_skills)} from various sources")
            
            return result if result else 'Not specified'
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error: ❌ Feil in _safe_get_skills_with_levels: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            return 'Not specified'

    def _safe_get_about_me(self, candidate_data: Dict[str, Any]) -> str:
        'Safe to extract information about me from various sources.'
        try:
            about_info = []
            
            # 1. Check the field about)
            about = candidate_data.get("about", "")
            if about and isinstance(about, str):
                about_info.append(about)
                self.logger.info(f"✅ Found Intel 'To Me': {len(about)} Symbols")
            
            # 2. Checking the field title as a source of information on the candidate
            title = candidate_data.get("title", "")
            if title:
                about_info.append(f"Position: {title}")
            
            # 3. Checking the last job description
            last_work = candidate_data.get("last_work", {})
            if isinstance(last_work, dict):
                description = last_work.get("description", "")
                if description:
                    about_info.append(f"Experience: {description[:300]}...")
            
            # 4. Checking experience for useful information
            experience = candidate_data.get("experience", {})
            if isinstance(experience, dict):
                # Checking the description or name of the company
                exp_description = experience.get("description", "")
                company = experience.get("company", "")
                if exp_description:
                    about_info.append(f"Professional experience: {exp_description[:200]}...")
                elif company:
                    about_info.append(f"Worked at: {company}")
            
            # 5. Checking skills as a source of profile information
            skills = candidate_data.get("skills", [])
            if isinstance(skills, list) and skills:
                skills_summary = ", ".join(skills[:5])  # First 5 skills
                if len(skills) > 5:
                    skills_summary += f" And another {len(skills) - 5} skills"
                about_info.append(f"Key skills: {skills_summary}")
            
            # Form the result
            if about_info:
                result = ". ".join(about_info)
                return result
            else:
                return 'No information available'
                
        except Exception as e:
            import traceback
            self.logger.error(f"❌ The error in _safe_get_about_me: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            return 'No information available'
    
    def _get_status_by_score(self, score: float) -> AgentStatus:
        'Determines status on the basis of evaluation'
        if score >= 80:
            return AgentStatus.PASS
        elif score >= 60:
            return AgentStatus.WARNING
        else:
            return AgentStatus.FAIL
class RequirementsAgent(BaseAgent):
    'Compliance Agent'
    
    def __init__(self):
        super().__init__('Requirements Agent')
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts('requirements_agent')
            system_prompt = agent_prompts.get('system_prompt', "Review candidates' eligibility.")
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # PURPOSE NET JSON DATA 
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # Formate the PROMPT - correctly eliminate all necessary changes
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 RequirementsAgent: Prompt requires variables: {required_vars}")
            
            # WE NEED ALL POSSIBLE CHANGES FROM CANDIDATE DATA
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # We extract additional variables from candidate_data
            if 'total_experience' in required_vars and 'total_experience' in candidate_data:
                format_vars['total_experience'] = json.dumps(candidate_data['total_experience'], ensure_ascii=False)
            
            if 'skills' in required_vars:
                skills = candidate_data.get('skill_set', []) or candidate_data.get('skills', [])
                format_vars['skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'about' in required_vars:
                format_vars['about'] = candidate_data.get('about', '')
            
            if 'experience' in required_vars:
                format_vars['experience'] = json.dumps(candidate_data.get('experience', []), ensure_ascii=False)
            
            if 'education' in required_vars:
                format_vars['education'] = json.dumps(candidate_data.get('education', []), ensure_ascii=False)
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ COMPLETE PROMPT with all variables: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ Critical error: We did not find a variable {ke} In the candidate's data!")
                self.logger.error(f"🔍 Accessable keys in candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Produced variables: {list(format_vars.keys())}")
                # We'll use the basic prompt with the JSON data.
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
            
            # CALLING GPTS WITH PROMPTS FROM FILL
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # GPT ANSWER
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", 'Conformity analysis')
            
            # SAFETY PROCESS DETAILS - convert the dict to string if necessary
            raw_details = gpt_result.get("details", [])
            details = []
            for item in raw_details:
                if isinstance(item, dict):
                    # If the GPT returned the object, convert it to the string
                    details.append(f"{item.get('criterion', 'Criterion')}: {item.get('assessment', str(item))}")
                else:
                    details.append(str(item))
            
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Error in {self.name}: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary='Error in the analysis of requirements',
                details=[f"Technical errors: {str(e)}"],
                processing_time=processing_time
            )

class ResumeAnalysisAgent(BaseAgent):
    'Agent for the quality analysis of the summary as a document'
    
    def __init__(self):
        super().__init__('Resume Analysis Agent')
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts('resume_analysis_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Review the quality of the summary as a document.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # PURPOSE NET JSON DATA
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # Formating the PROMPT – We extract all the necessary changes  
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 RESUMEANALYsisAgent: Prompto requires variables: {required_vars}")
            
            # WE NEED ALL POSSIBLE CHANGES FROM CANDIDATE DATA
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Extract additional variables from candidate_data for compatibility
            if 'about_section' in required_vars or 'about' in required_vars:
                about = candidate_data.get("about", "")
                format_vars['about_section'] = about or "Section 'Oself' not filled"
                format_vars['about'] = about
            
            if 'skills_list' in required_vars or 'skills' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                skills_text = ", ".join(skills) if isinstance(skills, list) else str(skills)
                format_vars['skills_list'] = skills_text or 'Skills not specified'
                format_vars['skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'job_title' in required_vars:
                format_vars['job_title'] = candidate_data.get("title", "")
            
            if 'experience_description' in required_vars or 'experience' in required_vars:
                experience = candidate_data.get("experience", [])
                experience_text = ""
                if isinstance(experience, list) and experience:
                    experience_text = "; ".join([f"{exp.get('position', '')} in {exp.get('company', '')}" for exp in experience[:3]])
                elif isinstance(experience, dict):
                    experience_text = f"{experience.get('position', '')} in {experience.get('company', '')}"
                format_vars['experience_description'] = experience_text or 'No experience reported'
                format_vars['experience'] = json.dumps(experience, ensure_ascii=False)
            
            if 'work_experience' in required_vars:
                total_exp = candidate_data.get("total_experience", {})
                work_exp_text = f"{total_exp.get('years', 0)} Years of experience" if total_exp else 'Experience not specified'
                format_vars['work_experience'] = work_exp_text
            
            if 'education_info' in required_vars or 'education' in required_vars:
                education = candidate_data.get("education", [])
                education_text = ""
                if isinstance(education, list) and education:
                    education_text = "; ".join([f"{edu.get('name', '')} ({edu.get('year', '')})" for edu in education[:2]])
                format_vars['education_info'] = education_text or 'No education specified'
                format_vars['education'] = json.dumps(education, ensure_ascii=False)
            
            if 'contact_info' in required_vars:
                format_vars['contact_info'] = "DON'T ANALYSIS THE CONTACT"
            
            if 'position_requirements' in required_vars:
                format_vars['position_requirements'] = position_requirements.get("position_type", "general")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ The complete ResuméAnalysisAgent with all the variables: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ Critical Error ResumeAnalysisAgent: We did not find a variable {ke}!")
                self.logger.error(f"🔍 Accessable keys in candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Produced variables: {list(format_vars.keys())}")
                # We only use the old logic as a last resort.
                # Comparability with old prompts
                # We extract real data from candidate_data
                about = candidate_data.get("about", "")
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                experience = candidate_data.get("experience", [])
                total_exp = candidate_data.get("total_experience", {})
                education = candidate_data.get("education", [])
                
                # Format data for prompt
                skills_text = ", ".join(skills) if isinstance(skills, list) else str(skills)
                experience_text = ""
                if isinstance(experience, list) and experience:
                    experience_text = "; ".join([f"{exp.get('position', '')} in {exp.get('company', '')}" for exp in experience[:3]])
                elif isinstance(experience, dict):
                    experience_text = f"{experience.get('position', '')} in {experience.get('company', '')}"
                
                work_exp_text = f"{total_exp.get('years', 0)} Years of experience" if total_exp else 'Experience not specified'
                education_text = ""
                if isinstance(education, list) and education:
                    education_text = "; ".join([f"{edu.get('name', '')} ({edu.get('year', '')})" for edu in education[:2]])
                
                user_prompt = analysis_prompt_template.format(
                    job_title=candidate_data.get("title", ""),
                    about_section=about or "Section 'Oself' not filled",
                    skills_list=skills_text or 'Skills not specified',
                    experience_description=experience_text or 'No experience reported',
                    work_experience=work_exp_text,
                    education_info=education_text or 'No education specified',
                    contact_info="DON'T ANALYSIS THE CONTACT",
                    position_requirements=position_requirements.get("position_type", "general")
                )
                user_prompt += f"\n\n CANDIDATE DATA (JSON):\n{candidate_data_json}"
            
            # CALLING GPTS WITH PROMPTS FROM FILL
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # GPT ANSWER
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", 'Quality analysis of the executive summary')
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Error in {self.name}: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary='Errors in the analysis of the summary',
                details=[f"Technical errors: {str(e)}"],
                processing_time=processing_time
            )

class ExperienceAgent(BaseAgent):
    'Agent for professional experience analysis'
    
    def __init__(self):
        super().__init__('Experience Agent')
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts('experience_agent')
            system_prompt = agent_prompts.get('system_prompt', "Review candidates' professional experience.")
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # PURPOSE NET JSON DATA
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # Formating the PROMPT – We extract all the necessary changes
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 EXPERIENCEAgent: Prompto requires variables: {required_vars}")
            
            # WE NEED ALL POSSIBLE CHANGES FROM CANDIDATE DATA
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Extract additional variables from candidate_data for compatibility
            if 'experience' in required_vars:
                format_vars['experience'] = json.dumps(candidate_data.get("experience", []), ensure_ascii=False)
            
            if 'total_experience' in required_vars:
                format_vars['total_experience'] = json.dumps(candidate_data.get("total_experience", {}), ensure_ascii=False)
            
            if 'position_type' in required_vars:
                format_vars['position_type'] = position_requirements.get("position_type", "technical")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ A PREVIOUS PROMPT EXPERIENCEAgent with all variables: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ Critical error ExperienceAgent: Not found a variable {ke}!")
                self.logger.error(f"🔍 Accessable keys in candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Produced variables: {list(format_vars.keys())}")
                # We'll use the basic prompt with the JSON data.
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\n CANDIDATE DATA (JSON):\n{candidate_data_json}"
            
            # CALLING GPTS WITH PROMPTS FROM FILL
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # GPT ANSWER
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", 'Analysis of the candidate &apos; s professional experience')
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Error in {self.name}: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary='Errors in the analysis of experience',
                details=[f"Technical errors: {str(e)}"],
                processing_time=processing_time
            )

class FormattingAgent(BaseAgent):
    'Agent for the design quality analysis'
    
    def __init__(self):
        super().__init__('Formatting Agent')
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts('formatting_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Review the quality of the summary.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # PURPOSE NET JSON DATA
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # Formating the PROMPT – We extract all the necessary changes
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 FormattingAgent: Prompto requires variables: {required_vars}")
            
            # WE NEED ALL POSSIBLE CHANGES FROM CANDIDATE DATA
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Extract additional variables from candidate_data for compatibility
            if 'title_quality' in required_vars:
                title = candidate_data.get("title", "")
                format_vars['title_quality'] = title if title else 'Heading/specialization not specified'
            
            if 'about_section' in required_vars:
                about = candidate_data.get("about", "")
                format_vars['about_section'] = about if about else 'The section is not available.'
            
            if 'skills_section' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                if isinstance(skills, list) and skills:
                    skills_analysis = f"Skills list: {', '.join(skills[:10])}" + ("..." if len(skills) > 10 else "")
                elif isinstance(skills, str) and skills:
                    skills_analysis = f"Skills: {skills[:200]}" + ("..." if len(skills) > 200 else "")
                else:
                    skills_analysis = 'Skills not specified'
                format_vars['skills_section'] = skills_analysis
            
            if 'experience_section' in required_vars:
                experience = candidate_data.get("experience", [])
                if isinstance(experience, list) and experience:
                    exp_items = []
                    for exp in experience[:3]:
                        position = exp.get('position', '')
                        company = exp.get('company', '')
                        if position or company:
                            exp_items.append(f"{position} in {company}")
                    experience_analysis = "; ".join(exp_items) if exp_items else 'Experience reported without details'
                else:
                    experience_analysis = 'No experience reported'
                format_vars['experience_section'] = experience_analysis
            
            if 'education_section' in required_vars:
                education = candidate_data.get("education", [])
                if isinstance(education, list) and education:
                    edu_items = []
                    for edu in education[:2]:
                        name = edu.get('name', '')
                        year = edu.get('year', '')
                        if name:
                            edu_items.append(f"{name}" + (f" ({year})" if year else ""))
                    education_analysis = "; ".join(edu_items) if edu_items else 'Education specified without details'
                else:
                    education_analysis = 'No education specified'
                format_vars['education_section'] = education_analysis
            
            if 'contacts_quality' in required_vars:
                format_vars['contacts_quality'] = "DON'T ANALYSIS THE CONTACT"
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ The complete FormattingAgent, with all variables, has been pre-formed: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ Critical Error FormattingAgent: We did not find the variable {ke}!")
                self.logger.error(f"🔍 Accessable keys in candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Produced variables: {list(format_vars.keys())}")
                # We only use the old logic as a last resort.
                title = candidate_data.get("title", "")
                about = candidate_data.get("about", "")
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                experience = candidate_data.get("experience", [])
                education = candidate_data.get("education", [])
                
                title_analysis = title if title else 'Heading/specialization not specified'
                about_analysis = about if about else 'The section is not available.'
                
                skills_analysis = ""
                if isinstance(skills, list) and skills:
                    skills_analysis = f"Skills list: {', '.join(skills[:10])}" + ("..." if len(skills) > 10 else "")
                elif isinstance(skills, str) and skills:
                    skills_analysis = f"Skills: {skills[:200]}" + ("..." if len(skills) > 200 else "")
                else:
                    skills_analysis = 'Skills not specified'
                
                experience_analysis = ""
                if isinstance(experience, list) and experience:
                    exp_items = []
                    for exp in experience[:3]:
                        position = exp.get('position', '')
                        company = exp.get('company', '')
                        if position or company:
                            exp_items.append(f"{position} in {company}")
                    experience_analysis = "; ".join(exp_items) if exp_items else 'Experience reported without details'
                else:
                    experience_analysis = 'No experience reported'
                
                education_analysis = ""
                if isinstance(education, list) and education:
                    edu_items = []
                    for edu in education[:2]:
                        name = edu.get('name', '')
                        year = edu.get('year', '')
                        if name:
                            edu_items.append(f"{name}" + (f" ({year})" if year else ""))
                    education_analysis = "; ".join(edu_items) if edu_items else 'Education specified without details'
                else:
                    education_analysis = 'No education specified'
                
                user_prompt = analysis_prompt_template.format(
                    title_quality=title_analysis,
                    contacts_quality="DON'T ANALYSIS THE CONTACT",
                    about_section=about_analysis,
                    skills_section=skills_analysis,
                    experience_section=experience_analysis,
                    education_section=education_analysis
                )
                user_prompt += f"\n\n CANDIDATE DATA (JSON):\n{candidate_data_json}"
            
            # CALLING GPTS WITH PROMPTS FROM FILL
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # GPT ANSWER
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", 'Analysis of the quality of the executive summary')
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Error in {self.name}: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary='Error in analysis',
                details=[f"Technical errors: {str(e)}"],
                processing_time=processing_time
            )

class AnomalyDetectionAgent(BaseAgent):
    'Agent in the anomaly detective.'
    
    def __init__(self):
        super().__init__('Anomaly Detection Agent')
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts('anomaly_detection_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Identify anomalies in these candidates.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # OUTLINE: Take out the exact content of the prompt.
            self.logger.error(f"🔍 ANOMALYDetectAgent analysis_prompt_template (first 500 characters)):")
            self.logger.error(f"{analysis_prompt_template[:500]}")
            if '"score"' in analysis_prompt_template:
                self.logger.error(f"❌ Found an invalid score field in the prompt!")
            if '{"score"' in analysis_prompt_template:
                self.logger.error(f"❌ THE PROBLEMS OF CONCERN {{In Prompte!")
            
            # PURPOSE NET JSON DATA
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # Formating the PROMPT – We extract all the necessary changes
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 ANOMALYDetectionAgent: Prompto requires variables: {required_vars}")
            
            # WE NEED ALL POSSIBLE CHANGES FROM CANDIDATE DATA
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Extract additional variables from candidate_data for compatibility
            if 'candidate_age' in required_vars:
                age = candidate_data.get("age")
                format_vars['candidate_age'] = str(age) if age else 'Age not specified'
            
            if 'experience_years' in required_vars:
                total_exp = candidate_data.get("total_experience", {})
                months = total_exp.get("months", 0) if total_exp else 0
                years = months / 12 if months else 0
                format_vars['experience_years'] = f"{years:.1f} years" if years else 'Experience not specified'
            
            if 'skills_list' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                format_vars['skills_list'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'career_progression' in required_vars:
                experience = candidate_data.get("experience", [])
                format_vars['career_progression'] = json.dumps(experience, ensure_ascii=False) if experience else "[]"
            
            if 'education_timeline' in required_vars:
                education = candidate_data.get("education", [])
                format_vars['education_timeline'] = json.dumps(education, ensure_ascii=False) if education else "[]"
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ The complete AnomalDetectionAgent with all variables has been pre-formed: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ Critical Error AnomalyDetectionAgent: We did not find a variable {ke}!")
                self.logger.error(f"🔍 Accessable keys in candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Produced variables: {list(format_vars.keys())}")
                # We'll use the basic prompt with the JSON data.
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\n CANDIDATE DATA (JSON):\n{candidate_data_json}"
            
            # CALLING GPTS WITH PROMPTS FROM FILL
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # GPT ANSWER
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", 'Analysis of anomalies in the candidate &apos; s data')
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Error in {self.name}: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary='Error: Detection of anomalies',
                details=[f"Technical errors: {str(e)}"],
                processing_time=processing_time
            )

class TechnicalSkillsAgent(BaseAgent):
    'Agent in technical skills analysis'
    
    def __init__(self):
        super().__init__('Technical Skills Agent')
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts('technical_skills_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Analyze the technical skills of the candidates.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # PURPOSE NET JSON DATA
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # Formating the PROMPT – We extract all the necessary changes
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 TECHNICALSkillsAgent: Prompto requires variables: {required_vars}")
            
            # WE NEED ALL POSSIBLE CHANGES FROM CANDIDATE DATA
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Extract additional variables from candidate_data for compatibility
            if 'candidate_skills' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                format_vars['candidate_skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'required_technologies' in required_vars:
                format_vars['required_technologies'] = json.dumps(position_requirements.get("skills", []), ensure_ascii=False)
            
            if 'experience_level' in required_vars:
                total_exp = candidate_data.get("total_experience", {})
                format_vars['experience_level'] = f"{total_exp.get('months', 0)} months" if total_exp else 'Experience not specified'
            
            if 'position_level' in required_vars:
                format_vars['position_level'] = position_requirements.get("level", "middle")
            
            if 'specialization' in required_vars:
                format_vars['specialization'] = candidate_data.get("title", "")
            
            if 'experience_description' in required_vars:
                experience = candidate_data.get("experience", [])
                experience_descriptions = []
                if isinstance(experience, list):
                    for exp in experience:
                        if exp.get('description'):
                            experience_descriptions.append(exp['description'])
                format_vars['experience_description'] = "; ".join(experience_descriptions[:3]) if experience_descriptions else 'No description of experience'
            
            if 'position_type' in required_vars:
                format_vars['position_type'] = position_requirements.get("position_type", "technical")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ The complete technicalSkillsAgent with all variables has been pre-formed: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ Critical error TechnicalSkillsAgent: Not found the variable {ke}!")
                self.logger.error(f"🔍 Accessable keys in candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Produced variables: {list(format_vars.keys())}")
                # We'll use the basic prompt with the JSON data.
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\n CANDIDATE DATA (JSON):\n{candidate_data_json}"
            
            # CALLING GPTS WITH PROMPTS FROM FILL
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # GPT ANSWER
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", 'Technical skills analysis')
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Error in {self.name}: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary='Error: Analysis of technical skills',
                details=[f"Technical errors: {str(e)}"],
                processing_time=processing_time
            )

class SkillLevelAgent(BaseAgent):
    'Agent for the strict evaluation of master &apos; s levels in HH.ru standards'
    
    def __init__(self):
        super().__init__('Skill Level Agent')
    
    async def analyze(self, candidate_data: Dict[str, Any], position_requirements: Dict[str, Any], 
                      additional_context: Optional[Dict[str, Any]] = None) -> AgentReport:
        start_time = time.time()
        
        try:
            # LOAD PROMPTS FROM THE FILE
            agent_prompts = self._get_agent_prompts('skill_level_agent')
            system_prompt = agent_prompts.get('system_prompt', 'Carefully assess the levels of skills.')
            analysis_prompt_template = agent_prompts.get('analysis_prompt', "Analyse the candidate's data: {candidate_data_json}")
            
            # PURPOSE NET JSON DATA
            candidate_data_json = self._prepare_raw_data_for_gpt(candidate_data)
            search_query = additional_context.get("search_query", "") if additional_context else ""
            
            import json
            position_requirements_json = json.dumps(position_requirements, ensure_ascii=False, indent=2)
            
            # Formating the PROMPT – We extract all the necessary changes
            import re
            required_vars = re.findall(r'\{(\w+)\}', analysis_prompt_template)
            self.logger.info(f"🔍 SkillLevelAgent: Prompt requires variables: {required_vars}")
            
            # WE NEED ALL POSSIBLE CHANGES FROM CANDIDATE DATA
            format_vars = {
                'candidate_data_json': candidate_data_json,
                'search_query': search_query,
                'position_requirements_json': position_requirements_json
            }
            
            # Extract additional variables from candidate_data for compatibility
            if 'skills' in required_vars:
                skills = candidate_data.get("skill_set", []) or candidate_data.get("skills", [])
                format_vars['skills'] = json.dumps(skills, ensure_ascii=False) if skills else "[]"
            
            if 'experience' in required_vars:
                format_vars['experience'] = json.dumps(candidate_data.get("experience", []), ensure_ascii=False)
            
            if 'total_experience' in required_vars:
                format_vars['total_experience'] = json.dumps(candidate_data.get("total_experience", {}), ensure_ascii=False)
            
            if 'position_type' in required_vars:
                format_vars['position_type'] = position_requirements.get("position_type", "technical")
            
            try:
                user_prompt = analysis_prompt_template.format(**format_vars)
                self.logger.info(f"✅ The complete SkillLevelAgent with all the variables: {list(format_vars.keys())}")
            except KeyError as ke:
                self.logger.error(f"❌ Critical error SkillLevelAgent: Not found a variable {ke}!")
                self.logger.error(f"🔍 Accessable keys in candidate_data: {list(candidate_data.keys())}")
                self.logger.error(f"🔍 Produced variables: {list(format_vars.keys())}")
                # We'll use the basic prompt with the JSON data.
                user_prompt = analysis_prompt_template.format(
                    candidate_data_json=candidate_data_json,
                    position_requirements_json=position_requirements_json
                )
                user_prompt += f"\n\n CANDIDATE DATA (JSON):\n{candidate_data_json}"
            
            # CALLING GPTS WITH PROMPTS FROM FILL
            gpt_result = await self._call_gpt(system_prompt, user_prompt)
            
            # GPT ANSWER
            score = float(gpt_result.get("score", 50.0))
            summary = gpt_result.get("summary", 'Assessment of skills')
            details = gpt_result.get("details", [])
            red_flags = gpt_result.get("red_flags", [])
            positive_points = gpt_result.get("positive_points", [])
            recommendations = gpt_result.get("recommendations", [])
            
            processing_time = time.time() - start_time
            return self._create_report(
                score=score,
                status=self._get_status_by_score(score),
                summary=summary,
                details=details,
                red_flags=red_flags,
                positive_points=positive_points,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Error in {self.name}: {e}")
            self.logger.error(f"🔍 COMPLETE TRACEBACK:\n{traceback.format_exc()}")
            processing_time = time.time() - start_time
            return self._create_report(
                score=0.0,
                status=AgentStatus.ERROR,
                summary='Errors in the analysis of skills',
                details=[f"Technical errors: {str(e)}"],
                processing_time=processing_time
            )