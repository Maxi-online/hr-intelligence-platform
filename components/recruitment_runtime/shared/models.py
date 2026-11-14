"""
Candidate Analysis - Shared Data Models

Centralized Pydantic models for all microservices of Candidate Analisis.

This module defines the common data models used in all components of the system
to ensure a type of safety, data validation and API consistence.

Model Categories:
- Enums: SearchField, ExperienceLevel, EmploymentType, etc.
- Search Models: SearchRequest, Candidate, SearchResponse
- AI Analysis Models: AIAnalysisRequest/Response, AgentReport
- Multi-Agent Models: MultiAgentAnalysisRequest/Response, MasterCoordinatorReport
- Database Models: DatabaseCandidate, CandidateProfile
- System Models: HealthResponse, RankingWeights

Key Features:
- Type Safety: Strict typification for all APIs
- Data validation: Automatic validation of incoming data  
- Serialization: JSON Serialization/Decerialization
- Documentation: OpenAPI documentation auto-generation
- Enums: Constants for dropdown values and filters

Design Principles:
Single Source of True: One Model for All Services
- Backward Compatibility: Careful Changes with Optional Fields
Clear names of fields and models
- Rich Types: Using Optional, List, Dict for accuracy

Usage Examples:
- FastAPI endpoints: response_model=List[Candidate]
- API validation: SearchRequest.model_validate(request_data)
- Type hints: def analyze(request: AIAnalysisRequest) -> AIAnalysisResponse
- JSON conversion: candidate.model_dump_json()

Author: Candidate Analysis Team
Version: 2.0.0 (Multi-Agent Models + Enhanced Validation)
Last Updated: 2025-01-04
"""
import os

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SearchField(str, Enum):
    NAME = "name"
    DESCRIPTION = "description"
    EVERYWHERE = "everywhere"

class ExperienceLevel(str, Enum):
    NO_EXPERIENCE = "noExperience"
    BETWEEN_1_AND_3 = "between1And3"
    BETWEEN_3_AND_6 = "between3And6"
    MORE_THAN_6 = "moreThan6"

class EmploymentType(str, Enum):
    FULL = "full"
    PART = "part"
    PROJECT = "project"
    VOLUNTEER = "volunteer"
    PROBATION = "probation"

class ScheduleType(str, Enum):
    FULL_DAY = "fullDay"
    SHIFT = "shift"
    FLEXIBLE = "flexible"
    REMOTE = "remote"
    FLY_IN_FLY_OUT = "flyInFlyOut"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"

class LanguageLevel(str, Enum):
    A1 = "a1"
    A2 = "a2"
    B1 = "b1"
    B2 = "b2"
    C1 = "c1"
    C2 = "c2"
    NATIVE = "native"  # Mother tongue

class Language(BaseModel):
    id: str = Field(..., description='ID Language')
    name: str = Field(..., description='Language name')
    
class LanguageRequirement(BaseModel):
    language_id: str = Field(..., description='ID Language')
    level: LanguageLevel = Field(..., description='Minimum level of ownership')

class RankingWeights(BaseModel):
    keyword_relevance: float = Field(0.4, description='Weight of relevance by key words')
    filter_match: float = Field(0.3, description='Filter conformity weight')
    recency: float = Field(0.2, description='Weight of relevance')
    profile_completeness: float = Field(0.1, description='The weight of the profile')

class SearchRequest(BaseModel):
    text: Optional[str] = Field(None, description='Keywords for Search')
    search_field: SearchField = Field(SearchField.EVERYWHERE, description='Search Area')
    area: Optional[List[int]] = Field(None, description='Geography (ID regions)')
    salary: Optional[int] = Field(None, description='Maximum wage')
    experience: Optional[ExperienceLevel] = Field(None, description='Experience')
    employment: Optional[List[EmploymentType]] = Field(None, description='Type of employment')
    schedule: Optional[List[ScheduleType]] = Field(None, description='Time schedule')
    professional_role: Optional[List[int]] = Field(None, description='Professional roles')
    period: Optional[int] = Field(None, description='Update period (days)')
    age_from: Optional[int] = Field(None, description='Minimum age')
    age_to: Optional[int] = Field(None, description='Maximum age')
    gender: Optional[Gender] = Field(None, description='Gender')
    language: Optional[List[LanguageRequirement]] = Field(None, description='Language requirements')
    page: int = Field(1, description='Page number')
    per_page: int = Field(20, description='Number of results on page')
    
    # Weights for AI ranking
    ranking_weights: Optional[RankingWeights] = Field(None, description='Weights of ranking for AI')

class Candidate(BaseModel):
    id: str = Field(..., description='ID candidate')
    name: Optional[str] = Field(None, description='FIO of candidate')
    age: Optional[int] = Field(None, description='Age')
    title: str = Field(..., description='Post title')
    area: Dict[str, Any] = Field(..., description='City/region')
    experience: Dict[str, Any] = Field(..., description='Experience')
    salary: Optional[Dict[str, Any]] = Field(None, description='Expectations for salaries')
    last_work: Optional[Dict[str, Any]] = Field(None, description='Last job')
    skills: List[str] = Field(default_factory=list, description='Skills')
    verified_skills: List[str] = Field(default_factory=list, description='Reconfirmed skills')
    updated_at: datetime = Field(..., description='Update date of the executive summary')
    url: str = Field(..., description='Reference to executive summary')
    photo_url: Optional[str] = Field(None, description='URL Photographs')
    has_cover_letter: bool = Field(False, description='Existence of a letter of transmittal')
    score: Optional[float] = Field(None, description='Assessment of relevance')
    
    # AI Analysis (added for full use of Candidate Profile))
    skill_analysis: Optional[List[Dict[str, Any]]] = Field(None, description='AI Skills analysis')
    analysis_status: Optional[str] = Field(None, description='AI Analysis Status')
    
    # Detailed AI analysis fields to explain the estimate
    keyword_relevance_score: Optional[float] = Field(None, description='AI Assessment of relevance by Keywords')
    filter_match_score: Optional[float] = Field(None, description='AI Filter conformity assessment')
    recency_score: Optional[float] = Field(None, description='AI Assessment of relevance')
    profile_completeness_score: Optional[float] = Field(None, description='AI Assessment of profile completeness')
    analysis_summary: Optional[str] = Field(None, description='Summary of the AI analysis')
    reasoning: Optional[str] = Field(None, description='Justification for AI valuation')
    
    # New fields for the multi-agent system
    multi_agent_data: Optional[Dict[str, Any]] = Field(None, description='Full multi-agent analysis data')
    relevance_boost: Optional[float] = Field(None, description='Bonus for the relevance of the search request')

class SearchResponse(BaseModel):
    candidates: List[Candidate] = Field(..., description='List of candidates')
    total_count: int = Field(..., description='Total results')
    page: int = Field(..., description='Current page')
    pages: int = Field(..., description='Total number of pages')

class RankingRequest(BaseModel):
    candidates: List[Candidate] = Field(..., description='Candidates for ranking')
    search_request: SearchRequest = Field(..., description='Initial search request')
    weights: Optional[RankingWeights] = Field(None, description='Weights for ranking')

class RankingResponse(BaseModel):
    ranked_candidates: List[Candidate] = Field(..., description='Retrieved candidates')
    ranking_metadata: Dict[str, Any] = Field(..., description='Nominal ranking metadata')

class HealthResponse(BaseModel):
    status: str = Field(..., description='Service status')
    timestamp: datetime = Field(..., description='Verification time')
    version: str = Field(..., description='Service version')

class ErrorResponse(BaseModel):
    error: str = Field(..., description='Description of error')
    details: Optional[str] = Field(None, description='Details of error')
    timestamp: datetime = Field(..., description='Time of Error')

class SkillAnalysis(BaseModel):
    skill_name: str = Field(..., description='Skills name')
    relevance_score: float = Field(..., description='Assessment of relevance (0-1)')
    proficiency_level: str = Field(..., description='Level of ownership')
    years_experience: Optional[float] = Field(None, description='Years of experience')
    ai_confidence: float = Field(..., description='AI &apos; s confidence in evaluation (0-1)')
    analysis_timestamp: datetime = Field(..., description='Analysis time')

class CandidateProfile(BaseModel):
    id: str = Field(..., description='ID candidate')
    hh_data: Candidate = Field(..., description='Data from HH.ru')
    skill_analysis: List[SkillAnalysis] = Field(default_factory=list, description='AI skills analysis')
    overall_ai_score: float = Field(0.0, description='Overall AI assessment')
    last_analyzed: Optional[datetime] = Field(None, description='Time of last analysis')
    analysis_status: str = Field("pending", description='Analysis status: pending, analizing, completed, failed')
    
    # Detailed AI analysis fields to explain the estimate
    keyword_relevance_score: Optional[float] = Field(None, description='AI Assessment of relevance by Keywords')
    filter_match_score: Optional[float] = Field(None, description='AI Filter conformity assessment')
    recency_score: Optional[float] = Field(None, description='AI Assessment of relevance')
    profile_completeness_score: Optional[float] = Field(None, description='AI Assessment of profile completeness')
    analysis_summary: Optional[str] = Field(None, description='Summary of the AI analysis')
    reasoning: Optional[str] = Field(None, description='Justification for AI valuation')
    
    # New fields for the multi-agent system
    multi_agent_data: Optional[Dict[str, Any]] = Field(None, description='Full multi-agent analysis data')
    relevance_boost: Optional[float] = Field(None, description='Bonus for the relevance of the search request')

class AIAnalysisRequest(BaseModel):
    candidate_id: str = Field(..., description='ID candidate')
    search_query: str = Field(..., description='Search request')
    skills: List[str] = Field(..., description='Analysis skills')
    experience_description: Optional[str] = Field(None, description='Description of experience')
    candidate_data: Optional[Dict[str, Any]] = Field(None, description='Full data of the candidate')
    search_filters: Optional[Dict[str, Any]] = Field(None, description='Search Filters')
    ranking_weights: Optional[RankingWeights] = Field(None, description='Weights of ranking for AI')

class AIAnalysisResponse(BaseModel):
    candidate_id: str = Field(..., description='ID candidate')
    skill_analysis: List[SkillAnalysis] = Field(..., description='Results of the skills analysis')
    overall_score: float = Field(..., description='Overall assessment')
    analysis_summary: str = Field(..., description='Summary of the analysis')
    processing_time: float = Field(..., description='Processing time in seconds')
    
    # New fields for detailed AI ranking
    keyword_relevance_score: Optional[float] = Field(None, description='AI Assessment of relevance by Keywords')
    filter_match_score: Optional[float] = Field(None, description='AI Filter conformity assessment')
    recency_score: Optional[float] = Field(None, description='AI Assessment of relevance')
    profile_completeness_score: Optional[float] = Field(None, description='AI Assessment of profile completeness')
    reasoning: Optional[str] = Field(None, description='Justification for AI valuation')

class DatabaseCandidate(BaseModel):
    id: str = Field(..., description='ID candidate')
    profile: CandidateProfile = Field(..., description='Profile of the candidate')
    created_at: datetime = Field(..., description='Time of writing')
    updated_at: datetime = Field(..., description='Time to update the record')
    search_count: int = Field(0, description='Searches')
    last_searched: Optional[datetime] = Field(None, description='Last search time')

# ================================
# MULTI-AGENCY MODEL SYSTEM
# ================================

class AgentStatus(str, Enum):
    'Agent &apos; s analysis status'
    PASS = 'pass'
    WARNING = "warning" 
    FAIL = "fail"
    ERROR = "error"

class AgentReport(BaseModel):
    'Basic class for agent report'
    agent_name: str = Field(..., description='Name of agent')
    score: float = Field(..., description='Agent evaluation (0-100 per cent)')
    status: AgentStatus = Field(..., description='Status of analysis')
    summary: str = Field(..., description='Summary of the analysis')
    details: List[str] = Field(default=[], description='Detailed observations')
    red_flags: List[str] = Field(default=[], description='Red flags')
    positive_points: List[str] = Field(default=[], description='Strong parties')
    recommendations: List[str] = Field(default=[], description='Recommendations')
    processing_time: float = Field(..., description='Processing time in seconds')
    timestamp: datetime = Field(default_factory=datetime.now, description='Time of report &apos; s creation')

class MasterCoordinatorReport(BaseModel):
    'Final report of the Coordinator'
    overall_score: float = Field(..., description='Final evaluation (average arithmetical)')
    individual_scores: Dict[str, float] = Field(..., description='Evaluations from each agent')
    master_assessment: str = Field(..., description='Master &apos; s common textual evaluation')
    recommendation: str = Field(..., description='Final recommendation')
    total_red_flags: int = Field(..., description='Total number of red flags')
    total_positive_points: int = Field(..., description='Total number of pluses')
    agents_with_warnings: List[str] = Field(default=[], description='Warning agents')
    agents_with_failures: List[str] = Field(default=[], description='Agents with critical errors')
    processing_time: float = Field(..., description='Total processing time')
    timestamp: datetime = Field(default_factory=datetime.now, description='Time of report &apos; s creation')

class MultiAgentAnalysisRequest(BaseModel):
    'Multi-agent analysis request'
    candidate_id: str = Field(..., description='ID candidate')
    position_type: str = Field(..., description='Type of entry (technical, legal, management, general)')
    search_query: str = Field(..., description='Search request/place of vacancy')
    position_requirements: Dict[str, Any] = Field(..., description='Position requirements')
    candidate_data: Dict[str, Any] = Field(..., description='Full data of the candidate')
    search_filters: Optional[Dict[str, Any]] = Field(None, description='Search Filters')
    active_agents: Optional[List[str]] = Field(None, description='List of active agents (if not specified - auto-definition)')

class MultiAgentAnalysisResponse(BaseModel):
    'Multi-agent analysis response'
    candidate_id: str = Field(..., description='ID candidate')
    master_report: MasterCoordinatorReport = Field(..., description="Master's final report")
    agent_reports: List[AgentReport] = Field(..., description='Detailed reports of all agents')
    active_agents: List[str] = Field(..., description='List of active agents')
    total_processing_time: float = Field(..., description='Total processing time')

# ================================
# NEW MODELS FOR THE VACANCY TRAFFIC
# ================================

class VacancyTopRequest(BaseModel):
    'Request for the construction of a TOP by reference to vacancy'
    vacancy_url: str = Field(..., description='Reference to vacancy on hh.ru')
    limit: Optional[int] = Field(10, description='Limiting the number of candidates on the TOP')

class VacancyTopResponse(BaseModel):
    'Response to the TAP of candidates for a specific vacancy'
    vacancy_id: str = Field(..., description='ID Vacancy')
    total_responses: int = Field(..., description='Total vacancy responses')
    candidates: List[Candidate] = Field(..., description='Rented candidates for the AI assessment')


class ConfigSaveRequest(BaseModel):
    'Request to maintain configuration'
    hh_client_id: str = Field(..., description="HH API Client ID")
    hh_client_secret: str = Field(..., description="HH API Client Secret")
    hh_access_token: Optional[str] = Field(None, description="HH API Access Token")
    hh_refresh_token: Optional[str] = Field(None, description="HH API Refresh Token")
    openrouter_api_key: str = Field(..., description="OpenRouter API Key")


class ConfigSaveResponse(BaseModel):
    'Response to maintaining configuration'
    success: bool = Field(..., description='Success of the operation')
    message: str = Field(..., description='Report on the outcome')
    config_applied: bool = Field(False, description='Whether configuration is used')


# == sync, corrected by elderman == @elder_man

class VacancyType(str, Enum):
    'Type of vacancy'
    OPEN = "open"  # Open
    DIRECT = "direct"  # Direct
    ANONYMOUS = "anonymous"  # Anonymous

class VacancyExperienceLevel(str, Enum):
    'Work experience required for a vacancy'
    NO_EXPERIENCE = "noExperience"  # No experience
    BETWEEN_1_AND_3 = "between1And3"  # 1 to 3 years
    BETWEEN_3_AND_6 = "between3And6"  # 3 to 6 years
    MORE_THAN_6 = "moreThan6"  # Over 6 years

class Currency(str, Enum):
    'Currency of wages'
    RUR = "RUR"  # Rubles
    USD = "USD"  # Dollars
    EUR = "EUR"  # Euro

class SalaryData(BaseModel):
    'Data on wages'
    from_amount: Optional[int] = Field(None, description='Pay from', ge=0)
    to_amount: Optional[int] = Field(None, description='Pay before', ge=0)
    currency: Currency = Field(Currency.RUR, description='Currency')
    gross: bool = Field(True, description='Before tax deduction')

class VacancyArea(BaseModel):
    'Region/city for vacancy'
    id: int = Field(..., description='HH ID region')
    name: str = Field(..., description='Name of region')

class VacancyProfessionalRole(BaseModel):
    'Professional role for the vacancy'
    id: int = Field(..., description='ID role in HH')
    name: str = Field(..., description='Name of the role')

class VacancySkill(BaseModel):
    'Skills/competence for a vacancy'
    name: str = Field(..., description='Skills name')
    required: bool = Field(True, description='Mandatory skills')

class VacancyContact(BaseModel):
    'Contact information for vacancy'
    name: str = Field(..., description='Name of contact person')
    email: Optional[str] = Field(None, description='Email for communication')
    phone: Optional[str] = Field(None, description='Communications telephone')

class VacancyDraft(BaseModel):
    'A blackboard job to create'
    # Basic information
    name: str = Field(..., description='Vacancy name', min_length=1, max_length=200)
    description: str = Field(..., description='Vacancy description', min_length=200)
    
    # Location
    area_id: int = Field(..., description='ID of the region')
    
    # Experience and type of work
    experience: VacancyExperienceLevel = Field(..., description='Experience required')
    employment: EmploymentType = Field(..., description='Type of employment')
    schedule: ScheduleType = Field(..., description='Time schedule')
    
    # Professional role
    professional_role_id: int = Field(..., description='ID professional role')
    
    # Wages (optimal)
    salary: Optional[SalaryData] = Field(None, description='Pay fork')
    
    # Skills
    key_skills: List[str] = Field(default_factory=list, description='Key skills')
    
    # Type of vacancy
    type: VacancyType = Field(VacancyType.OPEN, description='Type of vacancy')
    
    # Contact information
    contact: Optional[VacancyContact] = Field(None, description='Contact person')
    
    # Additional fields
    accept_handicapped: bool = Field(False, description='Accepting persons with disabilities')
    accept_kids: bool = Field(False, description='Reception of minors')

class VacancyResponse(BaseModel):
    'Response after vacancy'
    id: str = Field(..., description='ID created vacancy')
    url: str = Field(..., description='Reference to vacancy')
    name: str = Field(..., description='Vacancy name')
    area: Dict[str, Any] = Field(..., description='Information on the region')
    created_at: datetime = Field(..., description='Date established')
    expires_at: Optional[datetime] = Field(None, description='Expiry date')
    published: bool = Field(..., description='Vacancy published')

class VacancyValidationError(BaseModel):
    'Errors in vacation validation'
    field: str = Field(..., description='Field of Error')
    message: str = Field(..., description='Message of error')
    code: Optional[str] = Field(None, description='Code of error')

class VacancyCreationRequest(BaseModel):
    'Request for a vacancy'
    draft: VacancyDraft = Field(..., description='Job blackness')
    template_id: Optional[str] = Field(None, description='ID of the template used')
    company_name: str = Field(..., description='Company name')

class VacancyCreationResponse(BaseModel):
    'Response to vacancy'
    success: bool = Field(..., description='Success of the operation')
    vacancy: Optional[VacancyResponse] = Field(None, description='Vacancy data created')
    errors: List[VacancyValidationError] = Field(default_factory=list, description='Validation errors')
    message: str = Field(..., description='Report on the outcome')

class VacancyTemplate(BaseModel):
    'Vacancy template'
    id: str = Field(..., description='Unique ID template')
    name: str = Field(..., description='Name of the template')
    category: str = Field(..., description='Category (IT, Management, Sales, etc.)')
    
    # Main fields
    title: str = Field(..., description='Vacancy name')
    description: str = Field(..., description='Vacancy description')
    
    # Requirements
    experience: VacancyExperienceLevel = Field(..., description='Experience required')
    employment: List[EmploymentType] = Field(..., description='Types of employment')
    schedule: List[ScheduleType] = Field(..., description='Time schedule')
    
    # Wages
    salary: Optional[SalaryData] = Field(None, description='Pay fork')
    
    # Skills and requirements
    key_skills: List[VacancySkill] = Field(default_factory=list, description='Key skills')
    
    # Working conditions
    benefits: List[str] = Field(default_factory=list, description='Benefits and benefits')
    
    created_at: datetime = Field(default_factory=datetime.now, description='Date the template was created')
    updated_at: datetime = Field(default_factory=datetime.now, description='Date of update of the template')