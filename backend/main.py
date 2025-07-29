"""
Main FastAPI application entry point with database integration
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

# Import database and service layers
from dependencies import (
    get_healthy_db_service, 
    validate_project_id, 
    validate_pagination,
    get_project_or_404,
    log_request_middleware,
    handle_database_errors
)
from services.database_service import DatabaseService
from models import Project, ProjectSettings, ProjectSecret

# Import routers
from routers.service_validation import router as service_validation_router

# Create FastAPI app
app = FastAPI(
    title="CodegenCICD Dashboard",
    description="AI-powered CI/CD dashboard with validation pipeline",
    version="1.0.0"
)

# Add middleware
app.middleware("http")(log_request_middleware)

# Include routers
app.include_router(service_validation_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class ProjectCreateRequest(BaseModel):
    name: str
    github_owner: str
    github_repo: str
    webhook_url: Optional[str] = None
    auto_merge_enabled: bool = False
    auto_confirm_plans: bool = False

class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    webhook_url: Optional[str] = None
    auto_merge_enabled: Optional[bool] = None
    auto_confirm_plans: Optional[bool] = None

class ProjectSettingsRequest(BaseModel):
    planning_statement: Optional[str] = None
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    branch_name: Optional[str] = None

class ProjectSecretRequest(BaseModel):
    key: str
    value: str

class ProjectSecretsRequest(BaseModel):
    secrets: Dict[str, str]

# Basic health check endpoint
@app.get("/")
async def root():
    return {"message": "CodegenCICD Dashboard API", "status": "running"}

@app.get("/health")
async def health_check(db_service: DatabaseService = Depends(get_healthy_db_service)):
    """Enhanced health check with database status"""
    db_health = await db_service.health_check()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "service": "codegencd-api",
        "database": db_health
    }

# ============================================================================
# PROJECT MANAGEMENT ENDPOINTS (REAL DATABASE INTEGRATION)
# ============================================================================

@app.get("/api/projects")
@handle_database_errors
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Get all projects with pagination and search"""
    pagination = validate_pagination(skip, limit)
    
    if search:
        projects = await db_service.search_projects(search, limit)
        return {
            "projects": [project.dict() for project in projects],
            "total_count": len(projects),
            "search_term": search
        }
    else:
        result = await db_service.get_projects_list(
            limit=pagination["limit"], 
            offset=pagination["skip"]
        )
        return {
            "projects": [project.dict() for project in result["projects"]],
            "total_count": result["total_count"],
            "limit": result["limit"],
            "offset": result["offset"]
        }

@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
@handle_database_errors
async def create_project(
    project_data: ProjectCreateRequest,
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Create a new project"""
    # Convert to dict and add default webhook URL if not provided
    project_dict = project_data.dict()
    if not project_dict.get("webhook_url"):
        project_dict["webhook_url"] = f"https://webhook-gateway.pixeliumperfecto.workers.dev/webhook/{project_data.github_owner}/{project_data.github_repo}"
    
    result = await db_service.create_project_with_settings(project_dict)
    return {
        "project": result["project"].dict(),
        "message": "Project created successfully"
    }

@app.get("/api/projects/{project_id}")
@handle_database_errors
async def get_project(
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Get a specific project"""
    project = await get_project_or_404(project_id, db_service)
    return {"project": project.dict()}

@app.put("/api/projects/{project_id}")
@handle_database_errors
async def update_project(
    project_data: ProjectUpdateRequest,
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Update a project"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Update project
    update_dict = {k: v for k, v in project_data.dict().items() if v is not None}
    result = await db_service.update_project_configuration(
        project_id=project_id,
        project_data=update_dict
    )
    
    return {
        "project": result["project"].dict(),
        "message": "Project updated successfully"
    }

@app.delete("/api/projects/{project_id}")
@handle_database_errors
async def delete_project(
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Delete a project"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Delete project and all related data
    success = await db_service.delete_project_complete(project_id)
    
    if success:
        return {"message": "Project deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )

# ============================================================================
# PROJECT CONFIGURATION ENDPOINTS
# ============================================================================

@app.get("/api/projects/{project_id}/configuration")
@handle_database_errors
async def get_project_configuration(
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Get project configuration"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Get project settings
    settings = db_service.settings.get_by_project_id(project_id)
    
    if settings:
        return {"configuration": settings.dict()}
    else:
        # Return default configuration if none exists
        return {
            "configuration": {
                "id": None,
                "project_id": project_id,
                "planning_statement": None,
                "repository_rules": None,
                "setup_commands": None,
                "branch_name": "main",
                "created_at": None,
                "updated_at": None
            }
        }

@app.put("/api/projects/{project_id}/configuration")
@handle_database_errors
async def update_project_configuration(
    config_data: ProjectSettingsRequest,
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Update project configuration"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Update settings
    settings_dict = {k: v for k, v in config_data.dict().items() if v is not None}
    result = await db_service.update_project_configuration(
        project_id=project_id,
        settings_data=settings_dict
    )
    
    return {
        "configuration": result["settings"].dict() if result["settings"] else None,
        "message": "Configuration updated successfully"
    }

# ============================================================================
# PROJECT SECRETS ENDPOINTS
# ============================================================================

@app.get("/api/projects/{project_id}/secrets")
@handle_database_errors
async def get_project_secrets(
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Get project secrets (returns key names only for security)"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Get secrets (encrypted values only)
    secrets = db_service.secrets.get_by_project_id(project_id)
    
    return {
        "secrets": [
            {
                "id": secret.id,
                "key": secret.key_name,
                "created_at": secret.created_at
            }
            for secret in secrets
        ]
    }

@app.post("/api/projects/{project_id}/secrets", status_code=status.HTTP_201_CREATED)
@handle_database_errors
async def create_project_secret(
    secret_data: ProjectSecretRequest,
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Create a new project secret"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Create secret
    secret_dict = {
        "project_id": project_id,
        "key_name": secret_data.key,
        "value": secret_data.value
    }
    secret = db_service.secrets.create(secret_dict)
    
    return {
        "secret": {
            "id": secret.id,
            "key": secret.key_name,
            "created_at": secret.created_at
        },
        "message": "Secret created successfully"
    }

@app.put("/api/projects/{project_id}/secrets")
@handle_database_errors
async def update_project_secrets(
    secrets_data: ProjectSecretsRequest,
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Bulk update project secrets"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Update secrets
    result = await db_service.update_project_configuration(
        project_id=project_id,
        secrets_data=secrets_data.secrets
    )
    
    return {
        "secrets_updated": result["secrets_updated"],
        "message": "Secrets updated successfully"
    }

@app.delete("/api/projects/{project_id}/secrets/{key_name}")
@handle_database_errors
async def delete_project_secret(
    key_name: str,
    project_id: int = Depends(validate_project_id),
    db_service: DatabaseService = Depends(get_healthy_db_service)
):
    """Delete a specific project secret"""
    # Verify project exists
    await get_project_or_404(project_id, db_service)
    
    # Delete secret
    success = db_service.secrets.delete_by_project_and_key(project_id, key_name)
    
    if success:
        return {"message": "Secret deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{key_name}' not found"
        )

@app.post("/api/agent-runs")
async def create_agent_run(agent_run_data: dict):
    """Create a new agent run"""
    return {
        "id": 1,
        "project_id": agent_run_data.get("project_id", 1),
        "target_text": agent_run_data.get("target_text", ""),
        "planning_statement": agent_run_data.get("planning_statement", ""),
        "status": "running",
        "run_type": "regular",
        "result": None,
        "error_message": None,
        "pr_number": None,
        "pr_url": None,
        "validation_status": "pending",
        "auto_merge_enabled": False,
        "merge_completed": False,
        "started_at": "2024-01-01T00:00:00Z",
        "completed_at": None
    }

@app.get("/api/agent-runs")
async def get_agent_runs(project_id: int = None):
    """Get agent runs"""
    return {
        "agent_runs": [
            {
                "id": 1,
                "project_id": 1,
                "target_text": "Create a new dashboard component",
                "planning_statement": "Focus on React best practices",
                "status": "completed",
                "run_type": "pr",
                "result": "Successfully created PR #15 with dashboard improvements",
                "error_message": None,
                "pr_number": 15,
                "pr_url": "https://github.com/Zeeeepa/CodegenCICD/pull/15",
                "validation_status": "completed",
                "auto_merge_enabled": False,
                "merge_completed": False,
                "started_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:05:00Z"
            }
        ]
    }

@app.get("/api/github-repos")
async def get_github_repos():
    """Get available GitHub repositories"""
    return {
        "repositories": [
            {
                "id": 1,
                "name": "CodegenCICD",
                "full_name": "Zeeeepa/CodegenCICD",
                "owner": {"login": "Zeeeepa"},
                "description": "AI-powered CI/CD dashboard",
                "private": False,
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": 2,
                "name": "grainchain",
                "full_name": "Zeeeepa/grainchain",
                "owner": {"login": "Zeeeepa"},
                "description": "Langchain for sandboxes",
                "private": False,
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]
    }

# Serve static files (for the React frontend)
frontend_dir = Path(__file__).parent.parent / "frontend" / "build"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")
    
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve the React frontend"""
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            with open(index_file, "r") as f:
                return HTMLResponse(content=f.read())
        return {"message": "Frontend not built yet. Run 'npm run build' in the frontend directory."}

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Start the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
