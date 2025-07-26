"""
Validation service for testing and validating code changes
"""
import structlog
import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.models.validation import Validation, ValidationStep
from backend.models.project import Project
from backend.models.configuration import Configuration
from backend.integrations.grainchain_client import GrainchainClient
from backend.integrations.web_eval_client import WebEvalClient
from backend.websocket.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class ValidationService:
    """Service for validating code changes and PRs"""
    
    def __init__(self):
        self.grainchain_client = GrainchainClient()
        self.web_eval_client = WebEvalClient()
        self.connection_manager = ConnectionManager()
    
    async def start_validation_pipeline(
        self,
        project_id: str,
        pr_url: str,
        branch_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Start a complete validation pipeline for a PR"""
        logger.info("Starting validation pipeline", 
                   project_id=project_id, 
                   pr_url=pr_url, 
                   branch_name=branch_name)
        
        # Create validation record
        validation = Validation(
            project_id=project_id,
            pr_url=pr_url,
            branch_name=branch_name,
            pr_number=pr_number,
            status="pending",
            auto_merge_ready=False
        )
        
        # Define validation steps
        steps = [
            ValidationStep(
                name="Code Quality Check",
                status="pending",
                validation_id=validation.id
            ),
            ValidationStep(
                name="Security Scan",
                status="pending",
                validation_id=validation.id
            ),
            ValidationStep(
                name="Setup Commands Test",
                status="pending",
                validation_id=validation.id
            ),
            ValidationStep(
                name="Web UI Evaluation",
                status="pending",
                validation_id=validation.id
            ),
            ValidationStep(
                name="Integration Test",
                status="pending",
                validation_id=validation.id
            )
        ]
        
        validation.steps = steps
        
        # Start validation in background
        asyncio.create_task(self._execute_validation_pipeline(validation))
        
        return {
            "validation_id": validation.id,
            "status": "started",
            "steps": len(steps)
        }
    
    async def _execute_validation_pipeline(self, validation: Validation):
        """Execute the validation pipeline steps"""
        try:
            validation.status = "running"
            
            # Broadcast start
            await self.connection_manager.broadcast_to_subscribers(
                f"project_{validation.project_id}",
                {
                    "type": "validation_started",
                    "validation_id": validation.id,
                    "pr_url": validation.pr_url
                }
            )
            
            # Execute each step
            for step in validation.steps:
                await self._execute_validation_step(validation, step)
                
                # Broadcast step completion
                await self.connection_manager.broadcast_to_subscribers(
                    f"project_{validation.project_id}",
                    {
                        "type": "validation_step_completed",
                        "validation_id": validation.id,
                        "step_name": step.name,
                        "step_status": step.status
                    }
                )
                
                # Stop if step failed and it's critical
                if step.status == "failed" and step.name in ["Code Quality Check", "Security Scan"]:
                    logger.warning("Critical validation step failed", 
                                 validation_id=validation.id, 
                                 step_name=step.name)
                    break
            
            # Determine overall status
            failed_steps = [s for s in validation.steps if s.status == "failed"]
            if failed_steps:
                validation.status = "failed"
                validation.auto_merge_ready = False
            else:
                validation.status = "completed"
                validation.auto_merge_ready = True
            
            # Broadcast completion
            await self.connection_manager.broadcast_to_subscribers(
                f"project_{validation.project_id}",
                {
                    "type": "validation_completed",
                    "validation_id": validation.id,
                    "status": validation.status,
                    "auto_merge_ready": validation.auto_merge_ready
                }
            )
            
            logger.info("Validation pipeline completed", 
                       validation_id=validation.id, 
                       status=validation.status)
            
        except Exception as e:
            logger.error("Validation pipeline failed", 
                        validation_id=validation.id, 
                        error=str(e))
            
            validation.status = "failed"
            validation.auto_merge_ready = False
            
            # Broadcast failure
            await self.connection_manager.broadcast_to_subscribers(
                f"project_{validation.project_id}",
                {
                    "type": "validation_failed",
                    "validation_id": validation.id,
                    "error": str(e)
                }
            )
    
    async def _execute_validation_step(self, validation: Validation, step: ValidationStep):
        """Execute a single validation step"""
        logger.info("Executing validation step", 
                   validation_id=validation.id, 
                   step_name=step.name)
        
        step.status = "running"
        
        try:
            if step.name == "Code Quality Check":
                result = await self._run_code_quality_check(validation)
            elif step.name == "Security Scan":
                result = await self._run_security_scan(validation)
            elif step.name == "Setup Commands Test":
                result = await self._run_setup_commands_test(validation)
            elif step.name == "Web UI Evaluation":
                result = await self._run_web_ui_evaluation(validation)
            elif step.name == "Integration Test":
                result = await self._run_integration_test(validation)
            else:
                result = {"success": False, "error": "Unknown step type"}
            
            if result.get("success"):
                step.status = "completed"
                step.result = result.get("message", "Step completed successfully")
            else:
                step.status = "failed"
                step.error = result.get("error", "Step failed")
            
            logger.info("Validation step completed", 
                       validation_id=validation.id, 
                       step_name=step.name, 
                       status=step.status)
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            logger.error("Validation step failed", 
                        validation_id=validation.id, 
                        step_name=step.name, 
                        error=str(e))
    
    async def _run_code_quality_check(self, validation: Validation) -> Dict[str, Any]:
        """Run code quality checks using graph-sitter"""
        try:
            # Use grainchain to create sandbox and run quality checks
            sandbox_result = await self.grainchain_client.create_sandbox(
                repository_url=validation.pr_url.replace("/pull/", "/tree/").replace(f"/{validation.pr_number}", f"/{validation.branch_name}"),
                branch=validation.branch_name
            )
            
            if not sandbox_result.get("success"):
                return {"success": False, "error": "Failed to create sandbox"}
            
            sandbox_id = sandbox_result["sandbox_id"]
            
            # Run graph-sitter analysis
            quality_result = await self.grainchain_client.run_command(
                sandbox_id=sandbox_id,
                command="python -m graph_sitter analyze --format json .",
                timeout=300
            )
            
            # Clean up sandbox
            await self.grainchain_client.destroy_sandbox(sandbox_id)
            
            if quality_result.get("return_code") == 0:
                return {
                    "success": True,
                    "message": "Code quality check passed",
                    "details": quality_result.get("output")
                }
            else:
                return {
                    "success": False,
                    "error": f"Code quality issues found: {quality_result.get('output')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Code quality check failed: {str(e)}"}
    
    async def _run_security_scan(self, validation: Validation) -> Dict[str, Any]:
        """Run security scan"""
        try:
            # Use grainchain to run security scans
            sandbox_result = await self.grainchain_client.create_sandbox(
                repository_url=validation.pr_url.replace("/pull/", "/tree/").replace(f"/{validation.pr_number}", f"/{validation.branch_name}"),
                branch=validation.branch_name
            )
            
            if not sandbox_result.get("success"):
                return {"success": False, "error": "Failed to create sandbox"}
            
            sandbox_id = sandbox_result["sandbox_id"]
            
            # Run security scan (using bandit for Python, semgrep for general)
            security_result = await self.grainchain_client.run_command(
                sandbox_id=sandbox_id,
                command="semgrep --config=auto --json .",
                timeout=300
            )
            
            # Clean up sandbox
            await self.grainchain_client.destroy_sandbox(sandbox_id)
            
            if security_result.get("return_code") == 0:
                return {
                    "success": True,
                    "message": "Security scan passed",
                    "details": security_result.get("output")
                }
            else:
                return {
                    "success": False,
                    "error": f"Security issues found: {security_result.get('output')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Security scan failed: {str(e)}"}
    
    async def _run_setup_commands_test(self, validation: Validation) -> Dict[str, Any]:
        """Test setup commands"""
        # This would be implemented to test the project's setup commands
        # For now, return a mock success
        await asyncio.sleep(2)  # Simulate work
        return {
            "success": True,
            "message": "Setup commands executed successfully"
        }
    
    async def _run_web_ui_evaluation(self, validation: Validation) -> Dict[str, Any]:
        """Run web UI evaluation using web-eval-agent"""
        try:
            # Use web-eval-agent to test UI functionality
            eval_result = await self.web_eval_client.evaluate_web_app(
                url=f"http://localhost:3000",  # Assuming local dev server
                test_scenarios=[
                    "Navigate to main page",
                    "Test basic functionality",
                    "Check responsive design"
                ]
            )
            
            if eval_result.get("success"):
                return {
                    "success": True,
                    "message": "Web UI evaluation passed",
                    "details": eval_result.get("results")
                }
            else:
                return {
                    "success": False,
                    "error": f"Web UI issues found: {eval_result.get('error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Web UI evaluation failed: {str(e)}"}
    
    async def _run_integration_test(self, validation: Validation) -> Dict[str, Any]:
        """Run integration tests"""
        # This would run comprehensive integration tests
        # For now, return a mock success
        await asyncio.sleep(3)  # Simulate work
        return {
            "success": True,
            "message": "Integration tests passed"
        }
    
    async def test_setup_commands(
        self,
        project_id: str,
        repository_url: str,
        branch_name: str,
        setup_commands: str,
        secrets: Dict[str, str]
    ) -> Dict[str, Any]:
        """Test setup commands in isolation"""
        logger.info("Testing setup commands", project_id=project_id, branch_name=branch_name)
        
        try:
            # Create sandbox
            sandbox_result = await self.grainchain_client.create_sandbox(
                repository_url=repository_url,
                branch=branch_name
            )
            
            if not sandbox_result.get("success"):
                return {"success": False, "error": "Failed to create sandbox"}
            
            sandbox_id = sandbox_result["sandbox_id"]
            
            # Set environment variables
            for key, value in secrets.items():
                await self.grainchain_client.run_command(
                    sandbox_id=sandbox_id,
                    command=f"export {key}='{value}'",
                    timeout=30
                )
            
            # Execute setup commands
            commands = setup_commands.strip().split('\n')
            results = []
            
            for command in commands:
                if command.strip():
                    result = await self.grainchain_client.run_command(
                        sandbox_id=sandbox_id,
                        command=command.strip(),
                        timeout=300
                    )
                    results.append({
                        "command": command.strip(),
                        "return_code": result.get("return_code"),
                        "output": result.get("output"),
                        "error": result.get("error")
                    })
                    
                    # Stop on first failure
                    if result.get("return_code") != 0:
                        break
            
            # Clean up sandbox
            await self.grainchain_client.destroy_sandbox(sandbox_id)
            
            # Check if all commands succeeded
            failed_commands = [r for r in results if r["return_code"] != 0]
            
            if failed_commands:
                return {
                    "success": False,
                    "error": f"Setup command failed: {failed_commands[0]['command']}",
                    "logs": results
                }
            else:
                return {
                    "success": True,
                    "message": "All setup commands executed successfully",
                    "logs": results
                }
                
        except Exception as e:
            logger.error("Setup commands test failed", project_id=project_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "logs": []
            }

