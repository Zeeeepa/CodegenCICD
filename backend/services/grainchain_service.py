"""
Grainchain Integration Service
Provides unified sandbox management and code execution capabilities
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

try:
    from grainchain import Sandbox, SandboxConfig, get_available_providers
    GRAINCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("Grainchain not available - using mock implementation")
    GRAINCHAIN_AVAILABLE = False


class MockSandboxResult:
    """Mock result for when Grainchain is not available"""
    def __init__(self, stdout: str = "", stderr: str = "", exit_code: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.execution_time = 0.1


class MockSandbox:
    """Mock sandbox for when Grainchain is not available"""
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def execute(self, code: str) -> MockSandboxResult:
        # Simple mock execution
        if "print(" in code:
            output = "Mock execution output"
        elif "error" in code.lower():
            return MockSandboxResult("", "Mock error", 1)
        else:
            output = "Mock command executed successfully"
        
        return MockSandboxResult(stdout=output, stderr="", exit_code=0)
    
    async def upload_file(self, filename: str, content: str) -> bool:
        return True
    
    async def download_file(self, filename: str) -> str:
        return "Mock file content"
    
    async def create_snapshot(self) -> str:
        return f"mock_snapshot_{datetime.now().timestamp()}"
    
    async def restore_snapshot(self, snapshot_id: str) -> bool:
        return True


class GrainchainService:
    """
    Service for managing sandbox environments and code execution
    using the Grainchain library
    """
    
    def __init__(self):
        self.default_provider = os.environ.get("GRAINCHAIN_DEFAULT_PROVIDER", "local")
        self.available_providers = self._get_available_providers()
        
        # Configure sandbox settings for different providers
        self.sandbox_configs = {
            "local": self._create_config(timeout=300, memory_limit="1GB"),
            "e2b": self._create_config(timeout=600, memory_limit="2GB", cpu_limit=2.0),
            "daytona": self._create_config(timeout=900, memory_limit="4GB", cpu_limit=4.0),
            "morph": self._create_config(timeout=450, memory_limit="2GB", cpu_limit=2.0)
        }
        
        logger.info("GrainchainService initialized", 
                   default_provider=self.default_provider,
                   available_providers=self.available_providers)
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available sandbox providers"""
        if not GRAINCHAIN_AVAILABLE:
            return ["mock"]
        
        try:
            return get_available_providers()
        except Exception as e:
            logger.warning("Failed to get available providers", error=str(e))
            return ["local"]  # Fallback to local
    
    def _create_config(self, **kwargs) -> Optional[Any]:
        """Create sandbox configuration"""
        if not GRAINCHAIN_AVAILABLE:
            return None
        
        try:
            return SandboxConfig(**kwargs)
        except Exception as e:
            logger.warning("Failed to create sandbox config", error=str(e))
            return None
    
    async def execute_code(
        self, 
        code: str, 
        provider: Optional[str] = None,
        timeout: Optional[int] = None,
        environment_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute code in a sandbox environment
        
        Args:
            code: Code to execute
            provider: Sandbox provider to use (local, e2b, daytona, morph)
            timeout: Execution timeout in seconds
            environment_vars: Environment variables to set
            
        Returns:
            Dictionary with execution results
        """
        provider = provider or self.default_provider
        start_time = datetime.now()
        
        logger.info("Executing code in sandbox", 
                   provider=provider, 
                   code_length=len(code))
        
        try:
            if not GRAINCHAIN_AVAILABLE:
                # Use mock implementation
                async with MockSandbox() as sandbox:
                    result = await sandbox.execute(code)
            else:
                # Use real Grainchain
                config = self.sandbox_configs.get(provider)
                if timeout:
                    config = SandboxConfig(timeout=timeout, **(config.__dict__ if config else {}))
                
                async with Sandbox(provider=provider, config=config) as sandbox:
                    # Set environment variables if provided
                    if environment_vars:
                        for key, value in environment_vars.items():
                            await sandbox.execute(f"export {key}='{value}'")
                    
                    result = await sandbox.execute(code)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            response = {
                "success": result.exit_code == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "execution_time": execution_time,
                "provider": provider,
                "timestamp": start_time.isoformat()
            }
            
            logger.info("Code execution completed", 
                       provider=provider,
                       success=response["success"],
                       execution_time=execution_time)
            
            return response
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_response = {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "execution_time": execution_time,
                "provider": provider,
                "error": str(e),
                "timestamp": start_time.isoformat()
            }
            
            logger.error("Code execution failed", 
                        provider=provider,
                        error=str(e),
                        execution_time=execution_time)
            
            return error_response
    
    async def upload_file(
        self, 
        filename: str, 
        content: str, 
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to the sandbox
        
        Args:
            filename: Name of the file
            content: File content
            provider: Sandbox provider to use
            
        Returns:
            Dictionary with upload results
        """
        provider = provider or self.default_provider
        
        logger.info("Uploading file to sandbox", 
                   filename=filename, 
                   provider=provider,
                   content_size=len(content))
        
        try:
            if not GRAINCHAIN_AVAILABLE:
                async with MockSandbox() as sandbox:
                    success = await sandbox.upload_file(filename, content)
            else:
                config = self.sandbox_configs.get(provider)
                async with Sandbox(provider=provider, config=config) as sandbox:
                    success = await sandbox.upload_file(filename, content)
            
            response = {
                "success": success,
                "filename": filename,
                "size": len(content),
                "provider": provider,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("File upload completed", 
                       filename=filename,
                       provider=provider,
                       success=success)
            
            return response
            
        except Exception as e:
            error_response = {
                "success": False,
                "filename": filename,
                "provider": provider,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("File upload failed", 
                        filename=filename,
                        provider=provider,
                        error=str(e))
            
            return error_response
    
    async def download_file(
        self, 
        filename: str, 
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download a file from the sandbox
        
        Args:
            filename: Name of the file to download
            provider: Sandbox provider to use
            
        Returns:
            Dictionary with download results
        """
        provider = provider or self.default_provider
        
        logger.info("Downloading file from sandbox", 
                   filename=filename, 
                   provider=provider)
        
        try:
            if not GRAINCHAIN_AVAILABLE:
                async with MockSandbox() as sandbox:
                    content = await sandbox.download_file(filename)
            else:
                config = self.sandbox_configs.get(provider)
                async with Sandbox(provider=provider, config=config) as sandbox:
                    content = await sandbox.download_file(filename)
            
            response = {
                "success": True,
                "filename": filename,
                "content": content,
                "size": len(content),
                "provider": provider,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("File download completed", 
                       filename=filename,
                       provider=provider,
                       size=len(content))
            
            return response
            
        except Exception as e:
            error_response = {
                "success": False,
                "filename": filename,
                "provider": provider,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("File download failed", 
                        filename=filename,
                        provider=provider,
                        error=str(e))
            
            return error_response
    
    async def create_snapshot(
        self, 
        provider: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a snapshot of the current sandbox state
        
        Args:
            provider: Sandbox provider to use
            description: Optional description for the snapshot
            
        Returns:
            Dictionary with snapshot creation results
        """
        provider = provider or self.default_provider
        
        logger.info("Creating sandbox snapshot", 
                   provider=provider,
                   description=description)
        
        try:
            if not GRAINCHAIN_AVAILABLE:
                async with MockSandbox() as sandbox:
                    snapshot_id = await sandbox.create_snapshot()
            else:
                config = self.sandbox_configs.get(provider)
                async with Sandbox(provider=provider, config=config) as sandbox:
                    snapshot_id = await sandbox.create_snapshot()
            
            response = {
                "success": True,
                "snapshot_id": snapshot_id,
                "provider": provider,
                "description": description,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("Snapshot created successfully", 
                       snapshot_id=snapshot_id,
                       provider=provider)
            
            return response
            
        except Exception as e:
            error_response = {
                "success": False,
                "provider": provider,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Snapshot creation failed", 
                        provider=provider,
                        error=str(e))
            
            return error_response
    
    async def restore_snapshot(
        self, 
        snapshot_id: str, 
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Restore a sandbox from a snapshot
        
        Args:
            snapshot_id: ID of the snapshot to restore
            provider: Sandbox provider to use
            
        Returns:
            Dictionary with restoration results
        """
        provider = provider or self.default_provider
        
        logger.info("Restoring sandbox snapshot", 
                   snapshot_id=snapshot_id,
                   provider=provider)
        
        try:
            if not GRAINCHAIN_AVAILABLE:
                async with MockSandbox() as sandbox:
                    success = await sandbox.restore_snapshot(snapshot_id)
            else:
                config = self.sandbox_configs.get(provider)
                async with Sandbox(provider=provider, config=config) as sandbox:
                    success = await sandbox.restore_snapshot(snapshot_id)
            
            response = {
                "success": success,
                "snapshot_id": snapshot_id,
                "provider": provider,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("Snapshot restored successfully", 
                       snapshot_id=snapshot_id,
                       provider=provider,
                       success=success)
            
            return response
            
        except Exception as e:
            error_response = {
                "success": False,
                "snapshot_id": snapshot_id,
                "provider": provider,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Snapshot restoration failed", 
                        snapshot_id=snapshot_id,
                        provider=provider,
                        error=str(e))
            
            return error_response
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """
        Get status of all available sandbox providers
        
        Returns:
            Dictionary with provider status information
        """
        logger.info("Getting provider status")
        
        status = {
            "available_providers": self.available_providers,
            "default_provider": self.default_provider,
            "grainchain_available": GRAINCHAIN_AVAILABLE,
            "provider_configs": {}
        }
        
        for provider in self.available_providers:
            try:
                # Test provider availability with a simple command
                test_result = await self.execute_code(
                    "echo 'Provider test'", 
                    provider=provider
                )
                
                status["provider_configs"][provider] = {
                    "available": test_result["success"],
                    "response_time": test_result["execution_time"],
                    "last_tested": test_result["timestamp"]
                }
                
            except Exception as e:
                status["provider_configs"][provider] = {
                    "available": False,
                    "error": str(e),
                    "last_tested": datetime.now().isoformat()
                }
        
        logger.info("Provider status retrieved", 
                   available_count=len([p for p in status["provider_configs"].values() if p.get("available")]))
        
        return status
    
    async def run_performance_benchmark(
        self, 
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run performance benchmark on a sandbox provider
        
        Args:
            provider: Sandbox provider to benchmark
            
        Returns:
            Dictionary with benchmark results
        """
        provider = provider or self.default_provider
        
        logger.info("Running performance benchmark", provider=provider)
        
        benchmark_tests = [
            ("Basic Command", "echo 'Hello World'"),
            ("Python Execution", "python -c 'print(sum(range(1000)))'"),
            ("File Operations", "echo 'test content' > test.txt && cat test.txt"),
            ("CPU Test", "python -c 'sum(i*i for i in range(10000))'"),
        ]
        
        results = {
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }
        
        total_time = 0
        successful_tests = 0
        
        for test_name, test_code in benchmark_tests:
            try:
                result = await self.execute_code(test_code, provider=provider)
                
                results["tests"][test_name] = {
                    "success": result["success"],
                    "execution_time": result["execution_time"],
                    "exit_code": result["exit_code"]
                }
                
                if result["success"]:
                    successful_tests += 1
                    total_time += result["execution_time"]
                
            except Exception as e:
                results["tests"][test_name] = {
                    "success": False,
                    "error": str(e),
                    "execution_time": 0
                }
        
        results["summary"] = {
            "total_tests": len(benchmark_tests),
            "successful_tests": successful_tests,
            "success_rate": (successful_tests / len(benchmark_tests)) * 100,
            "average_execution_time": total_time / max(successful_tests, 1),
            "total_execution_time": total_time
        }
        
        logger.info("Performance benchmark completed", 
                   provider=provider,
                   success_rate=results["summary"]["success_rate"],
                   avg_time=results["summary"]["average_execution_time"])
        
        return results

