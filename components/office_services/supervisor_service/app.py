"""
Centralized Supervisor FastAPI application
HTTP API for Supervisor Microservice
"""
import os

import logging
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from supervisor import CentralizedSupervisor

# Logging settings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Centralized Supervisor Service",
    description='HTTP API for a centralized Supervisor Microservice',
    version="1.0.0"
)

# Global Supervisor
supervisor: CentralizedSupervisor = None

@app.on_event("startup")
async def startup_event():
    'Initialize at startup'
    global supervisor
    logger.info('🚀 Start Centralized Supervisor API...')
    
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
    
    supervisor = CentralizedSupervisor(openai_config, db_config)
    await supervisor.initialize()
    logger.info('✅ Centralized Supervisor API ready')

@app.on_event("shutdown")
async def shutdown_event():
    'Cleaning during stoppage'
    global supervisor
    if supervisor:
        await supervisor.cleanup()
    logger.info('👋 Centralized Supervisor API stopped')

class MessageRequest(BaseModel):
    message: str
    user_id: str = "api_user"
    session_id: str = None

@app.get("/")
async def root():
    'Service information'
    return {
        "service": "Centralized Supervisor Service",
        "version": "1.0.0",
        "status": "active",
        "description": 'Central Supervisor for AI Agent Command',
        "architecture": "PostgreSQL + GPT-5 + Centralized Management"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    if supervisor:
        status = await supervisor.get_status()
        return status
    else:
        return {"status": "initializing"}

@app.post("/process_message")
async def process_message(request: MessageRequest):
    'Supervisor message processing'
    if not supervisor:
        raise HTTPException(status_code=503, detail='Supervisor not initialized')
    
    try:
        response = await supervisor.process_message(
            request.message, 
            request.user_id, 
            request.session_id
        )
        return {
            "response": response,
            "service": "Centralized Supervisor",
            "user_id": request.user_id,
            "session_id": request.session_id
        }
    except Exception as e:
        logger.error(f"❌ Error in communication processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system_info")
async def get_system_info():
    'Getting information on the system'
    if not supervisor:
        raise HTTPException(status_code=503, detail='Supervisor not initialized')
    
    try:
        # Using an internal method to obtain system information
        result = await supervisor._get_system_info(detailed=True, include_metrics=True)
        return {"system_info": result}
    except Exception as e:
        logger.error(f"❌ Error in System Information: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent_status")
async def get_agent_status():
    'Acquiring the status of all agents'
    if not supervisor:
        raise HTTPException(status_code=503, detail='Supervisor not initialized')
    
    try:
        result = await supervisor._get_agent_status(include_performance=True)
        return {"agent_status": result}
    except Exception as e:
        logger.error(f"❌ Error in obtaining the status of agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics")
async def get_statistics():
    'Collection of work statistics'
    if not supervisor:
        raise HTTPException(status_code=503, detail='Supervisor not initialized')
    
    try:
        result = await supervisor._get_statistics(period="today", metrics=["all"])
        return {"statistics": result}
    except Exception as e:
        logger.error(f"❌ Error in obtaining statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info('🚀 Start Centralized Supervisor FastAPI server')
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8100,  # Supervisor at port 8100
        reload=True,
        log_level="info"
    )
