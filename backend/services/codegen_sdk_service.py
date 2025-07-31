"""
Codegen SDK Integration Service
Provides agent orchestration and API integration capabilities
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime
import httpx

logger = structlog.get_logger(__name__)

try:
    import codegen_api_client
    from codegen_api_client.rest import ApiException
    CODEGEN_SDK_AVAILABLE = True
except ImportError:
    logger.warning("Codegen API client not available - using mock implementation")
    CODEGEN_SDK_AVAILABLE = False


class MockAgentRun:
    """Mock agent run for when Codegen SDK is not available"""
    def __init__(self, **kwargs):
        self.id = f"mock_run_{datetime.now().timestamp()}"
        self.status = "running"
        self.created_at = datetime.now().isoformat()
        self.completed_at = None
        self.result = None
        self.error = None
        self.__dict__.update(kwargs)


class CodegenSDKService:
    """
    Service for Codegen agent orchestration and API integration
    """
    
    def __init__(self):
        self.org_id = int(os.environ.get("CODEGEN_ORG_ID", "323"))
        self.api_token = os.environ.get("CODEGEN_API_TOKEN")
        self.api_host = os.environ.get("CODEGEN_API_HOST", "https://api.codegen.com")
        
        self.sdk_available = CODEGEN_SDK_AVAILABLE and bool(self.api_token)
        
        if self.sdk_available:
            self._initialize_sdk()
        
        logger.info("CodegenSDKService initialized", 
                   org_id=self.org_id,
                   sdk_available=self.sdk_available,
                   api_token_configured=bool(self.api_token))
    
    def _initialize_sdk(self):
        """Initialize the Codegen SDK client"""
        try:
            configuration = codegen_api_client.Configuration(
                host=self.api_host
            )
            configuration.api_key['Authorization'] = f"Bearer {self.api_token}"
            
            self.api_client = codegen_api_client.ApiClient(configuration)
            self.agents_api = codegen_api_client.AgentsApi(self.api_client)
            self.organizations_api = codegen_api_client.OrganizationsApi(self.api_client)
            self.users_api = codegen_api_client.UsersApi(self.api_client)
            
            logger.info("Codegen SDK initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Codegen SDK", error=str(e))
            self.sdk_available = False
    
    async def create_agent_run(
        self, 
        task_data: Dict[str, Any],
        priority: str = "normal",
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new agent run
        
        Args:
            task_data: Task configuration and parameters
            priority: Task priority (low, normal, high, urgent)
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with agent run information
        """
        start_time = datetime.now()
        
        logger.info("Creating agent run", 
                   org_id=self.org_id,
                   priority=priority,
                   task_type=task_data.get("type", "unknown"))
        
        try:
            if not self.sdk_available:
                # Mock agent run creation
                mock_run = MockAgentRun(
                    status="running",
                    task_data=task_data,
                    priority=priority,
                    timeout=timeout
                )
                
                result = {
                    "success": True,
                    "agent_run_id": mock_run.id,
                    "status": mock_run.status,
                    "created_at": mock_run.created_at,
                    "org_id": self.org_id,
                    "priority": priority,
                    "task_data": task_data,
                    "mock": True,
                    "timestamp": start_time.isoformat()
                }
                
                logger.info("Mock agent run created", 
                           agent_run_id=mock_run.id)
                
                return result
            
            # Prepare create input
            create_input_data = {
                "task_description": task_data.get("description", ""),
                "task_type": task_data.get("type", "general"),
                "priority": priority,
                "configuration": task_data.get("configuration", {}),
                "context": task_data.get("context", {}),
                "timeout": timeout
            }
            
            create_input = codegen_api_client.CreateAgentRunInput(**create_input_data)
            
            # Create agent run via API
            response = self.agents_api.create_agent_run_v1_organizations_org_id_agent_run_post(
                org_id=self.org_id,
                create_agent_run_input=create_input
            )
            
            result = {
                "success": True,
                "agent_run_id": response.id,
                "status": response.status,
                "created_at": response.created_at,
                "org_id": self.org_id,
                "priority": priority,
                "task_data": task_data,
                "timestamp": start_time.isoformat()
            }
            
            logger.info("Agent run created successfully", 
                       agent_run_id=response.id,
                       status=response.status)
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "org_id": self.org_id,
                "task_data": task_data,
                "timestamp": start_time.isoformat()
            }
            
            if hasattr(e, 'status'):
                error_result["status_code"] = e.status
            
            logger.error("Failed to create agent run", 
                        error=str(e),
                        org_id=self.org_id)
            
            return error_result
    
    async def get_agent_run_status(
        self, 
        agent_run_id: str,
        include_logs: bool = False
    ) -> Dict[str, Any]:
        """
        Get agent run status and details
        
        Args:
            agent_run_id: ID of the agent run
            include_logs: Whether to include execution logs
            
        Returns:
            Dictionary with agent run status
        """
        logger.info("Getting agent run status", 
                   agent_run_id=agent_run_id,
                   org_id=self.org_id)
        
        try:
            if not self.sdk_available:
                # Mock status response
                mock_statuses = ["running", "completed", "failed", "pending"]
                import random
                
                status = random.choice(mock_statuses)
                
                result = {
                    "success": True,
                    "agent_run_id": agent_run_id,
                    "status": status,
                    "progress": 75 if status == "running" else (100 if status == "completed" else 0),
                    "result": "Task completed successfully" if status == "completed" else None,
                    "error": "Mock error message" if status == "failed" else None,
                    "started_at": datetime.now().isoformat(),
                    "completed_at": datetime.now().isoformat() if status in ["completed", "failed"] else None,
                    "execution_time": 120.5 if status in ["completed", "failed"] else None,
                    "mock": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                if include_logs:
                    result["logs"] = [
                        {"timestamp": datetime.now().isoformat(), "level": "info", "message": "Task started"},
                        {"timestamp": datetime.now().isoformat(), "level": "info", "message": "Processing request"},
                        {"timestamp": datetime.now().isoformat(), "level": "info", "message": "Task completed"}
                    ]
                
                logger.info("Mock agent run status retrieved", 
                           agent_run_id=agent_run_id,
                           status=status)
                
                return result
            
            # Get real agent run status
            response = self.agents_api.get_agent_run_v1_organizations_org_id_agent_run_agent_run_id_get(
                org_id=self.org_id,
                agent_run_id=agent_run_id
            )
            
            result = {
                "success": True,
                "agent_run_id": response.id,
                "status": response.status,
                "result": response.result,
                "error": response.error,
                "started_at": response.started_at,
                "completed_at": response.completed_at,
                "timestamp": datetime.now().isoformat()
            }
            
            # Calculate execution time if completed
            if response.started_at and response.completed_at:
                start = datetime.fromisoformat(response.started_at.replace('Z', '+00:00'))
                end = datetime.fromisoformat(response.completed_at.replace('Z', '+00:00'))
                result["execution_time"] = (end - start).total_seconds()
            
            logger.info("Agent run status retrieved", 
                       agent_run_id=agent_run_id,
                       status=response.status)
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "agent_run_id": agent_run_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            if hasattr(e, 'status'):
                error_result["status_code"] = e.status
            
            logger.error("Failed to get agent run status", 
                        agent_run_id=agent_run_id,
                        error=str(e))
            
            return error_result
    
    async def wait_for_completion(
        self, 
        agent_run_id: str,
        timeout: int = 600,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for agent run to complete
        
        Args:
            agent_run_id: ID of the agent run
            timeout: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Dictionary with final agent run status
        """
        start_time = datetime.now()
        
        logger.info("Waiting for agent run completion", 
                   agent_run_id=agent_run_id,
                   timeout=timeout,
                   poll_interval=poll_interval)
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            status_result = await self.get_agent_run_status(agent_run_id)
            
            if not status_result.get("success"):
                return status_result
            
            status = status_result.get("status")
            
            if status in ["completed", "failed", "cancelled"]:
                logger.info("Agent run completed", 
                           agent_run_id=agent_run_id,
                           final_status=status,
                           wait_time=(datetime.now() - start_time).total_seconds())
                
                return status_result
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        
        # Timeout reached
        timeout_result = {
            "success": False,
            "agent_run_id": agent_run_id,
            "error": f"Timeout waiting for completion after {timeout} seconds",
            "last_status": status_result.get("status", "unknown"),
            "wait_time": timeout,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.warning("Agent run wait timeout", 
                      agent_run_id=agent_run_id,
                      timeout=timeout)
        
        return timeout_result
    
    async def cancel_agent_run(
        self, 
        agent_run_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a running agent run
        
        Args:
            agent_run_id: ID of the agent run to cancel
            reason: Optional reason for cancellation
            
        Returns:
            Dictionary with cancellation result
        """
        logger.info("Cancelling agent run", 
                   agent_run_id=agent_run_id,
                   reason=reason)
        
        try:
            if not self.sdk_available:
                # Mock cancellation
                result = {
                    "success": True,
                    "agent_run_id": agent_run_id,
                    "status": "cancelled",
                    "reason": reason,
                    "cancelled_at": datetime.now().isoformat(),
                    "mock": True
                }
                
                logger.info("Mock agent run cancelled", agent_run_id=agent_run_id)
                return result
            
            # This would use a cancel endpoint if available in the API
            # For now, we'll return a not implemented response
            result = {
                "success": False,
                "agent_run_id": agent_run_id,
                "error": "Cancellation not implemented in current API version",
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "agent_run_id": agent_run_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Failed to cancel agent run", 
                        agent_run_id=agent_run_id,
                        error=str(e))
            
            return error_result
    
    async def list_agent_runs(
        self, 
        status_filter: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List agent runs for the organization
        
        Args:
            status_filter: Optional list of statuses to filter by
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Dictionary with list of agent runs
        """
        logger.info("Listing agent runs", 
                   org_id=self.org_id,
                   status_filter=status_filter,
                   limit=limit,
                   offset=offset)
        
        try:
            if not self.sdk_available:
                # Mock agent runs list
                mock_runs = []
                for i in range(min(limit, 10)):
                    mock_runs.append({
                        "id": f"mock_run_{i + offset}",
                        "status": ["running", "completed", "failed"][i % 3],
                        "created_at": datetime.now().isoformat(),
                        "task_type": "general",
                        "priority": "normal"
                    })
                
                result = {
                    "success": True,
                    "agent_runs": mock_runs,
                    "total": 25,  # Mock total
                    "limit": limit,
                    "offset": offset,
                    "mock": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info("Mock agent runs listed", count=len(mock_runs))
                return result
            
            # This would use a list endpoint if available
            result = {
                "success": False,
                "error": "List endpoint not implemented in current API version",
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Failed to list agent runs", error=str(e))
            return error_result
    
    async def get_organization_info(self) -> Dict[str, Any]:
        """
        Get organization information
        
        Returns:
            Dictionary with organization details
        """
        logger.info("Getting organization info", org_id=self.org_id)
        
        try:
            if not self.sdk_available:
                # Mock organization info
                result = {
                    "success": True,
                    "organization": {
                        "id": self.org_id,
                        "name": "Mock Organization",
                        "plan": "enterprise",
                        "created_at": "2024-01-01T00:00:00Z",
                        "settings": {
                            "max_concurrent_runs": 10,
                            "default_timeout": 3600
                        }
                    },
                    "mock": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info("Mock organization info retrieved")
                return result
            
            # Get real organization info
            response = self.organizations_api.get_organizations_v1_organizations_get()
            
            # Find our organization
            org_info = None
            for org in response.items:
                if org.id == self.org_id:
                    org_info = org
                    break
            
            if not org_info:
                return {
                    "success": False,
                    "error": f"Organization {self.org_id} not found",
                    "timestamp": datetime.now().isoformat()
                }
            
            result = {
                "success": True,
                "organization": {
                    "id": org_info.id,
                    "name": org_info.name,
                    "settings": org_info.settings.__dict__ if org_info.settings else {}
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("Organization info retrieved", org_name=org_info.name)
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Failed to get organization info", error=str(e))
            return error_result
    
    async def validate_api_connection(self) -> Dict[str, Any]:
        """
        Validate API connection and credentials
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating API connection")
        
        start_time = datetime.now()
        
        try:
            if not self.api_token:
                return {
                    "success": False,
                    "error": "API token not configured",
                    "timestamp": start_time.isoformat()
                }
            
            if not self.sdk_available:
                return {
                    "success": True,
                    "message": "Mock validation - SDK not available",
                    "api_host": self.api_host,
                    "org_id": self.org_id,
                    "mock": True,
                    "timestamp": start_time.isoformat()
                }
            
            # Test API connection by getting organization info
            org_result = await self.get_organization_info()
            
            if org_result.get("success"):
                response_time = (datetime.now() - start_time).total_seconds()
                
                result = {
                    "success": True,
                    "message": "API connection validated successfully",
                    "api_host": self.api_host,
                    "org_id": self.org_id,
                    "response_time": response_time,
                    "organization_name": org_result.get("organization", {}).get("name"),
                    "timestamp": start_time.isoformat()
                }
                
                logger.info("API connection validated", response_time=response_time)
                return result
            else:
                return {
                    "success": False,
                    "error": f"API validation failed: {org_result.get('error')}",
                    "api_host": self.api_host,
                    "org_id": self.org_id,
                    "timestamp": start_time.isoformat()
                }
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "api_host": self.api_host,
                "org_id": self.org_id,
                "timestamp": start_time.isoformat()
            }
            
            logger.error("API connection validation failed", error=str(e))
            return error_result
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status and health information
        
        Returns:
            Dictionary with service status
        """
        # Validate API connection
        connection_status = await self.validate_api_connection()
        
        return {
            "service": "CodegenSDKService",
            "status": "healthy" if connection_status.get("success") else "degraded",
            "sdk_available": self.sdk_available,
            "api_token_configured": bool(self.api_token),
            "api_host": self.api_host,
            "org_id": self.org_id,
            "connection_status": connection_status,
            "timestamp": datetime.now().isoformat()
        }

