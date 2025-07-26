"""
Validation Pipeline Orchestrator Service
Manages the complete 6-step validation process with grainchain + web-eval-agent integration
"""

import os
import asyncio
import subprocess
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from backend.services.grainchain_service import GrainchainService
from backend.services.web_eval_service import WebEvalService
from backend.services.gemini_service import GeminiService
from backend.services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)


class ValidationStep:
    """Represents a single validation step"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = "pending"  # pending, running, success, failed
        self.logs: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error: Optional[str] = None

    def start(self):
        self.status = "running"
        self.start_time = datetime.now()
        self.logs.append(f"Started {self.name} at {self.start_time.isoformat()}")

    def complete(self, success: bool = True, error: Optional[str] = None):
        self.status = "success" if success else "failed"
        self.end_time = datetime.now()
        self.error = error
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        self.logs.append(f"Completed {self.name} in {duration:.2f}s - {'SUCCESS' if success else 'FAILED'}")
        if error:
            self.logs.append(f"Error: {error}")

    def add_log(self, message: str):
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "logs": self.logs,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error": self.error,
            "duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None
        }


class ValidationPipeline:
    """Complete validation pipeline orchestrator"""
    
    def __init__(self, project_id: str, pr_url: str, pr_branch: str):
        self.project_id = project_id
        self.pr_url = pr_url
        self.pr_branch = pr_branch
        self.workspace_dir: Optional[str] = None
        self.retry_count = 0
        self.max_retries = 3
        
        # Initialize services
        self.grainchain = GrainchainService()
        self.web_eval = WebEvalService()
        self.gemini = GeminiService()
        self.deployment = DeploymentService()
        
        # Initialize validation steps
        self.steps = [
            ValidationStep("snapshot_creation", "Create sandbox environment with grainchain + web-eval-agent"),
            ValidationStep("code_clone", "Clone PR codebase to sandbox environment"),
            ValidationStep("deployment", "Execute setup commands and deploy application"),
            ValidationStep("deployment_validation", "Validate deployment using Gemini API"),
            ValidationStep("ui_testing", "Run comprehensive UI tests with web-eval-agent"),
            ValidationStep("auto_merge", "Auto-merge PR if validation passes and enabled")
        ]
        
        self.current_step_index = 0
        self.status = "pending"  # pending, running, success, failed, cancelled
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    async def run(self, websocket_callback=None) -> Dict[str, Any]:
        """Run the complete validation pipeline"""
        try:
            self.status = "running"
            self.start_time = datetime.now()
            logger.info(f"Starting validation pipeline for project {self.project_id}, PR: {self.pr_url}")
            
            # Execute each step
            for i, step in enumerate(self.steps):
                self.current_step_index = i
                
                # Send real-time update via WebSocket
                if websocket_callback:
                    await websocket_callback({
                        "type": "validation_update",
                        "project_id": self.project_id,
                        "step_index": i,
                        "step": step.to_dict(),
                        "overall_status": self.status
                    })
                
                success = await self._execute_step(step)
                
                if not success:
                    # Handle failure with retry logic
                    if self.retry_count < self.max_retries and step.name in ["deployment", "ui_testing"]:
                        logger.warning(f"Step {step.name} failed, retrying... ({self.retry_count + 1}/{self.max_retries})")
                        self.retry_count += 1
                        
                        # Send error context to Codegen API for automatic fix
                        await self._send_error_context_to_codegen(step)
                        
                        # Wait for potential PR update and retry
                        await asyncio.sleep(30)  # Wait 30 seconds for PR update
                        success = await self._execute_step(step)
                    
                    if not success:
                        self.status = "failed"
                        self.end_time = datetime.now()
                        logger.error(f"Validation pipeline failed at step: {step.name}")
                        break
            
            if self.status == "running":
                self.status = "success"
                self.end_time = datetime.now()
                logger.info(f"Validation pipeline completed successfully for project {self.project_id}")
            
            return self.to_dict()
            
        except Exception as e:
            self.status = "failed"
            self.end_time = datetime.now()
            logger.error(f"Validation pipeline error: {str(e)}")
            return self.to_dict()
        
        finally:
            # Cleanup workspace
            await self._cleanup()

    async def _execute_step(self, step: ValidationStep) -> bool:
        """Execute a single validation step"""
        step.start()
        
        try:
            if step.name == "snapshot_creation":
                return await self._create_snapshot(step)
            elif step.name == "code_clone":
                return await self._clone_code(step)
            elif step.name == "deployment":
                return await self._deploy_application(step)
            elif step.name == "deployment_validation":
                return await self._validate_deployment(step)
            elif step.name == "ui_testing":
                return await self._run_ui_tests(step)
            elif step.name == "auto_merge":
                return await self._auto_merge_pr(step)
            else:
                step.complete(False, f"Unknown step: {step.name}")
                return False
                
        except Exception as e:
            step.complete(False, str(e))
            return False

    async def _create_snapshot(self, step: ValidationStep) -> bool:
        """Step 1: Create sandbox environment with grainchain + web-eval-agent"""
        step.add_log("Creating sandbox environment...")
        
        try:
            # Create temporary workspace
            self.workspace_dir = tempfile.mkdtemp(prefix=f"validation_{self.project_id}_")
            step.add_log(f"Created workspace: {self.workspace_dir}")
            
            # Initialize grainchain environment
            grainchain_result = await self.grainchain.create_environment(
                workspace_dir=self.workspace_dir,
                project_id=self.project_id
            )
            
            if not grainchain_result["success"]:
                step.complete(False, f"Grainchain setup failed: {grainchain_result['error']}")
                return False
            
            step.add_log("Grainchain environment created successfully")
            
            # Initialize web-eval-agent
            web_eval_result = await self.web_eval.setup_environment(
                workspace_dir=self.workspace_dir,
                project_id=self.project_id
            )
            
            if not web_eval_result["success"]:
                step.complete(False, f"Web-eval-agent setup failed: {web_eval_result['error']}")
                return False
            
            step.add_log("Web-eval-agent environment created successfully")
            step.complete(True)
            return True
            
        except Exception as e:
            step.complete(False, str(e))
            return False

    async def _clone_code(self, step: ValidationStep) -> bool:
        """Step 2: Clone PR codebase to sandbox environment"""
        step.add_log(f"Cloning PR branch: {self.pr_branch}")
        
        try:
            # Extract repository URL from PR URL
            repo_url = self._extract_repo_url(self.pr_url)
            clone_dir = os.path.join(self.workspace_dir, "project")
            
            # Clone repository
            clone_cmd = f"git clone -b {self.pr_branch} {repo_url} {clone_dir}"
            result = subprocess.run(
                clone_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                step.complete(False, f"Git clone failed: {result.stderr}")
                return False
            
            step.add_log(f"Successfully cloned repository to {clone_dir}")
            step.add_log(f"Repository size: {self._get_directory_size(clone_dir)} MB")
            
            step.complete(True)
            return True
            
        except Exception as e:
            step.complete(False, str(e))
            return False

    async def _deploy_application(self, step: ValidationStep) -> bool:
        """Step 3: Execute setup commands and deploy application"""
        step.add_log("Executing setup commands...")
        
        try:
            # Get project configuration and setup commands
            from backend.database import SessionLocal
            from backend.models.project import Project
            
            db = SessionLocal()
            project = db.query(Project).filter(Project.id == self.project_id).first()
            
            if not project or not project.configuration or not project.configuration.setup_commands:
                step.complete(False, "No setup commands configured")
                return False
            
            setup_commands = project.configuration.setup_commands
            secrets = {secret.key: secret.get_decrypted_value() for secret in project.configuration.secrets}
            db.close()
            
            # Execute deployment
            deployment_result = await self.deployment.deploy(
                workspace_dir=os.path.join(self.workspace_dir, "project"),
                setup_commands=setup_commands,
                environment_vars=secrets,
                step_callback=lambda msg: step.add_log(msg)
            )
            
            if not deployment_result["success"]:
                step.complete(False, f"Deployment failed: {deployment_result['error']}")
                return False
            
            step.add_log("Application deployed successfully")
            step.complete(True)
            return True
            
        except Exception as e:
            step.complete(False, str(e))
            return False

    async def _validate_deployment(self, step: ValidationStep) -> bool:
        """Step 4: Validate deployment using Gemini API"""
        step.add_log("Validating deployment with Gemini API...")
        
        try:
            # Get deployment context
            deployment_logs = self.steps[2].logs  # Deployment step logs
            
            # Use Gemini to validate deployment
            validation_result = await self.gemini.validate_deployment(
                deployment_logs=deployment_logs,
                workspace_dir=self.workspace_dir,
                project_id=self.project_id
            )
            
            if not validation_result["success"]:
                step.complete(False, f"Deployment validation failed: {validation_result['error']}")
                return False
            
            step.add_log("Deployment validation passed")
            step.add_log(f"Validation score: {validation_result.get('score', 'N/A')}")
            
            step.complete(True)
            return True
            
        except Exception as e:
            step.complete(False, str(e))
            return False

    async def _run_ui_tests(self, step: ValidationStep) -> bool:
        """Step 5: Run comprehensive UI tests with web-eval-agent"""
        step.add_log("Running UI tests with web-eval-agent...")
        
        try:
            # Run comprehensive UI testing
            ui_test_result = await self.web_eval.run_comprehensive_tests(
                workspace_dir=self.workspace_dir,
                project_id=self.project_id,
                step_callback=lambda msg: step.add_log(msg)
            )
            
            if not ui_test_result["success"]:
                step.complete(False, f"UI tests failed: {ui_test_result['error']}")
                return False
            
            step.add_log("All UI tests passed successfully")
            step.add_log(f"Tests run: {ui_test_result.get('tests_count', 'N/A')}")
            step.add_log(f"Success rate: {ui_test_result.get('success_rate', 'N/A')}%")
            
            step.complete(True)
            return True
            
        except Exception as e:
            step.complete(False, str(e))
            return False

    async def _auto_merge_pr(self, step: ValidationStep) -> bool:
        """Step 6: Auto-merge PR if validation passes and enabled"""
        step.add_log("Checking auto-merge settings...")
        
        try:
            # Get project auto-merge setting
            from backend.database import SessionLocal
            from backend.models.project import Project
            
            db = SessionLocal()
            project = db.query(Project).filter(Project.id == self.project_id).first()
            
            if not project:
                step.complete(False, "Project not found")
                return False
            
            if not project.auto_merge_validated_pr:
                step.add_log("Auto-merge is disabled for this project")
                step.complete(True)
                return True
            
            # TODO: Implement GitHub API integration to merge PR
            step.add_log("Auto-merge is enabled - merging PR...")
            step.add_log(f"PR {self.pr_url} would be merged automatically")
            
            step.complete(True)
            return True
            
        except Exception as e:
            step.complete(False, str(e))
            return False

    async def _send_error_context_to_codegen(self, failed_step: ValidationStep):
        """Send error context to Codegen API for automatic fix"""
        try:
            # TODO: Implement Codegen API integration
            error_context = {
                "step": failed_step.name,
                "error": failed_step.error,
                "logs": failed_step.logs,
                "project_id": self.project_id,
                "pr_url": self.pr_url
            }
            
            logger.info(f"Sending error context to Codegen API: {error_context}")
            # This would send the error context to continue the agent run
            
        except Exception as e:
            logger.error(f"Failed to send error context to Codegen: {str(e)}")

    def _extract_repo_url(self, pr_url: str) -> str:
        """Extract repository URL from PR URL"""
        # Example: https://github.com/user/repo/pull/123 -> https://github.com/user/repo.git
        parts = pr_url.split('/')
        if len(parts) >= 5:
            return f"https://github.com/{parts[3]}/{parts[4]}.git"
        raise ValueError(f"Invalid PR URL format: {pr_url}")

    def _get_directory_size(self, directory: str) -> float:
        """Get directory size in MB"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return round(total_size / (1024 * 1024), 2)

    async def _cleanup(self):
        """Cleanup workspace and resources"""
        if self.workspace_dir and os.path.exists(self.workspace_dir):
            try:
                shutil.rmtree(self.workspace_dir)
                logger.info(f"Cleaned up workspace: {self.workspace_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup workspace: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert pipeline to dictionary for API responses"""
        return {
            "project_id": self.project_id,
            "pr_url": self.pr_url,
            "pr_branch": self.pr_branch,
            "status": self.status,
            "current_step_index": self.current_step_index,
            "retry_count": self.retry_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
            "steps": [step.to_dict() for step in self.steps]
        }
