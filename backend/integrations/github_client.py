"""
GitHub API client for repository and PR management
"""
import asyncio
from typing import Optional, Dict, Any, List, Union
import httpx
from github import Github, GithubException
import structlog
from datetime import datetime

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        if not self.token:
            raise ValueError("GitHub token must be provided")
        
        # PyGithub client for complex operations
        self.github = Github(self.token)
        
        # HTTP client for direct API calls
        self.http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CodegenCICD/1.0.0"
            },
            timeout=httpx.Timeout(30.0)
        )
        
        self.base_url = "https://api.github.com"
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    # Repository operations
    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        try:
            response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get repository", owner=owner, repo=repo, 
                        status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Failed to get repository", owner=owner, repo=repo, error=str(e))
            raise
    
    async def list_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository branches"""
        try:
            response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}/branches")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to list branches", owner=owner, repo=repo, error=str(e))
            raise
    
    async def get_branch(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        """Get specific branch information"""
        try:
            response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}/branches/{branch}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get branch", owner=owner, repo=repo, branch=branch, error=str(e))
            raise
    
    # Pull Request operations
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request information"""
        try:
            response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get PR", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def list_pull_requests(self, owner: str, repo: str, state: str = "open",
                                base: Optional[str] = None, head: Optional[str] = None) -> List[Dict[str, Any]]:
        """List pull requests"""
        try:
            params = {"state": state}
            if base:
                params["base"] = base
            if head:
                params["head"] = head
            
            response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}/pulls", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to list PRs", owner=owner, repo=repo, error=str(e))
            raise
    
    async def create_pull_request(self, owner: str, repo: str, title: str, body: str,
                                 head: str, base: str, draft: bool = False) -> Dict[str, Any]:
        """Create a new pull request"""
        try:
            payload = {
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft
            }
            
            response = await self.http_client.post(f"{self.base_url}/repos/{owner}/{repo}/pulls", json=payload)
            response.raise_for_status()
            
            pr_data = response.json()
            logger.info("Pull request created", owner=owner, repo=repo, pr_number=pr_data["number"])
            return pr_data
        except Exception as e:
            logger.error("Failed to create PR", owner=owner, repo=repo, error=str(e))
            raise
    
    async def update_pull_request(self, owner: str, repo: str, pr_number: int,
                                 title: Optional[str] = None, body: Optional[str] = None,
                                 state: Optional[str] = None) -> Dict[str, Any]:
        """Update pull request"""
        try:
            payload = {}
            if title:
                payload["title"] = title
            if body:
                payload["body"] = body
            if state:
                payload["state"] = state
            
            response = await self.http_client.patch(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}", 
                                                   json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to update PR", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def merge_pull_request(self, owner: str, repo: str, pr_number: int,
                                commit_title: Optional[str] = None, commit_message: Optional[str] = None,
                                merge_method: str = "merge") -> Dict[str, Any]:
        """Merge a pull request"""
        try:
            payload = {
                "merge_method": merge_method
            }
            if commit_title:
                payload["commit_title"] = commit_title
            if commit_message:
                payload["commit_message"] = commit_message
            
            response = await self.http_client.put(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                                                 json=payload)
            response.raise_for_status()
            
            merge_data = response.json()
            logger.info("Pull request merged", owner=owner, repo=repo, pr_number=pr_number)
            return merge_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 405:
                logger.warning("PR cannot be merged", owner=owner, repo=repo, pr_number=pr_number,
                              reason="Not mergeable or checks not passed")
            raise
        except Exception as e:
            logger.error("Failed to merge PR", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def get_pr_checks(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get PR check runs and status"""
        try:
            # Get PR to get the head SHA
            pr = await self.get_pull_request(owner, repo, pr_number)
            head_sha = pr["head"]["sha"]
            
            # Get check runs
            response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}/commits/{head_sha}/check-runs")
            response.raise_for_status()
            check_runs = response.json()
            
            # Get status checks
            status_response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}/commits/{head_sha}/status")
            status_response.raise_for_status()
            status_checks = status_response.json()
            
            return {
                "check_runs": check_runs,
                "status_checks": status_checks,
                "head_sha": head_sha
            }
        except Exception as e:
            logger.error("Failed to get PR checks", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def is_pr_mergeable(self, owner: str, repo: str, pr_number: int) -> bool:
        """Check if PR is mergeable"""
        try:
            pr = await self.get_pull_request(owner, repo, pr_number)
            checks = await self.get_pr_checks(owner, repo, pr_number)
            
            # Check basic mergeability
            if not pr.get("mergeable", False):
                return False
            
            # Check if PR is closed or merged
            if pr["state"] != "open":
                return False
            
            # Check status checks
            status_checks = checks["status_checks"]
            if status_checks["state"] not in ["success", "pending"]:
                return False
            
            # Check check runs
            check_runs = checks["check_runs"]["check_runs"]
            for check in check_runs:
                if check["status"] == "completed" and check["conclusion"] not in ["success", "neutral", "skipped"]:
                    return False
            
            return True
        except Exception as e:
            logger.error("Failed to check PR mergeability", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            return False
    
    # Comments and reviews
    async def create_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
        """Create a comment on a pull request"""
        try:
            payload = {"body": body}
            response = await self.http_client.post(f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                                                  json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to create PR comment", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def create_pr_review(self, owner: str, repo: str, pr_number: int, body: str,
                              event: str = "COMMENT") -> Dict[str, Any]:
        """Create a review on a pull request"""
        try:
            payload = {
                "body": body,
                "event": event  # APPROVE, REQUEST_CHANGES, COMMENT
            }
            response = await self.http_client.post(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                                                  json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to create PR review", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    # Webhook operations
    async def create_webhook(self, owner: str, repo: str, webhook_url: str,
                           events: List[str], secret: Optional[str] = None) -> Dict[str, Any]:
        """Create a webhook for the repository"""
        try:
            config = {
                "url": webhook_url,
                "content_type": "json"
            }
            if secret:
                config["secret"] = secret
            
            payload = {
                "name": "web",
                "active": True,
                "events": events,
                "config": config
            }
            
            response = await self.http_client.post(f"{self.base_url}/repos/{owner}/{repo}/hooks", json=payload)
            response.raise_for_status()
            
            webhook_data = response.json()
            logger.info("Webhook created", owner=owner, repo=repo, webhook_id=webhook_data["id"])
            return webhook_data
        except Exception as e:
            logger.error("Failed to create webhook", owner=owner, repo=repo, error=str(e))
            raise
    
    async def list_webhooks(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository webhooks"""
        try:
            response = await self.http_client.get(f"{self.base_url}/repos/{owner}/{repo}/hooks")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to list webhooks", owner=owner, repo=repo, error=str(e))
            raise
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: int) -> bool:
        """Delete a webhook"""
        try:
            response = await self.http_client.delete(f"{self.base_url}/repos/{owner}/{repo}/hooks/{webhook_id}")
            response.raise_for_status()
            logger.info("Webhook deleted", owner=owner, repo=repo, webhook_id=webhook_id)
            return True
        except Exception as e:
            logger.error("Failed to delete webhook", owner=owner, repo=repo, webhook_id=webhook_id, error=str(e))
            return False
    
    # Utility methods
    async def health_check(self) -> bool:
        """Check if GitHub API is accessible"""
        try:
            response = await self.http_client.get(f"{self.base_url}/user")
            return response.status_code == 200
        except Exception as e:
            logger.error("GitHub API health check failed", error=str(e))
            return False
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information"""
        try:
            response = await self.http_client.get(f"{self.base_url}/user")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get user info", error=str(e))
            raise
    
    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature"""
        import hmac
        import hashlib
        
        if not signature.startswith("sha256="):
            return False
        
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        received_signature = signature[7:]  # Remove 'sha256=' prefix
        return hmac.compare_digest(expected_signature, received_signature)


# Global client instance
_github_client: Optional[GitHubClient] = None


async def get_github_client() -> GitHubClient:
    """Get global GitHub client instance"""
    global _github_client
    if _github_client is None:
        _github_client = GitHubClient()
    return _github_client

