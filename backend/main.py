"""
Main FastAPI application entry point
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

# Import routers
from routers.service_validation import router as service_validation_router
from routers.projects import router as projects_router
from routers.health import router as health_router
from routers.webhooks import router as webhooks_router

# Import database dependencies
from dependencies import get_db_service
from services.database_service import DatabaseService

# Create FastAPI app
app = FastAPI(
    title="CodegenCICD Dashboard",
    description="AI-powered CI/CD dashboard with validation pipeline",
    version="1.0.0"
)

# Include routers
app.include_router(service_validation_router)
app.include_router(projects_router)
app.include_router(health_router)
app.include_router(webhooks_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class CreateProjectRequest(BaseModel):
    name: str
    github_owner: str
    github_repo: str
    auto_merge_enabled: bool = False
    auto_confirm_plans: bool = False
    settings: Optional[Dict[str, Any]] = None
    secrets: Optional[List[Dict[str, str]]] = None

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    auto_merge_enabled: Optional[bool] = None
    auto_confirm_plans: Optional[bool] = None
    webhook_url: Optional[str] = None

class UpdateSettingsRequest(BaseModel):
    planning_statement: Optional[str] = None
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    branch_name: Optional[str] = None

class UpdateSecretsRequest(BaseModel):
    secrets: List[Dict[str, str]]

# Basic health check endpoint
@app.get("/")
async def root():
    return {"message": "CodegenCICD Dashboard API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "codegencd-api"}

# Real database endpoints
@app.get("/api/projects")
async def get_projects(db_service: DatabaseService = Depends(get_db_service)):
    """Get all projects"""
    try:
        projects = await db_service.get_projects()
        return {"projects": [project.dict() for project in projects]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(
    project_data: CreateProjectRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Create a new project"""
    try:
        # Prepare project data
        project_dict = {
            "name": project_data.name,
            "github_owner": project_data.github_owner,
            "github_repo": project_data.github_repo,
            "auto_merge_enabled": project_data.auto_merge_enabled,
            "auto_confirm_plans": project_data.auto_confirm_plans,
            "status": "active"
        }
        
        # Prepare settings data
        settings_dict = project_data.settings or {}
        if "branch_name" not in settings_dict:
            settings_dict["branch_name"] = "main"
        
        # Create project with settings
        project = await db_service.create_project_with_settings(project_dict, settings_dict)
        
        # Add secrets if provided
        if project_data.secrets:
            await db_service.update_project_secrets(project.id, project_data.secrets)
        
        return project.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}")
async def get_project(
    project_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get project by ID"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_id}")
async def update_project(
    project_id: int,
    project_data: UpdateProjectRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Update project"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in project_data.dict().items() if v is not None}
        
        project = await db_service.update_project(project_id, update_data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Delete project"""
    try:
        deleted = await db_service.delete_project(project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/configuration")
async def get_project_configuration(
    project_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get project configuration"""
    try:
        config = await db_service.get_project_full_config(project_id)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_id}/settings")
async def update_project_settings(
    project_id: int,
    settings_data: UpdateSettingsRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Update project settings"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in settings_data.dict().items() if v is not None}
        
        settings = await db_service.update_project_settings(project_id, update_data)
        if not settings:
            raise HTTPException(status_code=404, detail="Project not found")
        return settings.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_id}/secrets")
async def update_project_secrets(
    project_id: int,
    secrets_data: UpdateSecretsRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Update project secrets"""
    try:
        success = await db_service.update_project_secrets(project_id, secrets_data.secrets)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message": "Secrets updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
