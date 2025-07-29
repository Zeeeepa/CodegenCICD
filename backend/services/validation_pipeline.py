"""
Validation pipeline for PR testing with Graph-Sitter, Grainchain, and Web-Eval-Agent
"""
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

from backend.models.project import Project, ProjectAgentRun, ValidationRun, ProjectSecret
from backend.database import get_db_session
from backend.integrations.github_client import GitHubClient
from backend.integrations.codegen_client import CodegenClient
from backend.services.grainchain_client import GrainchainClient
from backend.services.web_eval_client import WebEvalClient
from backend.services.graph_sitter_client import GraphSitterClient
from backend.integrations.gemini_client import GeminiClient
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ValidationPipeline:
    """Comprehensive PR validation pipeline"""
    
    def __init__(self):
        self.github_client = GitHubClient()
        self.codegen_client = CodegenClient()
        self.grainchain_client = GrainchainClient()
        self.web_eval_client = WebEvalClient()
        self.graph_sitter_client = GraphSitterClient()
        self.gemini_client = GeminiClient()
    
    async def start_validation(self, project_id: int, pr_number: int, agent_run_id: Optional[int] = None) -> int:
        """Start validation pipeline for a PR"""
        try:
            async with get_db_session() as db:
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    raise ValueError(f"Project {project_id} not found")
                
                # Create validation run record
                validation_run = ValidationRun(
                    agent_run_id=agent_run_id,
                    pr_number=pr_number,
                    status="pending"
                )
                db.add(validation_run)
                db.commit()
                db.refresh(validation_run)
                
                logger.info("Validation pipeline started", 
                           validation_run_id=validation_run.id,
                           project_id=project_id,
                           pr_number=pr_number)
                
                # Start validation in background
                asyncio.create_task(self._execute_validation(validation_run.id))
                
                return validation_run.id
                
        except Exception as e:
            logger.error("Failed to start validation pipeline", 
                        project_id=project_id, 
                        pr_number=pr_number, 
                        error=str(e))
            raise
    
    async def _execute_validation(self, validation_run_id: int):
        """Execute the complete validation pipeline"""
        try:
            async with get_db_session() as db:
                validation_run = db.query(ValidationRun).filter(ValidationRun.id == validation_run_id).first()
                if not validation_run:
                    return
                
                # Get project and agent run
                agent_run = None
                if validation_run.agent_run_id:
                    agent_run = db.query(ProjectAgentRun).filter(
                        ProjectAgentRun.id == validation_run.agent_run_id
                    ).first()
                
                if not agent_run:
                    logger.error("Agent run not found", validation_run_id=validation_run_id)
                    return
                
                project = db.query(Project).filter(Project.id == agent_run.project_id).first()
                if not project:
                    logger.error("Project not found", validation_run_id=validation_run_id)
                    return
                
                # Update status
                validation_run.status = "running"
                db.commit()
                
                # Execute validation steps
                success = await self._run_validation_steps(validation_run, project, agent_run)
                
                # Update final status
                validation_run.status = "passed" if success else "failed"
                validation_run.completed_at = datetime.utcnow()
                db.commit()
                
                # Handle results
                if success:
                    await self._handle_validation_success(validation_run, project, agent_run)
                else:
                    await self._handle_validation_failure(validation_run, project, agent_run)
                
        except Exception as e:
            logger.error("Validation pipeline execution failed", 
                        validation_run_id=validation_run_id, 
                        error=str(e))
            
            # Update status to failed
            async with get_db_session() as db:
                validation_run = db.query(ValidationRun).filter(ValidationRun.id == validation_run_id).first()
                if validation_run:
                    validation_run.status = "failed"
                    validation_run.error_logs = {"error": str(e)}
                    validation_run.completed_at = datetime.utcnow()
                    db.commit()
    
    async def _run_validation_steps(self, validation_run: ValidationRun, project: Project, agent_run: ProjectAgentRun) -> bool:
        """Run all validation steps"""
        try:
            # Step 1: Create snapshot with Grainchain
            logger.info("Step 1: Creating snapshot", validation_run_id=validation_run.id)
            snapshot_success = await self._create_snapshot(validation_run, project)
            if not snapshot_success:
                return False
            
            # Step 2: Clone PR codebase
            logger.info("Step 2: Cloning PR codebase", validation_run_id=validation_run.id)
            clone_success = await self._clone_pr_codebase(validation_run, project)
            if not clone_success:
                return False
            
            # Step 3: Run deployment commands
            logger.info("Step 3: Running deployment commands", validation_run_id=validation_run.id)
            deployment_success = await self._run_deployment_commands(validation_run, project)
            if not deployment_success:
                # Try to fix deployment issues
                fix_success = await self._attempt_deployment_fix(validation_run, project, agent_run)
                if not fix_success:
                    return False
            
            # Step 4: Run Web-Eval-Agent tests
            logger.info("Step 4: Running Web-Eval-Agent tests", validation_run_id=validation_run.id)
            web_eval_success = await self._run_web_eval_tests(validation_run, project)
            if not web_eval_success:
                # Try to fix web evaluation issues
                fix_success = await self._attempt_web_eval_fix(validation_run, project, agent_run)
                if not fix_success:
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Validation steps failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
            return False
    
    async def _create_snapshot(self, validation_run: ValidationRun, project: Project) -> bool:
        """Create snapshot using Grainchain"""
        try:
            # Get project secrets for environment setup
            async with get_db_session() as db:
                secrets = db.query(ProjectSecret).filter(
                    ProjectSecret.project_id == project.id
                ).all()
                
                env_vars = {secret.key: secret.value for secret in secrets}
                
                # Add required service URLs
                env_vars.update({
                    "GRAPH_SITTER_URL": settings.graph_sitter_url,
                    "WEB_EVAL_AGENT_URL": settings.web_eval_agent_url,
                    "GEMINI_API_KEY": settings.gemini_api_key
                })
            
            # Create snapshot with Grainchain
            snapshot_id = await self.grainchain_client.create_snapshot(
                name=f"validation-{validation_run.id}",
                environment_vars=env_vars,
                services=["graph-sitter", "web-eval-agent"]
            )
            
            if snapshot_id:
                validation_run.snapshot_created = True
                async with get_db_session() as db:
                    db.merge(validation_run)
                    db.commit()
                
                logger.info("Snapshot created successfully", 
                           validation_run_id=validation_run.id,
                           snapshot_id=snapshot_id)
                return True
            else:
                logger.error("Failed to create snapshot", validation_run_id=validation_run.id)
                return False
                
        except Exception as e:
            logger.error("Snapshot creation failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
            return False
    
    async def _clone_pr_codebase(self, validation_run: ValidationRun, project: Project) -> bool:
        """Clone PR codebase"""
        try:
            # Get PR details from GitHub
            pr_data = await self.github_client.get_pull_request(
                project.github_owner,
                project.github_repo,
                validation_run.pr_number
            )
            
            if not pr_data:
                logger.error("Failed to get PR data", validation_run_id=validation_run.id)
                return False
            
            # Clone the PR branch using Grainchain
            clone_success = await self.grainchain_client.clone_repository(
                repo_url=project.github_url,
                branch=pr_data.get("head", {}).get("ref"),
                target_dir=f"/tmp/validation-{validation_run.id}"
            )
            
            if clone_success:
                validation_run.codebase_cloned = True
                async with get_db_session() as db:
                    db.merge(validation_run)
                    db.commit()
                
                logger.info("Codebase cloned successfully", validation_run_id=validation_run.id)
                return True
            else:
                logger.error("Failed to clone codebase", validation_run_id=validation_run.id)
                return False
                
        except Exception as e:
            logger.error("Codebase cloning failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
            return False
    
    async def _run_deployment_commands(self, validation_run: ValidationRun, project: Project) -> bool:
        """Run deployment commands"""
        try:
            if not project.setup_commands:
                logger.warning("No setup commands configured", validation_run_id=validation_run.id)
                return True
            
            # Execute setup commands using Grainchain
            execution_result = await self.grainchain_client.execute_commands(
                commands=project.setup_commands.split('\n'),
                working_dir=f"/tmp/validation-{validation_run.id}",
                timeout=300  # 5 minutes timeout
            )
            
            # Store deployment logs
            validation_run.deployment_logs = execution_result
            async with get_db_session() as db:
                db.merge(validation_run)
                db.commit()
            
            if execution_result.get("success", False):
                validation_run.deployment_successful = True
                async with get_db_session() as db:
                    db.merge(validation_run)
                    db.commit()
                
                logger.info("Deployment commands executed successfully", 
                           validation_run_id=validation_run.id)
                return True
            else:
                logger.error("Deployment commands failed", 
                           validation_run_id=validation_run.id,
                           logs=execution_result.get("logs"))
                return False
                
        except Exception as e:
            logger.error("Deployment execution failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
            return False
    
    async def _run_web_eval_tests(self, validation_run: ValidationRun, project: Project) -> bool:
        """Run Web-Eval-Agent tests"""
        try:
            # Define test scenarios
            test_scenarios = [
                {
                    "name": "homepage_load",
                    "description": "Test if homepage loads correctly",
                    "url": "http://localhost:3000",  # Adjust based on project
                    "checks": ["page_loads", "no_errors", "basic_elements"]
                },
                {
                    "name": "navigation_test",
                    "description": "Test navigation functionality",
                    "url": "http://localhost:3000",
                    "checks": ["navigation_works", "links_functional"]
                },
                {
                    "name": "form_functionality",
                    "description": "Test form submissions and interactions",
                    "url": "http://localhost:3000",
                    "checks": ["forms_work", "validation_works"]
                }
            ]
            
            # Run tests using Web-Eval-Agent
            test_results = await self.web_eval_client.run_test_suite(
                scenarios=test_scenarios,
                base_url="http://localhost:3000",  # Adjust based on deployment
                timeout=180  # 3 minutes per test
            )
            
            # Store test results
            validation_run.web_eval_results = test_results
            async with get_db_session() as db:
                db.merge(validation_run)
                db.commit()
            
            # Check if all tests passed
            all_passed = all(
                result.get("status") == "passed" 
                for result in test_results.get("results", [])
            )
            
            if all_passed:
                validation_run.web_eval_passed = True
                async with get_db_session() as db:
                    db.merge(validation_run)
                    db.commit()
                
                logger.info("Web-Eval tests passed", validation_run_id=validation_run.id)
                return True
            else:
                logger.error("Web-Eval tests failed", 
                           validation_run_id=validation_run.id,
                           results=test_results)
                return False
                
        except Exception as e:
            logger.error("Web-Eval testing failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
            return False
    
    async def _attempt_deployment_fix(self, validation_run: ValidationRun, project: Project, agent_run: ProjectAgentRun) -> bool:
        """Attempt to fix deployment issues using Codegen API"""
        try:
            if not agent_run.codegen_run_id:
                return False
            
            # Get deployment logs
            deployment_logs = validation_run.deployment_logs or {}
            error_context = f"""
Deployment failed for PR #{validation_run.pr_number} in project {project.name}.

Error logs:
{json.dumps(deployment_logs, indent=2)}

Setup commands that failed:
{project.setup_commands}

Please analyze the errors and update the PR with fixes to resolve the deployment issues.
"""
            
            # Continue the agent run with error context
            response = await self.codegen_client.continue_agent_run(
                org_id=int(settings.codegen_org_id),
                run_id=agent_run.codegen_run_id,
                message=error_context
            )
            
            if response:
                logger.info("Deployment fix requested", 
                           validation_run_id=validation_run.id,
                           agent_run_id=agent_run.id)
                
                # Wait for fix and retry deployment
                await asyncio.sleep(30)  # Wait for potential fixes
                return await self._run_deployment_commands(validation_run, project)
            
            return False
            
        except Exception as e:
            logger.error("Deployment fix attempt failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
            return False
    
    async def _attempt_web_eval_fix(self, validation_run: ValidationRun, project: Project, agent_run: ProjectAgentRun) -> bool:
        """Attempt to fix web evaluation issues using Codegen API"""
        try:
            if not agent_run.codegen_run_id:
                return False
            
            # Get web eval results
            web_eval_results = validation_run.web_eval_results or {}
            error_context = f"""
Web evaluation tests failed for PR #{validation_run.pr_number} in project {project.name}.

Test results:
{json.dumps(web_eval_results, indent=2)}

Please analyze the test failures and update the PR with fixes to resolve the UI/functionality issues.
"""
            
            # Continue the agent run with error context
            response = await self.codegen_client.continue_agent_run(
                org_id=int(settings.codegen_org_id),
                run_id=agent_run.codegen_run_id,
                message=error_context
            )
            
            if response:
                logger.info("Web eval fix requested", 
                           validation_run_id=validation_run.id,
                           agent_run_id=agent_run.id)
                
                # Wait for fix and retry tests
                await asyncio.sleep(30)  # Wait for potential fixes
                return await self._run_web_eval_tests(validation_run, project)
            
            return False
            
        except Exception as e:
            logger.error("Web eval fix attempt failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
            return False
    
    async def _handle_validation_success(self, validation_run: ValidationRun, project: Project, agent_run: ProjectAgentRun):
        """Handle successful validation"""
        try:
            logger.info("Validation completed successfully", validation_run_id=validation_run.id)
            
            # Update agent run status
            agent_run.validation_status = "passed"
            async with get_db_session() as db:
                db.merge(agent_run)
                db.commit()
            
            # Check if auto-merge is enabled
            if project.auto_merge_validated_pr:
                await self._auto_merge_pr(validation_run, project)
            else:
                # Notify user of successful validation
                await self._notify_validation_complete(validation_run, project, success=True)
            
        except Exception as e:
            logger.error("Failed to handle validation success", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
    
    async def _handle_validation_failure(self, validation_run: ValidationRun, project: Project, agent_run: ProjectAgentRun):
        """Handle validation failure"""
        try:
            logger.info("Validation failed", validation_run_id=validation_run.id)
            
            # Update agent run status
            agent_run.validation_status = "failed"
            agent_run.validation_logs = {
                "deployment_logs": validation_run.deployment_logs,
                "web_eval_results": validation_run.web_eval_results,
                "error_logs": validation_run.error_logs
            }
            
            async with get_db_session() as db:
                db.merge(agent_run)
                db.commit()
            
            # Notify user of validation failure
            await self._notify_validation_complete(validation_run, project, success=False)
            
        except Exception as e:
            logger.error("Failed to handle validation failure", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
    
    async def _auto_merge_pr(self, validation_run: ValidationRun, project: Project):
        """Auto-merge PR if validation passed"""
        try:
            merge_success = await self.github_client.merge_pull_request(
                project.github_owner,
                project.github_repo,
                validation_run.pr_number,
                commit_title=f"Auto-merge validated PR #{validation_run.pr_number}",
                commit_message="PR passed all validation tests and was auto-merged."
            )
            
            if merge_success:
                logger.info("PR auto-merged successfully", 
                           validation_run_id=validation_run.id,
                           pr_number=validation_run.pr_number)
            else:
                logger.error("Failed to auto-merge PR", 
                           validation_run_id=validation_run.id,
                           pr_number=validation_run.pr_number)
            
        except Exception as e:
            logger.error("Auto-merge failed", 
                        validation_run_id=validation_run.id, 
                        error=str(e))
    
    async def _notify_validation_complete(self, validation_run: ValidationRun, project: Project, success: bool):
        """Notify frontend of validation completion"""
        try:
            # TODO: Implement WebSocket notification to frontend
            message = {
                "type": "validation_complete",
                "validation_run_id": validation_run.id,
                "project_id": project.id,
                "pr_number": validation_run.pr_number,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Validation notification sent", 
                       validation_run_id=validation_run.id,
                       success=success)
            
        except Exception as e:
            logger.error("Failed to send validation notification", 
                        validation_run_id=validation_run.id, 
                        error=str(e))

