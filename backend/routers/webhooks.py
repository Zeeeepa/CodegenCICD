"""
Webhooks router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from typing import Dict, Any
import structlog
import hmac
import hashlib

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """Handle GitHub webhook events"""
    try:
        # Get request body and headers
        body = await request.body()
        headers = request.headers
        
        # Verify webhook signature if secret is configured
        signature = headers.get("x-hub-signature-256")
        if signature and hasattr(settings, 'github_webhook_secret') and settings.github_webhook_secret:
            expected_signature = _calculate_signature(body, settings.github_webhook_secret)
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Invalid GitHub webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON payload
        import json
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Get event type
        event_type = headers.get("x-github-event")
        if not event_type:
            raise HTTPException(status_code=400, detail="Missing event type header")
        
        # Log webhook event
        logger.info("Received GitHub webhook",
                   event_type=event_type,
                   repository=payload.get("repository", {}).get("full_name"),
                   action=payload.get("action"))
        
        # Process webhook in background
        background_tasks.add_task(
            _process_github_webhook,
            event_type,
            payload
        )
        
        return {"status": "received"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process GitHub webhook", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.post("/test")
async def test_webhook(payload: Dict[str, Any]) -> Dict[str, str]:
    """Test webhook endpoint for development"""
    try:
        logger.info("Received test webhook", payload=payload)
        return {"status": "test webhook received", "payload": payload}
    except Exception as e:
        logger.error("Failed to process test webhook", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process test webhook")


def _calculate_signature(body: bytes, secret: str) -> str:
    """Calculate GitHub webhook signature"""
    signature = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


async def _process_github_webhook(event_type: str, payload: Dict[str, Any]) -> None:
    """Process GitHub webhook event in background"""
    try:
        if event_type == "pull_request":
            await _handle_pull_request_event(payload)
        elif event_type == "push":
            await _handle_push_event(payload)
        elif event_type == "issues":
            await _handle_issues_event(payload)
        else:
            logger.info("Unhandled GitHub webhook event type", event_type=event_type)
    
    except Exception as e:
        logger.error("Failed to process GitHub webhook event",
                    event_type=event_type,
                    error=str(e))


async def _handle_pull_request_event(payload: Dict[str, Any]) -> None:
    """Handle pull request webhook events"""
    try:
        action = payload.get("action")
        pr_data = payload.get("pull_request", {})
        repository = payload.get("repository", {})
        
        pr_number = pr_data.get("number")
        pr_url = pr_data.get("html_url")
        repo_full_name = repository.get("full_name")
        
        logger.info("Processing pull request event",
                   action=action,
                   pr_number=pr_number,
                   repository=repo_full_name)
        
        if action == "opened":
            # Handle new PR - trigger validation pipeline
            await _trigger_validation_pipeline(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                pr_url=pr_url,
                pr_branch=pr_data.get("head", {}).get("ref"),
                pr_commit_sha=pr_data.get("head", {}).get("sha")
            )
        
        elif action == "synchronize":
            # Handle PR update - re-trigger validation if needed
            logger.info("PR synchronized, considering re-validation",
                       pr_number=pr_number,
                       repository=repo_full_name)
        
        elif action == "closed":
            if pr_data.get("merged"):
                logger.info("PR merged",
                           pr_number=pr_number,
                           repository=repo_full_name)
            else:
                logger.info("PR closed without merge",
                           pr_number=pr_number,
                           repository=repo_full_name)
    
    except Exception as e:
        logger.error("Failed to handle pull request event", error=str(e))


async def _handle_push_event(payload: Dict[str, Any]) -> None:
    """Handle push webhook events"""
    try:
        repository = payload.get("repository", {})
        ref = payload.get("ref")
        commits = payload.get("commits", [])
        
        repo_full_name = repository.get("full_name")
        branch = ref.replace("refs/heads/", "") if ref else "unknown"
        
        logger.info("Processing push event",
                   repository=repo_full_name,
                   branch=branch,
                   commit_count=len(commits))
        
        # Handle push to main/default branch
        if branch in ["main", "master", repository.get("default_branch")]:
            logger.info("Push to default branch detected",
                       repository=repo_full_name,
                       branch=branch)
    
    except Exception as e:
        logger.error("Failed to handle push event", error=str(e))


async def _handle_issues_event(payload: Dict[str, Any]) -> None:
    """Handle issues webhook events"""
    try:
        action = payload.get("action")
        issue_data = payload.get("issue", {})
        repository = payload.get("repository", {})
        
        issue_number = issue_data.get("number")
        repo_full_name = repository.get("full_name")
        
        logger.info("Processing issues event",
                   action=action,
                   issue_number=issue_number,
                   repository=repo_full_name)
    
    except Exception as e:
        logger.error("Failed to handle issues event", error=str(e))


async def _trigger_validation_pipeline(repo_full_name: str,
                                     pr_number: int,
                                     pr_url: str,
                                     pr_branch: str,
                                     pr_commit_sha: str) -> None:
    """Trigger validation pipeline for a new PR"""
    try:
        # TODO: Implement validation pipeline trigger
        # This will be implemented in the validation service
        
        logger.info("Validation pipeline triggered",
                   repository=repo_full_name,
                   pr_number=pr_number,
                   pr_branch=pr_branch,
                   pr_commit_sha=pr_commit_sha)
        
        # For now, just log the trigger
        # In the full implementation, this would:
        # 1. Find the project in database by repo name
        # 2. Create a ValidationRun record
        # 3. Start the 7-step validation process
        # 4. Send real-time updates via WebSocket
        
    except Exception as e:
        logger.error("Failed to trigger validation pipeline",
                    repository=repo_full_name,
                    pr_number=pr_number,
                    error=str(e))

