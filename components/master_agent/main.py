"""
Master Agent Service - Master &apos; s main service

FastAPI Launch and Control Service by the REX Master Agent.
Provides REST API to interact with an agent.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .master_agent import MasterAgent
from .models import (
    MasterTaskRequest, MasterTaskResponse, MasterTaskStatus,
    ConversationMessage, MasterTaskStatusUpdate
)


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



# Logging settings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("master-agent-service")

# FastAPI application
app = FastAPI(
    title='Master Agent (REX) API',
    description='Chief Coordinator of the Neuro staff of the organization',
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Added by CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production limit domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
master_agent: Optional[MasterAgent] = None
config: Dict[str, Any] = {}
active_tasks: Dict[str, Dict[str, Any]] = {}
task_callbacks: Dict[str, List] = {}


# Request models
class TaskCreationRequest(BaseModel):
    goal: str
    context: Dict[str, Any] = {}
    priority: str = "normal"
    deadline: Optional[str] = None
    requester: str = "api_user"
    channel: str = "api"
    constraints: List[str] = []


class ConversationRequest(BaseModel):
    message: str
    sender: str
    channel: str = "api"
    conversation_id: Optional[str] = None


class WebhookMessage(BaseModel):
    'Webhawk message model from massers'
    channel: str
    raw_message: Dict[str, Any]


# Life-cycle developments
@app.on_event("startup")
async def startup_event():
    'Initialization at the start of the service'
    global master_agent, config
    
    try:
        logger.info('🚀 Start Master Agent Service...')
        
        # Upload configuration
        config = load_config()
        
        # Creation and Initialization of Master Agent
        master_agent = MasterAgent(config)
        await master_agent.initialize()
        
        # Message handler settings
        if hasattr(master_agent, 'messenger'):
            master_agent.messenger.add_message_handler(handle_incoming_message)
        
        logger.info('✅ Master Agent service successfully launched')
        
    except Exception as e:
        logger.error(f"❌ The Master Agent Service Error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    'Completion of service'
    global master_agent
    
    try:
        logger.info('🛑 Completion of Master Agency service...')
        
        if master_agent and hasattr(master_agent, 'memory_manager'):
            await master_agent.memory_manager.save_session()
        
        logger.info('✅ Master Agency service completed')
        
    except Exception as e:
        logger.error(f"❌ Error of completion of service: {e}")


# API endpoints
@app.get("/health")
async def health_check():
    'Service health check'
    if master_agent is None:
        raise HTTPException(status_code=503, detail='Master Agent not initialized')
    
    status = await master_agent.get_status()
    
    return {
        "status": "healthy",
        "service": "master_agent",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "agent_status": status
    }


@app.post("/api/master-agent/tasks", response_model=MasterTaskResponse)
async def create_task(request: TaskCreationRequest, background_tasks: BackgroundTasks):
    'Creating a new task for the master agent'
    if master_agent is None:
        raise HTTPException(status_code=503, detail='Master Agent not initialized')
    
    try:
        # Creation of the task
        task_request = MasterTaskRequest(
            goal=request.goal,
            context=request.context,
            priority=request.priority,
            requester=request.requester,
            channel=request.channel,
            constraints=request.constraints
        )
        
        # Creating callback to track progress
        task_progress_updates = []
        
        async def progress_callback(task_id: str, status: str, messages: List[str]):
            task_progress_updates.append({
                "task_id": task_id,
                "status": status,
                "messages": messages,
                "timestamp": datetime.now().isoformat()
            })
        
        # Launching the task against the background
        background_tasks.add_task(
            process_task_in_background,
            master_agent,
            task_request,
            progress_callback
        )
        
        # Return of initial reply
        response = MasterTaskResponse(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            status=MasterTaskStatus.RECEIVED,
            message='Target accepted',
            estimated_duration="I'm analyzing...",
            assigned_agents=[]
        )
        
        # Save callback for updates
        task_callbacks[response.task_id] = task_progress_updates
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error in Creating Task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    'Getting the status of the task'
    if task_id not in active_tasks and task_id not in task_callbacks:
        raise HTTPException(status_code=404, detail='The task is not found.')
    
    try:
        # Receive updates from callback
        updates = task_callbacks.get(task_id, [])
        
        if not updates:
            return {
                "task_id": task_id,
                "status": "pending",
                "progress": 0.0,
                "messages": ['Task in line']
            }
        
        # Last update
        latest_update = updates[-1]
        
        return {
            "task_id": task_id,
            "status": latest_update["status"],
            "progress": len(updates) * 0.2,  # Indicative progress
            "messages": latest_update["messages"],
            "updates_count": len(updates),
            "last_update": latest_update["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error in obtaining the status of task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    'Delivering the result of the task'
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail='The task has not been found or is still being carried out')
    
    try:
        task_data = active_tasks[task_id]
        
        return {
            "task_id": task_id,
            "status": task_data.get("status"),
            "result": task_data.get("result"),
            "execution_time": task_data.get("execution_time"),
            "quality_metrics": task_data.get("quality_metrics"),
            "agent_results": task_data.get("agent_results", [])
        }
        
    except Exception as e:
        logger.error(f"❌ Error in obtaining the task result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/master-agent/conversation")
async def handle_conversation(request: ConversationRequest):
    'Processing the dialogue with the master agent'
    if master_agent is None:
        raise HTTPException(status_code=503, detail='Master Agent not initialized')
    
    try:
        # Creation of a message
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"
        
        message = ConversationMessage(
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            sender=request.sender,
            recipient="master_agent",
            content=request.message,
            channel=request.channel,
            conversation_id=conversation_id
        )
        
        # Processing of the communication
        response_message = await master_agent.handle_conversation(message)
        
        return {
            "conversation_id": conversation_id,
            "response": response_message.content,
            "timestamp": response_message.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in dialogue processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/master-agent/webhook/{channel}")
async def handle_webhook(channel: str, webhook_data: WebhookMessage):
    'Webhawk from Massingers'
    if master_agent is None or not hasattr(master_agent, 'messenger'):
        raise HTTPException(status_code=503, detail='Messenger Interface not available')
    
    try:
        # Processing of incoming message
        message = await master_agent.messenger.handle_incoming_message(
            webhook_data.raw_message, 
            channel
        )
        
        if message:
            # Response generation
            response_message = await master_agent.handle_conversation(message)
            
            # Sending the reply back
            await master_agent.messenger.send_message(response_message)
            
            return {"status": "processed", "message_id": message.message_id}
        else:
            return {"status": "ignored", "reason": 'Unable to process message'}
        
    except Exception as e:
        logger.error(f"❌ The Webhook Processing Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/stats")
async def get_stats():
    'Getting Master Agent Statistics'
    if master_agent is None:
        raise HTTPException(status_code=503, detail='Master Agent not initialized')
    
    try:
        # Collection of statistics from all components
        agent_stats = await master_agent.get_status()
        
        stats = {
            "master_agent": agent_stats,
            "service_uptime": (datetime.now() - agent_stats.get("uptime_start", datetime.now())).total_seconds(),
            "active_tasks_count": len(active_tasks),
            "callbacks_count": len(task_callbacks)
        }
        
        # Component statistics
        if hasattr(master_agent, 'task_distributor'):
            stats["task_distributor"] = await master_agent.task_distributor.get_stats()
        
        if hasattr(master_agent, 'memory_manager'):
            stats["memory_manager"] = await master_agent.memory_manager.get_stats()
        
        if hasattr(master_agent, 'quality_controller'):
            stats["quality_controller"] = await master_agent.quality_controller.get_stats()
        
        if hasattr(master_agent, 'org_context'):
            stats["organization_context"] = await master_agent.org_context.get_stats()
        
        if hasattr(master_agent, 'messenger'):
            stats["messenger"] = await master_agent.messenger.get_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error in obtaining statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master-agent/quality/report")
async def get_quality_report(period_days: int = 7):
    'Collection of quality report'
    if master_agent is None or not hasattr(master_agent, 'quality_controller'):
        raise HTTPException(status_code=503, detail='Quality Control not available')
    
    try:
        report = await master_agent.quality_controller.generate_quality_report(period_days)
        return report
        
    except Exception as e:
        logger.error(f"❌ Error in Generating Quality Report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Support functions
async def process_task_in_background(agent: MasterAgent, task_request: MasterTaskRequest, 
                                   progress_callback):
    'Task processing in background mode'
    try:
        result = await agent.process_task(task_request, progress_callback)
        
        # Retaining the result
        active_tasks[result.task_id] = {
            "status": result.status,
            "result": result,
            "completion_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in background task processing: {e}")


async def handle_incoming_message(message: ConversationMessage):
    'Incoming Messenger Messages Processor'
    try:
        logger.info(f"📨 Message received from {message.sender}: {message.content[:50]}...")
        
        # There may be an additional processing logic here.
        
    except Exception as e:
        logger.error(f"❌ Error in the processing of the input message: {e}")


def load_config() -> Dict[str, Any]:
    'Upload configuration'
    try:
        # Attempted download from config/settings.yaml
        config_path = "config/settings.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = _resolve_settings_env(yaml.safe_load(f))
            logger.info(f"✅ The configuration is downloaded from {config_path}")
            return config
        
        # Basic configuration
        logger.warning('⚠️ No configuration file found, base used')
        return get_default_config()
        
    except Exception as e:
        logger.error(f"❌ Configuration Error: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    'Basic configuration'
    return {
        "master_agent": {
            "main_model": "gpt-5-mini",
            "fast_model": "gpt-5-mini",
            "max_completion_tokens": 4000,
            "temperature": 0.2,
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "base_url": "https://openrouter.ai/api/v1",
            "proxy": {
                "enabled": False
            },
            "gpt5_features": {
                "default_verbosity": "medium",
                "default_reasoning_effort": "medium"
            },
            "memory": {
                "chroma_persist_directory": "data/master_memory/chroma_db",
                "embedding_model": "text-embedding-3-small"
            }
        },
        "services": {
            "master_agent": {
                "port": 8020,
                "host": "0.0.0.0"
            },
            "recruitment_runtime": {
                "port": 8010,
                "host": "localhost"
            }
        },
        "messengers": {
            "teams": {
                "enabled": False
            },
            "telegram": {
                "enabled": False
            },
            "email": {
                "enabled": False
            }
        },
        "quality_control": {
            "min_success_rate": 0.8,
            "max_response_time": 300,
            "min_user_satisfaction": 0.7,
            "escalation_failure_rate": 0.3
        }
    }


# Start service
if __name__ == "__main__":
    # Settings made of variable environment or configuration
    host = os.getenv("MASTER_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("MASTER_AGENT_PORT", "8020"))
    
    logger.info(f"🚀 Start Master Agent service on {host}:{port}")
    
    uvicorn.run(
        "master_agent.main:app",
        host=host,
        port=port,
        reload=False,  # In Production Disable
        log_level="info"
    )
