import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
import json

class CloudflareClient:
    """Cloudflare API client for worker and webhook management."""
    
    def __init__(self, api_key: str, account_id: str, email: str = None):
        self.api_key = api_key
        self.account_id = account_id
        self.email = email
        self.base_url = "https://api.cloudflare.com/client/v4"
        
        # Set up headers based on authentication method
        if email:
            # Global API Key authentication
            self.headers = {
                "X-Auth-Email": email,
                "X-Auth-Key": api_key,
                "Content-Type": "application/json"
            }
        else:
            # API Token authentication
            self.headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Cloudflare API connection."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/user/tokens/verify",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return {
                            "success": True,
                            "message": "Cloudflare API connection successful"
                        }
                    else:
                        raise Exception(f"API verification failed: {result.get('errors', [])}")
                else:
                    raise Exception(f"Cloudflare API connection failed: {response.status}")
    
    async def list_workers(self) -> List[Dict[str, Any]]:
        """List all workers in the account."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/accounts/{self.account_id}/workers/scripts",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return result.get("result", [])
                    else:
                        raise Exception(f"Failed to list workers: {result.get('errors', [])}")
                else:
                    raise Exception(f"Failed to list workers: {response.status}")
    
    async def get_worker(self, worker_name: str) -> Dict[str, Any]:
        """Get worker details."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{worker_name}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return result.get("result", {})
                    else:
                        raise Exception(f"Failed to get worker: {result.get('errors', [])}")
                else:
                    raise Exception(f"Failed to get worker: {response.status}")
    
    async def deploy_webhook_worker(
        self, 
        worker_name: str, 
        worker_script: str,
        environment_variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Deploy webhook worker script."""
        
        # Deploy the worker script
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{worker_name}",
                headers={**self.headers, "Content-Type": "application/javascript"},
                data=worker_script
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to deploy worker: {response.status} - {error_text}")
        
        # Set environment variables if provided
        if environment_variables:
            await self.set_worker_environment_variables(worker_name, environment_variables)
        
        # Get worker URL
        worker_url = f"https://{worker_name}.{self.account_id}.workers.dev"
        
        return {
            "success": True,
            "worker_name": worker_name,
            "worker_url": worker_url,
            "message": "Webhook worker deployed successfully"
        }
    
    async def set_worker_environment_variables(
        self, 
        worker_name: str, 
        variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Set environment variables for a worker."""
        
        # Format environment variables for Cloudflare API
        env_vars = []
        for key, value in variables.items():
            env_vars.append({
                "name": key,
                "value": value,
                "type": "plain_text"
            })
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{worker_name}/settings",
                headers=self.headers,
                json={"bindings": env_vars}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return {
                            "success": True,
                            "message": "Environment variables set successfully"
                        }
                    else:
                        raise Exception(f"Failed to set environment variables: {result.get('errors', [])}")
                else:
                    raise Exception(f"Failed to set environment variables: {response.status}")
    
    async def get_worker_logs(self, worker_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get worker logs."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{worker_name}/tail",
                headers=self.headers,
                params={"limit": limit}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return result.get("result", [])
                    else:
                        raise Exception(f"Failed to get worker logs: {result.get('errors', [])}")
                else:
                    raise Exception(f"Failed to get worker logs: {response.status}")
    
    async def create_webhook_route(
        self, 
        zone_id: str, 
        pattern: str, 
        worker_name: str
    ) -> Dict[str, Any]:
        """Create a route for the webhook worker."""
        route_data = {
            "pattern": pattern,
            "script": worker_name
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/zones/{zone_id}/workers/routes",
                headers=self.headers,
                json=route_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return {
                            "success": True,
                            "route_id": result["result"]["id"],
                            "pattern": pattern,
                            "message": "Route created successfully"
                        }
                    else:
                        raise Exception(f"Failed to create route: {result.get('errors', [])}")
                else:
                    raise Exception(f"Failed to create route: {response.status}")
    
    async def test_webhook_worker(self, worker_url: str, test_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Test webhook worker with a test payload."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                worker_url,
                headers={"Content-Type": "application/json"},
                json=test_payload
            ) as response:
                response_text = await response.text()
                return {
                    "status_code": response.status,
                    "response": response_text,
                    "success": response.status == 200
                }

def generate_webhook_worker_script(dashboard_url: str) -> str:
    """Generate the webhook worker script."""
    return f'''
addEventListener('fetch', event => {{
  event.respondWith(handleRequest(event.request))
}})

async function handleRequest(request) {{
  // Handle CORS preflight requests
  if (request.method === 'OPTIONS') {{
    return new Response(null, {{
      status: 200,
      headers: {{
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-GitHub-Event, X-GitHub-Delivery, X-Hub-Signature-256',
      }}
    }})
  }}

  // Only handle POST requests
  if (request.method !== 'POST') {{
    return new Response('Method not allowed', {{ status: 405 }})
  }}

  try {{
    // Get GitHub webhook headers
    const githubEvent = request.headers.get('X-GitHub-Event')
    const githubDelivery = request.headers.get('X-GitHub-Delivery')
    const signature = request.headers.get('X-Hub-Signature-256')
    
    // Parse the webhook payload
    const payload = await request.json()
    
    // Log the webhook event
    console.log('GitHub Webhook Event:', {{
      event: githubEvent,
      delivery: githubDelivery,
      repository: payload.repository?.full_name,
      action: payload.action
    }})
    
    // Forward webhook to dashboard backend
    const dashboardResponse = await fetch('{dashboard_url}/api/webhooks/github', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'X-GitHub-Event': githubEvent,
        'X-GitHub-Delivery': githubDelivery,
        'X-Hub-Signature-256': signature
      }},
      body: JSON.stringify(payload)
    }})
    
    if (dashboardResponse.ok) {{
      return new Response('Webhook processed successfully', {{ 
        status: 200,
        headers: {{
          'Access-Control-Allow-Origin': '*'
        }}
      }})
    }} else {{
      console.error('Dashboard webhook processing failed:', dashboardResponse.status)
      return new Response('Webhook processing failed', {{ 
        status: 500,
        headers: {{
          'Access-Control-Allow-Origin': '*'
        }}
      }})
    }}
    
  }} catch (error) {{
    console.error('Webhook processing error:', error)
    return new Response('Internal server error', {{ 
      status: 500,
      headers: {{
        'Access-Control-Allow-Origin': '*'
      }}
    }})
  }}
}}
'''

