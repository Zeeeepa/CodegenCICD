"""
GitHub API client for repository management and PR operations
"""
import httpx
import structlog
from typing import Dict, Any, Optional, List
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.token = settings.github_token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodegenCICD/1.0.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to GitHub API"""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "GitHub API HTTP error",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                    endpoint=endpoint
                )
                raise
            except Exception as e:
                logger.error("GitHub API request failed", error=str(e), endpoint=endpoint)
                raise
    
    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        try:
            response = await self._make_request("GET", f"/repos/{owner}/{repo}")
            return response
        except Exception as e:
            logger.error("Failed to get repository", owner=owner, repo=repo, error=str(e))
            raise
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request information"""
        try:
            response = await self._make_request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
            return response
        except Exception as e:
            logger.error("Failed to get pull request", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def create_webhook(self, owner: str, repo: str, webhook_url: str, 
                           secret: str = None, events: List[str] = None) -> Dict[str, Any]:
        """Create a webhook for the repository"""
        if events is None:
            events = ["push", "pull_request", "issues"]
        
        payload = {
            "name": "web",
            "active": True,
            "events": events,
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0"
            }
        }
        
        if secret:
            payload["config"]["secret"] = secret
        
        try:
            response = await self._make_request("POST", f"/repos/{owner}/{repo}/hooks", json=payload)
            logger.info("Webhook created", owner=owner, repo=repo, webhook_id=response.get("id"))
            return response
        except Exception as e:
            logger.error("Failed to create webhook", owner=owner, repo=repo, error=str(e))
            raise
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: int) -> bool:
        """Delete a webhook"""
        try:
            await self._make_request("DELETE", f"/repos/{owner}/{repo}/hooks/{webhook_id}")
            logger.info("Webhook deleted", owner=owner, repo=repo, webhook_id=webhook_id)
            return True
        except Exception as e:
            logger.error("Failed to delete webhook", owner=owner, repo=repo, webhook_id=webhook_id, error=str(e))
            return False
    
    async def merge_pull_request(self, owner: str, repo: str, pr_number: int, 
                                commit_title: str = None, commit_message: str = None,
                                merge_method: str = "merge") -> Dict[str, Any]:
        """Merge a pull request"""
        payload = {
            "merge_method": merge_method
        }
        
        if commit_title:
            payload["commit_title"] = commit_title
        if commit_message:
            payload["commit_message"] = commit_message
        
        try:
            response = await self._make_request("PUT", f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", json=payload)
            logger.info("Pull request merged", owner=owner, repo=repo, pr_number=pr_number)
            return response
        except Exception as e:
            logger.error("Failed to merge pull request", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get files changed in a pull request"""
        try:
            response = await self._make_request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}/files")
            return response
        except Exception as e:
            logger.error("Failed to get PR files", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            return []
    
    async def create_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
        """Create a comment on a pull request"""
        payload = {"body": body}
        
        try:
            response = await self._make_request("POST", f"/repos/{owner}/{repo}/issues/{pr_number}/comments", json=payload)
            logger.info("PR comment created", owner=owner, repo=repo, pr_number=pr_number)
            return response
        except Exception as e:
            logger.error("Failed to create PR comment", owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def get_commit(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        """Get commit information"""
        try:
            response = await self._make_request("GET", f"/repos/{owner}/{repo}/commits/{sha}")
            return response
        except Exception as e:
            logger.error("Failed to get commit", owner=owner, repo=repo, sha=sha, error=str(e))
            raise
    
    async def get_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get repository branches"""
        try:
            response = await self._make_request("GET", f"/repos/{owner}/{repo}/branches")
            return response
        except Exception as e:
            logger.error("Failed to get branches", owner=owner, repo=repo, error=str(e))
            return []
    
    async def health_check(self) -> bool:
        """Check if GitHub API is accessible"""
        try:
            await self._make_request("GET", "/user")
            return True
        except Exception as e:
            logger.error("GitHub API health check failed", error=str(e))
            return False

