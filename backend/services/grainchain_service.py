"""
Grainchain Service Integration
Handles sandboxing and snapshotting for validation environments
"""

import os
import asyncio
import docker
import tempfile
import shutil
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GrainchainService:
    """Service for managing grainchain sandboxing and snapshotting"""
    
    def __init__(self):
        self.enabled = os.getenv("GRAINCHAIN_ENABLED", "true").lower() == "true"
        self.docker_socket = os.getenv("GRAINCHAIN_DOCKER_SOCKET", "/var/run/docker.sock")
        self.workspace_dir = os.getenv("GRAINCHAIN_WORKSPACE_DIR", "/tmp/grainchain_workspaces")
        self.max_containers = int(os.getenv("GRAINCHAIN_MAX_CONTAINERS", "10"))
        self.container_timeout = int(os.getenv("GRAINCHAIN_CONTAINER_TIMEOUT", "3600"))
        
        if not self.enabled:
            logger.warning("Grainchain is disabled")
            return
        
        try:
            self.docker_client = docker.from_env()
            logger.info("Initialized Grainchain service with Docker integration")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            self.enabled = False
        
        # Ensure workspace directory exists
        os.makedirs(self.workspace_dir, exist_ok=True)

    async def create_environment(self, workspace_dir: str, project_id: str) -> Dict[str, Any]:
        """Create a sandboxed environment for validation"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Grainchain is disabled"
            }
        
        try:
            logger.info(f"Creating grainchain environment for project {project_id}")
            
            # Create project-specific workspace
            project_workspace = os.path.join(workspace_dir, "grainchain")
            os.makedirs(project_workspace, exist_ok=True)
            
            # Create grainchain configuration
            config = {
                "project_id": project_id,
                "workspace": project_workspace,
                "created_at": datetime.now().isoformat(),
                "docker_image": "python:3.11-slim",
                "environment": {
                    "PYTHONPATH": "/workspace",
                    "PROJECT_ID": project_id
                }
            }
            
            # Create container for sandboxed execution
            container_name = f"grainchain-{project_id}-{int(datetime.now().timestamp())}"
            
            try:
                container = self.docker_client.containers.run(
                    image="python:3.11-slim",
                    name=container_name,
                    detach=True,
                    volumes={
                        project_workspace: {"bind": "/workspace", "mode": "rw"}
                    },
                    environment=config["environment"],
                    command="sleep infinity",  # Keep container running
                    remove=False,
                    mem_limit="512m",
                    cpu_count=1
                )
                
                config["container_id"] = container.id
                config["container_name"] = container_name
                
                logger.info(f"Created grainchain container: {container_name}")
                
                return {
                    "success": True,
                    "container_id": container.id,
                    "container_name": container_name,
                    "workspace": project_workspace,
                    "config": config
                }
                
            except docker.errors.APIError as e:
                logger.error(f"Failed to create container: {str(e)}")
                return {
                    "success": False,
                    "error": f"Container creation failed: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error creating grainchain environment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_command(self, container_id: str, command: str, 
                            working_dir: str = "/workspace") -> Dict[str, Any]:
        """Execute a command in the grainchain container"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Grainchain is disabled"
            }
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Execute command
            result = container.exec_run(
                cmd=command,
                workdir=working_dir,
                stdout=True,
                stderr=True
            )
            
            return {
                "success": result.exit_code == 0,
                "exit_code": result.exit_code,
                "stdout": result.output.decode('utf-8') if result.output else "",
                "stderr": "",  # Docker exec_run combines stdout and stderr
                "command": command
            }
            
        except docker.errors.NotFound:
            return {
                "success": False,
                "error": f"Container {container_id} not found"
            }
        except Exception as e:
            logger.error(f"Error executing command in container: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def install_dependencies(self, container_id: str, requirements: List[str]) -> Dict[str, Any]:
        """Install Python dependencies in the container"""
        if not requirements:
            return {"success": True, "message": "No dependencies to install"}
        
        try:
            # Install pip packages
            pip_command = f"pip install {' '.join(requirements)}"
            result = await self.execute_command(container_id, pip_command)
            
            if result["success"]:
                logger.info(f"Installed dependencies: {', '.join(requirements)}")
            else:
                logger.error(f"Failed to install dependencies: {result.get('stderr', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error installing dependencies: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_snapshot(self, container_id: str, snapshot_name: str) -> Dict[str, Any]:
        """Create a snapshot of the container state"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Grainchain is disabled"
            }
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Commit container to create image snapshot
            image = container.commit(
                repository=f"grainchain-snapshot",
                tag=snapshot_name,
                message=f"Snapshot created at {datetime.now().isoformat()}"
            )
            
            logger.info(f"Created snapshot: {image.id}")
            
            return {
                "success": True,
                "snapshot_id": image.id,
                "snapshot_name": snapshot_name,
                "created_at": datetime.now().isoformat()
            }
            
        except docker.errors.NotFound:
            return {
                "success": False,
                "error": f"Container {container_id} not found"
            }
        except Exception as e:
            logger.error(f"Error creating snapshot: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def restore_snapshot(self, snapshot_id: str, new_container_name: str) -> Dict[str, Any]:
        """Restore a container from a snapshot"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Grainchain is disabled"
            }
        
        try:
            # Create new container from snapshot image
            container = self.docker_client.containers.run(
                image=snapshot_id,
                name=new_container_name,
                detach=True,
                command="sleep infinity",
                remove=False,
                mem_limit="512m",
                cpu_count=1
            )
            
            logger.info(f"Restored container from snapshot: {new_container_name}")
            
            return {
                "success": True,
                "container_id": container.id,
                "container_name": new_container_name
            }
            
        except docker.errors.APIError as e:
            logger.error(f"Failed to restore from snapshot: {str(e)}")
            return {
                "success": False,
                "error": f"Snapshot restoration failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error restoring snapshot: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def cleanup_container(self, container_id: str) -> Dict[str, Any]:
        """Clean up a grainchain container"""
        if not self.enabled:
            return {"success": True, "message": "Grainchain is disabled"}
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Stop and remove container
            container.stop(timeout=10)
            container.remove()
            
            logger.info(f"Cleaned up container: {container_id}")
            
            return {
                "success": True,
                "message": f"Container {container_id} cleaned up"
            }
            
        except docker.errors.NotFound:
            return {
                "success": True,
                "message": f"Container {container_id} not found (already cleaned up)"
            }
        except Exception as e:
            logger.error(f"Error cleaning up container: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def list_containers(self) -> Dict[str, Any]:
        """List all grainchain containers"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Grainchain is disabled"
            }
        
        try:
            containers = self.docker_client.containers.list(
                filters={"name": "grainchain-"}
            )
            
            container_info = []
            for container in containers:
                container_info.append({
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "created": container.attrs["Created"],
                    "image": container.image.tags[0] if container.image.tags else "unknown"
                })
            
            return {
                "success": True,
                "containers": container_info,
                "count": len(container_info)
            }
            
        except Exception as e:
            logger.error(f"Error listing containers: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def cleanup_old_containers(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Clean up old grainchain containers"""
        if not self.enabled:
            return {"success": True, "message": "Grainchain is disabled"}
        
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={"name": "grainchain-"}
            )
            
            cleaned_count = 0
            current_time = datetime.now()
            
            for container in containers:
                created_time = datetime.fromisoformat(
                    container.attrs["Created"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
                
                age_hours = (current_time - created_time).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    try:
                        container.stop(timeout=5)
                        container.remove()
                        cleaned_count += 1
                        logger.info(f"Cleaned up old container: {container.name}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up container {container.name}: {str(e)}")
            
            return {
                "success": True,
                "cleaned_count": cleaned_count,
                "message": f"Cleaned up {cleaned_count} old containers"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old containers: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def is_enabled(self) -> bool:
        """Check if grainchain is enabled and available"""
        return self.enabled
