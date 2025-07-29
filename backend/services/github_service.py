"""
GitHub service for project management and webhook integration
"""
import os
import asyncio
import httpx
from typing import Dict, Any, List, Optional
import structlog
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GitHubService:
    """Service for GitHub API interactions"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodegenCICD/1.0"
        }
        
        # Cloudflare webhook URL from environment
        self.webhook_url = os.getenv("CLOUDFLARE_WORKER_URL", "https://webhook-gateway.pixeliumperfecto.workers.dev")
    
    async def get_user_repositories(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """Get all repositories for the authenticated user"""
        try:
            async with httpx.AsyncClient() as client:
                repositories = []
                page = 1
                
                while True:
                    response = await client.get(
                        f"{self.base_url}/user/repos",
                        headers=self.headers,
                        params={
                            "per_page": per_page,
                            "page": page,
                            "sort": "updated",
                            "direction": "desc"
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.error("Failed to fetch repositories", 
                                   status_code=response.status_code,
                                   response=response.text)
                        break
                    
                    repos = response.json()
                    if not repos:
                        break
                    
                    repositories.extend(repos)
                    page += 1
                    
                    # GitHub API pagination limit
                    if len(repos) < per_page:
                        break
                
                logger.info("Fetched user repositories", count=len(repositories))
                return repositories
                
        except Exception as e:
            logger.error("Error fetching user repositories", error=str(e))
            raise
    
    async def get_repository_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get all branches for a repository"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/branches",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error("Failed to fetch repository branches",
                               owner=owner, repo=repo,
                               status_code=response.status_code)
                    return []
                
                branches = response.json()
                logger.info("Fetched repository branches", 
                          owner=owner, repo=repo, count=len(branches))
                return branches
                
        except Exception as e:
            logger.error("Error fetching repository branches", 
                        owner=owner, repo=repo, error=str(e))
            return []
    
    async def set_repository_webhook(self, owner: str, repo: str, 
                                   webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Set webhook for a repository"""
        try:
            webhook_url = webhook_url or self.webhook_url
            
            # First, check if webhook already exists
            existing_webhook = await self.get_repository_webhook(owner, repo, webhook_url)
            if existing_webhook:
                logger.info("Webhook already exists", 
                          owner=owner, repo=repo, webhook_id=existing_webhook["id"])
                return existing_webhook
            
            # Create new webhook
            webhook_config = {
                "name": "web",
                "active": True,
                "events": [
                    "pull_request",
                    "push",
                    "pull_request_review",
                    "pull_request_review_comment"
                ],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks",
                    headers=self.headers,
                    json=webhook_config
                )
                
                if response.status_code == 201:
                    webhook = response.json()
                    logger.info("Webhook created successfully",
                              owner=owner, repo=repo, 
                              webhook_id=webhook["id"], url=webhook_url)
                    return webhook
                else:
                    logger.error("Failed to create webhook",
                               owner=owner, repo=repo,
                               status_code=response.status_code,
                               response=response.text)
                    raise Exception(f"Failed to create webhook: {response.status_code}")
                    
        except Exception as e:
            logger.error("Error setting repository webhook",
                        owner=owner, repo=repo, error=str(e))
            raise
    
    async def get_repository_webhook(self, owner: str, repo: str, 
                                   webhook_url: str) -> Optional[Dict[str, Any]]:
        """Check if webhook exists for repository"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    return None
                
                hooks = response.json()
                for hook in hooks:
                    if (hook.get("config", {}).get("url") == webhook_url and 
                        hook.get("active", False)):
                        return hook
                
                return None
                
        except Exception as e:
            logger.error("Error checking repository webhook",
                        owner=owner, repo=repo, error=str(e))
            return None
    
    async def remove_repository_webhook(self, owner: str, repo: str, 
                                      webhook_id: int) -> bool:
        """Remove webhook from repository"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks/{webhook_id}",
                    headers=self.headers
                )
                
                if response.status_code == 204:
                    logger.info("Webhook removed successfully",
                              owner=owner, repo=repo, webhook_id=webhook_id)
                    return True
                else:
                    logger.error("Failed to remove webhook",
                               owner=owner, repo=repo, webhook_id=webhook_id,
                               status_code=response.status_code)
                    return False
                    
        except Exception as e:
            logger.error("Error removing repository webhook",
                        owner=owner, repo=repo, webhook_id=webhook_id, error=str(e))
            return False
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get pull request details"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error("Failed to fetch pull request",
                               owner=owner, repo=repo, pr_number=pr_number,
                               status_code=response.status_code)
                    return None
                    
        except Exception as e:
            logger.error("Error fetching pull request",
                        owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            return None
    
    async def merge_pull_request(self, owner: str, repo: str, pr_number: int,
                               commit_title: Optional[str] = None,
                               commit_message: Optional[str] = None,
                               merge_method: str = "merge") -> Dict[str, Any]:
        """Merge a pull request"""
        try:
            merge_data = {
                "merge_method": merge_method  # merge, squash, or rebase
            }
            
            if commit_title:
                merge_data["commit_title"] = commit_title
            if commit_message:
                merge_data["commit_message"] = commit_message
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                    headers=self.headers,
                    json=merge_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Pull request merged successfully",
                              owner=owner, repo=repo, pr_number=pr_number,
                              sha=result.get("sha"))
                    return result
                else:
                    logger.error("Failed to merge pull request",
                               owner=owner, repo=repo, pr_number=pr_number,
                               status_code=response.status_code,
                               response=response.text)
                    raise Exception(f"Failed to merge PR: {response.status_code}")
                    
        except Exception as e:
            logger.error("Error merging pull request",
                        owner=owner, repo=repo, pr_number=pr_number, error=str(e))
            raise
    
    async def create_issue_comment(self, owner: str, repo: str, issue_number: int,
                                 comment: str) -> Dict[str, Any]:
        """Create a comment on an issue or pull request"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers=self.headers,
                    json={"body": comment}
                )
                
                if response.status_code == 201:
                    result = response.json()
                    logger.info("Comment created successfully",
                              owner=owner, repo=repo, issue_number=issue_number)
                    return result
                else:
                    logger.error("Failed to create comment",
                               owner=owner, repo=repo, issue_number=issue_number,
                               status_code=response.status_code)
                    raise Exception(f"Failed to create comment: {response.status_code}")
                    
        except Exception as e:
            logger.error("Error creating issue comment",
                        owner=owner, repo=repo, issue_number=issue_number, error=str(e))
            raise


# Global instance
github_service = GitHubService()

