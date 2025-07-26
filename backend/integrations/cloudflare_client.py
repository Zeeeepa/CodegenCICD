"""
Cloudflare client for webhook gateway management
"""
import httpx
import structlog
from typing import Dict, Any, Optional, List
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CloudflareClient:
    """Client for interacting with Cloudflare API"""
    
    def __init__(self):
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.api_key = settings.cloudflare_api_key
        self.account_id = settings.cloudflare_account_id
        self.worker_name = settings.cloudflare_worker_name
        self.worker_url = settings.cloudflare_worker_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD/1.0.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Cloudflare API"""
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
                    "Cloudflare API HTTP error",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                    endpoint=endpoint
                )
                raise
            except Exception as e:
                logger.error("Cloudflare API request failed", error=str(e), endpoint=endpoint)
                raise
    
    async def get_worker_info(self) -> Dict[str, Any]:
        """Get Cloudflare Worker information"""
        try:
            response = await self._make_request("GET", f"/accounts/{self.account_id}/workers/scripts/{self.worker_name}")
            return response
        except Exception as e:
            logger.error("Failed to get worker info", worker_name=self.worker_name, error=str(e))
            raise
    
    async def update_worker_script(self, script_content: str) -> Dict[str, Any]:
        """Update Cloudflare Worker script"""
        headers = {**self.headers, "Content-Type": "application/javascript"}
        
        try:
            response = await self._make_request(
                "PUT", 
                f"/accounts/{self.account_id}/workers/scripts/{self.worker_name}",
                content=script_content,
                headers=headers
            )
            logger.info("Worker script updated", worker_name=self.worker_name)
            return response
        except Exception as e:
            logger.error("Failed to update worker script", worker_name=self.worker_name, error=str(e))
            raise
    
    async def get_worker_routes(self) -> List[Dict[str, Any]]:
        """Get Cloudflare Worker routes"""
        try:
            response = await self._make_request("GET", f"/accounts/{self.account_id}/workers/scripts/{self.worker_name}/routes")
            return response.get("result", [])
        except Exception as e:
            logger.error("Failed to get worker routes", worker_name=self.worker_name, error=str(e))
            return []
    
    async def create_worker_route(self, pattern: str, zone_id: str = None) -> Dict[str, Any]:
        """Create a new worker route"""
        payload = {
            "pattern": pattern,
            "script": self.worker_name
        }
        
        if zone_id:
            payload["zone_id"] = zone_id
        
        try:
            response = await self._make_request("POST", f"/accounts/{self.account_id}/workers/routes", json=payload)
            logger.info("Worker route created", pattern=pattern, worker_name=self.worker_name)
            return response
        except Exception as e:
            logger.error("Failed to create worker route", pattern=pattern, error=str(e))
            raise
    
    async def test_webhook_endpoint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Test the webhook endpoint"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.worker_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("Failed to test webhook endpoint", url=self.worker_url, error=str(e))
            raise
    
    async def get_worker_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get Cloudflare Worker logs"""
        try:
            response = await self._make_request(
                "GET", 
                f"/accounts/{self.account_id}/workers/scripts/{self.worker_name}/logs",
                params={"limit": limit}
            )
            return response.get("result", [])
        except Exception as e:
            logger.error("Failed to get worker logs", worker_name=self.worker_name, error=str(e))
            return []
    
    async def get_worker_analytics(self, since: str = "1h") -> Dict[str, Any]:
        """Get Cloudflare Worker analytics"""
        try:
            response = await self._make_request(
                "GET",
                f"/accounts/{self.account_id}/workers/scripts/{self.worker_name}/analytics",
                params={"since": since}
            )
            return response.get("result", {})
        except Exception as e:
            logger.error("Failed to get worker analytics", worker_name=self.worker_name, error=str(e))
            return {}
    
    async def health_check(self) -> bool:
        """Check if Cloudflare API is accessible"""
        try:
            await self._make_request("GET", f"/accounts/{self.account_id}")
            return True
        except Exception as e:
            logger.error("Cloudflare API health check failed", error=str(e))
            return False
    
    def get_webhook_url(self, project_id: int = None) -> str:
        """Get webhook URL for GitHub integration"""
        if project_id:
            return f"{self.worker_url}/webhook/github/{project_id}"
        return f"{self.worker_url}/webhook/github"

