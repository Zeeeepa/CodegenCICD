"""
Project management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from datetime import datetime

from backend.dependencies import get_database_service_dependency, get_project_repository_dependency
from backend.services.database_service import DatabaseService
from backend.repositories.project_repository import ProjectRepository
from backend.models.project import Project
from backend.integrations.github_client import GitHubClient
from backend.integrations.codegen_client import CodegenClient
from backend.database import get_db
from backend.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])
settings = get_settings()


# Pydantic models for request/response
from pydantic import BaseModel

class ProjectCreateRequest(BaseModel):
    github_id: int
    name: str
    full_name: str
    description: Optional[str] = None
    github_owner: str
    github_repo: str
    github_url: str
    default_branch: str = "main"

class ProjectUpdateRequest(BaseModel):
    auto_confirm_plans: Optional[bool] = None
    auto_merge_validated_pr: Optional[bool] = None
    planning_statement: Optional[str] = None
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    setup_branch: Optional[str] = None

class SecretCreateRequest(BaseModel):
    key: str
    value: str

class AgentRunRequest(BaseModel):
    target_text: str

class AgentRunContinueRequest(BaseModel):
    message: str


@router.get("/github-repos")
async def list_github_repos(db: AsyncSession = Depends(get_db)):
    """List available GitHub repositories"""
    try:
        github_client = GitHubClient()
        repos = await github_client.list_repositories()
        
        # Get currently pinned projects
        pinned_projects = db.query(Project).filter(Project.is_active == True).all()
        pinned_github_ids = {p.github_id for p in pinned_projects}
        
        # Mark repos as pinned
        for repo in repos:
            repo["is_pinned"] = repo["id"] in pinned_github_ids
        
        return {"repositories": repos}
    except Exception as e:
        logger.error("Failed to list GitHub repositories", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    db_service: DatabaseService = Depends(get_database_service_dependency),
    project_repo: ProjectRepository = Depends(get_project_repository_dependency)
):
    """Create/pin a new project"""
    try:
        # Check if project already exists
        existing = project_repo.get_by_github_repo(request.github_owner, request.github_repo)
        if existing:
            raise HTTPException(status_code=409, detail="Project already exists")
        
        # Prepare project data
        project_data = {
            'name': request.name,
            'github_owner': request.github_owner,
            'github_repo': request.github_repo,
            'status': 'active',
            'webhook_url': settings.cloudflare_worker_url,
            'auto_merge_enabled': False,
            'auto_confirm_plans': False
        }
        
        # Create project with default settings
        settings_data = {
            'planning_statement': None,
            'repository_rules': None,
            'setup_commands': None,
            'branch_name': request.default_branch
        }
        
        project = await db_service.create_project_with_settings(project_data, settings_data)
        
        if not project:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        # Set up webhook in background
        if project.id:
            background_tasks.add_task(setup_project_webhook, project.id)
        
        logger.info("Project created", project_id=project.id, name=project.name)
        return {"project": project.dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create project", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_projects(
    db_service: DatabaseService = Depends(get_database_service_dependency)
):
    """List all active projects with statistics"""
    try:
        projects = await db_service.search_projects_with_stats()
        return {"projects": projects}
    except Exception as e:
        logger.error("Failed to list projects", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(
    project_id: int, 
    db_service: DatabaseService = Depends(get_database_service_dependency)
):
    """Get project details with full configuration"""
    try:
        project_config = await db_service.get_project_full_config(project_id)
        if not project_config:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"project": project_config}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get project", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update project settings"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update fields
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        db.commit()
        db.refresh(project)
        
        logger.info("Project updated", project_id=project_id, updates=update_data)
        return {"project": project.to_dict()}
        
    except Exception as e:
        logger.error("Failed to update project", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Unpin/deactivate a project"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project.is_active = False
        db.commit()
        
        logger.info("Project unpinned", project_id=project_id)
        return {"message": "Project unpinned successfully"}
        
    except Exception as e:
        logger.error("Failed to unpin project", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Project Secrets Management
@router.get("/{project_id}/secrets")
async def list_project_secrets(project_id: int, db: AsyncSession = Depends(get_db)):
    """List project secrets"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        secrets = db.query(ProjectSecret).filter(ProjectSecret.project_id == project_id).all()
        return {"secrets": [s.to_dict() for s in secrets]}
        
    except Exception as e:
        logger.error("Failed to list project secrets", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/secrets")
async def create_project_secret(
    project_id: int,
    request: SecretCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a project secret"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if secret already exists
        existing = db.query(ProjectSecret).filter(
            ProjectSecret.project_id == project_id,
            ProjectSecret.key == request.key
        ).first()
        
        if existing:
            # Update existing secret
            existing.value = request.value
            db.commit()
            db.refresh(existing)
            return {"secret": existing.to_dict()}
        else:
            # Create new secret
            secret = ProjectSecret(
                project_id=project_id,
                key=request.key,
                value=request.value
            )
            db.add(secret)
            db.commit()
            db.refresh(secret)
            return {"secret": secret.to_dict()}
        
    except Exception as e:
        logger.error("Failed to create project secret", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/secrets/{secret_id}")
async def delete_project_secret(
    project_id: int,
    secret_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project secret"""
    try:
        secret = db.query(ProjectSecret).filter(
            ProjectSecret.id == secret_id,
            ProjectSecret.project_id == project_id
        ).first()
        
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")
        
        db.delete(secret)
        db.commit()
        
        return {"message": "Secret deleted successfully"}
        
    except Exception as e:
        logger.error("Failed to delete project secret", project_id=project_id, secret_id=secret_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Agent Run Management
@router.post("/{project_id}/agent-runs")
async def create_agent_run(
    project_id: int,
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent run for the project"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Create agent run record
        agent_run = ProjectAgentRun(
            project_id=project_id,
            target_text=request.target_text,
            status="pending"
        )
        db.add(agent_run)
        db.commit()
        db.refresh(agent_run)
        
        # Start agent run in background
        background_tasks.add_task(execute_agent_run, agent_run.id)
        
        logger.info("Agent run created", agent_run_id=agent_run.id, project_id=project_id)
        return {"agent_run": agent_run.to_dict()}
        
    except Exception as e:
        logger.error("Failed to create agent run", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/agent-runs")
async def list_agent_runs(project_id: int, db: AsyncSession = Depends(get_db)):
    """List agent runs for the project"""
    try:
        runs = db.query(ProjectAgentRun).filter(
            ProjectAgentRun.project_id == project_id
        ).order_by(ProjectAgentRun.created_at.desc()).all()
        
        return {"agent_runs": [r.to_dict() for r in runs]}
        
    except Exception as e:
        logger.error("Failed to list agent runs", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/agent-runs/{run_id}")
async def get_agent_run(
    project_id: int,
    run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get agent run details"""
    try:
        run = db.query(ProjectAgentRun).filter(
            ProjectAgentRun.id == run_id,
            ProjectAgentRun.project_id == project_id
        ).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        return {"agent_run": run.to_dict()}
        
    except Exception as e:
        logger.error("Failed to get agent run", project_id=project_id, run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/agent-runs/{run_id}/continue")
async def continue_agent_run(
    project_id: int,
    run_id: int,
    request: AgentRunContinueRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Continue an agent run with additional input"""
    try:
        run = db.query(ProjectAgentRun).filter(
            ProjectAgentRun.id == run_id,
            ProjectAgentRun.project_id == project_id
        ).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        if run.status not in ["completed", "waiting_for_input"]:
            raise HTTPException(status_code=400, detail="Agent run cannot be continued")
        
        # Continue agent run in background
        background_tasks.add_task(continue_agent_run_task, run_id, request.message)
        
        return {"message": "Agent run continuation started"}
        
    except Exception as e:
        logger.error("Failed to continue agent run", project_id=project_id, run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/setup-commands/run")
async def run_setup_commands(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Run setup commands for the project"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.setup_commands:
            raise HTTPException(status_code=400, detail="No setup commands configured")
        
        # Run setup commands in background
        background_tasks.add_task(execute_setup_commands, project_id)
        
        return {"message": "Setup commands execution started"}
        
    except Exception as e:
        logger.error("Failed to run setup commands", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Background tasks
async def setup_project_webhook(project_id: int):
    """Set up GitHub webhook for the project"""
    try:
        async with get_db() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return
            
            webhook_service = WebhookService()
            webhook_url = await webhook_service.setup_github_webhook(
                project.github_owner,
                project.github_repo,
                project.webhook_url
            )
            
            if webhook_url:
                project.webhook_active = True
                db.commit()
                logger.info("Webhook set up successfully", project_id=project_id)
            
    except Exception as e:
        logger.error("Failed to set up webhook", project_id=project_id, error=str(e))


async def execute_agent_run(agent_run_id: int):
    """Execute agent run via Codegen API"""
    try:
        async with get_db() as db:
            run = db.query(ProjectAgentRun).filter(ProjectAgentRun.id == agent_run_id).first()
            if not run:
                return
            
            project = db.query(Project).filter(Project.id == run.project_id).first()
            if not project:
                return
            
            # Update status
            run.status = "running"
            db.commit()
            
            # Prepare prompt
            prompt = f"<Project='{project.name}'>\n"
            if project.planning_statement:
                prompt += f"{project.planning_statement}\n\n"
            if project.repository_rules:
                prompt += f"Repository Rules:\n{project.repository_rules}\n\n"
            prompt += f"Target: {run.target_text}"
            
            # Execute via Codegen API
            codegen_client = CodegenClient()
            response = await codegen_client.create_agent_run(
                org_id=int(settings.codegen_org_id),
                prompt=prompt,
                metadata={"project_id": project.id, "agent_run_id": run.id}
            )
            
            # Update run with response
            run.codegen_run_id = response.id
            run.response_data = response.to_dict()
            run.status = response.status or "running"
            db.commit()
            
            logger.info("Agent run started", agent_run_id=agent_run_id, codegen_run_id=response.id)
            
    except Exception as e:
        logger.error("Failed to execute agent run", agent_run_id=agent_run_id, error=str(e))
        # Update run status to failed
        async with get_db() as db:
            run = db.query(ProjectAgentRun).filter(ProjectAgentRun.id == agent_run_id).first()
            if run:
                run.status = "failed"
                db.commit()


async def continue_agent_run_task(agent_run_id: int, message: str):
    """Continue agent run with additional message"""
    try:
        async with get_db() as db:
            run = db.query(ProjectAgentRun).filter(ProjectAgentRun.id == agent_run_id).first()
            if not run or not run.codegen_run_id:
                return
            
            codegen_client = CodegenClient()
            response = await codegen_client.continue_agent_run(
                org_id=int(settings.codegen_org_id),
                run_id=run.codegen_run_id,
                message=message
            )
            
            # Update run status
            run.status = "running"
            run.response_data = response.to_dict()
            db.commit()
            
            logger.info("Agent run continued", agent_run_id=agent_run_id)
            
    except Exception as e:
        logger.error("Failed to continue agent run", agent_run_id=agent_run_id, error=str(e))


async def execute_setup_commands(project_id: int):
    """Execute setup commands for the project"""
    try:
        async with get_db() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project or not project.setup_commands:
                return
            
            # TODO: Implement setup command execution using Grainchain
            # This would involve creating a sandbox, cloning the repo, and running commands
            logger.info("Setup commands execution started", project_id=project_id)
            
    except Exception as e:
        logger.error("Failed to execute setup commands", project_id=project_id, error=str(e))
