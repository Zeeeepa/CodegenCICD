import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
import json
import uuid
import subprocess
import os

class GrainchainClient:
    """Client for Grainchain sandboxing and snapshot management."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://localhost:8001"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Grainchain service."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return {
                            "success": True,
                            "status": health_data.get("status", "healthy"),
                            "version": health_data.get("version", "unknown")
                        }
                    else:
                        raise Exception(f"Health check failed: {response.status}")
        except Exception as e:
            raise Exception(f"Grainchain connection failed: {str(e)}")
    
    async def create_snapshot(
        self, 
        config: Dict[str, Any], 
        snapshot_id: str = None
    ) -> Dict[str, Any]:
        """Create a new sandbox snapshot with pre-installed services."""
        
        if snapshot_id is None:
            snapshot_id = f"snapshot-{uuid.uuid4().hex[:8]}"
        
        snapshot_config = {
            "snapshot_id": snapshot_id,
            "base_image": config.get("base_image", "ubuntu:22.04"),
            "pre_install_packages": config.get("pre_install_packages", []),
            "services": config.get("services", []),
            "environment_variables": config.get("environment_variables", {}),
            "working_directory": config.get("working_directory", "/workspace"),
            "timeout": config.get("timeout", 1800)  # 30 minutes
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/snapshots",
                    headers=self.headers,
                    json=snapshot_config,
                    timeout=aiohttp.ClientTimeout(total=600)  # 10 minutes for creation
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        return {
                            "success": True,
                            "snapshot_id": result.get("snapshot_id", snapshot_id),
                            "status": result.get("status", "created"),
                            "services": result.get("services", []),
                            "message": "Snapshot created successfully"
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Snapshot creation failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "snapshot_id": snapshot_id
            }
    
    async def execute_in_snapshot(
        self, 
        snapshot_id: str, 
        commands: List[str],
        working_directory: str = "/workspace",
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Execute commands in a snapshot."""
        
        execution_config = {
            "commands": commands,
            "working_directory": working_directory,
            "timeout": timeout,
            "capture_output": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/snapshots/{snapshot_id}/execute",
                    headers=self.headers,
                    json=execution_config,
                    timeout=aiohttp.ClientTimeout(total=timeout + 30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": result.get("exit_code", 1) == 0,
                            "exit_code": result.get("exit_code", 1),
                            "stdout": result.get("stdout", ""),
                            "stderr": result.get("stderr", ""),
                            "logs": result.get("logs", []),
                            "duration": result.get("duration", 0)
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Command execution failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "logs": [f"Error: {str(e)}"],
                "duration": 0
            }
    
    async def get_snapshot_status(self, snapshot_id: str) -> Dict[str, Any]:
        """Get the status of a snapshot."""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/snapshots/{snapshot_id}",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to get snapshot status: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "unknown"
            }
    
    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots."""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/snapshots",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("snapshots", [])
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to list snapshots: {response.status} - {error_text}")
        except Exception as e:
            return []
    
    async def delete_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Delete a snapshot."""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/snapshots/{snapshot_id}",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status in [200, 204]:
                        return {
                            "success": True,
                            "message": "Snapshot deleted successfully"
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to delete snapshot: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_snapshot_logs(self, snapshot_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get logs from a snapshot."""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/snapshots/{snapshot_id}/logs",
                    headers=self.headers,
                    params={"lines": lines},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "logs": result.get("logs", []),
                            "timestamp": result.get("timestamp")
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to get logs: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "logs": []
            }
    
    async def copy_files_to_snapshot(
        self, 
        snapshot_id: str, 
        local_path: str, 
        remote_path: str
    ) -> Dict[str, Any]:
        """Copy files from local system to snapshot."""
        
        try:
            # For now, we'll use the execute command to handle file copying
            # In a real implementation, this might use a file upload endpoint
            copy_commands = [
                f"mkdir -p {os.path.dirname(remote_path)}",
                f"cp -r {local_path} {remote_path}"
            ]
            
            result = await self.execute_in_snapshot(snapshot_id, copy_commands)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Files copied to {remote_path}"
                }
            else:
                raise Exception(f"Copy failed: {result['stderr']}")
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_service_status(self, snapshot_id: str, service_name: str) -> Dict[str, Any]:
        """Get the status of a specific service in the snapshot."""
        
        try:
            # Check service status using systemctl or ps
            status_commands = [
                f"systemctl is-active {service_name} || ps aux | grep {service_name} | grep -v grep"
            ]
            
            result = await self.execute_in_snapshot(snapshot_id, status_commands)
            
            service_running = "active" in result["stdout"] or service_name in result["stdout"]
            
            return {
                "success": True,
                "service_name": service_name,
                "running": service_running,
                "status": "running" if service_running else "stopped",
                "details": result["stdout"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "service_name": service_name,
                "running": False,
                "status": "unknown",
                "error": str(e)
            }
    
    async def create_validation_snapshot(
        self, 
        snapshot_id: str,
        environment_variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Create a specialized snapshot for validation with pre-installed tools."""
        
        if environment_variables is None:
            environment_variables = {}
        
        # Configuration for validation snapshot with all required services
        validation_config = {
            "base_image": "ubuntu:22.04",
            "pre_install_packages": [
                "git", "curl", "wget", "build-essential", 
                "python3", "python3-pip", "nodejs", "npm",
                "docker.io", "docker-compose"
            ],
            "services": [
                {
                    "name": "graph-sitter",
                    "image": "zeeeepa/graph-sitter:latest",
                    "port": 8002,
                    "health_check": "/health"
                },
                {
                    "name": "web-eval-agent", 
                    "image": "zeeeepa/web-eval-agent:latest",
                    "port": 8003,
                    "env": {
                        "GEMINI_API_KEY": environment_variables.get("GEMINI_API_KEY", ""),
                        "NODE_ENV": "production"
                    },
                    "health_check": "/health"
                }
            ],
            "environment_variables": environment_variables,
            "working_directory": "/workspace",
            "timeout": 1800
        }
        
        return await self.create_snapshot(validation_config, snapshot_id)

# Local deployment functions for Grainchain
async def deploy_grainchain_locally(port: int = 8001) -> Dict[str, Any]:
    """Deploy Grainchain service locally."""
    
    try:
        # Clone the repository if it doesn't exist
        repo_dir = "/tmp/grainchain"
        if os.path.exists(repo_dir):
            import shutil
            shutil.rmtree(repo_dir)
        
        # Clone the repository
        clone_result = subprocess.run([
            "git", "clone", "https://github.com/Zeeeepa/grainchain.git", repo_dir
        ], capture_output=True, text=True, timeout=60)
        
        if clone_result.returncode != 0:
            raise Exception(f"Failed to clone grainchain: {clone_result.stderr}")
        
        # Install dependencies
        install_result = subprocess.run([
            "pip", "install", "-r", "requirements.txt"
        ], cwd=repo_dir, capture_output=True, text=True, timeout=300)
        
        if install_result.returncode != 0:
            raise Exception(f"Failed to install dependencies: {install_result.stderr}")
        
        # Start the service in background
        start_result = subprocess.Popen([
            "python", "main.py", "--port", str(port)
        ], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for the service to start
        await asyncio.sleep(5)
        
        # Test if service is running
        client = GrainchainClient(f"http://localhost:{port}")
        try:
            await client.test_connection()
            return {
                "success": True,
                "service_url": f"http://localhost:{port}",
                "process_id": start_result.pid,
                "message": "Grainchain deployed successfully"
            }
        except Exception as e:
            start_result.terminate()
            raise Exception(f"Service deployment failed: {str(e)}")
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to deploy Grainchain"
        }

