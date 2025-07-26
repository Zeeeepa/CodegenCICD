"""
CodegenCICD Dashboard - Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from contextlib import asynccontextmanager

from backend.database import init_db
from backend.routers import projects, agent_runs, webhooks, configurations
from backend.websocket.connection_manager import ConnectionManager

# Global connection manager for WebSocket connections
connection_manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    print("🚀 CodegenCICD Dashboard started successfully!")
    yield
    # Shutdown
    print("👋 CodegenCICD Dashboard shutting down...")

# Create FastAPI application
app = FastAPI(
    title="CodegenCICD Dashboard",
    description="AI-powered CI/CD dashboard with Codegen integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(agent_runs.router, prefix="/api/v1/agent-runs", tags=["agent-runs"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(configurations.router, prefix="/api/v1/configurations", tags=["configurations"])

# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket, client_id: str):
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await connection_manager.send_personal_message(f"Echo: {data}", client_id)
    except Exception as e:
        print(f"WebSocket error for client {client_id}: {e}")
    finally:
        connection_manager.disconnect(client_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "CodegenCICD Dashboard"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "CodegenCICD Dashboard API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
