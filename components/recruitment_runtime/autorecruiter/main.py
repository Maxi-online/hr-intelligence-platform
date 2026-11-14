"""
AutoRecruiter - Autonomous agent for passive recruitment

Autonomous AI agent who uses LLM for planning and decision-making,
Working with existing microservices as tools.

Author: Candidate Analysis Team  
Version: 2.0.0 (AutoRecruiter Implementation)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uuid
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# Add a root directory to the journey.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import setup_logging, load_config
from .models import AutoGPTTaskRequest, AutoGPTTaskResponse, AutoGPTTaskStatus
from .recruitment_runtime_agent import PassiveRecruiterAgent

# Logging settings
logger = setup_logging("autorecruiter")

app = FastAPI(
    title="AutoRecruiter",
    description='Autonomous AI agent for passive recruitment with LLM planning',
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
master_agent = None
active_tasks: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    'Initialization of the AutoGPT system'
    global master_agent
    
    try:
        logger.info('🤖 Initialization of AutoRecruiter...')
        
        config = load_config()
        master_agent = PassiveRecruiterAgent(config)
        await master_agent.initialize()
        
        logger.info('✅ AutoRecruiter system ready to work')
        
    except Exception as e:
        logger.error(f"Error: ❌ Initialization of AutoRecruiter: {e}")
        raise

@app.get("/health")
async def health_check():
    'AutoRecruiter System Health Test'
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "master_agent": master_agent is not None,
        "active_tasks": len(active_tasks)
    }

@app.post("/api/autorecruiter/tasks", response_model=AutoGPTTaskResponse)
async def create_autorecruiter_task(request: AutoGPTTaskRequest, background_tasks: BackgroundTasks):
    """
    Create an autonomous task for AutoRecruiter Agent
    
    AutoRecruiter Agent gets a high-level target and plans autonomously
    and perform the necessary actions using existing microservices
    """
    try:
        task_id = f"autorecruiter_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🎯 New AutoRecruiter Task: {task_id}")
        logger.info(f"🎯 Objective: {request.goal}")
        
        # Record the task
        active_tasks[task_id] = {
            "id": task_id,
            "goal": request.goal,
            "context": request.context,
            "requirements": request.requirements,
            "constraints": request.constraints,
            "status": "accepted",
            "created_at": datetime.now(),
            "current_action": "planning",
            "agent_thoughts": [],
            "actions_taken": [],
            "results": None
        }
        
        # Run AutoRecruiter agent in background
        background_tasks.add_task(execute_autorecruiter_task, task_id, request)
        
        return AutoGPTTaskResponse(
            task_id=task_id,
            status="accepted",
            message='AutoRecruiter agent started to perform the task autonomously',
            estimated_duration='The agent will determine for himself.'
        )
        
    except Exception as e:
        logger.error(f"❌ The error of creating the AutoRecruiter task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/autorecruiter/tasks/{task_id}/status", response_model=AutoGPTTaskStatus)
async def get_autorecruiter_task_status(task_id: str):
    'AutoRecruiter task status'
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail='The task is not found.')
        
        task = active_tasks[task_id]
        
        return AutoGPTTaskStatus(
            task_id=task_id,
            status=task["status"],
            current_action=task["current_action"],
            agent_thoughts=task["agent_thoughts"],
            actions_taken=task["actions_taken"],
            created_at=task["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in obtaining the AutoRecruiter status task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/autorecruiter/tasks/{task_id}/result")
async def get_autorecruiter_task_result(task_id: str):
    'AutoRecruiter Tasker Results'
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail='The task is not found.')
        
        task = active_tasks[task_id]
        
        if task["status"] not in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail='The task is not yet completed')
        
        return {
            "task_id": task_id,
            "status": task["status"],
            "goal": task["goal"],
            "agent_thoughts": task["agent_thoughts"],
            "actions_taken": task["actions_taken"],
            "results": task["results"],
            "completed_at": task.get("completed_at"),
            "total_duration": task.get("total_duration")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: ❌ Results of AutoRecruiter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_autorecruiter_task(task_id: str, request: AutoGPTTaskRequest):
    """
    AutoRecruiter task
    
    AutoRecruiter is an autonomous agent:
    1. Analyses target via LLM
    2. Planes the necessary actions
    3. Performs actions through tools (API microservices))
    4. Assesss results and decides on next steps
    5. Repeat cycle before goal
    """
    try:
        logger.info(f"🤖 AutoRecruiter agent starts work on task {task_id}")
        
        # Update status
        active_tasks[task_id]["status"] = "in_progress"
        
        # Start AutoRecruiter autonomous cycle
        # Adds requements and constraints to the content
        enriched_context = dict(request.context) if request.context else {}
        enriched_context.update({
            "requirements": request.requirements,
            "constraints": request.constraints
        })
        
        result = await master_agent.execute_autonomous_goal(
            goal=request.goal,
            context=enriched_context,
            task_id=task_id,
            progress_callback=lambda action, thoughts: update_task_progress(task_id, action, thoughts)
        )
        
        # Save the results.
        active_tasks[task_id]["status"] = "completed"
        active_tasks[task_id]["results"] = result
        active_tasks[task_id]["completed_at"] = datetime.now()
        active_tasks[task_id]["total_duration"] = (
            active_tasks[task_id]["completed_at"] - active_tasks[task_id]["created_at"]
        ).total_seconds()
        
        logger.info(f"✅ AutoRecruiter Task {task_id} implemented autonomously")
        
    except Exception as e:
        logger.error(f"❌ Error in performing the AutoRecruiter task {task_id}: {e}")
        
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["completed_at"] = datetime.now()

def update_task_progress(task_id: str, action: str, thoughts: List[str]):
    'Update progress in the AutoRecruiter task'
    if task_id in active_tasks:
        active_tasks[task_id]["current_action"] = action
        active_tasks[task_id]["agent_thoughts"].extend(thoughts)
        active_tasks[task_id]["actions_taken"].append({
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "thoughts": thoughts
        })

if __name__ == "__main__":
    import uvicorn
    
    config = load_config()
    service_config = config.get("services", {}).get("autorecruiter", {
        "host": "0.0.0.0",
        "port": 8010,
        "debug": False
    })
    
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8010),
        reload=service_config.get("debug", False)
    )
