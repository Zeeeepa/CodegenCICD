"""
GitHub API service for repository management and operations
"""
import os
import httpx
from typing import Optional, Dict, Any, List
from github import Github
from dotenv import load_dotenv

load_dotenv()

class GitHubService:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        
        self.github = Github(self.token)
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"token {self.token}"},
            timeout=30.0
        )
    
    async def get_repository_info(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository information from GitHub API"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                response.raise_for_status()
                
        except Exception as e:
            print(f"Error getting repository info for {owner}/{repo}: {e}")
            return None
    
    async def get_repository_branches(self, owner: str, repo: str) -> List[str]:
        """Get list of branches for a repository"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/branches"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                branches_data = response.json()
                return [branch["name"] for branch in branches_data]
            else:
                response.raise_for_status()
                return []
                
        except Exception as e:
            print(f"Error getting branches for {owner}/{repo}: {e}")
            return []
    
    async def create_webhook(self, owner: str, repo: str, webhook_url: str, secret: str) -> Optional[Dict[str, Any]]:
        """Create a webhook for a repository"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/hooks"
            payload = {
                "name": "web",
                "active": True,
                "events": ["pull_request", "push"],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": secret,
                    "insecure_ssl": "0"
                }
            }
            
            response = await self.client.post(url, json=payload)
            
            if response.status_code == 201:
                return response.json()
            else:
                response.raise_for_status()
                return None
                
        except Exception as e:
            print(f"Error creating webhook for {owner}/{repo}: {e}")
            return None
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get pull request information"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"Error getting PR {pr_number} for {owner}/{repo}: {e}")
            return None
    
    async def merge_pull_request(self, owner: str, repo: str, pr_number: int, merge_method: str = "merge") -> Optional[Dict[str, Any]]:
        """Merge a pull request"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/merge"
            payload = {
                "merge_method": merge_method
            }
            
            response = await self.client.put(url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
                return None
                
        except Exception as e:
            print(f"Error merging PR {pr_number} for {owner}/{repo}: {e}")
            return None
    
    async def clone_repository(self, owner: str, repo: str, branch: str, target_dir: str) -> bool:
        """Clone a repository to a target directory"""
        try:
            # This would be implemented using git commands or pygit2
            # For now, return a placeholder
            print(f"Would clone {owner}/{repo}:{branch} to {target_dir}")
            return True
            
        except Exception as e:
            print(f"Error cloning repository {owner}/{repo}: {e}")
            return False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
