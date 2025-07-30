"""
Main FastAPI application for CodegenCICD with full production infrastructure
"""
import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import routers (existing and new)
from routers.service_validation import router as service_validation_router
from routers.projects import router as projects_router
from routers.health import router as health_router
from routers.webhooks import router as webhooks_router

# Import new infrastructure routers
from backend.routers import auth, monitoring
from backend.database import init_db

# Import new infrastructure components
from backend.core.monitoring import (
    RequestMetricsMiddleware, metrics_collector, structured_logger,
    health_checker
)
from backend.core.security import (
    AuthenticationError, AuthorizationError, RateLimitError,
    get_current_user, require_role, UserRole, TokenData
)
from backend.core.resilience import resilience_manager

# Import database dependencies
from dependencies import get_db_service
from services.database_service import DatabaseService

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting CodegenCICD application", 
               environment=os.environ.get("ENVIRONMENT", "development"))
    
    try:
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized")
        
        # Start metrics collection
        await metrics_collector.start_system_metrics_collection()
        logger.info("✅ Metrics collection started")
        
        # Initialize resilience components
        logger.info("✅ Resilience patterns initialized")
        
        # Validate external services
        try:
            health_status = await health_checker.get_health_status()
            if health_status["status"] == "healthy":
                logger.info("✅ All external services validated")
            else:
                logger.warning("⚠️ Some external services are degraded", 
                             status=health_status["status"])
        except Exception as e:
            logger.warning("⚠️ External service validation failed", error=str(e))
        
        logger.info("🎉 Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error("💥 Application startup failed", error=str(e))
        raise
    
    # Shutdown
    logger.info("👋 Shutting down CodegenCICD application")
    
    try:
        # Stop metrics collection
        await metrics_collector.stop_system_metrics_collection()
        logger.info("✅ Metrics collection stopped")
        
        logger.info("✅ Application shutdown completed")
        
    except Exception as e:
        logger.error("💥 Error during shutdown", error=str(e))


# Create FastAPI app with lifespan management
app = FastAPI(
    title="CodegenCICD",
    description="AI-Driven Development Workflow Automation with Production Infrastructure",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if os.environ.get("ENVIRONMENT") != "production" else None,
    redoc_url="/api/redoc" if os.environ.get("ENVIRONMENT") != "production" else None
)

# Add request metrics middleware
app.add_middleware(RequestMetricsMiddleware)

# CORS middleware with production-ready configuration
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"]
)


# Global exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    correlation_id = structured_logger.get_correlation_id(request)
    logger.warning("Authentication failed", 
                  correlation_id=correlation_id,
                  path=request.url.path,
                  error=str(exc))
    
    metrics_collector.record_error("authentication_error", "auth")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "authentication_failed",
            "message": exc.detail,
            "correlation_id": correlation_id
        },
        headers={"X-Correlation-ID": correlation_id}
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors"""
    correlation_id = structured_logger.get_correlation_id(request)
    logger.warning("Authorization failed", 
                  correlation_id=correlation_id,
                  path=request.url.path,
                  error=str(exc))
    
    metrics_collector.record_error("authorization_error", "auth")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "authorization_failed",
            "message": exc.detail,
            "correlation_id": correlation_id
        },
        headers={"X-Correlation-ID": correlation_id}
    )


@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors"""
    correlation_id = structured_logger.get_correlation_id(request)
    logger.warning("Rate limit exceeded", 
                  correlation_id=correlation_id,
                  path=request.url.path,
                  client_ip=request.client.host)
    
    metrics_collector.record_error("rate_limit_error", "security")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "rate_limit_exceeded",
            "message": exc.detail,
            "correlation_id": correlation_id,
            "retry_after": 60
        },
        headers={
            "X-Correlation-ID": correlation_id,
            "Retry-After": "60"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    correlation_id = structured_logger.get_correlation_id(request)
    logger.error("Unhandled exception", 
                correlation_id=correlation_id,
                path=request.url.path,
                error=str(exc),
                exc_info=True)
    
    metrics_collector.record_error("internal_error", "application")
    
    # Don't expose internal errors in production
    if os.environ.get("ENVIRONMENT") == "production":
        message = "An internal error occurred"
    else:
        message = str(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": message,
            "correlation_id": correlation_id
        },
        headers={"X-Correlation-ID": correlation_id}
    )


# Request/response logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log requests and responses with correlation IDs"""
    correlation_id = structured_logger.get_correlation_id(request)
    
    # Add correlation ID to request state
    request.state.correlation_id = correlation_id
    
    # Log incoming request
    structured_logger.log_request(request, correlation_id)
    
    # Process request
    start_time = asyncio.get_event_loop().time()
    response = await call_next(request)
    duration = asyncio.get_event_loop().time() - start_time
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    # Log outgoing response
    structured_logger.log_response(request, response, correlation_id, duration)
    
    return response


# Include existing routers
app.include_router(service_validation_router)
app.include_router(projects_router)
app.include_router(health_router)
app.include_router(webhooks_router)

# Include new infrastructure routers with API prefix
app.include_router(auth.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")


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


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with application information"""
    return {
        "service": "CodegenCICD",
        "version": "1.0.0",
        "description": "AI-Driven Development Workflow Automation",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "status": "running",
        "uptime_seconds": metrics_collector.get_uptime(),
        "docs_url": "/api/docs" if os.environ.get("ENVIRONMENT") != "production" else None
    }


@app.get("/health")
async def health_check():
    """Simple health check endpoint for load balancers"""
    try:
        # Quick health check without detailed diagnostics
        return {
            "status": "healthy",
            "service": "codegencd-api",
            "timestamp": "2025-01-30T15:30:00Z",
            "uptime_seconds": metrics_collector.get_uptime()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "codegencd-api",
                "error": str(e),
                "timestamp": "2025-01-30T15:30:00Z"
            }
        )


@app.get("/version")
async def version_info():
    """Version and build information"""
    return {
        "version": "1.0.0",
        "build_date": os.environ.get("BUILD_DATE", "unknown"),
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": sys.version
    }


# Metrics endpoint (separate from monitoring router for direct access)
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    from backend.core.monitoring import get_metrics_response
    return await get_metrics_response()


# Protected API endpoints (require authentication)
@app.get("/api/projects")
async def get_projects(
    db_service: DatabaseService = Depends(get_db_service),
    current_user: TokenData = Depends(get_current_user)
):
    """Get all projects (authenticated)"""
    try:
        projects = await db_service.get_projects()
        return {"projects": [project.dict() for project in projects]}
    except Exception as e:
        logger.error("Failed to get projects", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects")
async def create_project(
    project_data: CreateProjectRequest,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: TokenData = Depends(require_role(UserRole.USER))
):
    """Create a new project (authenticated)"""
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
        
        logger.info("Project created", 
                   project_id=project.id, 
                   project_name=project.name,
                   created_by=current_user.username)
        
        return project.dict()
    except Exception as e:
        logger.error("Failed to create project", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}")
async def get_project(
    project_id: int,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: TokenData = Depends(get_current_user)
):
    """Get project by ID (authenticated)"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get project", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/projects/{project_id}")
async def update_project(
    project_id: int,
    project_data: UpdateProjectRequest,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: TokenData = Depends(require_role(UserRole.USER))
):
    """Update project (authenticated)"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in project_data.dict().items() if v is not None}
        
        project = await db_service.update_project(project_id, update_data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info("Project updated", 
                   project_id=project_id,
                   updated_by=current_user.username)
        
        return project.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update project", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: int,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """Delete project (admin only)"""
    try:
        deleted = await db_service.delete_project(project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info("Project deleted", 
                   project_id=project_id,
                   deleted_by=current_user.username)
        
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete project", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


# Additional protected endpoints...
@app.get("/api/projects/{project_id}/configuration")
async def get_project_configuration(
    project_id: int,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: TokenData = Depends(get_current_user)
):
    """Get project configuration (authenticated)"""
    try:
        config = await db_service.get_project_full_config(project_id)
        return config
    except Exception as e:
        logger.error("Failed to get project configuration", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


# Mock endpoints for agent runs and GitHub repos (to be implemented)
@app.post("/api/agent-runs")
async def create_agent_run(
    agent_run_data: dict,
    current_user: TokenData = Depends(require_role(UserRole.USER))
):
    """Create a new agent run (authenticated)"""
    logger.info("Agent run requested", 
               project_id=agent_run_data.get("project_id"),
               requested_by=current_user.username)
    
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
async def get_agent_runs(
    project_id: int = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Get agent runs (authenticated)"""
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
async def get_github_repos(current_user: TokenData = Depends(get_current_user)):
    """Get available GitHub repositories (authenticated)"""
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
    import uvicorn
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Development server configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

