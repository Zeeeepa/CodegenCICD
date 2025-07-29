"""
Agent run management API routes
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import structlog

from backend.services.agent_run_service import agent_run_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/agent-runs", tags=["agent-runs"])


class CreateAgentRunRequest(BaseModel):
    project_id: int
    target_text: str
    auto_confirm_plans: bool = False


class ContinueAgentRunRequest(BaseModel):
    message: str


class ConfirmPlanRequest(BaseModel):
    confirmation: str = "Proceed"


@router.post("/")
async def create_agent_run(request: CreateAgentRunRequest):
    """Create a new agent run"""
    try:
        agent_run = await agent_run_service.create_agent_run(
            project_id=request.project_id,
            target=request.target_text,
            auto_confirm_plans=request.auto_confirm_plans
        )
        
        # Convert to dict for response
        agent_run_data = {
            "id": agent_run.id,
            "project_id": agent_run.project_id,
            "codegen_run_id": agent_run.codegen_run_id,
            "target": agent_run.target,
            "status": agent_run.status.value,
            "run_type": agent_run.run_type.value,
            "progress_percentage": agent_run.progress_percentage,
            "current_step": agent_run.current_step,
            "auto_confirm_plans": agent_run.auto_confirm_plans,
            "pr_url": agent_run.pr_url,
            "pr_number": agent_run.pr_number,
            "created_at": agent_run.created_at.isoformat()
        }
        
        return {"agent_run": agent_run_data}
        
    except Exception as e:
        logger.error("Error creating agent run", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create agent run")


@router.get("/{agent_run_id}")
async def get_agent_run(agent_run_id: int):
    """Get agent run details"""
    try:
        agent_run = await agent_run_service.get_agent_run(agent_run_id)
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        # Get latest response
        latest_response = agent_run.get_latest_response()
        
        agent_run_data = {
            "id": agent_run.id,
            "project_id": agent_run.project_id,
            "codegen_run_id": agent_run.codegen_run_id,
            "target": agent_run.target,
            "planning_statement": agent_run.planning_statement,
            "status": agent_run.status.value,
            "run_type": agent_run.run_type.value,
            "progress_percentage": agent_run.progress_percentage,
            "current_step": agent_run.current_step,
            "final_response": agent_run.final_response,
            "error_message": agent_run.error_message,
            "pr_url": agent_run.pr_url,
            "pr_number": agent_run.pr_number,
            "auto_confirm_plans": agent_run.auto_confirm_plans,
            "execution_time_seconds": agent_run.execution_time_seconds,
            "created_at": agent_run.created_at.isoformat(),
            "updated_at": agent_run.updated_at.isoformat() if agent_run.updated_at else None,
            "latest_response": None
        }
        
        if latest_response:
            agent_run_data["latest_response"] = {
                "id": latest_response.id,
                "response_type": latest_response.response_type,
                "content": latest_response.content,
                "is_final": latest_response.is_final,
                "requires_user_input": latest_response.requires_user_input,
                "plan_data": latest_response.plan_data,
                "pr_data": latest_response.pr_data,
                "created_at": latest_response.created_at.isoformat()
            }
        
        return {"agent_run": agent_run_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching agent run", 
                   agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch agent run")


@router.post("/{agent_run_id}/continue")
async def continue_agent_run(agent_run_id: int, request: ContinueAgentRunRequest):
    """Continue an agent run with user input"""
    try:
        agent_run = await agent_run_service.continue_agent_run(
            agent_run_id=agent_run_id,
            message=request.message
        )
        
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        return {"message": "Agent run continued successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error continuing agent run", 
                   agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to continue agent run")


@router.post("/{agent_run_id}/confirm-plan")
async def confirm_plan(agent_run_id: int, request: ConfirmPlanRequest):
    """Confirm a plan from an agent run"""
    try:
        agent_run = await agent_run_service.continue_agent_run(
            agent_run_id=agent_run_id,
            message=request.confirmation
        )
        
        if not agent_run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        return {"message": "Plan confirmed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error confirming plan", 
                   agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to confirm plan")


@router.post("/{agent_run_id}/cancel")
async def cancel_agent_run(agent_run_id: int):
    """Cancel an agent run"""
    try:
        success = await agent_run_service.cancel_agent_run(agent_run_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        return {"message": "Agent run cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cancelling agent run", 
                   agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cancel agent run")


@router.get("/{agent_run_id}/responses")
async def get_agent_run_responses(agent_run_id: int):
    """Get all responses for an agent run"""
    try:
        responses = await agent_run_service.get_agent_run_responses(agent_run_id)
        
        response_data = []
        for response in responses:
            response_data.append({
                "id": response.id,
                "sequence_number": response.sequence_number,
                "response_type": response.response_type,
                "content": response.content,
                "is_final": response.is_final,
                "requires_user_input": response.requires_user_input,
                "plan_data": response.plan_data,
                "pr_data": response.pr_data,
                "metadata": response.metadata,
                "created_at": response.created_at.isoformat()
            })
        
        return {"responses": response_data}
        
    except Exception as e:
        logger.error("Error fetching agent run responses", 
                   agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch agent run responses")


@router.get("/{agent_run_id}/steps")
async def get_agent_run_steps(agent_run_id: int):
    """Get all steps for an agent run"""
    try:
        steps = await agent_run_service.get_agent_run_steps(agent_run_id)
        
        step_data = []
        for step in steps:
            step_data.append({
                "id": step.id,
                "step_number": step.step_number,
                "step_name": step.step_name,
                "step_description": step.step_description,
                "started_at": step.started_at,
                "completed_at": step.completed_at,
                "duration_seconds": step.duration_seconds,
                "step_data": step.step_data,
                "result_data": step.result_data,
                "error_message": step.error_message,
                "is_completed": step.is_completed,
                "is_successful": step.is_successful,
                "created_at": step.created_at.isoformat()
            })
        
        return {"steps": step_data}
        
    except Exception as e:
        logger.error("Error fetching agent run steps", 
                   agent_run_id=agent_run_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch agent run steps")

