"""
Main FastAPI application entry point
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Import routers
from routers.service_validation import router as service_validation_router

# Create FastAPI app
app = FastAPI(
    title="CodegenCICD Dashboard",
    description="AI-powered CI/CD dashboard with validation pipeline",
    version="1.0.0"
)

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

# Basic health check endpoint
@app.get("/")
async def root():
    return {"message": "CodegenCICD Dashboard API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "codegencd-api"}

# Mock endpoints for the UI
@app.get("/api/projects")
async def get_projects():
    """Get all projects"""
    return {
        "projects": [
            {
                "id": 1,
                "name": "Sample Project",
                "github_owner": "Zeeeepa",
                "github_repo": "CodegenCICD",
                "status": "active",
                "webhook_url": "https://webhook-gateway.pixeliumperfecto.workers.dev/webhook/Zeeeepa/CodegenCICD",
                "auto_merge_enabled": False,
                "auto_confirm_plans": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]
    }

@app.post("/api/projects")
async def create_project(project_data: dict):
    """Create a new project"""
    return {
        "id": 2,
        "name": project_data.get("name", "New Project"),
        "github_owner": project_data.get("github_owner", ""),
        "github_repo": project_data.get("github_repo", ""),
        "status": "active",
        "webhook_url": f"https://webhook-gateway.pixeliumperfecto.workers.dev/webhook/{project_data.get('github_owner', '')}/{project_data.get('github_repo', '')}",
        "auto_merge_enabled": project_data.get("auto_merge_enabled", False),
        "auto_confirm_plans": project_data.get("auto_confirm_plans", False),
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }

@app.get("/api/projects/{project_id}/configuration")
async def get_project_configuration(project_id: int):
    """Get project configuration"""
    return {
        "id": 1,
        "project_id": project_id,
        "repository_rules": "Follow TypeScript best practices and use Material-UI components.",
        "setup_commands": "cd frontend\nnpm install\nnpm run build\nnpm start",
        "planning_statement": "You are working on a React TypeScript project with Material-UI. Focus on clean, maintainable code.",
        "branch_name": "main",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }

@app.put("/api/projects/{project_id}/configuration")
async def update_project_configuration(project_id: int, config_data: dict):
    """Update project configuration"""
    return {
        "id": 1,
        "project_id": project_id,
        "repository_rules": config_data.get("repository_rules", ""),
        "setup_commands": config_data.get("setup_commands", ""),
        "planning_statement": config_data.get("planning_statement", ""),
        "branch_name": config_data.get("branch_name", "main"),
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }

@app.get("/api/projects/{project_id}/secrets")
async def get_project_secrets(project_id: int):
    """Get project secrets"""
    return {
        "secrets": [
            {
                "id": 1,
                "project_id": project_id,
                "key": "CODEGEN_API_TOKEN",
                "value": "sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99",
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": 2,
                "project_id": project_id,
                "key": "GITHUB_TOKEN",
                "value": "your_github_token_here",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
    }

@app.post("/api/projects/{project_id}/secrets")
async def create_project_secret(project_id: int, secret_data: dict):
    """Create a new project secret"""
    return {
        "id": 3,
        "project_id": project_id,
        "key": secret_data.get("key", ""),
        "value": secret_data.get("value", ""),
        "created_at": "2024-01-01T00:00:00Z"
    }

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
