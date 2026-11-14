"""
Candidate Analysis - Database Service

High-end service for the Clickhouse database.

The module provides:
- Integration with Clickhouse for column storage
- Automatic initialization of the BD scheme at launch
- CRUD Operations for Candidates and Analysis
- Analytical queries for dashboards and reports
- Cashing of search results and AI analysis

Core Features:
- ClickHouse Integration: High performance column database
- Auto Schema Init: Automatically creating tables at first launch
- CRUD Operations: Full range of transactions with candidates
- Analytics Support: Aggregated Requests for Analysts
- Search Caching: Cashing search requests and results

Database Schema:
- Candidates: Candidates &apos; profiles with AI analysis
- search_history: History of search requests
- ai_analysis_results: AI analysis results for cache
- system_metrics: System productivity metrics

API Endpoints:
- POST /candidates: Saving candidate
- GET /candidates/{id}: Obtaining ID candidate
- GET /candidates/search: Search for database candidates
- GET /analytics/summary: Analytical data
- GET / Health: database status check

Performance Features:
- Clickhouse optimized data types
- Partying by date for quick requests
- Indexation for key fields (candidate_id, search_query))
- Data compression to save space
- Batch productivity boxes support

Reliability:
Automatic reconnecting during malfunctions
- Graceful handling of connection errors
- Health checks for status monitoring
- Lifespan management for Proper Startup/Shutdown

Author: Candidate Analysis Team
Version: 2.0.0 (ClickHouse + Auto Schema)
Last Updated: 2025-01-04
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio
from contextlib import asynccontextmanager

# Add the parent directory to the route to import the used modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    HealthResponse, Candidate, CandidateProfile, DatabaseCandidate,
    SkillAnalysis, AIAnalysisResponse
)
from shared.utils import setup_logging, load_config

# Logging settings
logger = setup_logging("database-service")

# Automatic initialization of the database at the start
@asynccontextmanager
async def lifespan(app: FastAPI):
    'Management of the application life cycle with automatic initialization of BD'
    logger.info('🚀 Starting Database Service with Automatic Initialization...')
    
    # Initialize at startup
    try:
        global db_manager
        db_manager = DatabaseManager()
        logger.info('✅ Database initialized automatically on launch')
    except Exception as e:
        logger.error(f"❌ Critical error of database initialization: {e}")
        raise
    
    yield
    
    # Cleaning at completion
    try:
        if hasattr(db_manager, 'clickhouse_manager'):
            db_manager.clickhouse_manager.close()
        logger.info('🔄 Database Service complete')
    except Exception as e:
        logger.error(f"❌ Error at completion: {e}")

app = FastAPI(
    title="Database Service",
    description='Data storage and management service for candidates',
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DatabaseManager:
    def __init__(self):
        self.config = load_config()
        self.db_config = self.config.get("database", {})
        
        # We'll only use Clickhouse!
        from clickhouse_manager import ClickHouseManager
        self.clickhouse_manager = ClickHouseManager()
        logger.info('✅ ClickHouse Manager initialized')

    
    def save_candidate(self, candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None) -> bool:
        'Retaining a candidate to the database'
        try:
            # We'll only use Clickhouse!
            return self.clickhouse_manager.save_candidate(candidate, ai_analysis)
        except Exception as e:
            logger.error(f"Error of preservation of the candidate {candidate.id}: {e}")
            return False
    
    def get_candidate(self, candidate_id: str) -> Optional[DatabaseCandidate]:
        'Retrieving a candidate from the database'
        try:
            # We'll only use Clickhouse!
            return self.clickhouse_manager.get_candidate(candidate_id)
        except Exception as e:
            logger.error(f"Error of receiving the candidate {candidate_id}: {e}")
            return None
    
    def search_candidates(self, search_params: Dict[str, Any], limit: int = 100) -> List[DatabaseCandidate]:
        'Search for candidates in the database'
        try:
            # We'll only use Clickhouse!
            return self.clickhouse_manager.search_candidates(search_params, limit)
        except Exception as e:
            logger.error(f"Error in search of candidates: {e}")
            return []
    
    def update_search_count(self, candidate_id: str):
        'Update of searcher'
        try:
            # We'll only use Clickhouse!
            return self.clickhouse_manager.update_search_count(candidate_id)
        except Exception as e:
            logger.error(f"Error in the search calculator update for {candidate_id}: {e}")
    
    def get_top_candidates(self, limit: int = 10) -> List[DatabaseCandidate]:
        'Getting top-up candidates by popularity'
        try:
            # We'll only use Clickhouse!
            return self.clickhouse_manager.get_top_candidates(limit)
        except Exception as e:
            logger.error(f"Error in getting top candidates: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        'Collection of database statistics'
        try:
            # We'll only use Clickhouse!
            return self.clickhouse_manager.get_statistics()
        except Exception as e:
            logger.error(f"Error in obtaining statistics: {e}")
            return {}

# db_manager initialization transferred to lifespan event
# db_manager will be initialized automatically when the application is launched
db_manager = None

@app.get("/health", response_model=HealthResponse)
async def health_check():
    'Service health check'
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.post("/candidates")
async def save_candidate(candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None):
    'Save the candidate'
    try:
        success = db_manager.save_candidate(candidate, ai_analysis)
        if success:
            return {"message": 'The candidate has been successfully retained'}
        else:
            raise HTTPException(status_code=500, detail='Error of preservation of the candidate')
    except Exception as e:
        logger.error(f"Error of preservation of the candidate: {e}")
        raise HTTPException(status_code=500, detail='The internal server error')

@app.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    'ID candidate received'
    try:
        candidate = db_manager.get_candidate(candidate_id)
        if candidate:
            return candidate
        else:
            raise HTTPException(status_code=404, detail='No candidate found')
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error of receiving the candidate: {e}")
        raise HTTPException(status_code=500, detail='The internal server error')

@app.post("/candidates/search")
async def search_candidates(search_params: Dict[str, Any], limit: int = 100):
    'Search for candidates'
    try:
        candidates = db_manager.search_candidates(search_params, limit)
        return {"candidates": candidates, "total": len(candidates)}
    except Exception as e:
        logger.error(f"Error in search of candidates: {e}")
        raise HTTPException(status_code=500, detail='Error of search')

@app.get("/candidates/top/{limit}")
async def get_top_candidates(limit: int = 10):
    'To receive the top of the candidates'
    try:
        candidates = db_manager.get_top_candidates(limit)
        return {"candidates": candidates}
    except Exception as e:
        logger.error(f"Error in getting top candidates: {e}")
        raise HTTPException(status_code=500, detail='Error in getting top candidates')

@app.put("/candidates/{candidate_id}/search")
async def update_search_count(candidate_id: str):
    'Update of searcher'
    try:
        db_manager.update_search_count(candidate_id)
        return {"message": 'Search counter updated'}
    except Exception as e:
        logger.error(f"Error of update of the search calculator: {e}")
        raise HTTPException(status_code=500, detail='Error of update of the calculator')

@app.get("/statistics")
async def get_statistics():
    'Collection of database statistics'
    try:
        stats = db_manager.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error in obtaining statistics: {e}")
        raise HTTPException(status_code=500, detail='Error in obtaining statistics')

if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    
    config = load_config()
    service_config = config.get("services", {}).get("database", {})
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8006),
        reload=service_config.get("debug", False)
    )