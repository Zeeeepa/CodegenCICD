"""
CodegenCICD Dashboard - Main FastAPI Application
"""
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from backend.config import get_settings
from backend.database import init_db, close_db, get_db
from backend.websocket.connection_manager import ConnectionManager

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
settings = get_settings()

# Global connection manager for WebSocket connections
connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting CodegenCICD Dashboard...")
    await init_db()
    logger.info("🚀 CodegenCICD Dashboard started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CodegenCICD Dashboard...")
    await close_db()
    logger.info("👋 CodegenCICD Dashboard shut down gracefully")


# Create FastAPI application
app = FastAPI(
    title="CodegenCICD Dashboard",
    description="AI-powered CI/CD dashboard with Codegen integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket endpoint for real-time communication
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await connection_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await connection_manager.handle_message(client_id, message)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from client", client_id=client_id, data=data)
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, client_id)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", client_id=client_id)
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e))
    finally:
        connection_manager.disconnect(client_id)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CodegenCICD Dashboard",
        "version": "1.0.0",
        "environment": settings.environment
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "CodegenCICD Dashboard API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "websocket": "/ws/{client_id}",
        "health": "/health"
    }


# WebSocket stats endpoint (for monitoring)
@app.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    if not settings.debug:
        return {"error": "Stats only available in debug mode"}
    
    return connection_manager.get_connection_stats()


# Include API routers (will be added in next phase)
# from backend.routers import projects, agent_runs, configurations, webhooks
# app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
# app.include_router(agent_runs.router, prefix="/api/v1/agent-runs", tags=["agent-runs"])
# app.include_router(configurations.router, prefix="/api/v1/configurations", tags=["configurations"])
# app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

