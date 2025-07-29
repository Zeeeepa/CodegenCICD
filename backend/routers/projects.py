"""
Project management API routes
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import structlog

from backend.services.project_service import project_service
from backend.services.github_service import github_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


class AddProjectRequest(BaseModel):
    github_repo_data: Dict[str, Any]


class UpdateProjectSettingsRequest(BaseModel):
    repository_rules: str = None
    setup_commands: str = None
    setup_branch: str = None
    planning_statement: str = None
    secrets: Dict[str, str] = None
    validation_timeout: int = None
    max_validation_retries: int = None
    deployment_commands: str = None
    health_check_url: str = None


class UpdateProjectConfigRequest(BaseModel):
    auto_merge_enabled: bool = None
    auto_confirm_plans: bool = None
    auto_merge_threshold: int = None
    validation_enabled: bool = None


@router.get("/github-repositories")
async def get_github_repositories():
    """Get all GitHub repositories for the user"""
    try:
        repositories = await project_service.get_github_repositories()
        return {"repositories": repositories}
    except Exception as e:
        logger.error("Error fetching GitHub repositories", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch GitHub repositories")


@router.get("/dashboard")
async def get_dashboard_projects():
    """Get all projects on the dashboard"""
    try:
        projects = await project_service.get_dashboard_projects()
        return {"projects": projects}
    except Exception as e:
        logger.error("Error fetching dashboard projects", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard projects")


@router.post("/add")
async def add_project_to_dashboard(request: AddProjectRequest):
    """Add a GitHub repository as a project to the dashboard"""
    try:
        project = await project_service.add_project_to_dashboard(request.github_repo_data)
        
        # Convert to dict for response
        project_data = {
            "id": project.id,
            "github_id": project.github_id,
            "name": project.name,
            "full_name": project.full_name,
            "description": project.description,
            "github_owner": project.github_owner,
            "github_repo": project.github_repo,
            "github_branch": project.github_branch,
            "github_url": project.github_url,
            "webhook_active": project.webhook_active,
            "webhook_url": project.webhook_url,
            "auto_merge_enabled": project.auto_merge_enabled,
            "auto_confirm_plans": project.auto_confirm_plans,
            "status": project.status,
            "created_at": project.created_at.isoformat()
        }
        
        return {"project": project_data}
        
    except Exception as e:
        logger.error("Error adding project to dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add project to dashboard")


@router.delete("/{project_id}")
async def remove_project_from_dashboard(project_id: int):
    """Remove a project from the dashboard"""
    try:
        success = await project_service.remove_project_from_dashboard(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"message": "Project removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error removing project from dashboard", 
                   project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to remove project from dashboard")


@router.get("/{project_id}/settings")
async def get_project_settings(project_id: int):
    """Get project settings"""
    try:
        settings = await project_service.get_project_settings(project_id)
        if not settings:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"settings": settings}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching project settings", 
                   project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch project settings")


@router.put("/{project_id}/settings")
async def update_project_settings(project_id: int, request: UpdateProjectSettingsRequest):
    """Update project settings"""
    try:
        # Convert request to dict, excluding None values
        settings_data = {k: v for k, v in request.dict().items() if v is not None}
        
        success = await project_service.update_project_settings(project_id, settings_data)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"message": "Project settings updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating project settings", 
                   project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update project settings")


@router.put("/{project_id}/config")
async def update_project_config(project_id: int, request: UpdateProjectConfigRequest):
    """Update project configuration"""
    try:
        # Convert request to dict, excluding None values
        config_data = {k: v for k, v in request.dict().items() if v is not None}
        
        success = await project_service.update_project_config(project_id, config_data)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"message": "Project configuration updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating project configuration", 
                   project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update project configuration")


@router.get("/{project_id}/branches")
async def get_repository_branches(project_id: int):
    """Get branches for a project's repository"""
    try:
        branches = await project_service.get_repository_branches(project_id)
        return {"branches": branches}
        
    except Exception as e:
        logger.error("Error fetching repository branches", 
                   project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch repository branches")


@router.post("/{project_id}/setup-commands/run")
async def run_setup_commands(project_id: int, branch: str = "main"):
    """Run setup commands for a project"""
    try:
        # Get project settings
        settings = await project_service.get_project_settings(project_id)
        if not settings or not settings.get("setup_commands"):
            raise HTTPException(status_code=400, detail="No setup commands configured")
        
        # TODO: Implement setup command execution with grainchain
        # This would involve:
        # 1. Create a sandbox environment
        # 2. Clone the repository on the specified branch
        # 3. Execute the setup commands
        # 4. Return logs and status
        
        return {
            "message": "Setup commands execution started",
            "status": "pending",
            "branch": branch
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error running setup commands", 
                   project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to run setup commands")

