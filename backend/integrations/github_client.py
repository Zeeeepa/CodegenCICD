"""
GitHub API client for CodegenCICD Dashboard
"""
from typing import Dict, Any, Optional, List
import structlog

from .base_client import BaseClient, APIError
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GitHubClient(BaseClient):
    """Client for interacting with GitHub API"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        
        if not self.token:
            raise ValueError("GitHub token is required")
        
        super().__init__(
            service_name="github_api",
            base_url="https://api.github.com",
            api_key=self.token,
            timeout=30,
            max_retries=3
        )
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for GitHub API requests"""
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def _health_check_request(self) -> None:
        """Health check by getting user info"""
        await self.get("/user")
    
    # Repository Operations
    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        try:
            response = await self.get(f"/repos/{owner}/{repo}")
            return response
        except Exception as e:
            self.logger.error("Failed to get repository",
                            owner=owner,
                            repo=repo,
                            error=str(e))
            raise
    
    async def list_repositories(self, 
                               org: Optional[str] = None,
                               per_page: int = 30,
                               page: int = 1) -> List[Dict[str, Any]]:
        """List repositories for user or organization"""
        try:
            if org:
                endpoint = f"/orgs/{org}/repos"
            else:
                endpoint = "/user/repos"
            
            params = {
                "per_page": per_page,
                "page": page,
                "sort": "updated",
                "direction": "desc"
            }
            
            response = await self.get(endpoint, params=params)
            return response if isinstance(response, list) else []
            
        except Exception as e:
            self.logger.error("Failed to list repositories",
                            org=org,
                            error=str(e))
            raise
    
    async def get_repository_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get repository branches"""
        try:
            response = await self.get(f"/repos/{owner}/{repo}/branches")
            return response if isinstance(response, list) else []
        except Exception as e:
            self.logger.error("Failed to get repository branches",
                            owner=owner,
                            repo=repo,
                            error=str(e))
            raise
    
    async def get_default_branch(self, owner: str, repo: str) -> str:
        """Get repository default branch"""
        try:
            repo_data = await self.get_repository(owner, repo)
            return repo_data.get("default_branch", "main")
        except Exception as e:
            self.logger.error("Failed to get default branch",
                            owner=owner,
                            repo=repo,
                            error=str(e))
            raise
    
    # Pull Request Operations
    async def create_pull_request(self,
                                 owner: str,
                                 repo: str,
                                 title: str,
                                 body: str,
                                 head: str,
                                 base: str,
                                 draft: bool = False) -> Dict[str, Any]:
        """Create a pull request"""
        try:
            payload = {
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft
            }
            
            self.logger.info("Creating pull request",
                           owner=owner,
                           repo=repo,
                           title=title,
                           head=head,
                           base=base)
            
            response = await self.post(f"/repos/{owner}/{repo}/pulls", data=payload)
            
            self.logger.info("Pull request created successfully",
                           pr_number=response.get("number"),
                           pr_url=response.get("html_url"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create pull request",
                            owner=owner,
                            repo=repo,
                            title=title,
                            error=str(e))
            raise
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request details"""
        try:
            response = await self.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
            return response
        except Exception as e:
            self.logger.error("Failed to get pull request",
                            owner=owner,
                            repo=repo,
                            pr_number=pr_number,
                            error=str(e))
            raise
    
    async def list_pull_requests(self,
                                owner: str,
                                repo: str,
                                state: str = "open",
                                per_page: int = 30,
                                page: int = 1) -> List[Dict[str, Any]]:
        """List pull requests"""
        try:
            params = {
                "state": state,
                "per_page": per_page,
                "page": page,
                "sort": "updated",
                "direction": "desc"
            }
            
            response = await self.get(f"/repos/{owner}/{repo}/pulls", params=params)
            return response if isinstance(response, list) else []
            
        except Exception as e:
            self.logger.error("Failed to list pull requests",
                            owner=owner,
                            repo=repo,
                            error=str(e))
            raise
    
    async def merge_pull_request(self,
                                owner: str,
                                repo: str,
                                pr_number: int,
                                commit_title: Optional[str] = None,
                                commit_message: Optional[str] = None,
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
            
            self.logger.info("Merging pull request",
                           owner=owner,
                           repo=repo,
                           pr_number=pr_number,
                           merge_method=merge_method)
            
            response = await self.put(f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", data=payload)
            
            self.logger.info("Pull request merged successfully",
                           pr_number=pr_number,
                           sha=response.get("sha"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to merge pull request",
                            owner=owner,
                            repo=repo,
                            pr_number=pr_number,
                            error=str(e))
            raise
    
    async def close_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Close a pull request"""
        try:
            payload = {"state": "closed"}
            
            response = await self.patch(f"/repos/{owner}/{repo}/pulls/{pr_number}", data=payload)
            
            self.logger.info("Pull request closed",
                           owner=owner,
                           repo=repo,
                           pr_number=pr_number)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to close pull request",
                            owner=owner,
                            repo=repo,
                            pr_number=pr_number,
                            error=str(e))
            raise
    
    # Issue Operations
    async def create_issue(self,
                          owner: str,
                          repo: str,
                          title: str,
                          body: str,
                          labels: Optional[List[str]] = None,
                          assignees: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create an issue"""
        try:
            payload = {
                "title": title,
                "body": body
            }
            
            if labels:
                payload["labels"] = labels
            if assignees:
                payload["assignees"] = assignees
            
            response = await self.post(f"/repos/{owner}/{repo}/issues", data=payload)
            
            self.logger.info("Issue created successfully",
                           issue_number=response.get("number"),
                           issue_url=response.get("html_url"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create issue",
                            owner=owner,
                            repo=repo,
                            title=title,
                            error=str(e))
            raise
    
    async def add_comment(self,
                         owner: str,
                         repo: str,
                         issue_number: int,
                         body: str) -> Dict[str, Any]:
        """Add comment to issue or pull request"""
        try:
            payload = {"body": body}
            
            response = await self.post(f"/repos/{owner}/{repo}/issues/{issue_number}/comments", data=payload)
            
            self.logger.info("Comment added successfully",
                           owner=owner,
                           repo=repo,
                           issue_number=issue_number)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to add comment",
                            owner=owner,
                            repo=repo,
                            issue_number=issue_number,
                            error=str(e))
            raise
    
    # Webhook Operations
    async def create_webhook(self,
                            owner: str,
                            repo: str,
                            webhook_url: str,
                            secret: Optional[str] = None,
                            events: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a webhook"""
        try:
            if events is None:
                events = ["push", "pull_request", "issues"]
            
            config = {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0"
            }
            
            if secret:
                config["secret"] = secret
            
            payload = {
                "name": "web",
                "active": True,
                "events": events,
                "config": config
            }
            
            response = await self.post(f"/repos/{owner}/{repo}/hooks", data=payload)
            
            self.logger.info("Webhook created successfully",
                           owner=owner,
                           repo=repo,
                           webhook_id=response.get("id"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create webhook",
                            owner=owner,
                            repo=repo,
                            webhook_url=webhook_url,
                            error=str(e))
            raise
    
    async def list_webhooks(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository webhooks"""
        try:
            response = await self.get(f"/repos/{owner}/{repo}/hooks")
            return response if isinstance(response, list) else []
        except Exception as e:
            self.logger.error("Failed to list webhooks",
                            owner=owner,
                            repo=repo,
                            error=str(e))
            raise
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: int) -> None:
        """Delete a webhook"""
        try:
            await self.delete(f"/repos/{owner}/{repo}/hooks/{webhook_id}")
            
            self.logger.info("Webhook deleted successfully",
                           owner=owner,
                           repo=repo,
                           webhook_id=webhook_id)
            
        except Exception as e:
            self.logger.error("Failed to delete webhook",
                            owner=owner,
                            repo=repo,
                            webhook_id=webhook_id,
                            error=str(e))
            raise
    
    # Branch Operations
    async def create_branch(self,
                           owner: str,
                           repo: str,
                           branch_name: str,
                           from_branch: str = "main") -> Dict[str, Any]:
        """Create a new branch"""
        try:
            # Get the SHA of the source branch
            branch_data = await self.get(f"/repos/{owner}/{repo}/git/refs/heads/{from_branch}")
            source_sha = branch_data["object"]["sha"]
            
            # Create new branch
            payload = {
                "ref": f"refs/heads/{branch_name}",
                "sha": source_sha
            }
            
            response = await self.post(f"/repos/{owner}/{repo}/git/refs", data=payload)
            
            self.logger.info("Branch created successfully",
                           owner=owner,
                           repo=repo,
                           branch_name=branch_name,
                           from_branch=from_branch)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create branch",
                            owner=owner,
                            repo=repo,
                            branch_name=branch_name,
                            error=str(e))
            raise
    
    async def delete_branch(self, owner: str, repo: str, branch_name: str) -> None:
        """Delete a branch"""
        try:
            await self.delete(f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}")
            
            self.logger.info("Branch deleted successfully",
                           owner=owner,
                           repo=repo,
                           branch_name=branch_name)
            
        except Exception as e:
            self.logger.error("Failed to delete branch",
                            owner=owner,
                            repo=repo,
                            branch_name=branch_name,
                            error=str(e))
            raise
    
    # User Operations
    async def get_user(self) -> Dict[str, Any]:
        """Get authenticated user information"""
        try:
            response = await self.get("/user")
            return response
        except Exception as e:
            self.logger.error("Failed to get user information", error=str(e))
            raise
    
    async def get_user_organizations(self) -> List[Dict[str, Any]]:
        """Get user's organizations"""
        try:
            response = await self.get("/user/orgs")
            return response if isinstance(response, list) else []
        except Exception as e:
            self.logger.error("Failed to get user organizations", error=str(e))
            raise

