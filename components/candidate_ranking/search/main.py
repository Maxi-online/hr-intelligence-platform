"""
Candidate Analysis - Search Service

The main search and orchestra service.

This module is the central component of the Candidate Anallysis system, which:
- Organizes the search for candidates through HeadHunter API
- Coordinates AI analysis of the summary in true parallel mode
- Integration of search, ranking and analysis results
- Provides API for Frentend'a with detailed statistics

Main opportunities:
Integration with HeadHunter.ru API to identify candidates
- Multi-track summary processing for high productivity
- Batch dispatch of candidates for AI analysis
- Collect and provide HH API statistics (429/503 errors))
- Cashing and optimization of requests

Architecture:
    SearchService -> HH API Service -> HeadHunter.ru
                  -> AI Analysis Service -> OpenAI GPT-4.1-nano
                  -> Database Service -> ClickHouse

Author: Candidate Analysis Team
Version: 2.0.0
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional, Tuple
import requests
import httpx
import asyncio
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add the parent directory to the route to import the used modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse,
    SearchRequest,
    Candidate,
    AIAnalysisRequest,
    AIAnalysisResponse,
    CandidateProfile,
    DatabaseCandidate,
    MultiAgentAnalysisRequest,
    MultiAgentAnalysisResponse,
    VacancyTopRequest,
    VacancyTopResponse,
    RankingRequest
)
from shared.utils import setup_logging, load_config

# Logging settings
logger = setup_logging("search-service")

# ----FastAPI app ----
app = FastAPI(
    title="Search Service",
    description='Search for candidates, orchesstrating HH.ru API, AI Analysis, and Database Services.',
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchService:
    """
    The main class of the search and orchestra service.
    
    Coordinates interaction between different microservices to ensure
    Full-cycle search, analysis and ranking of candidates.
    
    Architectural features:
    - Linear initialization of URL services to support Docker and the local environment
    - Batch processing of candidates to optimize productivity
    - Detailed collection of HH API statistics for monitoring
    - Graceful handling errors and recovery mechanisms
    
    Attributes:
        config (dict): configuration from settings.yaml
        services_config (dict): Microservice configuration
        logger: Logger to track transactions
        _hh_api_url (str): URL HeadHunter API service (lazy)
        _ai_analysis_url (str): URL AI Analysis service (lazy) 
        _database_url (str): URL Database service (lazy)
    """
    
    def __init__(self):
        """
        Initialization of Search Service.
        
        Download configuration and prepares lazy-initialization of URL services.
        """
        self.config = load_config()
        self.services_config = self.config.get("services", {})
        self.logger = logger
        # Initialization of the URL will take place on request
        self._hh_api_url = None
        self._ranking_url = None
        self._ai_analysis_url = None
        self._database_url = None

    def _get_service_url(self, service_name: str, is_docker: bool) -> str:
        """
        URL microservice with Docker support and local environment.
        
        Args:
            service_name (str): Service name (hh_api, ai_analysis, database))
            is_docker (bool): Docker Environment Flag
            
        Returns:
            : Full URL service (http://host:port)
            
        Raises:
            ValueError: If the service port is not set
            
        Note:
            Docker uses docker_host, local - host (localhost))
        """
        conf = self.services_config.get(service_name, {})
        host = conf.get('docker_host') if is_docker else conf.get('host', 'localhost')
        port = conf.get('port')
        if not port:
            raise ValueError(f"Port for service {service_name} I'm not in the mood.")
        return f"http://{host}:{port}"

    @property
    def hh_api_url(self):
        if self._hh_api_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._hh_api_url = self._get_service_url("hh_api", is_docker)
        return self._hh_api_url

    # ranking_url no longer required - only AI ranking used

    @property
    def ai_analysis_url(self):
        if self._ai_analysis_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._ai_analysis_url = self._get_service_url("ai_analysis", is_docker)
        return self._ai_analysis_url

    @property
    def ranking_url(self):
        if self._ranking_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._ranking_url = self._get_service_url("ranking", is_docker)
        return self._ranking_url

    @property
    def database_url(self):
        if self._database_url is None:
            is_docker = os.getenv("DOCKER_ENV") == "true"
            self._database_url = self._get_service_url("database", is_docker)
        return self._database_url

    def _get_full_resume_data(self, candidate_id: str) -> Tuple[Optional[Dict], Dict[str, Any]]:
        """
        Getting detailed summary data from HeadHunter API with smart retri logic.
        
        This method ensures that the complete summary c is obtained in a sustainable manner:
        - Exponential Repeats in Errors 429 (Too Many Requests))
        - Analysis of the quality of the data obtained
        - Detailed statistics for HH API monitoring
        
        Args:
            candidate_id (str): A unique HH candidate identifier
            
        Returns:
            Tuple[Optional[Dict], Dict[str, Any]]:
                - Optional[Dict]: Complete summary data or None in case of error
                - Dict[str, Any]: Status of API Request with Detailed Information
                
        API Status Dict contains:
            - Access (bool): Successful request
            - status_code (int): HTTP response code status
            - attempts (int): Number of attempts
            - error_message (str): Error message (if there is)
            - data_quality (str): Data quality (good/partial/poor/unknown))
            
        Data Quality Assessment:
            - Good: There's self, experience and education.
            - "Partial": There are some of the key fields
            - Poor: Basic information only
            - "Unknown: Error in Quality Assessment
            
        Retry Strategy:
            - No more than 3 attempts.
            - Explicit delay: 1s, 2s, 4s
            - Jitter to avoid thundering herd
            - Graceful handling 429/503/500 errors
        """
        import random
        import time
        
        max_retries = 3
        base_delay = 1.0
        api_status = {
            "success": False,
            "status_code": None,
            "attempts": 0,
            "error_message": None,
            "data_quality": "unknown"
        }
        
        for attempt in range(max_retries):
            api_status["attempts"] = attempt + 1
            try:
                if attempt > 0:
                    # Explicit delay with jitter to avoid 429
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                    self.logger.warning(f"🔄 Attempted {attempt + 1}/{max_retries} for {candidate_id}We're waiting. {delay:.1f}c")
                    time.sleep(delay)
                
                self.logger.info(f"🔍 Request for complete executive summaries: {candidate_id} (attempted) {attempt + 1})")
                
                url = f"{self.hh_api_url}/resume/{candidate_id}"
                response = requests.get(url, timeout=15)
                api_status["status_code"] = response.status_code

                if response.status_code == 200:
                    try:
                        full_data = response.json()
                        self.logger.info(f"✅ Data received for {candidate_id}: {len(str(full_data))} Symbols")
                        
                        # VERIFICATION OF DATA QUALITY
                        if isinstance(full_data, dict):
                            has_about = bool(full_data.get('about', ''))
                            has_experience = bool(full_data.get('experience', []))
                            has_education = bool(full_data.get('education', []))
                            
                            if has_about or has_experience or has_education:
                                api_status["data_quality"] = "good"
                                self.logger.info(f"📊 Qualitative data for {candidate_id}: about={has_about}, exp={has_experience}, edu={has_education}")
                            else:
                                api_status["data_quality"] = "partial"
                                self.logger.warning(f"⚠️ Data incomplete for {candidate_id}but we use what we have.")
                        
                        api_status["success"] = True
                        return full_data, api_status
                        
                    except Exception as json_error:
                        api_status["error_message"] = f"JSON error: {json_error}"
                        self.logger.error(f"❌ JSON error for {candidate_id}: {json_error}")
                        if attempt == max_retries - 1:
                            return None, api_status
                        continue
                        
                elif response.status_code == 429:
                    api_status["error_message"] = "Rate limit exceeded"
                    self.logger.warning(f"🚫 HH API limit for {candidate_id} (429), retrie through {base_delay * (2 ** attempt)}s")
                    if attempt == max_retries - 1:
                        self.logger.error(f"💥 Unable to obtain data {candidate_id} after {max_retries} attempts")
                        return None, api_status
                    continue
                    
                else:
                    api_status["error_message"] = f"HH API error {response.status_code}"
                    self.logger.error(f"🚨 HH API error {response.status_code} for {candidate_id}")
                    if attempt == max_retries - 1:
                        return None, api_status
                    continue
                
            except Exception as e:
                api_status["error_message"] = f"Network error: {e}"
                self.logger.error(f"❌ Network error for {candidate_id}: {e}")
                if attempt == max_retries - 1:
                    return None, api_status
                continue
        
        return None, api_status

    def _get_vacancy_responses(self, vacancy_url: str) -> Dict[str, Any]:
        'Proxie to hh_api to receive feedback on a vacancy reference'
        try:
            response = requests.post(f"{self.hh_api_url}/vacancy/responses", json={"vacancy_url": vacancy_url}, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error in getting answers on vacancies: {e}")
            raise HTTPException(status_code=500, detail='Error in getting answers on vacancies')

    def _get_vacancy_details(self, vacancy_url: str) -> Dict[str, Any]:
        'Proxie to hh_api for detailed vacancy information'
        try:
            response = requests.post(f"{self.hh_api_url}/vacancy/details", json={"vacancy_url": vacancy_url}, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error in getting a vacation: {e}")
            raise HTTPException(status_code=500, detail='Error in getting a vacation')

    def _resume_to_candidate(self, resume_data: Dict[str, Any]) -> Candidate:
        'Local conversion of HH / resume to Candidate (minimum compatible)).'
        from shared.utils import parse_date, parse_salary
        resume_id = resume_data.get("id", "")
        title = resume_data.get("title", "")
        area = resume_data.get("area", {})
        experience = resume_data.get("total_experience", {})
        salary_data = resume_data.get("salary")
        updated_at = parse_date(resume_data.get("updated_at", ""))

        name = 'Candidature'
        age = resume_data.get("age")

        skills: List[str] = []
        if "skill_set" in resume_data and isinstance(resume_data["skill_set"], list):
            skills.extend([s for s in resume_data["skill_set"] if isinstance(s, str)])
        if "key_skills" in resume_data and isinstance(resume_data["key_skills"], list):
            skills.extend([s.get("name", "") for s in resume_data["key_skills"] if isinstance(s, dict)])

        last_work = {}
        if "experience" in resume_data and isinstance(resume_data["experience"], list) and resume_data["experience"]:
            last_exp = resume_data["experience"][0]
            last_work = {
                "name": last_exp.get("company", ""),
                "position": last_exp.get("position", ""),
                "description": last_exp.get("description", "")
            }

        salary = parse_salary(salary_data) if salary_data else None
        resume_url = f"https://hh.ru/resume/{resume_id}"
        photo_url = None
        if resume_data.get("photo"):
            photo_url = resume_data["photo"].get("medium", resume_data["photo"].get("small"))

        has_cover_letter = resume_data.get("has_cover_letter", False)

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
            has_cover_letter=has_cover_letter
        )

    def get_dictionaries(self) -> Dict[str, Any]:
        try:
            areas_response = requests.get(f"{self.hh_api_url}/areas", timeout=30)
            areas = areas_response.json() if areas_response.status_code == 200 else []

            roles_response = requests.get(f"{self.hh_api_url}/professional-roles", timeout=30)
            roles = roles_response.json() if roles_response.status_code == 200 else []
            
            languages_response = requests.get(f"{self.hh_api_url}/languages", timeout=30)
            languages = languages_response.json() if languages_response.status_code == 200 else []
            
            # We receive all the handbooks with the same request (if available)
            dictionaries_response = requests.get(f"{self.hh_api_url}/dictionaries", timeout=30)
            dictionaries = dictionaries_response.json() if dictionaries_response.status_code == 200 else {}
            
            return {
                "areas": areas, 
                "professional_roles": roles,
                "languages": languages,
                "dictionaries": dictionaries
            }
        except Exception as e:
            self.logger.error(f"Error in receiving guidelines: {e}")
            return {}

    def _process_single_candidate(self, candidate: Candidate, search_request: SearchRequest) -> Tuple[CandidateProfile, bool]:
        'Processing of one candidate (may be done in parallel))'
        try:
            candidate_start_time = time.time()
            import threading
            thread_id = threading.current_thread().ident
            
            print(f"🎯 DEBUG PRINT: Input to _process_single_candidate for candidate {candidate.id} [Thread-{thread_id}]")
            self.logger.info(f"🎯 PARALLEL FLOWS {thread_id}:: PROCESSING OBJECT {candidate.id}")  # FLAMMABLE PLAYING
            # FULL DATA FROM HH.RU API FOR EVER CANDIDATE!
            self.logger.info(f"🔍 DEBUG: Call _get_ful_resource_data for {candidate.id}")
            full_resume_data, api_status = self._get_full_resume_data(candidate.id)
            self.logger.info(f"🔍 DEBUG: Result _get_full_resume_data: {bool(full_resume_data)}API status: {api_status}")
            print(f"🔍 DEBUG PRINT: Result _get_full_resume_data: {bool(full_resume_data)}API status: {api_status}")
            
            # Checking if there's a candidate in the database with the final analysis
            db_candidate = self._get_candidate_from_db(candidate.id)
            
            if db_candidate and db_candidate.profile.analysis_status == 'completed':
                return db_candidate.profile, True
            
            # CORRIGENDUM: Create a profile without AI analysis (AI analysis will be in batch)
                candidate.score = 0.0
                
                profile = CandidateProfile(
                    id=candidate.id,
                    hh_data=candidate,
                    skill_analysis=[],
                    overall_ai_score=0.0,
                analysis_status='pending'  # Waiting for batch analysis
                )
            success = True  # Successfully produced data
            
            # Keep it in the database.
            self._save_candidate_to_db(profile)
            
            # CRITICAL LOIGRATION: Time for the completion of the candidate &apos; s processing
            candidate_time = time.time() - candidate_start_time
            self.logger.info(f"✅ FLOWS {thread_id}:: Completed candidate {candidate.id} for {candidate_time:.2f}s, success: {success}")
            print(f"✅ DEBUG PRINT: COMPLETE {candidate.id} [Thread-{thread_id}] for {candidate_time:.2f}s")
            
            return profile, success
            
        except Exception as e:
            candidate_time = time.time() - candidate_start_time
            self.logger.error(f"❌ FLOWS {thread_id}: Errors in the candidate {candidate.id} for {candidate_time:.2f}s: {e}")
            print(f"❌ Debug Print: Error {candidate.id} [Thread-{thread_id}] for {candidate_time:.2f}s")
            
            # Create profile without AI analysis
            profile = CandidateProfile(
                id=candidate.id,
                hh_data=candidate,
                skill_analysis=[],
                overall_ai_score=0.0,
                analysis_status='failed'
            )
            self._save_candidate_to_db(profile)
            return profile, False

    def search_candidates(self, search_request: SearchRequest) -> Tuple[List[Candidate], Dict[str, Any]]:
        """
        Basic method of identifying and analysing candidates with true parallel processing.
        
        Performs the full processing cycle:
        1. Search for basic data via HeadHunter API
        2. Simultaneous collection of detailed summary data 
        3. Batch to AI analysis for maximum efficiency
        4. Collection of detailed HH API statistics for monitoring
        
        Args:
            search_request (SearchRequest): Search parameters (text, region, experience, etc.).)
            
        Returns:
            Tuple[List[Candidate], Dict[str, Any]]: 
                - List [Candidate]: List of evaluated candidates with AI estimates
                - Dict[str, Any]: HH API statistics (successful/ failure requests, errors))
                
        Raises:
            HTTPException: HH API or AI Analysis errors
            
        Algorithm Flow:
            1. HH API Search ♪ To receive the list of candidates
            2. Parallel Resume Fetch ♪ The details of each summary
            3. Batch AI Analysis ♪ All candidates are processed in parallel
            4. Results Integration ♪ Data and Statistics Combination
            
        Performance Features:
            - Batch processing of 10 candidates for optimization
            - Really parallel AI analysis through AsyncOpenAI
            - Detailed error statistics (429, 503, 500) for diagnosis
            - Graceful demobilization for HH API problems
            
        HH API Statistics Tracking:
            - total_requests: Total number of requests for HH API
            - successful_requests: Successful requests (200 OK)
            - status_429_errors: Errors over the limit
            - status_503_errors: Service unavailability errors
            - rate_limit_exceeded: Total excess limits
            - good_data_count: Summary with full data
            - partial_data_count: Summary with partial data
        """
        try:
            # 1. HH API Search
            search_params = search_request.model_dump(exclude_none=True)
            self.logger.info(f"Send a request to HH API with parameters: {search_params}")
            
            hh_response = requests.get(f"{self.hh_api_url}/search", params=search_params, timeout=120)
            
            if hh_response.status_code != 200:
                raise HTTPException(status_code=hh_response.status_code, detail=f"Error: The HH API: {hh_response.text}")
            
            hh_data = hh_response.json()
            self.logger.info(f"Response received from HH API: {len(hh_data.get('candidates', []))} Candidates")
            
            hh_candidates = [Candidate(**item) for item in hh_data.get("candidates", [])]
            self.logger.info(f"Processed {len(hh_candidates)} Candidates")
            
            # 2. PARALLEL PROCESSING OF BATCH CANDIDATES FOR 10 🚀
            start_time = time.time()
            self.logger.info(f"🚀 Commence parallel processing {len(hh_candidates)} 10 booth candidates...")
            print(f"🔍 DEBUG after Logger: Len(hh_candidates))={len(hh_candidates)}")
            
            # We'll break up the Batch candidates at 10.
            batch_size = 10
            batches = [hh_candidates[i:i + batch_size] for i in range(0, len(hh_candidates), batch_size)]
            self.logger.info(f"📦 Smashed on {len(batches)} Fathers for the {batch_size} Candidates")
            
            processed_profiles: List[CandidateProfile] = []
            successful_ai_analyses = 0
            
            # HH API status tracking
            hh_api_stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "status_500_errors": 0,
                "status_429_errors": 0,
                "status_503_errors": 0,
                "rate_limit_exceeded": 0,
                "partial_data_count": 0,
                "good_data_count": 0,
                "failed_candidates": []
            }
            
            # REAL PARALLELITY: Gather all candidates and send a one-man batch request
            all_candidates = []
            all_requests = []
            
            for batch_num, batch in enumerate(batches, 1):
                self.logger.info(f"🔄 We're getting the booth ready {batch_num}/{len(batches)} ({len(batch)} of candidates)")
                
                # Prepare data for each candidate (without AI analysis))
                for idx, candidate in enumerate(batch):
                    try:
                        # Slight delay between candidates to avoid 429 mass processing
                        if idx > 0:  # Do not delay the first candidate
                            import random
                            delay = random.uniform(0.2, 0.5)  # 200-500ms delay
                            time.sleep(delay)
                        
                        # Get full summary data.
                        full_resume_data, api_status = self._get_full_resume_data(candidate.id)
                        
                        # Update HH API statistics
                        hh_api_stats["total_requests"] += 1
                        if api_status["success"]:
                            hh_api_stats["successful_requests"] += 1
                            if api_status["data_quality"] == "good":
                                hh_api_stats["good_data_count"] += 1
                            elif api_status["data_quality"] == "partial":
                                hh_api_stats["partial_data_count"] += 1
                        else:
                            hh_api_stats["failed_requests"] += 1
                            hh_api_stats["failed_candidates"].append({
                                "candidate_id": candidate.id,
                                "status_code": api_status.get("status_code"),
                                "error_message": api_status.get("error_message"),
                                "attempts": api_status.get("attempts")
                            })
                            if api_status.get("status_code") == 500:
                                hh_api_stats["status_500_errors"] += 1
                            elif api_status.get("status_code") == 429:
                                hh_api_stats["status_429_errors"] += 1
                                hh_api_stats["rate_limit_exceeded"] += 1
                            elif api_status.get("status_code") == 503:
                                hh_api_stats["status_503_errors"] += 1
                                hh_api_stats["rate_limit_exceeded"] += 1
                        
                        # Checking if there's a candidate in the database with the final analysis
                        db_candidate = self._get_candidate_from_db(candidate.id)
                        
                        if db_candidate and hasattr(db_candidate, 'analysis_status') and db_candidate.analysis_status == "completed":
                            # We're going to use a ready-made database analysis.
                            profile = CandidateProfile(
                                id=candidate.id,  # CORRIGENDUM: Add mandatory field id
                                hh_data=candidate,
                                overall_ai_score=db_candidate.overall_ai_score,
                                skill_analysis=db_candidate.skill_analysis,
                                analysis_status="completed",
                                keyword_relevance_score=db_candidate.keyword_relevance_score,
                                filter_match_score=db_candidate.filter_match_score,
                                recency_score=db_candidate.recency_score,
                                profile_completeness_score=db_candidate.profile_completeness_score,
                                analysis_summary=db_candidate.analysis_summary,
                                reasoning=db_candidate.reasoning,
                                multi_agent_data=db_candidate.multi_agent_data,
                                relevance_boost=db_candidate.relevance_boost
                            )
                            processed_profiles.append(profile)
                            successful_ai_analyses += 1
                            self.logger.info(f"✅ Used ready-made database analysis for candidate {candidate.id}")
                        else:
                            # Request for AI analysis
                            position_type = self._determine_position_type(search_request.text or "")
                            position_requirements = self._extract_position_requirements(search_request)
                            
                            if full_resume_data:
                                if isinstance(full_resume_data, dict) and 'resume' in full_resume_data:
                                    candidate_data = full_resume_data['resume']
                                else:
                                    candidate_data = full_resume_data
                            else:
                                candidate_data = candidate.model_dump()
                            
                            multi_agent_request = MultiAgentAnalysisRequest(
                                candidate_id=candidate.id,
                                position_type=position_type,
                                search_query=search_request.text or "",
                                position_requirements=position_requirements,
                                candidate_data=candidate_data,
                                search_filters=search_request.model_dump(exclude={'ranking_weights'})
                            )
                            
                            all_candidates.append(candidate)
                            all_requests.append(multi_agent_request)
                            
                    except Exception as e:
                        self.logger.error(f"Error of candidate preparation {candidate.id}: {e}")
            
            # REAL PARALLELITY: Send all candidates by request
            if all_requests:
                self.logger.info(f"🚀 THIS PARALLELITY: Sending {len(all_requests)} I'm asking you for one piece of evidence.")
                
                try:
                    response = requests.post(
                        f"{self.ai_analysis_url}/multi-agent/batch", 
                        json=[req.model_dump(mode='json') for req in all_requests],
                        timeout=3600  # 1 hour to process 200-300 candidates
                    )
                    response.raise_for_status()
                    
                    # Processing the batch results
                    batch_responses = response.json()
                    for i, batch_response in enumerate(batch_responses):
                        try:
                            multi_agent_response = MultiAgentAnalysisResponse(**batch_response)
                            candidate = all_candidates[i]
                            
                            # Calculate the final score
                            final_score = self._calculate_relevance_score(
                                candidate, 
                                search_request.text or "",
                                multi_agent_response.master_report.overall_score
                            )
                            
                            # Create a candidate profile
                            profile = CandidateProfile(
                                id=candidate.id,  # CORRIGENDUM: Add mandatory field id
                                hh_data=candidate,
                                overall_ai_score=final_score,
                                skill_analysis=[],  # As long as we're empty, agent_reports data
                                analysis_status="completed",
                                keyword_relevance_score=final_score,
                                filter_match_score=0.0,
                                recency_score=0.0,
                                profile_completeness_score=0.0,
                                analysis_summary=multi_agent_response.master_report.master_assessment[:500] + "..." if len(multi_agent_response.master_report.master_assessment) > 500 else multi_agent_response.master_report.master_assessment,
                                reasoning=multi_agent_response.master_report.recommendation,
                                multi_agent_data=multi_agent_response.model_dump(),
                                relevance_boost=0.0
                            )
                            
                            processed_profiles.append(profile)
                            successful_ai_analyses += 1
                            
                            # Saved in database
                            self._save_candidate_to_db(profile)
                            
                            self.logger.info(f"✅ Candidature {candidate.id}: AI Evaluation {final_score:.1f}%")
                            
                        except Exception as e:
                            self.logger.error(f"Error in processing results for the candidate {all_candidates[i].id}: {e}")
                    
                    self.logger.info(f"✅ THIS PARALLELITY: PROCESSED {successful_ai_analyses} of candidates from {len(all_requests)}")
                    
                except Exception as e:
                    self.logger.error(f"The Batch AI analysis error: {e}")
                    # In case of error, we create profiles without AI analysis
                    for candidate in all_candidates:
                        profile = CandidateProfile(
                            id=candidate.id,  # CORRIGENDUM: Add mandatory field id
                            hh_data=candidate,
                            overall_ai_score=0.0,
                            skill_analysis=[],
                            analysis_status="failed",
                            keyword_relevance_score=0.0,
                            filter_match_score=0.0,
                            recency_score=0.0,
                            profile_completeness_score=0.0,
                            analysis_summary='AI analysis not performed',
                            reasoning='The error of analysis',
                            multi_agent_data={},
                            relevance_boost=0.0
                        )
                        processed_profiles.append(profile)
            
            processing_time = time.time() - start_time
            self.logger.info(f"⚡ Parallel processing completed for {processing_time:.2f}s. Successful AI analyses: {successful_ai_analyses}/{len(hh_candidates)}")

            self.logger.info(f"Processed {len(processed_profiles)} Profiles, successful AI analyses: {successful_ai_analyses}")
            
            # If there's no successful AI tests, we'll return the fallback.
            if successful_ai_analyses == 0:
                self.logger.warning("AI analysis's not working, we're returning the first 10 candidates without ranking")
                return hh_candidates[:10]
            
            # 3. AI ranking (replacement of algorithmic ranking))
            if not processed_profiles:
                self.logger.warning('No profile for ranking')
                return []

            try:
                # Create candidates with full AI analysis
                ai_ranked_candidates = []
                for profile in processed_profiles:
                    candidate_data = profile.hh_data.model_dump()
                    candidate_data['score'] = profile.overall_ai_score
                    # Add AI skills analysis 
                    candidate_data['skill_analysis'] = [skill.model_dump() for skill in profile.skill_analysis]
                    candidate_data['analysis_status'] = profile.analysis_status
                    # Add detailed AI analysis fields to explain the estimate
                    candidate_data['keyword_relevance_score'] = profile.keyword_relevance_score
                    candidate_data['filter_match_score'] = profile.filter_match_score
                    candidate_data['recency_score'] = profile.recency_score
                    candidate_data['profile_completeness_score'] = profile.profile_completeness_score
                    candidate_data['analysis_summary'] = profile.analysis_summary
                    candidate_data['reasoning'] = profile.reasoning
                    # 🔥 CRITICAL IMPORTANT: Adding multi-agent data!
                    candidate_data['multi_agent_data'] = profile.multi_agent_data
                    candidate_data['relevance_boost'] = profile.relevance_boost
                    ai_ranked_candidates.append(Candidate(**candidate_data))
                
                # Sorted by AI estimate (dropping)
                ai_ranked_candidates.sort(key=lambda x: x.score or 0.0, reverse=True)
                
                self.logger.info(f"AI ranking completed: {len(ai_ranked_candidates)} Candidates graded according to AI evaluation")
                
                # Update the database search counter
                for candidate in ai_ranked_candidates:
                    self._update_search_count_in_db(candidate.id)
                    
                # Logging HH API statistics
                self.logger.info(f"📊 HH API statistics: {hh_api_stats['successful_requests']}/{hh_api_stats['total_requests']} successful requests")
                if hh_api_stats['status_500_errors'] > 0:
                    self.logger.warning(f"🚨 Error of 500: {hh_api_stats['status_500_errors']}")
                if hh_api_stats['status_429_errors'] > 0:
                    self.logger.warning(f"🚫 The errors 429: {hh_api_stats['status_429_errors']}")
                if hh_api_stats['status_503_errors'] > 0:
                    self.logger.warning(f"🔴 error 503 (limit exhausted)): {hh_api_stats['status_503_errors']}")
                if hh_api_stats['rate_limit_exceeded'] > 0:
                    self.logger.warning(f"⚡ Total excess limit: {hh_api_stats['rate_limit_exceeded']}")
                    
                return ai_ranked_candidates, hh_api_stats
                
            except Exception as e:
                self.logger.error(f"Error in ranking: {e}")
                # In case of error, the first 10 candidates are returned
                self.logger.warning(f"📊 HH API statistics (with error)): {hh_api_stats['successful_requests']}/{hh_api_stats['total_requests']} successful requests")
                return hh_candidates[:10], hh_api_stats

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network errors in search: {e}")
            raise HTTPException(status_code=503, detail=f"Network error: {e}")
        except Exception as e:
            self.logger.error(f"Unknown error in search: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"The internal server error: {e}")

    def build_top_for_vacancy(self, vacancy_url: str, limit: int = 10) -> VacancyTopResponse:
        'New stream: vacancy rate \\\\responses \\AI-analysis \\TPR of candidates'
        # (1) Receive feedback on the vacancy
        vacancy_details = self._get_vacancy_details(vacancy_url)
        responses_data = self._get_vacancy_responses(vacancy_url)
        vacancy_id = responses_data.get("vacancy_id", "")
        items = responses_data.get("items", [])

        # We expect items to contain an array of summaries or their id.
        candidates: List[Candidate] = []
        for item in items:
            try:
                # Harmonization: If there is a summary object, convert, if id, pull the details
                resume_id = item.get("resume_id") if isinstance(item, dict) else None
                resume_obj = item.get("resume") if isinstance(item, dict) else None
                if resume_obj:
                    candidate = self._resume_to_candidate(resume_obj)
                elif resume_id:
                    full = requests.get(f"{self.hh_api_url}/resume/{resume_id}", timeout=60)
                    full.raise_for_status()
                    candidate = self._resume_to_candidate(full.json().get("resume", {}))
                else:
                    continue
                candidates.append(candidate)
            except Exception as e:
                self.logger.warning(f"Response element missing: {e}")

        if not candidates:
            return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=0, candidates=[])

        # (2) Retracting detailed data + preparing a suite of multi-agent analysis
        all_candidates = []
        all_requests = []
        for candidate in candidates:
            full_resume_data, _ = self._get_full_resume_data(candidate.id)
            candidate_data = full_resume_data.get("resume", full_resume_data) if isinstance(full_resume_data, dict) else candidate.model_dump()
            # We try to extract requirements from the job (name + keywords))
            vacancy_title = (vacancy_details.get("name") or "") if isinstance(vacancy_details, dict) else ""
            position_type = self._determine_position_type(vacancy_title or candidate.title or "")
            position_requirements = self._extract_position_requirements(SearchRequest(text=vacancy_title, page=1, per_page=1))
            all_candidates.append(candidate)
            all_requests.append(MultiAgentAnalysisRequest(
                candidate_id=candidate.id,
                position_type=position_type,
                search_query=vacancy_title or candidate.title or "",
                position_requirements=position_requirements,
                candidate_data=candidate_data,
                search_filters={}
            ))

        # (3) Send the booth to AI Analysis
        try:
            response = requests.post(
                f"{self.ai_analysis_url}/multi-agent/batch",
                json=[r.model_dump(mode='json') for r in all_requests],
                timeout=3600
            )
            response.raise_for_status()
            batch_responses = response.json()
        except Exception as e:
            self.logger.error(f"Failure in response analysis: {e}")
            # If AI is not available, return without sorting
            return VacancyTopResponse(
                vacancy_id=vacancy_id,
                total_responses=len(all_candidates),
                candidates=all_candidates[:limit]
            )

        # (4) Consider the final points and sort them
        tops: List[Candidate] = []
        for i, br in enumerate(batch_responses):
            try:
                ma = MultiAgentAnalysisResponse(**br)
                base_score = ma.master_report.overall_score
                candidate = all_candidates[i]
                final_score = self._calculate_relevance_score(candidate, candidate.title or "", base_score)
                candidate.score = round(final_score, 3)
                tops.append(candidate)
            except Exception as e:
                self.logger.warning(f"Errors of the result collection for the candidate {all_candidates[i].id}: {e}")

        tops.sort(key=lambda c: c.score or 0, reverse=True)
        # Final sorting via ranking service (AI-first, score))
        try:
            rank_payload = RankingRequest(candidates=tops, search_request=SearchRequest(text=vacancy_title or "", page=1, per_page=len(tops)))
            resp = requests.post(f"{self.ranking_url}/rank", json=rank_payload.model_dump(mode='json'), timeout=60)
            resp.raise_for_status()
            ranked_data = resp.json()
            ranked_candidates = ranked_data.get("ranked_candidates", [])
            if limit:
                ranked_candidates = ranked_candidates[:limit]
            # Transform to Candidate if necessary
            final_list = []
            for c in ranked_candidates:
                if isinstance(c, dict):
                    final_list.append(Candidate(**c))
                else:
                    final_list.append(c)
            return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=len(all_candidates), candidates=final_list)
        except Exception:
            # Fallback for local sorting
            if limit:
                tops = tops[:limit]
            return VacancyTopResponse(vacancy_id=vacancy_id, total_responses=len(all_candidates), candidates=tops)

    def _get_candidate_from_db(self, candidate_id: str) -> Optional[DatabaseCandidate]:
        try:
            response = requests.get(f"{self.database_url}/candidates/{candidate_id}", timeout=60)
            if response.status_code == 200:
                return DatabaseCandidate(**response.json())
            return None
        except Exception as e:
            self.logger.warning(f"Unable to obtain candidate {candidate_id} of database: {e}")
            return None


    
    def _determine_position_type(self, search_query: str) -> str:
        'Determines the type of item based on a search request'
        query_lower = search_query.lower()
        
        # Technical positions
        if any(tech in query_lower for tech in ['Developer', "developer", 'Programmer', "devops", "fullstack", "backend", "frontend"]):
            return "technical"
        
        # Management positions  
        if any(mgmt in query_lower for mgmt in ['Manager', "manager", 'Head', 'Director', 'Tymlid', "lead"]):
            return "management"
        
        # Sales
        if any(sales in query_lower for sales in ['sales', "sales", 'Sales manager']):
            return "sales"
        
        return "general"
    
    def _extract_position_requirements(self, search_request: SearchRequest) -> dict:
        'Extract position requests from the search request'
        search_text = search_request.text or ""
        
        # Improve skills from search requests
        required_skills = []
        
        # Request technology
        tech_keywords = ["python", "java", "javascript", "react", "django", "spring", "nodejs", "golang", "kubernetes", "docker"]
        for tech in tech_keywords:
            if tech in search_text.lower():
                required_skills.append(tech.title())
        
        # IMPROVED: Transmit full information on experiences
        experience_info = self._get_detailed_experience_requirements(getattr(search_request, 'experience', None))
        
        # IMPROVED: Transmit detailed requirements from all search filters
        return {
            "required_skills": required_skills,
            "min_experience_years": experience_info["min_years"],
            "max_experience_years": experience_info["max_years"], 
            "experience_description": experience_info["description"],
            "experience_level": experience_info["level"],
            "search_query": search_text,
            "employment_types": [emp.value for emp in (search_request.employment or [])],
            "schedule_types": [sch.value for sch in (search_request.schedule or [])],
            "professional_roles": search_request.professional_role or [],
            "areas": search_request.area or [],
            "salary_max": search_request.salary,
            "age_range": {
                "min": search_request.age_from,
                "max": search_request.age_to
            },
            "education": [],
            "languages": search_request.language or []
        }
    
    def _get_detailed_experience_requirements(self, experience_str) -> dict:
        'Transforms the HH.ru experience line into detailed requirements information'
        if not experience_str or experience_str == "noExperience":
            return {
                "min_years": 0,
                "max_years": 0,
                "description": 'Without experience',
                "level": "noExperience"
            }
        elif experience_str == "between1And3":
            return {
                "min_years": 1,
                "max_years": 3,
                "description": '1 to 3 years',
                "level": "between1And3"
            }
        elif experience_str == "between3And6":
            return {
                "min_years": 3,
                "max_years": 6,
                "description": '3 to 6 years',
                "level": "between3And6"
            }
        elif experience_str == "moreThan6":
            return {
                "min_years": 6,
                "max_years": None,
                "description": 'Over 6 years',
                "level": "moreThan6"
            }
        else:
            # If the number is transferred, we return it.
            try:
                years = int(experience_str)
                return {
                    "min_years": years,
                    "max_years": years,
                    "description": f"Exactly. {years} years",
                    "level": "custom"
                }
            except (ValueError, TypeError):
                return {
                    "min_years": 0,
                    "max_years": None,
                    "description": 'No experience requirements specified',
                    "level": "unknown"
                }

    def _convert_experience_to_years(self, experience_str) -> int:
        'Transforms the HH.ru experience line into minimum years (compatibility))'
        experience_info = self._get_detailed_experience_requirements(experience_str)
        return experience_info["min_years"]
    
    def _calculate_relevance_score(self, candidate: Candidate, search_query: str, base_score: float) -> float:
        'Calculates the final speed given the relevance of the search request'
        if not search_query:
            return base_score
        
        relevance_boost = 0.0
        query_words = search_query.lower().split()
        
        # Checking to match the title of the post
        candidate_title = (candidate.title or "").lower()
        for word in query_words:
            if word in candidate_title:
                relevance_boost += 15.0  # Big bonus for matching the name
        
        # Checking to match skills.
        candidate_skills = [skill.lower() for skill in (candidate.skills or [])]
        for word in query_words:
            for skill in candidate_skills:
                if word in skill:
                    relevance_boost += 5.0  # Bonus for Competency
        
        # Check out the experience profile.
        candidate_experience = (getattr(candidate, 'experience_text', '') or '').lower()
        for word in query_words:
            if word in candidate_experience:
                relevance_boost += 2.0  # A little bonus for mentioning experience.
        
        # Limiting the maximum bass
        relevance_boost = min(relevance_boost, 25.0)
        
        return min(100.0, base_score + relevance_boost)

    def _save_candidate_to_db(self, profile: CandidateProfile):
        try:
            # Database API is awaiting Candidate and ai_analysis separately
            candidate_data = profile.hh_data.model_dump(mode='json')
            
            # Form an AI Analysis if you have
            ai_analysis_data = None
            if profile.skill_analysis and profile.overall_ai_score > 0:
                # SkillAnalysis objects are correctly serilled
                skill_analysis_data = []
                if isinstance(profile.skill_analysis, list):
                    skill_analysis_data = [
                        skill.model_dump(mode='json') if hasattr(skill, 'model_dump') 
                        else skill for skill in profile.skill_analysis
                    ]
                
                ai_analysis_data = {
                    "candidate_id": profile.id,
                    "skill_analysis": skill_analysis_data,
                    "overall_score": profile.overall_ai_score,
                    "analysis_summary": f"Analysis completed with status: {profile.analysis_status}",
                    "processing_time": 1.0
                }
            
            # Sent according to API database
            payload = {
                "candidate": candidate_data,
                "ai_analysis": ai_analysis_data
            }
            
            requests.post(f"{self.database_url}/candidates", json=payload, timeout=120).raise_for_status()
        except Exception as e:
            self.logger.error(f"Unable to retain candidate {profile.id} to database: {e}")

    def _update_search_count_in_db(self, candidate_id: str):
        try:
            requests.put(f"{self.database_url}/candidates/{candidate_id}/search", timeout=60).raise_for_status()
        except Exception as e:
            self.logger.warning(f"Unable to update search counter for {candidate_id}: {e}")


search_service = SearchService()

@app.get("/ping")
async def ping():
    'A simple test of the availability of a search service'
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/filters", tags=["Filters"])
def get_filters():
    return search_service.get_dictionaries()

@app.get("/dictionaries", tags=["Dictionaries"])
def get_dictionaries():
    'Collection of all handbooks'
    try:
        result = search_service.get_dictionaries()
        if not result:
            raise HTTPException(status_code=500, detail='Error in receiving guidelines')
        return result
    except Exception as e:
        logger.error(f"Error in receiving guidelines: {e}")
        raise HTTPException(status_code=500, detail='Error in receiving guidelines')

# == sync, corrected by elderman == @elder_man
@app.post("/vacancy/top", response_model=VacancyTopResponse)
def build_vacancy_top(req: VacancyTopRequest):
    return search_service.build_top_for_vacancy(req.vacancy_url, req.limit or 10)

def create_search_request_search(
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
    'Created SearchRequest from Query Options in Search Service'
    
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

@app.get("/search", tags=["Search"])
def search(search_request: SearchRequest = Depends(create_search_request_search)):
    'Search for candidates via GET request'
    try:
        candidates, hh_api_stats = search_service.search_candidates(search_request)
        
        # Form the correct HH API response structure
        return {
            "candidates": [candidate.model_dump() for candidate in candidates],
            "total_count": len(candidates),
            "page": search_request.page,
            "pages": 1,  # So far, we're returning one page.
            "hh_api_status": {
                "total_requests": hh_api_stats["total_requests"],
                "successful_requests": hh_api_stats["successful_requests"],
                "failed_requests": hh_api_stats["failed_requests"],
                "status_500_errors": hh_api_stats["status_500_errors"],
                "status_429_errors": hh_api_stats["status_429_errors"],
                "status_503_errors": hh_api_stats["status_503_errors"],
                "rate_limit_exceeded": hh_api_stats["rate_limit_exceeded"],
                "good_data_count": hh_api_stats["good_data_count"],
                "partial_data_count": hh_api_stats["partial_data_count"],
                "has_issues": hh_api_stats["failed_requests"] > 0,
                "is_rate_limited": hh_api_stats["rate_limit_exceeded"] > 0,
                "success_rate": (hh_api_stats["successful_requests"] / hh_api_stats["total_requests"] * 100) if hh_api_stats["total_requests"] > 0 else 100
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error of search: {e}")
        raise HTTPException(status_code=500, detail='Error of search')

if __name__ == "__main__":
    import uvicorn
    config = load_config()
    service_config = config.get("services", {}).get("search", {})
    port = service_config.get("port", 8001)
    host = service_config.get("host", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)