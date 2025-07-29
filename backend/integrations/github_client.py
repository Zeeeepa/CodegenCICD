import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import base64
import json
from datetime import datetime

class GitHubClient:
    """GitHub API client for repository management and webhook configuration."""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test GitHub API connection."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/user",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    user_data = await response.json()
                    return {
                        "success": True,
                        "user": user_data.get("login"),
                        "name": user_data.get("name")
                    }
                else:
                    raise Exception(f"GitHub API connection failed: {response.status}")
    
    async def list_repositories(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """List all accessible repositories."""
        repositories = []
        page = 1
        
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(
                    f"{self.base_url}/user/repos",
                    headers=self.headers,
                    params={
                        "per_page": per_page,
                        "page": page,
                        "sort": "updated",
                        "direction": "desc"
                    }
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch repositories: {response.status}")
                    
                    repos = await response.json()
                    if not repos:
                        break
                    
                    for repo in repos:
                        repositories.append({
                            "id": repo["id"],
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "owner": repo["owner"]["login"],
                            "description": repo.get("description", ""),
                            "private": repo["private"],
                            "clone_url": repo["clone_url"],
                            "ssh_url": repo["ssh_url"],
                            "html_url": repo["html_url"],
                            "default_branch": repo["default_branch"],
                            "updated_at": repo["updated_at"],
                            "language": repo.get("language"),
                            "topics": repo.get("topics", [])
                        })
                    
                    if len(repos) < per_page:
                        break
                    
                    page += 1
        
        return repositories
    
    async def get_repository_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get all branches for a repository."""
        branches = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/repos/{owner}/{repo}/branches",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    branch_data = await response.json()
                    for branch in branch_data:
                        branches.append({
                            "name": branch["name"],
                            "sha": branch["commit"]["sha"],
                            "protected": branch.get("protected", False)
                        })
                else:
                    raise Exception(f"Failed to fetch branches: {response.status}")
        
        return branches
    
    async def setup_webhook(
        self, 
        owner: str, 
        repo: str, 
        webhook_url: str,
        events: List[str] = None
    ) -> Dict[str, Any]:
        """Set up webhook for repository."""
        if events is None:
            events = ["pull_request", "push", "issues"]
        
        webhook_config = {
            "name": "web",
            "active": True,
            "events": events,
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            # First, check if webhook already exists
            async with session.get(
                f"{self.base_url}/repos/{owner}/{repo}/hooks",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    existing_hooks = await response.json()
                    for hook in existing_hooks:
                        if hook["config"].get("url") == webhook_url:
                            return {
                                "success": True,
                                "webhook_id": hook["id"],
                                "message": "Webhook already exists",
                                "webhook_url": webhook_url
                            }
            
            # Create new webhook
            async with session.post(
                f"{self.base_url}/repos/{owner}/{repo}/hooks",
                headers=self.headers,
                json=webhook_config
            ) as response:
                if response.status == 201:
                    webhook_data = await response.json()
                    return {
                        "success": True,
                        "webhook_id": webhook_data["id"],
                        "message": "Webhook created successfully",
                        "webhook_url": webhook_url
                    }
                else:
                    error_data = await response.json()
                    raise Exception(f"Failed to create webhook: {error_data}")
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request details."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    pr_data = await response.json()
                    return {
                        "number": pr_data["number"],
                        "title": pr_data["title"],
                        "body": pr_data.get("body", ""),
                        "state": pr_data["state"],
                        "html_url": pr_data["html_url"],
                        "head_ref": pr_data["head"]["ref"],
                        "head_sha": pr_data["head"]["sha"],
                        "base_ref": pr_data["base"]["ref"],
                        "base_sha": pr_data["base"]["sha"],
                        "clone_url": pr_data["head"]["repo"]["clone_url"],
                        "mergeable": pr_data.get("mergeable"),
                        "created_at": pr_data["created_at"],
                        "updated_at": pr_data["updated_at"]
                    }
                else:
                    raise Exception(f"Failed to fetch PR: {response.status}")
    
    async def merge_pull_request(
        self, 
        owner: str, 
        repo: str, 
        pr_number: int,
        commit_title: str = None,
        commit_message: str = None,
        merge_method: str = "merge"
    ) -> Dict[str, Any]:
        """Merge a pull request."""
        merge_data = {
            "merge_method": merge_method
        }
        
        if commit_title:
            merge_data["commit_title"] = commit_title
        if commit_message:
            merge_data["commit_message"] = commit_message
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                headers=self.headers,
                json=merge_data
            ) as response:
                if response.status == 200:
                    merge_result = await response.json()
                    return {
                        "success": True,
                        "sha": merge_result["sha"],
                        "merged": merge_result["merged"],
                        "message": merge_result["message"]
                    }
                else:
                    error_data = await response.json()
                    raise Exception(f"Failed to merge PR: {error_data}")
    
    async def create_issue_comment(
        self, 
        owner: str, 
        repo: str, 
        issue_number: int, 
        body: str
    ) -> Dict[str, Any]:
        """Create a comment on an issue or PR."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self.headers,
                json={"body": body}
            ) as response:
                if response.status == 201:
                    comment_data = await response.json()
                    return {
                        "success": True,
                        "comment_id": comment_data["id"],
                        "html_url": comment_data["html_url"]
                    }
                else:
                    raise Exception(f"Failed to create comment: {response.status}")
    
    async def get_pr_info(self, pr_url: str) -> Dict[str, Any]:
        """Extract PR information from URL."""
        # Parse GitHub PR URL: https://github.com/owner/repo/pull/123
        parts = pr_url.replace("https://github.com/", "").split("/")
        if len(parts) >= 4 and parts[2] == "pull":
            owner = parts[0]
            repo = parts[1]
            pr_number = int(parts[3])
            
            return await self.get_pull_request(owner, repo, pr_number)
        else:
            raise Exception(f"Invalid PR URL format: {pr_url}")
    
    async def get_repository_content(
        self, 
        owner: str, 
        repo: str, 
        path: str = "",
        ref: str = None
    ) -> Dict[str, Any]:
        """Get repository content."""
        params = {}
        if ref:
            params["ref"] = ref
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch content: {response.status}")
    
    async def search_repositories(self, query: str, per_page: int = 30) -> List[Dict[str, Any]]:
        """Search repositories."""
        repositories = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/search/repositories",
                headers=self.headers,
                params={
                    "q": query,
                    "per_page": per_page,
                    "sort": "updated"
                }
            ) as response:
                if response.status == 200:
                    search_data = await response.json()
                    for repo in search_data.get("items", []):
                        repositories.append({
                            "id": repo["id"],
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "owner": repo["owner"]["login"],
                            "description": repo.get("description", ""),
                            "private": repo["private"],
                            "clone_url": repo["clone_url"],
                            "html_url": repo["html_url"],
                            "default_branch": repo["default_branch"],
                            "updated_at": repo["updated_at"],
                            "language": repo.get("language"),
                            "topics": repo.get("topics", []),
                            "stars": repo["stargazers_count"],
                            "forks": repo["forks_count"]
                        })
                else:
                    raise Exception(f"Failed to search repositories: {response.status}")
        
        return repositories

