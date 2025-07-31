"""
Cloudflare API client for worker deployment and management
"""
import httpx
import structlog
from typing import Optional, Dict, Any

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CloudflareClient:
    """Client for interacting with Cloudflare API"""
    
    def __init__(self):
        self.api_key = settings.cloudflare_api_key
        self.account_id = settings.cloudflare_account_id
        self.base_url = "https://api.cloudflare.com/client/v4"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def deploy_worker(self, worker_name: str, script_content: str) -> bool:
        """Deploy a Cloudflare Worker script"""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{worker_name}"
            
            # Prepare the script content
            files = {
                'metadata': (None, '{"main_module": "worker.js"}', 'application/json'),
                'worker.js': (None, script_content, 'application/javascript')
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully deployed worker: {worker_name}")
                    return True
                else:
                    logger.error(f"Failed to deploy worker: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deploying Cloudflare worker: {str(e)}")
            return False
    
    async def get_worker(self, worker_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a Cloudflare Worker"""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{worker_name}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get worker info: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting Cloudflare worker info: {str(e)}")
            return None
    
    async def delete_worker(self, worker_name: str) -> bool:
        """Delete a Cloudflare Worker"""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{worker_name}"
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    logger.info(f"Successfully deleted worker: {worker_name}")
                    return True
                else:
                    logger.error(f"Failed to delete worker: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting Cloudflare worker: {str(e)}")
            return False
    
    async def list_workers(self) -> Optional[Dict[str, Any]]:
        """List all Cloudflare Workers in the account"""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/workers/scripts"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to list workers: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error listing Cloudflare workers: {str(e)}")
            return None
