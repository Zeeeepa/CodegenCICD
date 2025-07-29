"""
Webhook service for GitHub integration and Cloudflare worker management
"""
import asyncio
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

from backend.integrations.github_client import GitHubClient
from backend.integrations.cloudflare_client import CloudflareClient
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebhookService:
    """Service for managing webhooks and processing webhook events"""
    
    def __init__(self):
        self.github_client = GitHubClient()
        self.cloudflare_client = CloudflareClient()
    
    async def setup_github_webhook(self, owner: str, repo: str, webhook_url: str) -> Optional[str]:
        """Set up GitHub webhook for a repository"""
        try:
            webhook_config = {
                "name": "web",
                "active": True,
                "events": [
                    "pull_request",
                    "pull_request_review",
                    "push",
                    "issues",
                    "issue_comment"
                ],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                }
            }
            
            # Add secret if configured
            if settings.github_webhook_secret:
                webhook_config["config"]["secret"] = settings.github_webhook_secret
            
            webhook = await self.github_client.create_webhook(owner, repo, webhook_config)
            
            logger.info("GitHub webhook created", 
                       owner=owner, 
                       repo=repo, 
                       webhook_id=webhook.get("id"),
                       webhook_url=webhook_url)
            
            return webhook.get("url")
            
        except Exception as e:
            logger.error("Failed to create GitHub webhook", 
                        owner=owner, 
                        repo=repo, 
                        error=str(e))
            return None
    
    async def remove_github_webhook(self, owner: str, repo: str, webhook_id: int) -> bool:
        """Remove GitHub webhook from a repository"""
        try:
            await self.github_client.delete_webhook(owner, repo, webhook_id)
            logger.info("GitHub webhook removed", owner=owner, repo=repo, webhook_id=webhook_id)
            return True
        except Exception as e:
            logger.error("Failed to remove GitHub webhook", 
                        owner=owner, 
                        repo=repo, 
                        webhook_id=webhook_id,
                        error=str(e))
            return False
    
    def verify_github_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature"""
        if not secret:
            return True  # Skip verification if no secret configured
        
        try:
            expected_signature = "sha256=" + hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error("Failed to verify GitHub signature", error=str(e))
            return False
    
    async def process_github_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Process incoming GitHub webhook"""
        try:
            event_type = headers.get("x-github-event", "unknown")
            delivery_id = headers.get("x-github-delivery", "unknown")
            
            logger.info("Processing GitHub webhook", 
                       event_type=event_type, 
                       delivery_id=delivery_id)
            
            # Verify signature if secret is configured
            if settings.github_webhook_secret:
                signature = headers.get("x-hub-signature-256", "")
                payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
                
                if not self.verify_github_signature(payload_bytes, signature, settings.github_webhook_secret):
                    logger.warning("Invalid GitHub webhook signature", delivery_id=delivery_id)
                    return {"status": "error", "message": "Invalid signature"}
            
            # Process different event types
            if event_type == "pull_request":
                return await self.process_pull_request_event(payload)
            elif event_type == "pull_request_review":
                return await self.process_pull_request_review_event(payload)
            elif event_type == "push":
                return await self.process_push_event(payload)
            elif event_type == "issues":
                return await self.process_issues_event(payload)
            elif event_type == "issue_comment":
                return await self.process_issue_comment_event(payload)
            else:
                logger.info("Unhandled GitHub event type", event_type=event_type)
                return {"status": "ignored", "message": f"Event type {event_type} not handled"}
            
        except Exception as e:
            logger.error("Failed to process GitHub webhook", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def process_pull_request_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process pull request events"""
        try:
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            repository = payload.get("repository", {})
            
            pr_number = pr.get("number")
            pr_title = pr.get("title")
            pr_url = pr.get("html_url")
            repo_full_name = repository.get("full_name")
            
            logger.info("Processing PR event", 
                       action=action, 
                       pr_number=pr_number, 
                       repo=repo_full_name)
            
            # Handle different PR actions
            if action in ["opened", "synchronize", "reopened"]:
                # PR created or updated - trigger validation if needed
                await self.handle_pr_validation_trigger(repo_full_name, pr_number, pr_url)
            elif action == "closed":
                # PR closed - clean up validation resources
                await self.handle_pr_cleanup(repo_full_name, pr_number)
            
            # Notify frontend via WebSocket
            await self.notify_frontend({
                "type": "pull_request",
                "action": action,
                "repository": repo_full_name,
                "pr_number": pr_number,
                "pr_title": pr_title,
                "pr_url": pr_url,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {"status": "processed", "action": action, "pr_number": pr_number}
            
        except Exception as e:
            logger.error("Failed to process PR event", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def process_pull_request_review_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process pull request review events"""
        try:
            action = payload.get("action")
            review = payload.get("review", {})
            pr = payload.get("pull_request", {})
            repository = payload.get("repository", {})
            
            pr_number = pr.get("number")
            review_state = review.get("state")
            repo_full_name = repository.get("full_name")
            
            logger.info("Processing PR review event", 
                       action=action, 
                       pr_number=pr_number, 
                       review_state=review_state,
                       repo=repo_full_name)
            
            # Notify frontend
            await self.notify_frontend({
                "type": "pull_request_review",
                "action": action,
                "repository": repo_full_name,
                "pr_number": pr_number,
                "review_state": review_state,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {"status": "processed", "action": action, "pr_number": pr_number}
            
        except Exception as e:
            logger.error("Failed to process PR review event", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def process_push_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process push events"""
        try:
            ref = payload.get("ref", "")
            repository = payload.get("repository", {})
            commits = payload.get("commits", [])
            
            repo_full_name = repository.get("full_name")
            branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
            
            logger.info("Processing push event", 
                       repo=repo_full_name, 
                       branch=branch, 
                       commit_count=len(commits))
            
            # Notify frontend
            await self.notify_frontend({
                "type": "push",
                "repository": repo_full_name,
                "branch": branch,
                "commit_count": len(commits),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {"status": "processed", "branch": branch, "commits": len(commits)}
            
        except Exception as e:
            logger.error("Failed to process push event", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def process_issues_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process issues events"""
        try:
            action = payload.get("action")
            issue = payload.get("issue", {})
            repository = payload.get("repository", {})
            
            issue_number = issue.get("number")
            issue_title = issue.get("title")
            repo_full_name = repository.get("full_name")
            
            logger.info("Processing issue event", 
                       action=action, 
                       issue_number=issue_number, 
                       repo=repo_full_name)
            
            # Notify frontend
            await self.notify_frontend({
                "type": "issues",
                "action": action,
                "repository": repo_full_name,
                "issue_number": issue_number,
                "issue_title": issue_title,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {"status": "processed", "action": action, "issue_number": issue_number}
            
        except Exception as e:
            logger.error("Failed to process issue event", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def process_issue_comment_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process issue comment events"""
        try:
            action = payload.get("action")
            comment = payload.get("comment", {})
            issue = payload.get("issue", {})
            repository = payload.get("repository", {})
            
            issue_number = issue.get("number")
            comment_body = comment.get("body", "")[:100]  # Truncate for logging
            repo_full_name = repository.get("full_name")
            
            logger.info("Processing issue comment event", 
                       action=action, 
                       issue_number=issue_number, 
                       repo=repo_full_name)
            
            # Notify frontend
            await self.notify_frontend({
                "type": "issue_comment",
                "action": action,
                "repository": repo_full_name,
                "issue_number": issue_number,
                "comment_preview": comment_body,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {"status": "processed", "action": action, "issue_number": issue_number}
            
        except Exception as e:
            logger.error("Failed to process issue comment event", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def handle_pr_validation_trigger(self, repo_full_name: str, pr_number: int, pr_url: str):
        """Trigger PR validation flow"""
        try:
            # TODO: Implement validation flow trigger
            # This would check if the project has auto-validation enabled
            # and start the validation pipeline
            logger.info("PR validation trigger", repo=repo_full_name, pr_number=pr_number)
            
        except Exception as e:
            logger.error("Failed to trigger PR validation", 
                        repo=repo_full_name, 
                        pr_number=pr_number, 
                        error=str(e))
    
    async def handle_pr_cleanup(self, repo_full_name: str, pr_number: int):
        """Clean up resources when PR is closed"""
        try:
            # TODO: Implement cleanup logic
            # This would clean up validation snapshots, stop running processes, etc.
            logger.info("PR cleanup", repo=repo_full_name, pr_number=pr_number)
            
        except Exception as e:
            logger.error("Failed to clean up PR resources", 
                        repo=repo_full_name, 
                        pr_number=pr_number, 
                        error=str(e))
    
    async def notify_frontend(self, message: Dict[str, Any]):
        """Send notification to frontend via WebSocket"""
        try:
            # TODO: Implement WebSocket notification
            # This would send real-time updates to the frontend
            logger.info("Frontend notification", message_type=message.get("type"))
            
        except Exception as e:
            logger.error("Failed to notify frontend", error=str(e))
    
    async def setup_cloudflare_worker(self) -> bool:
        """Set up or update Cloudflare worker for webhook handling"""
        try:
            worker_script = self.generate_worker_script()
            
            success = await self.cloudflare_client.deploy_worker(
                settings.cloudflare_worker_name,
                worker_script
            )
            
            if success:
                logger.info("Cloudflare worker deployed successfully")
                return True
            else:
                logger.error("Failed to deploy Cloudflare worker")
                return False
                
        except Exception as e:
            logger.error("Failed to set up Cloudflare worker", error=str(e))
            return False
    
    def generate_worker_script(self) -> str:
        """Generate Cloudflare worker script for webhook handling"""
        return f"""
addEventListener('fetch', event => {{
  event.respondWith(handleRequest(event.request))
}})

async function handleRequest(request) {{
  // Only handle POST requests
  if (request.method !== 'POST') {{
    return new Response('Method not allowed', {{ status: 405 }})
  }}
  
  try {{
    // Get request headers and body
    const headers = Object.fromEntries(request.headers.entries())
    const body = await request.json()
    
    // Forward to backend
    const backendUrl = '{settings.backend_url}/api/webhooks/github'
    const response = await fetch(backendUrl, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'X-GitHub-Event': headers['x-github-event'] || '',
        'X-GitHub-Delivery': headers['x-github-delivery'] || '',
        'X-Hub-Signature-256': headers['x-hub-signature-256'] || ''
      }},
      body: JSON.stringify(body)
    }})
    
    const result = await response.json()
    
    return new Response(JSON.stringify(result), {{
      status: response.status,
      headers: {{ 'Content-Type': 'application/json' }}
    }})
    
  }} catch (error) {{
    console.error('Webhook processing error:', error)
    return new Response(JSON.stringify({{ 
      status: 'error', 
      message: error.message 
    }}), {{
      status: 500,
      headers: {{ 'Content-Type': 'application/json' }}
    }})
  }}
}}
"""

