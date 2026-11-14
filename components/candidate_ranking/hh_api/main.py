"""
Candidate Analysis - HeadHunter API Integration Service

Integration service with HeadHunter.ru API to search for and obtain candidates.

This module provides reliable integration with external API HeadHunter, including:
- OAuth 2.0 Authorisation with automatic upgrade of currents
- Sustainable requests with exponential backoff for errors
- Correct processing of rate limiting (429, 503) 
- Detailed diagnosis of problems for monitoring
- Collection of both basic and detailed summary data

Key Features:
- OAuth 2.0 Flow: Full support for the authorization of HeadHunter
- Smart Retry Logic: Exponential Repeats with 429/503 Errors
- Token Management: Automatic update of access_token
- Error Promotion: Correct Transfer of HTTP Statuses
- Rate Limited Handling: Smart Processing of API Limits

API Endpoints:
- /search: Searching for filter candidates
- /sume/{id}: Obtaining detailed summary data
- /areas: Regional Directory
- /oauth/authorize: User authorization
- /oauth/refresh: Update access_token

Error Handling Strategy:
- 429 Too Many Requests: Retry with exponential delay
- 503 Service Unavailable: Retry + flag rate_limit_exceeded
- 500 Internal Server Error: Direct error transmission
- 401/403: Authorization errors
- Network errors: Graceful degradation

Performance & Reliability:
- Maximum 3 attempts for each request
- Jitter in delays to avoid thundering herd
- Detailed logic of all operations
- Correct processing of timeouts

Author: Candidate Analysis Team
Version: 2.0.0 (Improved Error Handling & Token Management)
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import time

# Add the parent directory to the route to import the used modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import HealthResponse, SearchRequest, Candidate, VacancyTopRequest, VacancyTopResponse
from shared.utils import setup_logging, HTTPClient, parse_date, parse_salary, calculate_average_salary, load_config

# Logging settings
logger = setup_logging("hh-api-service")

app = FastAPI(
    title="HH API Service",
    description='HeadHunter API Integration Service',
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

class HHAPIClient:
    def __init__(self):
        # Load configuration from settings.yaml
        self.config = load_config()
        hh_config = self.config.get("hh_api", {})
        
        self.base_url = hh_config.get("base_url", "https://api.hh.ru")
        self.user_agent = hh_config.get("user_agent", "")
        self.http_client = HTTPClient(self.base_url)
        
        # OAuth credentials configuration
        self.client_id = hh_config.get("client_id", "")
        self.client_secret = hh_config.get("client_secret", "")
        
        # User currents from configuration  
        user_tokens = hh_config.get("user_tokens", {})
        self.access_token = user_tokens.get("access_token")
        self.refresh_token = user_tokens.get("refresh_token")
        self.token_expires_at = user_tokens.get("expires_at")
    
    def _get_headers(self) -> Dict[str, str]:
        'Collection of headings for queries'
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json"
        }
        
        # Add to the current if you have
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        return headers
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        'Auction of a user &apos; s URL'
        auth_url = "https://hh.ru/oauth/authorize"
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri
        }
        if state:
            params["state"] = state
            
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"
    
    def get_token_from_code(self, authorization_code: str, redirect_uri: str):
        'Authorization Code access current'
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": authorization_code,
                "redirect_uri": redirect_uri
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                logger.info('Token is available via authoration code')
                return token_data
            else:
                logger.error(f"The error of token: {response.status_code} - {response.text}")
                raise HTTPException(status_code=400, detail=f"Error of authorization: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error when requesting a token: {e}")
            raise HTTPException(status_code=500, detail='Error of authentication')
    
    def refresh_access_token(self):
        'Update of access current via refresh token'
        if not self.refresh_token:
            raise HTTPException(status_code=401, detail='No refresh token to update')
            
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                if token_data.get("refresh_token"):
                    self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                logger.info('Token has been successfully updated')
                return token_data
            else:
                logger.error(f"Errors in the update of the token: {response.status_code} - {response.text}")
                raise HTTPException(status_code=401, detail='Errors in the update of the token')
                    
        except Exception as e:
            logger.error(f"Error when updating the token: {e}")
            raise HTTPException(status_code=500, detail='Error of authentication')
    
    def _force_refresh_token(self):
        'Coercive updating of the current (exceeds the validity period))'
        if not self.refresh_token:
            raise Exception('No refresh token for forced updating')
            
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                old_token = self.access_token[:20] + "..." if self.access_token else "None"
                
                self.access_token = token_data.get("access_token")
                if token_data.get("refresh_token"):
                    self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                
                new_token = self.access_token[:20] + "..." if self.access_token else "None"
                logger.info(f"🔄 Token has been forcibly updated: {old_token} → {new_token}")
                return token_data
            elif response.status_code == 400:
                error_data = response.json()
                if error_data.get("error") == "invalid_grant" and "not expired" in error_data.get("error_description", ""):
                    logger.warning('⚠️ HH API does not allow the current to be updated (not yet due))')
                    raise Exception('The token is still valid, HH API is blocking the update.')
                else:
                    logger.error(f"❌ Errors in the update of the token: {response.status_code} - {response.text}")
                    raise Exception(f"Error: The HH API: {response.text}")
            else:
                logger.error(f"❌ Unexpected status when updating the current: {response.status_code}")
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ The forced updating of the current was not possible: {e}")
            raise
    
    def get_application_token(self):
        'Acquire application current via Clive Credentials Grant'
        try:
            token_url = "https://hh.ru/oauth/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(token_url, data=data, headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                # client_credentials is usually not refresh_token
                self.refresh_token = None
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                logger.info('The application tone is successfully obtained via Ccent Credentials Grant')
                return token_data
            else:
                logger.error(f"Error in obtaining the application token: {response.status_code} - {response.text}")
                # If Ccent Credentials is not supported, remove the exception to the need for user authorization
                if response.status_code == 400:
                    raise HTTPException(status_code=401, detail='User authorization required for access to abstracts.')
                raise HTTPException(status_code=500, detail=f"Error in obtaining the application token: {response.text}")
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error when requesting an application token: {e}")
            raise HTTPException(status_code=500, detail='Error of application authentication')
    
    def _ensure_token(self):
        'Test of access current'
        if not self.access_token:
            # Trying to get an application current using Client Credentials Grant
            logger.info('Get an application current via Ccent Credentials Grant...')
            self.get_application_token()
            return
        
        # Check to see if the current's up.
        if self.token_expires_at and time.time() >= self.token_expires_at - 300:  # 5 minutes buffer.
            if self.refresh_token:
                logger.info("Token's running out, updating...")
                self.refresh_access_token()
            else:
                # If there's no current, we're trying to get a new application current
                logger.info("Token's out, we're getting a new application current...")
                self.get_application_token()
    
    def _make_authenticated_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        'Implementation of the authentic request'
        # Public endpoints don't need a token.
        public_endpoints = ["/areas", "/professional_roles", "/languages"]
        
        if endpoint in public_endpoints:
            # Public endpoints are running without a current.
            try:
                logger.info(f"We're executing a public request to {endpoint} with parameters: {params}")
                response = self.http_client.get(endpoint, headers=self._get_headers(), params=params)
                logger.info(f"Response received from {endpoint}:: Status {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.error(f"🚫 Exceeded request limit for public endpoint {endpoint}")
                    raise HTTPException(status_code=429, detail='Exceeded HH API request limit. Try later.')
                else:
                    logger.error(f"⚠️ HH API error {response.status_code} for {endpoint}: {response.text}")
                    raise HTTPException(status_code=response.status_code, detail=f"Error: The HH API: {response.text}")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Network error of public request {endpoint}: {e}")
                raise HTTPException(status_code=503, detail=f"Network errors when contacting HH API: {e}")
        
        # For the rest of the endpoints, you need a token.
        # Checking/receiveing currents
        if not self.access_token or (self.token_expires_at and time.time() > self.token_expires_at):
            self._ensure_token()
        
        # Retry logic for 429 errors
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"We are in the process of completing an authentic request for {endpoint} with parameters: {params} (attempted) {attempt + 1})")
                
                # We use requests directly to control error processing
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self._get_headers(), params=params)
                logger.info(f"Response received from {endpoint}:: Status {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        # In the first 429 errors, we try to forced to update the token
                        logger.warning(f"🔍 429 errors for {endpoint}, attempt={attempt}, refresh_token={bool(self.refresh_token)}")
                        
                        if attempt == 0 and self.refresh_token:
                            try:
                                logger.warning(f"🔄 Attempted forcible renewal of the current due to 429 {endpoint}")
                                self._force_refresh_token()
                                logger.info(f"✅ Token updated, repeat request to {endpoint}")
                                continue
                            except Exception as refresh_error:
                                logger.warning(f"⚠️ Unable to update the current: {refresh_error}")
                        
                        import random
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except Exception:
                                delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                        else:
                            delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                        logger.warning(f"🚫 HH API limit for {endpoint} (429), retrie through {delay:.1f}s")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"💥 Exceeded HH API request limit for {endpoint} after {max_retries} attempts")
                        raise HTTPException(status_code=429, detail='Exceeded HH API request limit. Try later.')
                elif response.status_code == 401:
                    logger.error(f"🔐 HH API authorization errors for {endpoint}")
                    raise HTTPException(status_code=401, detail="Error of authorization of HH API. Check your employer's access current (OAuth)).")
                elif response.status_code == 403:
                    logger.error(f"🚫 Access prohibited HH API for {endpoint}")
                    raise HTTPException(status_code=403, detail='Access prohibited. Insufficient rights (employer &apos; s rights required for negotiation/response)).')
                elif response.status_code == 404:
                    logger.error(f"📭 Resource not found HH API for {endpoint}")
                    raise HTTPException(status_code=404, detail='The requested resource has not been found.')
                else:
                    logger.error(f"⚠️ HH API error {response.status_code} for {endpoint}: {response.text}")
                    raise HTTPException(status_code=response.status_code, detail=f"Error: The HH API: {response.text}")
                    
            except HTTPException:
                # HTTP errors as they are
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"🔄 Network error for {endpoint}, retrie through {delay}s: {e}")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Critical network error for {endpoint}: {e}")
                    raise HTTPException(status_code=503, detail=f"Network errors when contacting HH API: {e}")
    
    def get_areas(self) -> List[Dict[str, Any]]:
        'Retrieving the list of regions'
        try:
            response = self._make_authenticated_request("/areas")
            return response
        except Exception as e:
            logger.error(f"Error in obtaining a list of regions: {e}")
            raise HTTPException(status_code=500, detail='Error in obtaining a list of regions')

    # ===== New: Reactions to vacancies by reference =====
    def _extract_vacancy_id(self, vacancy_url: str) -> Optional[str]:
        try:
            # Simplest parser ID: expected /vacancy/<id>
            import re
            match = re.search(r"vacancy/(\d+)", vacancy_url)
            return match.group(1) if match else None
        except Exception:
            return None

    def get_vacancy_details(self, vacancy_url: str) -> Dict[str, Any]:
        'Retrieving details of vacancy by reference (public endpoint of vacancies)).'
        vacancy_id = self._extract_vacancy_id(vacancy_url)
        if not vacancy_id:
            raise HTTPException(status_code=400, detail='Uncorrect reference to vacancy')
        try:
            url = f"{self.base_url}/vacancies/{vacancy_id}"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                data = response.json()
                data["vacancy_id"] = vacancy_id
                return data
            else:
                logger.error(f"Error in getting a vacation: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail='Error in getting a vacation')
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in getting a vacation {vacancy_id}: {e}")
            raise HTTPException(status_code=500, detail='Error in getting a vacation')

    def get_vacancy_responses(self, vacancy_url: str, per_page: int = 50, max_pages: int = 20) -> Dict[str, Any]:
        """Receivables (census) for vacancies. OAuth employer and negotiation rights required.

        Implemented through negotiations/response: GET /negotiations/response?vacancy_id=<id>
        Returns the unified list with resume_id for further receipt of the executive summary.
        """
        vacancy_id = self._extract_vacancy_id(vacancy_url)
        if not vacancy_id:
            raise HTTPException(status_code=400, detail='Uncorrect reference to vacancy')

        try:
            collected: List[Dict[str, Any]] = []
            page = 0
            while page < max_pages:
                params = {"vacancy_id": vacancy_id, "page": page, "per_page": per_page}
                # Use the right endpoint to get feedback.
                data = self._make_authenticated_request("/negotiations/response", params=params)
                items = data.get("items", []) if isinstance(data, dict) else []
                
                logger.info(f"Received {len(items)} Page responses {page}")
                
                for it in items:
                    resume_obj = it.get("resume") if isinstance(it, dict) else None
                    resume_id = None
                    if isinstance(resume_obj, dict):
                        resume_id = resume_obj.get("id")
                    if not resume_id:
                        # fallback: Sometimes there may be fields of linex in it.
                        links = it.get("links", []) if isinstance(it, dict) else []
                        for l in links:
                            if isinstance(l, dict) and l.get("rel") == "resume":
                                href = l.get("href", "")
                                # Expected / resumes/<id>
                                import re
                                m = re.search(r"resumes/(\w+)", href)
                                if m:
                                    resume_id = m.group(1)
                                    break
                    if resume_id:
                        collected.append({"resume_id": resume_id, "raw": it})

                pages_total = data.get("pages") if isinstance(data, dict) else None
                page += 1
                if pages_total is not None and page >= pages_total:
                    break
                if not items:  # If it's an empty page, let's stop.
                    break

            logger.info(f"Total collected {len(collected)} resume_id responses for vacancy {vacancy_id}")
            return {"vacancy_id": vacancy_id, "items": collected, "total": len(collected)}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in receiving vacation answers {vacancy_id}: {e}")
            raise HTTPException(status_code=500, detail='Error in receiving vacation answers')
    
    def get_professional_roles(self) -> Dict[str, Any]:
        'Getting a list of professional roles'
        try:
            response = self._make_authenticated_request("/professional_roles")
            return response
        except Exception as e:
            logger.error(f"Error in obtaining professional roles: {e}")
            raise HTTPException(status_code=500, detail='Error in obtaining professional roles')
    
    def get_languages(self) -> List[Dict[str, Any]]:
        'Collection of the list of languages (public endpoint)'
        try:
            response = self._make_authenticated_request("/languages")
            return response
        except Exception as e:
            logger.error(f"Error in obtaining a language list: {e}")
            # Fallback to the basic list of languages if API is not available
            return [
                {"id": "1", "name": 'Russian'},
                {"id": "2", "name": 'English'},
                {"id": "3", "name": 'German'},
                {"id": "4", "name": 'French'},
                {"id": "5", "name": 'Spanish'},
                {"id": "6", "name": 'Chinese'},
                {"id": "7", "name": 'Japanese'},
                {"id": "8", "name": 'Korean'},
                {"id": "9", "name": 'Italian'},
                {"id": "10", "name": 'Portuguese'}
            ]
    
    def get_dictionaries(self) -> Dict[str, Any]:
        'Collection of all available handbooks'
        try:
            # Unite several anonymous endpoints.
            result = {}
            
            # Languages
            try:
                languages_response = self._make_authenticated_request("/languages")
                result["language"] = languages_response
            except:
                result["language"] = [
                    {"id": "1", "name": 'Russian'},
                    {"id": "2", "name": 'English'},
                    {"id": "3", "name": 'German'},
                    {"id": "4", "name": 'French'},
                    {"id": "5", "name": 'Spanish'}
                ]
            
            # Work experience - back-cut values (corresponding to HH API))
            result["experience"] = [
                {"id": "noExperience", "name": 'No experience'},
                {"id": "between1And3", "name": '1 to 3 years'},
                {"id": "between3And6", "name": '3 to 6 years'},
                {"id": "moreThan6", "name": 'Over 6 years'}
            ]
            
            # Type of employment
            result["employment"] = [
                {"id": "full", "name": 'Full employment'},
                {"id": "part", "name": 'Part-time employment'},
                {"id": "project", "name": 'Project work'},
                {"id": "volunteer", "name": 'Volunteering'},
                {"id": "probation", "name": 'Internship'}
            ]
            
            # Time schedule
            result["schedule"] = [
                {"id": "fullDay", "name": 'Full day'},
                {"id": "shift", "name": 'Replacement schedule'},
                {"id": "flexible", "name": 'Flexible schedule'},
                {"id": "remote", "name": 'Remote work'},
                {"id": "flyInFlyOut", "name": 'Watch method'}
            ]
            
            # Language levels
            result["language_level"] = [
                {"id": "a1", "name": 'A1 — Primary'},
                {"id": "a2", "name": 'A2 - Elementary'},
                {"id": "b1", "name": 'B1 - Medium'},
                {"id": "b2", "name": 'B2 — Medium advanced'},
                {"id": "c1", "name": 'C1 - Advanced'},
                {"id": "c2", "name": 'C2 - Professional'},
                {"id": "native", "name": 'Honey.'}
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error in receiving guidelines: {e}")
            raise HTTPException(status_code=500, detail='Error in receiving guidelines')
    
    def search_resumes(self, search_request: SearchRequest) -> Dict[str, Any]:
        'Searching for shortlists of candidates'
        try:
            # Formation of the request parameters for the executive summary
            params = {
                "per_page": search_request.per_page,
                "page": search_request.page - 1  # HH API uses 0-based indexation
            }
            
            if search_request.text:
                params["text"] = search_request.text
            
            # search_field maintained for summary
            if search_request.search_field:
                params["search_field"] = search_request.search_field.value
            
            if search_request.area:
                # For summary area must be one value
                if isinstance(search_request.area, list):
                    params["area"] = search_request.area[0] if search_request.area else None
                else:
                    params["area"] = search_request.area
            
            if search_request.salary:
                params["salary"] = search_request.salary
            
            if search_request.experience:
                params["experience"] = search_request.experience.value
            
            if search_request.employment:
                # HH API is waiting for the line, not the list.
                params["employment"] = search_request.employment[0].value if search_request.employment else None
            
            if search_request.schedule:
                # HH API is waiting for the line, not the list.
                params["schedule"] = search_request.schedule[0].value if search_request.schedule else None
            
            if search_request.professional_role:
                params["professional_role"] = search_request.professional_role
            
            if search_request.period:
                params["period"] = search_request.period
            
            if search_request.age_from:
                params["age_from"] = search_request.age_from
            
            if search_request.age_to:
                params["age_to"] = search_request.age_to
            
            if search_request.gender:
                params["gender"] = search_request.gender.value
            
            if search_request.language:
                # Conversion of languages to HH API format
                language_params = []
                for lang_req in search_request.language:
                    language_params.append(f"{lang_req.language_id}.{lang_req.level.value}")
                params["language"] = language_params
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Add detailed logic
            logger.info(f"HH API request parameters (summary): {params}")
            
            # We're gonna use the endpoint of the resume.
            response = self._make_authenticated_request("/resumes", params=params)
            
            # Logging the answer
            logger.info(f"Response received from HH API: {response}")
            
            return response
        except HTTPException:
            # HTTP errors (including 401 Unauthorized)) 
            raise
        except Exception as e:
            logger.error(f"Unexpected Search Error: {e}")
            raise HTTPException(status_code=500, detail='Internal Error Search Resume')
    
    def get_resume_details(self, resume_id: str) -> Dict[str, Any]:
        'Obtaining details of the executive summary'
        try:
            response = self._make_authenticated_request(f"/resumes/{resume_id}")
            return response
        except HTTPException:
            # HTTP errors (including 401 Unauthorized))
            raise
        except Exception as e:
            logger.error(f"An unexpected mistake in getting the details of the summary: {e}")
            raise HTTPException(status_code=500, detail='Internal error of receiving details of the summary')
    
    def _parse_candidate(self, resume_data: Dict[str, Any]) -> Candidate:
        'Parsing the candidate from HH API &apos; s response (summary)'
        try:
            # Extraction of basic information from the summary
            resume_id = resume_data.get("id", "")
            title = resume_data.get("title", "")
            area = resume_data.get("area", {})
            experience = resume_data.get("total_experience", {})
            salary_data = resume_data.get("salary")
            updated_at = parse_date(resume_data.get("updated_at", ""))
            
            # Information about the candidate
            name = 'Candidature'  # HH API hides FIO for anonymity
            age = resume_data.get("age")
            
            # Improving skills from the summary
            skills = []
            verified_skills = []
            
            # Skills can be found in different fields
            if "skill_set" in resume_data:
                skills = resume_data["skill_set"]
            
            if "key_skills" in resume_data:
                key_skills = resume_data["key_skills"]
                if isinstance(key_skills, list):
                    skills.extend([skill.get("name", "") for skill in key_skills if isinstance(skill, dict)])
            
            # Information about the last workplace
            last_work = {}
            if "experience" in resume_data and resume_data["experience"]:
                last_exp = resume_data["experience"][0] if isinstance(resume_data["experience"], list) else {}
                last_work = {
                    "name": last_exp.get("company", ""),
                    "position": last_exp.get("position", ""),
                    "description": last_exp.get("description", "")
                }
            
            # Wage parsing
            salary = None
            if salary_data:
                salary = parse_salary(salary_data)
            
            # Synopsis development
            resume_url = f"https://hh.ru/resume/{resume_id}"
            
            # Photo of the candidate
            photo_url = None
            if "photo" in resume_data and resume_data["photo"]:
                photo_url = resume_data["photo"].get("medium", resume_data["photo"].get("small"))
            
            # Verification of the presence of the letter of transmittal
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
                verified_skills=verified_skills,
                updated_at=updated_at,
                url=resume_url,
                photo_url=photo_url,
                has_cover_letter=has_cover_letter
            )
            
        except Exception as e:
            logger.error(f"Error of parsing summary: {e}")
            raise

# Customer Initialization HH API
hh_client = HHAPIClient()

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
        areas = hh_client.get_areas()
        return {"areas": areas}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errors in obtaining regions: {e}")
        raise HTTPException(status_code=500, detail='Errors in obtaining regions')

@app.get("/professional-roles")
async def get_professional_roles():
    'Getting a list of professional roles'
    try:
        roles = hh_client.get_professional_roles()
        return {"professional_roles": roles}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in obtaining professional roles: {e}")
        raise HTTPException(status_code=500, detail='Error in obtaining professional roles')

@app.get("/languages")
async def get_languages():
    'Getting a list of languages'
    try:
        languages = hh_client.get_languages()
        return {"languages": languages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error of language: {e}")
        raise HTTPException(status_code=500, detail='Error of language')

@app.get("/dictionaries")
async def get_dictionaries():
    'Collection of all handbooks'
    try:
        dictionaries = hh_client.get_dictionaries()
        return {"dictionaries": dictionaries}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in receiving guidelines: {e}")
        raise HTTPException(status_code=500, detail='Error in receiving guidelines')

# ===== NEW: HTTPendpoint for feedback on the vacancy reference =====
@app.post("/vacancy/details", response_model=Dict[str, Any])
async def get_vacancy_details_endpoint(payload: VacancyTopRequest):
    try:
        data = hh_client.get_vacancy_details(payload.vacancy_url)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in processing the job request: {e}")
        raise HTTPException(status_code=500, detail='Error in getting a vacation')

@app.post("/vacancy/responses", response_model=Dict[str, Any])
async def get_vacancy_responses_endpoint(payload: VacancyTopRequest):
    try:
        data = hh_client.get_vacancy_responses(payload.vacancy_url, per_page=payload.limit or 50)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in response request processing: {e}")
        raise HTTPException(status_code=500, detail='Error in receiving answers')

def create_search_request(
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
    'Create SearchRequest from Query Options'
    
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

@app.get("/search")
async def search_resumes(search_request: SearchRequest = Depends(create_search_request)):
    'Search resume via GET Request'
    try:
        # Conduct of vacancy searches
        search_results = hh_client.search_resumes(search_request)
        
        # Parsing results
        candidates = []
        for item in search_results.get("items", []):
            try:
                candidate = hh_client._parse_candidate(item)
                candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Errors of Parking Vacation: {e}")
                continue
        
        # Formation of the response
        total_count = search_results.get("found", 0)
        pages = search_results.get("pages", 0)
        
        return {
            "candidates": [candidate.model_dump() for candidate in candidates],
            "total_count": total_count,
            "page": search_request.page,
            "pages": pages
        }
        
    except HTTPException as he:
        # HTTP errors (including 401 Unauthorized))
        logger.error(f"HTTP error in search: {he.status_code} - {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected Search Error: {e}")
        raise HTTPException(status_code=500, detail='Internal Search Service Error')

@app.get("/resume/{resume_id}")
async def get_resume_details(resume_id: str):
    'Obtaining details of the executive summary'
    try:
        resume_data = hh_client.get_resume_details(resume_id)
        return {"resume": resume_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in obtaining details: {e}")
        raise HTTPException(status_code=500, detail='Error in obtaining details')

@app.get("/oauth/authorize-url")
async def get_authorize_url(redirect_uri: str, state: str = None):
    'Obtaining URL to authorise user in HH.ru'
    try:
        auth_url = hh_client.get_authorization_url(redirect_uri, state)
        return {"authorization_url": auth_url}
    except Exception as e:
        logger.error(f"Error in forming the authorization URL: {e}")
        raise HTTPException(status_code=500, detail='Error in forming the authorization URL')

@app.post("/oauth/token")
async def exchange_code_for_token(code: str, redirect_uri: str):
    'Exchange of authoration code on access token'
    try:
        token_data = hh_client.get_token_from_code(code, redirect_uri)
        return {
            "access_token": token_data.get("access_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in exchanging code to token: {e}")
        raise HTTPException(status_code=500, detail='The error of token')

@app.post("/oauth/refresh")
async def refresh_token():
    'Update access token via refresh token'
    try:
        token_data = hh_client.refresh_access_token()
        return {
            "access_token": token_data.get("access_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errors in the update of the token: {e}")
        raise HTTPException(status_code=500, detail='Errors in the update of the token')

@app.post("/settings/auth")
async def update_auth_settings(auth_settings: dict):
    'Update of authentication settings'
    try:
        # Update HH API client settings
        if "hh_client_id" in auth_settings:
            hh_client.client_id = auth_settings["hh_client_id"]
        
        if "hh_client_secret" in auth_settings:
            hh_client.client_secret = auth_settings["hh_client_secret"]
        
        if "hh_user_agent" in auth_settings:
            hh_client.user_agent = auth_settings["hh_user_agent"]
        
        logger.info('HH API settings updated')
        return {
            "status": "success", 
            "message": 'HH API settings updated',
            "client_id": hh_client.client_id[:10] + "..." if hh_client.client_id else None,
            "user_agent": hh_client.user_agent
        }
    except Exception as e:
        logger.error(f"Error: Update of HH API Settings: {e}")
        raise HTTPException(status_code=500, detail='Error: Update of HH API Settings')

if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("hh_api", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8003),
        reload=service_config.get("debug", False)
    )