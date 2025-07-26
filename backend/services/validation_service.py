"""
Validation pipeline service for orchestrating complete CI/CD validation flow
"""
import asyncio
import structlog
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.validation import ValidationRun, ValidationStep, ValidationResult, ValidationStatus, ValidationStepType
from backend.models.agent_run import AgentRun
from backend.models.project import Project
from backend.integrations import GrainchainClient, WebEvalClient, GeminiClient, GitHubClient
from backend.websocket.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class ValidationService:
    """Service for managing validation pipeline execution"""
    
    def __init__(self, db: AsyncSession, connection_manager: ConnectionManager):
        self.db = db
        self.connection_manager = connection_manager
        self.grainchain = GrainchainClient()
        self.web_eval = WebEvalClient()
        self.gemini = GeminiClient()
        self.github = GitHubClient()
    
    async def start_validation_pipeline(self, project_id: int, pr_number: int, 
                                      pr_url: str, pr_branch: str, commit_sha: str,
                                      agent_run_id: int = None) -> ValidationRun:
        """Start the complete validation pipeline"""
        
        # Get project information
        project_result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Create validation run
        validation_run = ValidationRun(
            project_id=project_id,
            agent_run_id=agent_run_id,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_branch=pr_branch,
            commit_sha=commit_sha,
            validation_config=project.get_validation_config(),
            auto_merge_enabled=project.auto_merge_enabled
        )
        
        self.db.add(validation_run)
        await self.db.commit()
        await self.db.refresh(validation_run)
        
        logger.info(
            "Validation pipeline started",
            validation_run_id=validation_run.id,
            project_id=project_id,
            pr_number=pr_number
        )
        
        # Start validation in background
        asyncio.create_task(self._execute_validation_pipeline(validation_run, project))
        
        return validation_run
    
    async def _execute_validation_pipeline(self, validation_run: ValidationRun, project: Project):
        """Execute the complete validation pipeline"""
        try:
            validation_run.start_validation()
            await self.db.commit()
            
            # Broadcast validation start
            await self._broadcast_validation_update(validation_run, "Validation pipeline started")
            
            # Define validation steps
            steps = [
                (ValidationStepType.SNAPSHOT_CREATION, "Create sandbox snapshot", self._step_create_snapshot),
                (ValidationStepType.CODE_CLONING, "Clone PR codebase", self._step_clone_code),
                (ValidationStepType.DEPLOYMENT, "Execute deployment commands", self._step_deploy),
                (ValidationStepType.GRAINCHAIN_VALIDATION, "Validate deployment with AI", self._step_validate_deployment),
                (ValidationStepType.WEB_EVAL_TESTING, "Run comprehensive UI tests", self._step_run_ui_tests),
                (ValidationStepType.MERGE_PREPARATION, "Prepare for auto-merge", self._step_prepare_merge)
            ]
            
            # Execute steps sequentially
            for i, (step_type, step_name, step_func) in enumerate(steps):
                step = ValidationStep(
                    validation_run_id=validation_run.id,
                    step_type=step_type,
                    step_name=step_name,
                    step_order=i + 1
                )
                
                self.db.add(step)
                await self.db.commit()
                await self.db.refresh(step)
                
                # Update progress
                progress = int((i / len(steps)) * 100)
                validation_run.update_progress(progress, step_name)
                await self.db.commit()
                
                # Broadcast step start
                await self._broadcast_validation_update(validation_run, f"Starting: {step_name}")
                
                # Execute step
                try:
                    step.start_step()
                    await self.db.commit()
                    
                    success = await step_func(validation_run, project, step)
                    
                    step.complete_step(success)
                    await self.db.commit()
                    
                    if not success:
                        logger.error(
                            "Validation step failed",
                            validation_run_id=validation_run.id,
                            step_type=step_type.value,
                            error=step.error_message
                        )
                        
                        # Try to auto-fix with Codegen if possible
                        if await self._attempt_auto_fix(validation_run, project, step):
                            continue
                        else:
                            # Stop pipeline on failure
                            validation_run.complete_validation(False, f"Step failed: {step_name}")
                            await self.db.commit()
                            await self._broadcast_validation_update(validation_run, f"Pipeline failed at: {step_name}")
                            return
                
                except Exception as e:
                    logger.error(
                        "Validation step error",
                        validation_run_id=validation_run.id,
                        step_type=step_type.value,
                        error=str(e)
                    )
                    
                    step.complete_step(False, str(e))
                    await self.db.commit()
                    
                    validation_run.complete_validation(False, f"Step error: {step_name} - {str(e)}")
                    await self.db.commit()
                    await self._broadcast_validation_update(validation_run, f"Pipeline error at: {step_name}")
                    return
            
            # All steps completed successfully
            validation_run.complete_validation(True)
            await self.db.commit()
            
            # Handle auto-merge if enabled
            if validation_run.auto_merge_enabled and validation_run.merge_ready:
                await self._execute_auto_merge(validation_run, project)
            
            await self._broadcast_validation_update(validation_run, "Validation pipeline completed successfully")
            
        except Exception as e:
            logger.error(
                "Validation pipeline error",
                validation_run_id=validation_run.id,
                error=str(e)
            )
            
            validation_run.complete_validation(False, f"Pipeline error: {str(e)}")
            await self.db.commit()
            await self._broadcast_validation_update(validation_run, f"Pipeline failed: {str(e)}")
    
    async def _step_create_snapshot(self, validation_run: ValidationRun, project: Project, step: ValidationStep) -> bool:
        """Step 1: Create sandbox snapshot"""
        try:
            snapshot_name = f"validation-{validation_run.id}-{project.name}"
            
            snapshot = await self.grainchain.create_snapshot(
                name=snapshot_name,
                description=f"Validation snapshot for PR #{validation_run.pr_number}"
            )
            
            validation_run.snapshot_id = snapshot.get("id")
            validation_run.snapshot_url = snapshot.get("url")
            
            step.output = f"Snapshot created: {snapshot.get('id')}"
            
            return True
            
        except Exception as e:
            step.error_message = f"Failed to create snapshot: {str(e)}"
            return False
    
    async def _step_clone_code(self, validation_run: ValidationRun, project: Project, step: ValidationStep) -> bool:
        """Step 2: Clone PR codebase"""
        try:
            if not validation_run.snapshot_id:
                step.error_message = "No snapshot available for cloning"
                return False
            
            # Construct clone URL
            clone_url = f"https://github.com/{project.full_name}.git"
            
            result = await self.grainchain.clone_repository(
                snapshot_id=validation_run.snapshot_id,
                repo_url=clone_url,
                branch=validation_run.pr_branch,
                target_dir="/workspace"
            )
            
            step.output = f"Repository cloned: {result.get('status')}"
            step.exit_code = result.get("exit_code", 0)
            
            return result.get("exit_code") == 0
            
        except Exception as e:
            step.error_message = f"Failed to clone repository: {str(e)}"
            return False
    
    async def _step_deploy(self, validation_run: ValidationRun, project: Project, step: ValidationStep) -> bool:
        """Step 3: Execute deployment commands"""
        try:
            if not validation_run.snapshot_id:
                step.error_message = "No snapshot available for deployment"
                return False
            
            if not project.setup_commands:
                step.output = "No setup commands configured, skipping deployment"
                return True
            
            # Parse setup commands
            commands = [cmd.strip() for cmd in project.setup_commands.split('\n') if cmd.strip()]
            
            results = await self.grainchain.execute_setup_commands(
                snapshot_id=validation_run.snapshot_id,
                commands=commands,
                working_dir="/workspace"
            )
            
            # Check if all commands succeeded
            all_success = all(result.get("success", False) for result in results)
            
            # Collect deployment logs
            deployment_logs = []
            for result in results:
                deployment_logs.append(f"Command: {result.get('command')}")
                deployment_logs.append(f"Success: {result.get('success')}")
                if result.get('result'):
                    deployment_logs.append(f"Output: {result['result'].get('output', '')}")
                deployment_logs.append("---")
            
            validation_run.deployment_logs = '\n'.join(deployment_logs)
            step.output = f"Executed {len(commands)} commands, success: {all_success}"
            
            return all_success
            
        except Exception as e:
            step.error_message = f"Failed to execute deployment: {str(e)}"
            return False
    
    async def _step_validate_deployment(self, validation_run: ValidationRun, project: Project, step: ValidationStep) -> bool:
        """Step 4: Validate deployment with Gemini AI"""
        try:
            if not validation_run.deployment_logs:
                step.error_message = "No deployment logs available for validation"
                return False
            
            # Use Gemini to validate deployment
            validation_result = await self.gemini.validate_deployment(
                deployment_logs=validation_run.deployment_logs,
                setup_commands=project.setup_commands or "",
                context=f"Project: {project.name}, PR: #{validation_run.pr_number}"
            )
            
            # Store validation result
            result = ValidationResult(
                validation_run_id=validation_run.id,
                validator_name="gemini",
                result_type="deployment_validation",
                passed=validation_result.get("success", False),
                score=validation_result.get("confidence", 0),
                details=validation_result
            )
            
            self.db.add(result)
            
            step.output = f"AI validation: {validation_result.get('explanation', 'No explanation')}"
            
            return validation_result.get("success", False)
            
        except Exception as e:
            step.error_message = f"Failed to validate deployment: {str(e)}"
            return False
    
    async def _step_run_ui_tests(self, validation_run: ValidationRun, project: Project, step: ValidationStep) -> bool:
        """Step 5: Run comprehensive UI tests with web-eval-agent"""
        try:
            if not validation_run.deployment_url:
                # Try to determine deployment URL
                validation_run.deployment_url = f"http://localhost:3000"  # Default for most projects
            
            # Run comprehensive web evaluation
            test_result = await self.web_eval.run_comprehensive_test(
                url=validation_run.deployment_url,
                project_config={"project_name": project.name}
            )
            
            test_id = test_result.get("id")
            
            # Wait for test completion (with timeout)
            max_wait = 300  # 5 minutes
            wait_time = 0
            
            while wait_time < max_wait:
                status = await self.web_eval.get_evaluation_status(test_id)
                
                if status in ["completed", "failed"]:
                    break
                
                await asyncio.sleep(10)
                wait_time += 10
            
            # Get final results
            final_results = await self.web_eval.get_test_results(test_id)
            
            # Store test results
            result = ValidationResult(
                validation_run_id=validation_run.id,
                validator_name="web_eval_agent",
                result_type="ui_testing",
                passed=final_results.get("overall_passed", False),
                score=final_results.get("overall_score", 0),
                details=final_results,
                issues_count=final_results.get("total_issues", 0),
                critical_issues=final_results.get("critical_issues", 0)
            )
            
            self.db.add(result)
            
            step.output = f"UI tests completed: {final_results.get('summary', 'No summary')}"
            
            return final_results.get("overall_passed", False)
            
        except Exception as e:
            step.error_message = f"Failed to run UI tests: {str(e)}"
            return False
    
    async def _step_prepare_merge(self, validation_run: ValidationRun, project: Project, step: ValidationStep) -> bool:
        """Step 6: Prepare for auto-merge"""
        try:
            if validation_run.auto_merge_enabled:
                # Check if all previous steps passed
                all_passed = validation_run.passed_steps == (validation_run.passed_steps + validation_run.failed_steps)
                
                if all_passed:
                    validation_run.merge_ready = True
                    step.output = "Ready for auto-merge"
                else:
                    step.output = "Not ready for auto-merge due to failed steps"
            else:
                step.output = "Auto-merge disabled, manual merge required"
            
            return True
            
        except Exception as e:
            step.error_message = f"Failed to prepare merge: {str(e)}"
            return False
    
    async def _attempt_auto_fix(self, validation_run: ValidationRun, project: Project, failed_step: ValidationStep) -> bool:
        """Attempt to auto-fix issues using Codegen API"""
        try:
            if not validation_run.agent_run_id:
                return False
            
            # Get agent run
            agent_run_result = await self.db.execute(select(AgentRun).where(AgentRun.id == validation_run.agent_run_id))
            agent_run = agent_run_result.scalar_one_or_none()
            
            if not agent_run:
                return False
            
            # Generate fix prompt using Gemini
            error_context = f"Validation step '{failed_step.step_name}' failed: {failed_step.error_message}"
            fix_prompt = await self.gemini.generate_fix_prompt(error_context, failed_step.output)
            
            # Continue agent run with fix prompt
            from backend.integrations import CodegenClient
            codegen = CodegenClient()
            
            await codegen.continue_agent_run(agent_run.codegen_run_id, fix_prompt)
            
            logger.info(
                "Auto-fix attempted",
                validation_run_id=validation_run.id,
                agent_run_id=agent_run.id,
                step_type=failed_step.step_type.value
            )
            
            return True
            
        except Exception as e:
            logger.error("Auto-fix failed", error=str(e))
            return False
    
    async def _execute_auto_merge(self, validation_run: ValidationRun, project: Project):
        """Execute auto-merge for validated PR"""
        try:
            merge_result = await self.github.merge_pull_request(
                owner=project.github_owner,
                repo=project.github_repo,
                pr_number=validation_run.pr_number,
                commit_title=f"Auto-merge validated PR #{validation_run.pr_number}",
                commit_message="Automatically merged after successful validation pipeline"
            )
            
            validation_run.merge_url = merge_result.get("html_url")
            await self.db.commit()
            
            logger.info(
                "Auto-merge completed",
                validation_run_id=validation_run.id,
                pr_number=validation_run.pr_number,
                merge_url=validation_run.merge_url
            )
            
            await self._broadcast_validation_update(validation_run, "PR auto-merged successfully")
            
        except Exception as e:
            logger.error(
                "Auto-merge failed",
                validation_run_id=validation_run.id,
                pr_number=validation_run.pr_number,
                error=str(e)
            )
            
            await self._broadcast_validation_update(validation_run, f"Auto-merge failed: {str(e)}")
    
    async def _broadcast_validation_update(self, validation_run: ValidationRun, message: str):
        """Broadcast validation update via WebSocket"""
        try:
            update_data = {
                "type": "validation_update",
                "validation_run_id": validation_run.id,
                "project_id": validation_run.project_id,
                "status": validation_run.status.value,
                "progress": validation_run.progress_percentage,
                "current_step": validation_run.current_step,
                "message": message,
                "timestamp": validation_run.updated_at.isoformat() if validation_run.updated_at else None
            }
            
            await self.connection_manager.broadcast_to_project(validation_run.project_id, update_data)
            
        except Exception as e:
            logger.error("Failed to broadcast validation update", error=str(e))
    
    async def get_validation_run(self, validation_run_id: int) -> Optional[ValidationRun]:
        """Get validation run by ID"""
        result = await self.db.execute(select(ValidationRun).where(ValidationRun.id == validation_run_id))
        return result.scalar_one_or_none()
    
    async def cancel_validation(self, validation_run_id: int) -> bool:
        """Cancel a running validation"""
        try:
            validation_run = await self.get_validation_run(validation_run_id)
            
            if not validation_run or validation_run.is_completed:
                return False
            
            validation_run.status = ValidationStatus.CANCELLED
            await self.db.commit()
            
            # Clean up snapshot if exists
            if validation_run.snapshot_id:
                await self.grainchain.delete_snapshot(validation_run.snapshot_id)
            
            await self._broadcast_validation_update(validation_run, "Validation cancelled")
            
            return True
            
        except Exception as e:
            logger.error("Failed to cancel validation", validation_run_id=validation_run_id, error=str(e))
            return False

