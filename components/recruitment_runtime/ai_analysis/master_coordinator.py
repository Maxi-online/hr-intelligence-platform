"""
Candidate Analysis - Master Coordinator for Multi-Agent System

Coordinator of the Multi-Agency System for the Analysis of Candidates.

This module is the brain of the entire AI analysis system, which:
- Managing the orchestra of 6 specialized agents
- Arranges the results of all agents into a single conclusion
- Generates professional recommendations in the top manager style
- Provides true parallel processing through AsyncOpenAI

Core Functionality:
- Agent Organization: coordination of the work of all specialized agents
- Results Aggregation: Combining agent reports into a single picture
- Master Analysis: Final analysis via GPT-5-nano
- Professional Recommendations: Business Conclusions for HR Divisions

Architecture:
    MasterCoordinator
    ├── Agent Selection (by position type)
    ├── Parallel Agent Execution (true async)
    ├── Results Aggregation & Scoring
    ├── Master GPT Analysis 
    └── Professional Recommendation Generation

Key Features:
- AsyncOpenAI for parallel master analysis calls
- Sub-sets of agents to suit the type of item
- Intelligent aggregation of estimates
- Professional recommendations (recommand/not recommended/not applicable))
- Diagnosis of errors and performance metrics

Performance:
- Master analysis time: ~3-5 seconds per candidate
- Support for Batchev parallel processing
- Exponential Repeat for OpenAI Errors
- Graceful degration when agents are not available

Master Report Structure:
- overall_score: Final evaluation (0-100)
- Recommendation: RECOMMENDATION/ NOT RECOMMENDED/OR
- master_assessment: Opened professional opinion
- individual_scores: Detailed estimates for each criterion
- structurals/weaknesses: The strengths and weaknesses of the candidate

Author: Candidate Analysis Team
Version: 3.0.0 (AsyncOpenAI + True Parallelism)
Last Updated: 2025-01-04
"""

import time
import statistics
import asyncio
import json
import random
from typing import Dict, Any, List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import AsyncOpenAI for GPT analysis
try:
    import openai
    from openai import AsyncOpenAI
    import httpx
    import backoff
except ImportError:
    openai = None
    httpx = None
    backoff = None

from shared.models import (
    MultiAgentAnalysisRequest, MultiAgentAnalysisResponse, 
    MasterCoordinatorReport, AgentReport, AgentStatus
)
from shared.utils import setup_logging

# EXPENSIVE AGENCIES WITHOUT RELEVANT WAYS
import sys
import os

# In the Docker container, all files are in /app
# Add ai_analysis to PYTHONPATH if necessary
if '/app/ai_analysis' not in sys.path:
    sys.path.insert(0, '/app/ai_analysis')
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

# Simple imports without relative routes
from agents import RequirementsAgent, ResumeAnalysisAgent, ExperienceAgent
from agents import FormattingAgent, AnomalyDetectionAgent
from agents import TechnicalSkillsAgent, SkillLevelAgent

logger = setup_logging("master-coordinator")

class MasterCoordinator:
    'Multi-agent system coordinator workshop'
    
    def __init__(self):
        self.logger = logger
        
        # FACILITATION OF load_config()
        from shared.utils import load_config
        self.config = load_config()
        
        # CORRIGENDUM: Load the separate master coordinator configuration
        self._load_coordinator_config()
        self.ai_config = self.config.get("ai_analysis", {})
        
        # USE PROMPT MANAGER INTO A SELECTED POLLUTANT
        from prompt_manager import get_prompt_manager
        self.prompt_manager = get_prompt_manager()
        
        # OUTCOME OPENAI CLICKS WITH PROKSY (as in BaseAgent)
        self._setup_openai_with_proxy()
        
        # Initiate all available agents
        self.agents = {
            "requirements": RequirementsAgent(),
            "resume_analysis": ResumeAnalysisAgent(), 
            "technical_skills": TechnicalSkillsAgent(),
            "skill_level": SkillLevelAgent(),
            "experience": ExperienceAgent(),
            "formatting": FormattingAgent(),
            "anomaly_detection": AnomalyDetectionAgent()
        }
        
        # Agent configuration for different types of entries
        self.position_agent_config = {
            "technical": ["requirements", "technical_skills", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"],
            "management": ["requirements", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"],
            "sales": ["requirements", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"],
            "general": ["requirements", "skill_level", "resume_analysis", "experience", "formatting", "anomaly_detection"]
        }
    
    async def analyze_candidate(self, request: MultiAgentAnalysisRequest) -> MultiAgentAnalysisResponse:
        'Main function of analysis of candidate through all agents'
        start_time = time.time()
        
        try:
            # 1. Identify active agents
            active_agents = self._get_active_agents(request.position_type, request.active_agents)
            self.logger.info(f"Activate agents to analyse candidate {request.candidate_id}: {active_agents}")
            
            # 2. We're running an analysis of all active PARALLONO agents
            agent_reports = await self._run_agents_analysis(
                active_agents, request.candidate_data, request.position_requirements, 
                {"search_query": request.search_query, "search_filters": request.search_filters}
            )
            
            # 3. Generate the master's final report
            self.logger.info(f"🔥 Let's move on to the production of the master's report, received {len(agent_reports)} agent reports")
            master_report = await self._generate_master_report(agent_reports, request)
            self.logger.info(f"🔥 The master &apos; s report has been successfully generated")
            
            # 4. Form the final answer.
            total_processing_time = time.time() - start_time
            
            return MultiAgentAnalysisResponse(
                candidate_id=request.candidate_id,
                master_report=master_report,
                agent_reports=agent_reports,
                active_agents=active_agents,
                total_processing_time=total_processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Critical error in the master coordinator for the candidate {request.candidate_id}: {e}")
            raise e
    
    def _get_active_agents(self, position_type: str, requested_agents: Optional[List[str]]) -> List[str]:
        'Identify active agent list'
        if requested_agents:
            # Use clearly identified agents.
            return [agent for agent in requested_agents if agent in self.agents]
        
        # Automatic definition by type of entry
        return self.position_agent_config.get(position_type, self.position_agent_config["general"])
    
    async def _run_agents_analysis(self, active_agents: List[str], candidate_data: Dict[str, Any], 
                                 position_requirements: Dict[str, Any], additional_context: Dict[str, Any]) -> List[AgentReport]:
        'Runs an analysis of all active agents of PARALLONO'
        
        # Create tasks for all agents
        tasks = []
        for agent_name in active_agents:
            agent = self.agents[agent_name]
            task = self._run_single_agent(agent_name, agent, candidate_data, position_requirements, additional_context)
            tasks.append(task)
        
        self.logger.info(f"🚀 Launch {len(tasks)} PARALLELAL ASSISTANCES")
        
        # Perform all the tasks in parallel.
        agent_reports = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processing results and errors
        processed_reports = []
        for i, result in enumerate(agent_reports):
            agent_name = active_agents[i]
            
            if isinstance(result, Exception):
                self.logger.error(f"❌ Error in the agent {agent_name}: {result}")
                # Create an error report
                error_report = AgentReport(
                    agent_name=agent_name,
                    score=0.0,
                    status=AgentStatus.ERROR,
                    summary=f"Error of the agent {agent_name}",
                    details=[f"Technical errors: {str(result)}"],
                    red_flags=['The agent failed to perform the analysis.'],
                    positive_points=[],
                    recommendations=['Manual verification required'],
                    processing_time=0.0
                )
                processed_reports.append(error_report)
            else:
                processed_reports.append(result)
                self.logger.info(f"✅ Agent {agent_name} Completed the assessment analysis {result.score:.1f}%")
        
        self.logger.info(f"🏁 All {len(processed_reports)} agents have completed work")
        return processed_reports
    
    async def _run_single_agent(self, agent_name: str, agent, candidate_data: Dict[str, Any], 
                              position_requirements: Dict[str, Any], additional_context: Dict[str, Any]) -> AgentReport:
        'Starts one agent with error processing'
        try:
            self.logger.info(f"⚡ Launching agent: {agent_name}")
            report = await agent.analyze(candidate_data, position_requirements, additional_context)
            return report
        except Exception as e:
            self.logger.error(f"💥 Critical error in the agent {agent_name}: {e}")
            raise e
    
    async def _generate_master_report(self, agent_reports: List[AgentReport], 
                               request: MultiAgentAnalysisRequest) -> MasterCoordinatorReport:
        'Generates the final report of the Coordinator'
        start_time = time.time()
        
        # 1. Compute arithmetic average estimates
        valid_scores = [report.score for report in agent_reports if report.status != AgentStatus.ERROR]
        overall_score = statistics.mean(valid_scores) if valid_scores else 0.0
        
        # 2. Individual assessments collected
        individual_scores = {report.agent_name: report.score for report in agent_reports}
        
        # 3. Analysis of agent status
        agents_with_warnings = [r.agent_name for r in agent_reports if r.status == AgentStatus.WARNING]
        agents_with_failures = [r.agent_name for r in agent_reports if r.status == AgentStatus.FAIL]
        
        # 4. Counting red flags and pros
        total_red_flags = sum(len(report.red_flags) for report in agent_reports)
        total_positive_points = sum(len(report.positive_points) for report in agent_reports)
        
        # 5. Generate the textual evaluation of the master
        self.logger.info(f"🤖 MASTER COORDINATOR: Start generating analysis for the candidate")
        master_assessment = await self._generate_master_assessment(
            agent_reports, overall_score, total_red_flags, total_positive_points, 
            agents_with_warnings, agents_with_failures, request
        )
        self.logger.info(f"🤖 MASTER COORDINATOR: Analysis generated, length: {len(master_assessment)} Symbols")
        
        # 6. Defining the final recommendation
        recommendation = self._get_final_recommendation(overall_score, total_red_flags, len(agents_with_failures))
        
        processing_time = time.time() - start_time
        
        return MasterCoordinatorReport(
            overall_score=round(overall_score, 1),
            individual_scores=individual_scores,
            master_assessment=master_assessment,
            recommendation=recommendation,
            total_red_flags=total_red_flags,
            total_positive_points=total_positive_points,
            agents_with_warnings=agents_with_warnings,
            agents_with_failures=agents_with_failures,
            processing_time=processing_time
        )
    
    async def _generate_master_assessment(self, agent_reports: List[AgentReport], overall_score: float,
                                   total_red_flags: int, total_positive_points: int,
                                   agents_with_warnings: List[str], agents_with_failures: List[str],
                                   request: MultiAgentAnalysisRequest) -> str:
        "Generates the master's quality text evaluation via GPT"
        self.logger.info(f"🔥 OTADE_generate_master_assessment: Start generation, OpenAI client: {self.openai_client is not None}")
        
        # Gather all the data from the agents for the master's analysis.
        agent_data = []
        for report in agent_reports:
            agent_info = {
                "name": report.agent_name,
                "score": report.score,
                "status": report.status.value,
                "summary": report.summary,
                "details": report.details,
                "red_flags": report.red_flags,
                "positive_points": report.positive_points,
                "recommendations": report.recommendations
            }
            agent_data.append(agent_info)
        
        # Generate quality analysis through AsyncOpenAI
        return await self._call_gpt_for_master_analysis(
            agent_data, overall_score, request.candidate_data, 
            request.position_requirements, request.search_query
        )
    

    
    def _load_coordinator_config(self):
        'Uploads the master coordinator configuration from agent_configs.yaml'
        try:
            import yaml
            # We're gonna try out a few ways.
            possible_paths = [
                "ai_analysis/agent_configs.yaml",  # Local
                "/app/ai_analysis/agent_configs.yaml"  # Docker
            ]
            
            for config_path in possible_paths:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        full_config = yaml.safe_load(f)
                        self.coordinator_config = full_config.get('master_coordinator', {})
                        self.logger.info(f"✅ Workshop coordinator configuration downloaded from {config_path}")
                        return
            
            self.logger.warning(f"⚠️ agent_configs.yaml file not found for Master Coordinator")
            self.coordinator_config = {}
        except Exception as e:
            self.logger.error(f"Error: ❌ Configuration of Master Coordinator: {e}")
            self.coordinator_config = {}
    
    def _setup_openai_with_proxy(self):
        'OpenAI is a client with a proxie (a copy of the logic from BaseAgent))'
        try:
            # Get an API key.
            api_key = self.ai_config.get("openai_api_key")
            if not api_key:
                self.logger.warning(f"⚠️ OPENAI_API_KEY not installed for Master Coordinator")
            
            # Settings HTTP Proxi from configuration
            proxy_config = self.ai_config.get("proxy", {})
            proxy_enabled = proxy_config.get("enabled", False)
            
            if proxy_enabled and httpx:
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
                    
                    self.logger.info(f"🌐 OpenAI Proxi client initialized for Master Coordinator: {proxy_host}:{proxy_port}")
                else:
                    # If Proxi settings are incomplete, the normal customer is used
                    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                    self.logger.warning(f"⚠️ Proxi is on for the master coordinator, but the settings are incomplete. Direct connection used.")
            else:
                # Normal httpx client with no proxie for AsyncOpenAI
                if httpx:
                    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
                    self.logger.info(f"🔗 OpenAI client without proxie initialized for master coordinator")
                else:
                    http_client = None
                    self.logger.warning(f"⚠️ httpx is not available to the coordinator")
            
            # OpenRouter Client Initialization
            if openai:
                base_url = self.ai_config.get("base_url", "https://openrouter.ai/api/v1")
                
                if "openrouter.ai" in base_url:
                    # OpenRouter Mode
                    openrouter_key = self.ai_config.get("openrouter_api_key")
                    if not openrouter_key:
                        raise ValueError('OpenRouter requires openrouter_api_key in configuration')
                    
                    # Create a client without a proxie for OpenRouter
                    self.openai_client = AsyncOpenAI(
                        api_key=openrouter_key,
                        base_url=base_url
                    )
                    self.logger.info(f"🔄 OpenRouter AsyncOpenAI client for Master Coordinator: {base_url}")
                    
                    # OpenRouter settings
                    self.site_url = self.ai_config.get("site_url", "")
                    self.site_name = self.ai_config.get("site_name", "CandidateRanking")
                else:
                    # Old OpenAI Mode
                    if http_client:
                        self.openai_client = AsyncOpenAI(
                            api_key=api_key,
                            http_client=http_client,
                            base_url=base_url if base_url != "https://openrouter.ai/api/v1" else None
                        )
                    else:
                        self.openai_client = AsyncOpenAI(
                            api_key=api_key,
                            base_url=base_url if base_url != "https://openrouter.ai/api/v1" else None
                        )
                    self.site_url = ""
                    self.site_name = ""
                
                # Model parameters from configuration
                self.model = self.ai_config.get("model", "gpt-5-mini")
                self.max_completion_tokens = self.ai_config.get("max_completion_tokens", 5000)  # GPT-5 Point for Coordinator
                
                # GPT-5 Points for Coordinator
                coordinator_config = self.config.get("ai_analysis", {}).get("multi_agent", {}).get("master_coordinator", {})
                self.verbosity = coordinator_config.get("verbosity", "high")
                self.reasoning_effort = coordinator_config.get("reasoning_effort", "medium")
                self.temperature = self.ai_config.get("temperature", 0.0)
                
                self.logger.info(f"✅ AsyncOpenAI Master Coordinator client set (model): {self.model})")
            else:
                self.openai_client = None
                self.logger.warning(f"⚠️ AsyncOpenAI is not available to the coordinator")
            
        except Exception as e:
            self.logger.error(f"❌ AsyncOpenAI Customer Configuration Error for Master Coordinator: {e}")
            self.openai_client = None
    
    async def _call_gpt_for_master_analysis(self, agent_data: List[Dict], overall_score: float, 
                                     candidate_data: Dict, position_requirements: Dict, search_query: str) -> str:
        'Call GPT for quality analysis of all data by the Coordinator'
        
        self.logger.info(f"🤖 MATER-COORDINATOR: The GPT analysis challenge begins")
        self.logger.info(f"🤖 OPENAI client available: {self.openai_client is not None}")
        
        if not self.openai_client:
            # Fallback: If OpenAI is not available, generate simple text
            self.logger.warning(f"⚠️ OPENAI is not available and is used by Fallback")
            return self._generate_fallback_assessment(agent_data, overall_score, search_query)
        
        try:
            # Check candidate_data type and process correctly
            if isinstance(candidate_data, list):
                # If it's a list, take the first element.
                candidate_dict = candidate_data[0] if candidate_data else {}
                self.logger.warning(f"🤖 MATER-COORDINATOR: candidate_data is a list using the first element")
            elif isinstance(candidate_data, dict):
                candidate_dict = candidate_data
            else:
                self.logger.error(f"🤖 MASTER-COORDINATOR: Unexpected type candidate_data: {type(candidate_data)}")
                candidate_dict = {}
            
            # Prepare data for GPT
            candidate_summary = {
                "name": candidate_dict.get("name", 'Not specified'),
                "title": candidate_dict.get("title", 'Not specified'),
                "experience_months": candidate_dict.get("experience", {}).get("total_months", 0) if isinstance(candidate_dict.get("experience"), dict) else 0,
                "area": candidate_dict.get("area", {}).get("name", 'Not specified') if isinstance(candidate_dict.get("area"), dict) else 'Not specified',
                "salary": candidate_dict.get("salary", {}),
                "skills": candidate_dict.get("skills", []),
                "education": candidate_dict.get("education", []),
                "about": candidate_dict.get("about", "")
            }
            
            # We get prompts from PromptManager.
            self.logger.info(f"🤖 ♪ We're downloading promptManager promptManager ♪")
            system_prompt = self.prompt_manager.get_prompt("master_coordinator", "system_prompt")
            analysis_prompt = self.prompt_manager.get_prompt("master_coordinator", "analysis_prompt")
            
            self.logger.info(f"🤖 system_prompt found: {system_prompt is not None}")
            self.logger.info(f"🤖 analysis_prompt found: {analysis_prompt is not None}")
            
            if not system_prompt or not analysis_prompt:
                self.logger.warning('⚠️ MATER COORDINATOR: Prompts not found, used fallsback')
                return self._generate_fallback_assessment(agent_data, overall_score, search_query)
            
            # Format analysis_prompt with data
            formatted_analysis_prompt = analysis_prompt.format(
                candidate_summary=json.dumps(candidate_summary, ensure_ascii=False, indent=2),
                search_query=search_query,
                position_requirements=json.dumps(position_requirements, ensure_ascii=False, indent=2),
                agent_data=json.dumps(agent_data, ensure_ascii=False, indent=2),
                overall_score=overall_score
            )
            
            # Prepare parameters for OpenRouter
            extra_headers = {}
            if hasattr(self, 'site_url') and self.site_url:
                extra_headers["HTTP-Referer"] = self.site_url
            if hasattr(self, 'site_name') and self.site_name:
                extra_headers["X-Title"] = self.site_name

            # SUSTAINABLE ASYNCHRONY, supported by OpenRouter and GPT-5
            gpt5_params = {}
            if hasattr(self, 'verbosity') and hasattr(self, 'reasoning_effort'):
                gpt5_params.update({
                    "verbosity": self.verbosity,
                    "reasoning_effort": self.reasoning_effort
                })
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_analysis_prompt}
                ],
                max_completion_tokens=self.max_completion_tokens,  # GPT-5 parameter
                temperature=self.temperature,
                extra_headers=extra_headers if extra_headers else {},
                # GPT-5 parameters are transmitted directly
                verbosity=gpt5_params.get("verbosity", "high") if gpt5_params else "high",
                reasoning_effort=gpt5_params.get("reasoning_effort", "medium") if gpt5_params else "medium"
            )
            
            gpt_analysis = response.choices[0].message.content.strip()
            self.logger.info('✅ GPT analysis successfully generated')
            return gpt_analysis
            
        except Exception as e:
            self.logger.error(f"❌ GPT analysis error of master: {e}")
            return self._generate_fallback_assessment(agent_data, overall_score, search_query)
    
    def _generate_fallback_assessment(self, agent_data: List[Dict], overall_score: float, search_query: str) -> str:
        'Generates simplified analysis when GPT is not available'
        
        high_scores = [agent for agent in agent_data if agent["score"] >= 70]
        low_scores = [agent for agent in agent_data if agent["score"] < 50]
        
        assessment = f"**Automatic analysis of the candidate** (GPT not available)\n\n"
        assessment += f"Overall assessment: {overall_score:.1f}%\n\n"
        
        if overall_score >= 70:
            assessment += f"The candidate shows a good match. '{search_query}'. "
        elif overall_score >= 50:
            assessment += f"The candidate partially meets the requirements of the entry. '{search_query}'. "
        else:
            assessment += f"The candidate does not meet the requirements of the position.{search_query}'. "
        
        if high_scores:
            assessment += f"The strengths have shown {len(high_scores)} Agents. "
        
        if low_scores:
            assessment += f"Problems identified in the {len(low_scores)} Areas of analysis. "
        
        assessment += '\n\nFull analysis requires the activation of the GPT Coordinator.'
        
        return assessment
    
    def _generate_conclusion(self, score: float, red_flags: int, failures: int, 
                           request: MultiAgentAnalysisRequest) -> str:
        'Generates the final conclusion'
        if score >= 85 and red_flags <= 2:
            return f"Excellent candidate for position '{request.search_query}'. High compliance and minimum risk. Recommended for further consideration."
        
        elif score >= 70 and failures == 0:
            return f"Good candidate for position.{request.search_query}'. Meets the basic requirements with minor comments. It's good for an interview."
        
        elif score >= 60:
            return f"The candidate can fit for position '{request.search_query}' with additional inspection. There are areas for discussion at the interview."
        
        elif score >= 40:
            return f"The candidate partially meets the requirements of the entry. '{request.search_query}'. A thorough evaluation at the interview is required."
        
        else:
            return f"The candidate does not meet the requirements of the position.{request.search_query}'. High risks, more suitable candidates recommended."
    
    def _get_final_recommendation(self, score: float, red_flags: int, failures: int) -> str:
        'Determines final recommendation'
        if score >= 80 and failures == 0:
            return 'RECOMMENDED TO THE Interview'
        elif score >= 65 and failures <= 1:
            return 'SEE WITH care'
        elif score >= 50:
            return 'THINKS of additional checks'
        else:
            return 'NOT RECOMMENDED'
    
    def _get_status_emoji(self, status: AgentStatus) -> str:
        'Returns emoji for status.'
        emoji_map = {
            AgentStatus.PASS: "✅",
            AgentStatus.WARNING: "⚠️", 
            AgentStatus.FAIL: "❌",
            AgentStatus.ERROR: "🔥"
        }
        return emoji_map.get(status, "❓")
    
    def get_available_agents(self) -> Dict[str, str]:
        'Returns the list of available agents'
        return {name: agent.name for name, agent in self.agents.items()}
    
    def get_position_config(self) -> Dict[str, List[str]]:
        'Returns agent configuration for different types of entries'
        return self.position_agent_config.copy()