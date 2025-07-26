"""
Main API router that combines all endpoint routers
"""

from fastapi import APIRouter
from backend.routers import projects, agent_runs, configurations, webhooks

# Create main API router
api_router = APIRouter()

# Include all routers with their prefixes
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"]
)

api_router.include_router(
    agent_runs.router,
    prefix="/agent-runs",
    tags=["agent-runs"]
)

api_router.include_router(
    configurations.router,
    prefix="/configurations",
    tags=["configurations"]
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"]
)
