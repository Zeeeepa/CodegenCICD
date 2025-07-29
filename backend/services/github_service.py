"""
GitHub API service for repository management and webhook setup
"""
import os
import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
    
    async def validate_repository(self, owner: str, repo: str) -> bool:
        """Validate that a GitHub repository exists and is accessible"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=headers,
                    timeout=30.0
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error validating repository {owner}/{repo}: {e}")
            return False
    
    async def get_user_repositories(self) -> List[Dict[str, Any]]:
        """Get repositories accessible to the authenticated user"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # Get user repos
                response = await client.get(
                    f"{self.base_url}/user/repos",
                    headers=headers,
                    params={
                        "sort": "updated",
                        "per_page": 100,
                        "type": "all"
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
                repos = response.json()
                
                # Also get organization repos
                org_repos = []
                try:
                    orgs_response = await client.get(
                        f"{self.base_url}/user/orgs",
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if orgs_response.status_code == 200:
                        orgs = orgs_response.json()
                        
                        for org in orgs:
                            org_repos_response = await client.get(
                                f"{self.base_url}/orgs/{org['login']}/repos",
                                headers=headers,
                                params={"per_page": 100},
                                timeout=30.0
                            )
                            
                            if org_repos_response.status_code == 200:
                                org_repos.extend(org_repos_response.json())
                                
                except Exception as e:
                    logger.warning(f"Failed to get organization repos: {e}")
                
                # Combine and deduplicate
                all_repos = repos + org_repos
                seen = set()
                unique_repos = []
                
                for repo in all_repos:
                    if repo['id'] not in seen:
                        seen.add(repo['id'])
                        unique_repos.append({
                            'id': repo['id'],
                            'name': repo['name'],
                            'full_name': repo['full_name'],
                            'owner': repo['owner'],
                            'description': repo.get('description'),
                            'private': repo['private'],
                            'updated_at': repo['updated_at']
                        })
                
                # Sort by updated date
                unique_repos.sort(key=lambda x: x['updated_at'], reverse=True)
                
                logger.info(f"Retrieved {len(unique_repos)} repositories")
                return unique_repos
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting repositories: {e}")
            raise Exception(f"Failed to get repositories: {e}")
        except Exception as e:
            logger.error(f"Error getting repositories: {e}")
            raise
    
    async def setup_webhook(self, owner: str, repo: str, webhook_url: str) -> Dict[str, Any]:
        """Set up a webhook for the repository"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"
                }
                
                # Check if webhook already exists
                existing_webhooks = await self.get_webhooks(owner, repo)
                for webhook in existing_webhooks:
                    if webhook.get('config', {}).get('url') == webhook_url:
                        logger.info(f"Webhook already exists for {owner}/{repo}")
                        return webhook
                
                # Create new webhook
                payload = {
                    "name": "web",
                    "active": True,
                    "events": [
                        "pull_request",
                        "push",
                        "pull_request_review",
                        "issue_comment"
                    ],
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "insecure_ssl": "0"
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Created webhook for {owner}/{repo}: {result.get('id')}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error setting up webhook: {e}")
            raise Exception(f"Failed to setup webhook: {e}")
        except Exception as e:
            logger.error(f"Error setting up webhook: {e}")
            raise
    
    async def get_webhooks(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get existing webhooks for a repository"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting webhooks: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting webhooks: {e}")
            return []
    
    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get pull request information"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting pull request: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting pull request: {e}")
            return None
    
    async def merge_pull_request(self, owner: str, repo: str, pr_number: int, 
                                commit_title: str = "", commit_message: str = "") -> Dict[str, Any]:
        """Merge a pull request"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "commit_title": commit_title or f"Merge pull request #{pr_number}",
                    "commit_message": commit_message,
                    "merge_method": "merge"
                }
                
                response = await client.put(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Merged pull request #{pr_number} in {owner}/{repo}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error merging pull request: {e}")
            raise Exception(f"Failed to merge pull request: {e}")
        except Exception as e:
            logger.error(f"Error merging pull request: {e}")
            raise
    
    async def create_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """Create a comment on an issue or pull request"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"
                }
                
                payload = {"body": body}
                
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Created comment on issue #{issue_number} in {owner}/{repo}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating issue comment: {e}")
            raise Exception(f"Failed to create issue comment: {e}")
        except Exception as e:
            logger.error(f"Error creating issue comment: {e}")
            raise

