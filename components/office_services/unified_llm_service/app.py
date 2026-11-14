"""
Universal LLM Service FastAPI application
HTTP API for a single LLM microservice
"""
import os

import logging
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from llm_service import UnifiedLLMService

# Logging settings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unified LLM Service",
    description='HTTP API for a single LLM microservice GPT-5',
    version="1.0.0"
)

# Global copy of LLM Service
llm_service: UnifiedLLMService = None

@app.on_event("startup")
async def startup_event():
    'Initialize at startup'
    global llm_service
    logger.info('🚀 Run Universal LLM Service API...')
    
    # OpenAI configuration
    openai_config = {
        'api_key': 'your-openai-api-key',  # Will be downloaded from settings
        'proxy_url': 'http://your-proxy-url:port',  # Will be downloaded from settings
        'model': 'gpt-5-mini'
    }
    
    # PostgreSQL database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'office_services_user',
        'password': os.environ["SERVICES_CENTRAL_POSTGRES_ENVIRONMENT_POSTGRES_PASSWORD"],
        'database': 'office_services_agents'
    }
    
    llm_service = UnifiedLLMService(openai_config, db_config)
    await llm_service.initialize()
    logger.info('✅ Universal LLM Service API is ready')

@app.on_event("shutdown")
async def shutdown_event():
    'Cleaning during stoppage'
    global llm_service
    if llm_service:
        await llm_service.cleanup()
    logger.info('👋 Universal LLM Service API stopped')

class GenerateRequest(BaseModel):
    agent_id: str
    message: str
    user_id: str = "api_user"
    session_id: str = None

@app.get("/")
async def root():
    'Service information'
    return {
        "service": "Unified LLM Service",
        "version": "1.0.0",
        "status": "active",
        "description": 'Single LLM Microservice GPT-5 for all agents',
        "architecture": "PostgreSQL + GPT-5 + Agent Configurations"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    if llm_service:
        status = await llm_service.get_agent_status("system")
        return {
            "status": "healthy",
            "service": "Unified LLM Service",
            "database_connected": llm_service.db_connection is not None,
            "timestamp": status.get("timestamp", "unknown")
        }
    else:
        return {"status": "initializing"}

@app.post("/generate_response")
async def generate_response(request: GenerateRequest):
    'Agent response generation via Universal LLM Service'
    if not llm_service:
        raise HTTPException(status_code=503, detail='LLM Service not initialized')
    
    try:
        response = await llm_service.generate_agent_response(
            request.agent_id,
            request.message,
            request.user_id,
            request.session_id
        )
        return {
            "response": response,
            "agent_id": request.agent_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "service": "Unified LLM Service"
        }
    except Exception as e:
        logger.error(f"❌ Error of Generation of Answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent_status/{agent_id}")
async def get_agent_status(agent_id: str):
    'Getting Agent Status'
    if not llm_service:
        raise HTTPException(status_code=503, detail='LLM Service not initialized')
    
    try:
        status = await llm_service.get_agent_status(agent_id)
        return {"agent_status": status}
    except Exception as e:
        logger.error(f"❌ Error in obtaining the status of agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/available_agents")
async def get_available_agents():
    'Getting a list of available agents'
    if not llm_service:
        raise HTTPException(status_code=503, detail='LLM Service not initialized')
    
    try:
        # Get a list of all active agents from the database.
        cursor = llm_service.db_connection.cursor()
        cursor.execute("""
            SELECT agent_id, agent_name, role, is_active
            FROM agent_configurations 
            WHERE is_active = true
            ORDER BY agent_name
        """)
        results = cursor.fetchall()
        cursor.close()
        
        agents = [
            {
                "agent_id": row[0],
                "agent_name": row[1],
                "role": row[2],
                "is_active": row[3]
            }
            for row in results
        ]
        
        return {
            "available_agents": agents,
            "total_count": len(agents)
        }
    except Exception as e:
        logger.error(f"❌ Error in obtaining a list of agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info('🚀 Run Universal LLM Service FastAPI server')
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8102,  # Universal LLM Service at port 8102
        reload=True,
        log_level="info"
    )
