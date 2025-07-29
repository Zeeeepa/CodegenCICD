"""
Webhook handling endpoints
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from typing import Dict, Any
import structlog
import json

from backend.services.webhook_service import WebhookService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/github")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle incoming GitHub webhook"""
    try:
        # Get headers
        headers = dict(request.headers)
        
        # Get payload
        payload_bytes = await request.body()
        payload = json.loads(payload_bytes.decode())
        
        logger.info("Received GitHub webhook", 
                   event_type=headers.get("x-github-event"),
                   delivery_id=headers.get("x-github-delivery"))
        
        # Process webhook in background
        webhook_service = WebhookService()
        result = await webhook_service.process_github_webhook(payload, headers)
        
        return result
        
    except Exception as e:
        logger.error("Failed to process GitHub webhook", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/setup")
async def setup_github_webhooks():
    """Set up GitHub webhooks for all active projects"""
    try:
        # TODO: Implement bulk webhook setup
        return {"message": "Webhook setup initiated"}
    except Exception as e:
        logger.error("Failed to set up webhooks", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cloudflare/deploy")
async def deploy_cloudflare_worker():
    """Deploy or update Cloudflare worker for webhook handling"""
    try:
        webhook_service = WebhookService()
        success = await webhook_service.setup_cloudflare_worker()
        
        if success:
            return {"message": "Cloudflare worker deployed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to deploy Cloudflare worker")
            
    except Exception as e:
        logger.error("Failed to deploy Cloudflare worker", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

