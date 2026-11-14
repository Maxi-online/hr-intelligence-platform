"""
Candidate Analysis - AI Analysis Service

AI Multi-Agent Analysis Service for candidates with true parallel processing.

This module provides intellectual analysis of candidates using:
- GPT-5-nano for rapid and accurate analysis
- AsyncOpenAI for true parallel processing
- Multi-agent architecture with 6 specialized agents
- Master coordinator for the final professional qualification

Main components:
- AIANALIZER: Lonely Analysis of Candidates (legacy)
- Multi-Agent System: Parallel Analysis through Specialized Agents
- Master Coordinate: Outcome and recommendations

AI Analysis Architecture:
    Multi-Agent Request -> 6 Specialist Agents (Parallel)
                        -> Master Coordinator -> Professional Assessment
                        -> Final Recommendation + Score

Performance Features:
- OpenAI API asynchronous calls for maximum speed
- Batch processing of candidates at the same time  
- Exponential Repeats in Errors
- Detailed diagnostic logic

Agents:
- TechnicalSkillsAgent: Technical Skills Analysis
- ExperienceRelevanceAgent: Assessing the relevance of experience  
CulturalFitAgent: Cultural Conformity Analysis
- GrowthPotentialAgent: Assessing Growth Potential
- ResumeAnalysisAgent: Quality Analysis of Summary
- AnomalyDetectionAgent: Identification of inconsistencies

Author: Candidate Analysis Team
Version: 3.0.0 (AsyncOpenAI + True Parallelism)
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import httpx
import json
import os
import sys
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the parent directory to the route to import the used modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse, AIAnalysisRequest, AIAnalysisResponse, 
    SkillAnalysis, CandidateProfile, RankingWeights,
    MultiAgentAnalysisRequest, MultiAgentAnalysisResponse
)
from shared.utils import setup_logging, load_config

# Logging settings
logger = setup_logging("ai-analysis-service")

app = FastAPI(
    title="AI Analysis Service",
    description='AI Analysis of Candidates &apos; Skills using GPT-5-nano',
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

class AIAnalyzer:
    def __init__(self):
        self.config = load_config()
        self.ai_config = self.config.get("ai_analysis", {})
        
        # Initialization of OpenAI with a modern client - configuration priority!
        api_key = self.ai_config.get("openai_api_key") or os.getenv("OPENAI_API_KEY") 
        if not api_key:
            logger.warning('OPENAI_API_KEY not installed')
        else:
            logger.info(f"Use OpenAI key: {api_key[:20]}...")
        
        # Settings HTTP Proxi from configuration
        proxy_config = self.ai_config.get("proxy", {})
        proxy_enabled = proxy_config.get("enabled", False)
        
        if proxy_enabled:
            # We're going to get proxie settings from configuration or variable environments
            proxy_host = os.getenv("PROXY_HOST") or proxy_config.get("host", "")
            proxy_port = os.getenv("PROXY_PORT") or proxy_config.get("port", "")
            proxy_username = os.getenv("PROXY_USERNAME") or proxy_config.get("username", "")
            proxy_password = os.getenv("PROXY_PASSWORD") or proxy_config.get("password", "")
            proxy_protocol = os.getenv("PROXY_PROTOCOL") or proxy_config.get("protocol", "http")
            
            if proxy_host and proxy_port:
                # Form an uRL proxie
                if proxy_username and proxy_password:
                    proxy_url = f"{proxy_protocol}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                else:
                    proxy_url = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
                
                # Create httpx client with proxie
                http_client = httpx.Client(
                    proxy=proxy_url
                )
                
                logger.info(f"OpenAI client initialized with HTTP Proxi: {proxy_host}:{proxy_port}")
            else:
                # If Proxi settings are incomplete, the normal customer is used
                http_client = httpx.Client()
                logger.warning('Proxi is on, but the settings are incomplete. Direct connection used.')
        else:
            # Normal httpx client without proxie
            http_client = httpx.Client()
            logger.info('OpenAI client initialized without proxi')
        
        # OpenRouter Client Initialization
        base_url = self.ai_config.get("base_url", "https://openrouter.ai/api/v1")
        
        # Check if OpenRouter is used
        if "openrouter.ai" in base_url:
            # OpenRouter Mode
            openrouter_key = self.ai_config.get("openrouter_api_key")
            if not openrouter_key:
                raise ValueError('OpenRouter requires openrouter_api_key in configuration')
            
            # Create a client without a proxie for OpenRouter
            self.client = OpenAI(
                api_key=openrouter_key,
                base_url=base_url
            )
            logger.info(f"🔄 OpenRouter client initialized: {base_url}")
            
            # OpenRouter settings
            self.site_url = self.ai_config.get("site_url", "")
            self.site_name = self.ai_config.get("site_name", "CandidateRanking")
        else:
            # Old OpenAI Mode
            self.client = OpenAI(
                api_key=api_key,
                http_client=http_client,
                base_url=base_url if base_url != "https://openrouter.ai/api/v1" else None
            )
            self.site_url = ""
            self.site_name = ""
            logger.info('OpenAI client initialized')
        
        self.model = self.ai_config.get("model", "gpt-5-mini")
        self.max_completion_tokens = self.ai_config.get("max_completion_tokens", 4000)  # GPT-5 parameter
        self.temperature = self.ai_config.get("temperature", 0.0)
        self.retry_attempts = self.ai_config.get("retry_attempts", 3)
        
        # Prompts
        self.prompts = self.ai_config.get("prompts", {})
    
    def analyze_skills(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        'Analysis of the candidate &apos; s skills using GPT-5-nano based on ranking weights'
        start_time = time.time()
        
        try:
            # We extract additional data from candidate_data
            candidate_data = request.candidate_data or {}
            candidate_title = candidate_data.get("title", 'Not specified')
            last_work = candidate_data.get("last_work", {})
            last_work_position = last_work.get("position", 'Not specified') if last_work else 'Not specified'
            last_work_company = last_work.get("name", 'Not specified') if last_work else 'Not specified'
            experience_data = candidate_data.get("experience", {})
            total_experience_months = experience_data.get("months", 0) if experience_data else 0
            
            # Formation of a skills analysis prompt
            skill_prompt = self.prompts.get("skill_analysis", "").format(
                job_title=request.search_query,
                skills=", ".join(request.skills),
                experience=request.experience_description or 'Not specified',
                search_query=request.search_query,
                candidate_title=candidate_title,
                last_work_position=last_work_position,
                last_work_company=last_work_company,
                total_experience_months=total_experience_months
            )
            
            # GPT-5-nano for skills analysis
            skill_analysis = self._call_gpt4(skill_prompt)
            
            # Parsing the results of the skills analysis
            skill_results = self._parse_skill_analysis(skill_analysis)
            
            # Receive ranking weights or use default values
            weights = request.ranking_weights or RankingWeights()
            
            # Formation of a prompt for total weight rating
            overall_prompt = self.prompts.get("overall_assessment", "").format(
                job_title=request.search_query,
                skill_analysis=json.dumps([s.model_dump() for s in skill_results], ensure_ascii=False, default=str),
                search_query=request.search_query,
                candidate_data=json.dumps(request.candidate_data or {}, ensure_ascii=False, default=str),
                search_filters=json.dumps(request.search_filters or {}, ensure_ascii=False, default=str),
                candidate_title=candidate_title,
                last_work_position=last_work_position,
                last_work_company=last_work_company,
                total_experience_months=total_experience_months,
                keyword_relevance_weight=weights.keyword_relevance,
                filter_match_weight=weights.filter_match,
                recency_weight=weights.recency,
                profile_completeness_weight=weights.profile_completeness
            )
            
            # GPT-5-nano call for overall assessment
            overall_assessment = self._call_gpt4(overall_prompt)
            
            # Parsing overall rating with new fields
            overall_result = self._parse_overall_assessment(overall_assessment)
            
            processing_time = time.time() - start_time
            
            return AIAnalysisResponse(
                candidate_id=request.candidate_id,
                skill_analysis=skill_results,
                overall_score=overall_result.get("overall_score", 0.0),
                analysis_summary=overall_result.get("summary", ""),
                processing_time=processing_time,
                keyword_relevance_score=overall_result.get("keyword_relevance_score"),
                filter_match_score=overall_result.get("filter_match_score"),
                recency_score=overall_result.get("recency_score"),
                profile_completeness_score=overall_result.get("profile_completeness_score"),
                reasoning=overall_result.get("reasoning")
            )
            
        except Exception as e:
            logger.error(f"Error: Analysis of Skills for the Candidate {request.candidate_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failure in AI analysis: {str(e)}")
    
    def _call_gpt4(self, prompt: str) -> str:
        'GPT-5-nano call with repeated attempts'
        for attempt in range(self.retry_attempts):
            try:
                # Prepare parameters for OpenRouter
                extra_headers = {}
                if self.site_url:
                    extra_headers["HTTP-Referer"] = self.site_url
                if self.site_name:
                    extra_headers["X-Title"] = self.site_name
                
                # GPT-5 Skills Analysis Options
                gpt5_params = {}
                gpt5_features = self.ai_config.get("gpt5_features", {})
                if gpt5_features:
                    gpt5_params.update({
                        "verbosity": gpt5_features.get("default_verbosity", "medium"),
                        "reasoning_effort": gpt5_features.get("default_reasoning_effort", "medium")
                    })
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You're an expert in the assessment of candidates' skills. Answer only in JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=self.max_completion_tokens,  # GPT-5 parameter
                    temperature=self.temperature,
                    extra_headers=extra_headers if extra_headers else {},
                    # GPT-5 parameters are transmitted directly
                    verbosity=gpt5_params.get("verbosity", "medium") if gpt5_params else "medium",
                    reasoning_effort=gpt5_params.get("reasoning_effort", "medium") if gpt5_params else "medium"
                )
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.warning(f"Attempted {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    raise e
                time.sleep(1)
    
    def _parse_skill_analysis(self, response: str) -> List[SkillAnalysis]:
        'Parsing the results of the skills analysis'
        try:
            # Extract JSON from the response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError('JSON is not found in the answer')
            
            json_str = response[json_start:json_end]
            skills_data = json.loads(json_str)
            
            skill_analyses = []
            for skill_data in skills_data:
                skill_analysis = SkillAnalysis(
                    skill_name=skill_data.get("skill_name", ""),
                    relevance_score=float(skill_data.get("relevance_score", 0.0)),
                    proficiency_level=skill_data.get("proficiency_level", "Unknown"),
                    years_experience=skill_data.get("years_experience"),
                    ai_confidence=float(skill_data.get("ai_confidence", 0.5)),
                    analysis_timestamp=datetime.now()
                )
                skill_analyses.append(skill_analysis)
            
            return skill_analyses
            
        except Exception as e:
            logger.error(f"Parsing error analysis of skills: {e}")
            logger.error(f"GPT's response: {response}")
            raise ValueError(f"Wrong GPT response format: {e}")
    
    def _parse_overall_assessment(self, response: str) -> Dict[str, Any]:
        'Parsing overall rating with new fields for AI ranking'
        try:
            # Extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError('JSON is not found in the answer')
            
            json_str = response[json_start:json_end]
            assessment_data = json.loads(json_str)
            
            return {
                "overall_score": float(assessment_data.get("overall_score", 0.0)),
                "summary": assessment_data.get("summary", ""),
                "keyword_relevance_score": assessment_data.get("keyword_relevance_score"),
                "filter_match_score": assessment_data.get("filter_match_score"),
                "recency_score": assessment_data.get("recency_score"),
                "profile_completeness_score": assessment_data.get("profile_completeness_score"),
                "reasoning": assessment_data.get("reasoning")
            }
            
        except Exception as e:
            logger.error(f"Error of Parsing General Assessment: {e}")
            logger.error(f"GPT's response: {response}")
            return {
                "overall_score": 0.0, 
                "summary": 'Error of analysis',
                "keyword_relevance_score": None,
                "filter_match_score": None,
                "recency_score": None,
                "profile_completeness_score": None,
                "reasoning": None
            }
    
    def batch_analyze(self, requests: List[AIAnalysisRequest]) -> List[AIAnalysisResponse]:
        'Several candidates &apos; package analysis'
        results = []
        for request in requests:
            try:
                result = self.analyze_skills(request)
                results.append(result)
            except Exception as e:
                logger.error(f"Error: Analysis of the candidate {request.candidate_id}: {e}")
                # Create an empty result in case of error
                results.append(AIAnalysisResponse(
                    candidate_id=request.candidate_id,
                    skill_analysis=[],
                    overall_score=0.0,
                    analysis_summary='Error of analysis',
                    processing_time=0.0
                ))
        return results

# Initialization of AI Analyst
ai_analyzer = AIAnalyzer()

# Import and Initialization of Master Coordinator
try:
    # Adding the current directory to local imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)  # Add to the beginning for priority
    
    # We're going to try different import options.
    try:
        from master_coordinator import MasterCoordinator
    except ImportError:
        from ai_analysis.master_coordinator import MasterCoordinator
    
    master_coordinator = MasterCoordinator()
    logger.info('🤖 Multi-agent system coordinator workshop initialized')
except Exception as e:
    logger.error(f"Error: Initialization of Master Coordinator: {e}")
    import traceback
    logger.error(f"Full mistake: {traceback.format_exc()}")
    master_coordinator = None

@app.get("/health", response_model=HealthResponse)
async def health_check():
    'Service health check'
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_candidate(request: AIAnalysisRequest):
    'Analysis of one candidate &apos; s skills'
    try:
        return ai_analyzer.analyze_skills(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: Analysis of the candidate: {e}")
        raise HTTPException(status_code=500, detail='The internal server error')

@app.post("/analyze/batch")
async def analyze_candidates_batch(requests: List[AIAnalysisRequest]):
    'Several candidates &apos; package analysis'
    try:
        return ai_analyzer.batch_analyze(requests)
    except Exception as e:
        logger.error(f"Error in package analysis: {e}")
        raise HTTPException(status_code=500, detail='Error in package analysis')

@app.get("/config")
async def get_ai_config():
    'AI analysis configuration acquisition'
    try:
        return {
            "model": ai_analyzer.model,
            "max_completion_tokens": ai_analyzer.max_completion_tokens,
            # "temperature": ai_analyzer.temperature,
            "retry_attempts": ai_analyzer.retry_attempts
        }
    except Exception as e:
        logger.error(f"Error of Configuration: {e}")
        raise HTTPException(status_code=500, detail='Error of Configuration')

@app.post("/settings/auth")
async def update_auth_settings(auth_settings: dict):
    'Update of authentication settings'
    try:
        # Update OpenAI settings
        if "openai_api_key" in auth_settings:
            ai_analyzer.client = OpenAI(api_key=auth_settings["openai_api_key"])
            logger.info('OpenAI API key updated')
        
        # Fixed model (gpt-5-nano), unchanged
        return {
            "status": "success",
            "message": 'The AI Analysis settings have been updated',
            "model": ai_analyzer.model,  # Always gpt-5-nano
            "api_key_set": bool(ai_analyzer.client.api_key if hasattr(ai_analyzer.client, 'api_key') else False)
        }
    except Exception as e:
        logger.error(f"Error: Update of the AI Analysis Settings: {e}")
        raise HTTPException(status_code=500, detail='Error: Update of the AI Analysis Settings')

# ================================
# ENDPOINTS MULTI-AGENCY SYSTEM
# ================================

@app.post("/multi-agent/analyze", response_model=MultiAgentAnalysisResponse)
async def analyze_candidate_multi_agent(request: MultiAgentAnalysisRequest):
    'Multi-agent analysis of the candidate'
    try:
        if not master_coordinator:
            raise HTTPException(status_code=503, detail='Master Coordinator not available')
        
        logger.info(f"🤖 Launch multi-agent analysis for candidate {request.candidate_id}")
        
        # FLAMMING: VERIFICATION OF WHAT IS TO BE TRANSFERED IN CANDIDATE_DATA
        candidate_data_size = len(str(request.candidate_data))
        candidate_data_keys = list(request.candidate_data.keys()) if isinstance(request.candidate_data, dict) else 'Not a word.'
        logger.debug(f"🔍 candidate_data for {request.candidate_id}: size={candidate_data_size}, keys={candidate_data_keys}")
        
        # A child's role in the model of problem fields
        if isinstance(request.candidate_data, dict):
            experience = request.candidate_data.get('experience')
            education = request.candidate_data.get('education') 
            language = request.candidate_data.get('language')
            skills = request.candidate_data.get('skills')
            skill_set = request.candidate_data.get('skill_set')
            
            logger.error(f"🔍 TYPES OF DATA:")
            logger.error(f"   experience: {type(experience)} = {experience if experience is None else (f'List from {len(experience)} elements' if isinstance(experience, list) else 'Not List')}")
            logger.error(f"   education: {type(education)} = {education if education is None else (f'List from {len(education)} elements' if isinstance(education, list) else 'Not List')}")
            logger.error(f"   language: {type(language)} = {language if language is None else (f'List from {len(language)} elements' if isinstance(language, list) else 'Not List')}")
            logger.error(f"   skills: {type(skills)} = {skills if skills is None else (f'List from {len(skills)} elements' if isinstance(skills, list) else 'Not List')}")
            logger.error(f"   skill_set: {type(skill_set)} = {skill_set if skill_set is None else (f'List from {len(skill_set)} elements' if isinstance(skill_set, list) else 'Not List')}")
        
        # This is the call of the asynchronous!
        result = await master_coordinator.analyze_candidate(request)
        
        logger.info(f"✅ Multi-agent analysis completed for candidate {request.candidate_id}. " + 
                   f"Overall assessment: {result.master_report.overall_score:.1f}%")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: Multi-agent analysis of the candidate {request.candidate_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-Agent Analysis Error: {str(e)}")

@app.get("/multi-agent/agents")
async def get_available_agents():
    'Getting a list of available agents'
    try:
        if not master_coordinator:
            raise HTTPException(status_code=503, detail='Master Coordinator not available')
        
        return {
            "available_agents": master_coordinator.get_available_agents(),
            "position_configs": master_coordinator.get_position_config(),
            "total_agents": len(master_coordinator.agents)
        }
    except Exception as e:
        logger.error(f"Error in obtaining a list of agents: {e}")
        raise HTTPException(status_code=500, detail='Error in obtaining a list of agents')

@app.get("/multi-agent/health")
async def multi_agent_health_check():
    'Multi-agent system health check'
    try:
        health_status = {
            "master_coordinator": master_coordinator is not None,
            "agents_count": len(master_coordinator.agents) if master_coordinator else 0,
            "timestamp": datetime.now(),
            "status": "healthy" if master_coordinator else "unhealthy"
        }
        
        if master_coordinator:
            health_status["available_agents"] = list(master_coordinator.agents.keys())
        
        return health_status
        
    except Exception as e:
        logger.error(f"Mistakes in the Multi-Agent System Health Inspection: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now()
        }

@app.post("/multi-agent/batch", response_model=List[MultiAgentAnalysisResponse])
async def analyze_candidates_batch_multi_agent(requests: List[MultiAgentAnalysisRequest]):
    """
    Batch multi-agent analysis of candidates with true parallel processing.
    
    Key API endpoint for mass analysis of candidates with maximum productivity.
    Implements a two-stage parallel architecture for optimal processing speed.
    
    Algorithm (True Parallelism):
        Step 1: Launching of all agents for all candidates simultaneously
                 6 agents × N candidates = massive parallelism
        Stage 2: Launching of all Master Coordinators simultaneously 
                 N Master co-ordinates are running in parallel
    
    Args:
        (ListiAgentAnalysisRequest): List of up to 10 candidates for analysis
        
    Returns:
        List [multiAgentAnalysisResponse]: Results of analysis of each candidate
        
    Request Model Fields:
        - candidate_id: Unique ID candidate  
        - candidate_data: Complete summary data from HH API
        - position_requirements: Position requirements
        - position_type: Type of entry (technical/management/creative))
        - active_agents: List of active agents for analysis
        - search_query: Search for context
        - search_filters: Search Filters
        
    Response Model Fields:
        - candidate_id: ID candidate
        - master_report: Master Coordinator &apos; s Final Conclusion
        - agent_reports: Detailed reports of each agent
        - active_agents: List of agents used
        - total_processing_time: Processing time
        
    Performance Characteristics:
        - A maximum of 10 candidates for a request for stability
        - AsyncOpenAI for genuine asynchronous GPT-5-nano calls
        - Processing time ~20-25 seconds for 10 candidates (instead of 200+sequential))
        - Graceful error handling: the mistakes of one candidate do not affect others
        - Detailed logic of progress for monitoring
        
    Error Handling:
        - 503: Master Coordinator not available
        - 400: No candidate limit exceeded (>10)
        - Individual errors of candidates do not interrupt the processing of others
        
    Example Usage:
        POST /multi-agent/batch
        [
            {
                "candidate_id": "12345",
                "candidate_data": {...},
                "position_requirements": "Python Developer",
                "position_type": "technical",
                "active_agents": ["technical_skills", "experience_relevance"]
            }
        ]
    """
    try:
        if not master_coordinator:
            raise HTTPException(status_code=503, detail='Master Coordinator not available')
        
        # Limiting to 10 candidates for security
        if len(requests) > 10:
            raise HTTPException(status_code=400, detail='A maximum of 10 candidates at a time')
        
        logger.info(f"🚀 Launching of the SECRET PARALLEL Multi-Agent Analysis for {len(requests)} Candidates")
        
        # PHASE 1: Collect all agent_reports for all candidates
        agent_tasks = []
        for request in requests:
            # We're starting agent analysis without a master coordinator.
            active_agents = master_coordinator._get_active_agents(request.position_type, request.active_agents)
            task = master_coordinator._run_agents_analysis(
                active_agents, request.candidate_data, request.position_requirements, 
                {"search_query": request.search_query, "search_filters": request.search_filters}
            )
            agent_tasks.append((task, request, active_agents))
        
        # Get all the results from PARALLOLONO agents.
        agent_results = await asyncio.gather(*[task for task, _, _ in agent_tasks], return_exceptions=True)
        
        # PHASE 2: Start all master analyses of the PARALLLO
        master_tasks = []
        valid_candidates = []
        
        for i, (agent_result, request, active_agents) in enumerate(zip(agent_results, [t[1] for t in agent_tasks], [t[2] for t in agent_tasks])):
            if isinstance(agent_result, Exception):
                logger.error(f"❌ Mistakes of agents for candidates {request.candidate_id}: {agent_result}")
                continue
                
            # Create a master analysis task
            master_task = master_coordinator._generate_master_report(agent_result, request)
            master_tasks.append(master_task)
            valid_candidates.append((request, agent_result, active_agents))
        
        logger.info(f"⚡ Launch {len(master_tasks)} PARALLOLONO'S SCIENTIFIC EXPERIENCE")
        
        # Perform all the labs.
        master_results = await asyncio.gather(*master_tasks, return_exceptions=True)
        
        # PHASE 3: Collecting Final Results
        processed_results = []
        for i, (master_result, (request, agent_reports, active_agents)) in enumerate(zip(master_results, valid_candidates)):
            if isinstance(master_result, Exception):
                logger.error(f"Error: ❌ The Master Analysis of the Candidate {request.candidate_id}: {master_result}")
                continue
            
            # Form the final answer.
            response = MultiAgentAnalysisResponse(
                candidate_id=request.candidate_id,
                master_report=master_result,
                agent_reports=agent_reports,
                active_agents=active_agents,
                total_processing_time=0.0  # Do it separately if you need to.
            )
            processed_results.append(response)
            logger.info(f"✅ Candidature {response.candidate_id} Analysed: {response.master_report.overall_score:.1f}%")
        
        logger.info(f"🏁 Batch analysis completed: {len(processed_results)}/{len(requests)} successful")
        return processed_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errors of Multi-Agent Analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Errors of Baptist Analysis: {str(e)}")
        
if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("ai_analysis", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8005),
        reload=service_config.get("debug", False)
    )