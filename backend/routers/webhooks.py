"""
GitHub webhook handling API endpoints
"""
import structlog
import hmac
import hashlib
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.project import Project
from backend.models.webhook_event import WebhookEvent
from backend.services.validation_service import ValidationService
from backend.websocket.connection_manager import ConnectionManager
from backend.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
connection_manager = ConnectionManager()
settings = get_settings()


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature.startswith('sha256='):
        return False
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f'sha256={expected_signature}', signature)


async def process_pr_webhook(webhook_event_id: str, db: AsyncSession):
    """Background task to process PR webhook events"""
    try:
        # Get webhook event
        result = await db.execute(select(WebhookEvent).where(WebhookEvent.id == webhook_event_id))
        webhook_event = result.scalar_one_or_none()
        
        if not webhook_event:
            logger.error("Webhook event not found", webhook_event_id=webhook_event_id)
            return
        
        payload = webhook_event.payload
        action = payload.get('action')
        pr_data = payload.get('pull_request', {})
        
        # Only process opened/synchronize events
        if action not in ['opened', 'synchronize']:
            logger.info("Ignoring PR webhook action", action=action, webhook_event_id=webhook_event_id)
            return
        
        # Get project
        repo_url = payload.get('repository', {}).get('html_url')
        if not repo_url:
            logger.error("No repository URL in webhook", webhook_event_id=webhook_event_id)
            return
        
        project_result = await db.execute(
            select(Project).where(Project.repository_url == repo_url)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            logger.error("Project not found for repository", repo_url=repo_url)
            return
        
        # Extract PR information
        pr_number = pr_data.get('number')
        pr_url = pr_data.get('html_url')
        branch_name = pr_data.get('head', {}).get('ref')
        
        logger.info("Processing PR webhook", 
                   project_id=project.id, 
                   pr_number=pr_number, 
                   action=action)
        
        # Broadcast PR event
        await connection_manager.broadcast_to_subscribers(
            f"project_{project.id}",
            {
                "type": "pr_webhook",
                "project_id": project.id,
                "pr_number": pr_number,
                "pr_url": pr_url,
                "action": action,
                "branch_name": branch_name
            }
        )
        
        # Start validation pipeline if this is a new PR or update
        validation_service = ValidationService()
        
        validation_result = await validation_service.start_validation_pipeline(
            project_id=project.id,
            pr_url=pr_url,
            branch_name=branch_name,
            pr_number=pr_number
        )
        
        logger.info("Validation pipeline started", 
                   project_id=project.id, 
                   validation_id=validation_result.get('validation_id'))
        
    except Exception as e:
        logger.error("Failed to process PR webhook", 
                    webhook_event_id=webhook_event_id, 
                    error=str(e))


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub webhook events"""
    try:
        # Get headers
        signature = request.headers.get('X-Hub-Signature-256')
        event_type = request.headers.get('X-GitHub-Event')
        delivery_id = request.headers.get('X-GitHub-Delivery')
        
        if not signature or not event_type:
            raise HTTPException(status_code=400, detail="Missing required headers")
        
        # Get payload
        payload_bytes = await request.body()
        
        # Verify signature (using GitHub token as secret for now)
        # In production, use a dedicated webhook secret
        if not verify_github_signature(payload_bytes, signature, settings.github_token):
            logger.warning("Invalid webhook signature", delivery_id=delivery_id)
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        logger.info("Received GitHub webhook", 
                   event_type=event_type, 
                   delivery_id=delivery_id)
        
        # Store webhook event
        webhook_event = WebhookEvent(
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload,
            signature=signature
        )
        
        db.add(webhook_event)
        await db.commit()
        await db.refresh(webhook_event)
        
        # Process specific event types
        if event_type == 'pull_request':
            background_tasks.add_task(process_pr_webhook, webhook_event.id, db)
        
        return {"message": "Webhook received", "event_id": webhook_event.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process webhook", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.get("/events")
async def list_webhook_events(
    event_type: str = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List webhook events"""
    try:
        query = select(WebhookEvent).offset(skip).limit(limit).order_by(WebhookEvent.created_at.desc())
        
        if event_type:
            query = query.where(WebhookEvent.event_type == event_type)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "delivery_id": event.delivery_id,
                "created_at": event.created_at.isoformat(),
                "payload_summary": {
                    "action": event.payload.get("action"),
                    "repository": event.payload.get("repository", {}).get("name"),
                    "sender": event.payload.get("sender", {}).get("login")
                }
            }
            for event in events
        ]
        
    except Exception as e:
        logger.error("Failed to list webhook events", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook events")


@router.get("/events/{event_id}")
async def get_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific webhook event"""
    try:
        result = await db.execute(select(WebhookEvent).where(WebhookEvent.id == event_id))
        event = result.scalar_one_or_none()
        
        if not event:
            raise HTTPException(status_code=404, detail="Webhook event not found")
        
        return {
            "id": event.id,
            "event_type": event.event_type,
            "delivery_id": event.delivery_id,
            "signature": event.signature,
            "payload": event.payload,
            "created_at": event.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get webhook event", event_id=event_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook event")

