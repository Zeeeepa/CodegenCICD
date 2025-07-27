"""
Validation pipeline service for CodegenCICD Dashboard
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base_service import BaseService
from backend.database import AsyncSessionLocal
from backend.models import ValidationRun, ValidationStep, ValidationResult, Project
from backend.models.validation import ValidationStatus, ValidationStepStatus, ValidationStepType
from backend.integrations import GeminiClient, GitHubClient
from backend.integrations.grainchain_client import GrainchainClient
from backend.integrations.web_eval_client import WebEvalClient
from backend.integrations.graph_sitter_client import GraphSitterClient
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ValidationService(BaseService):
    """Service for executing validation pipelines"""
    
    def __init__(self):
        super().__init__("validation_service")
        self._active_validations: Dict[str, asyncio.Task] = {}
    
    async def _initialize_service(self) -> None:
        """Initialize validation service"""
        self.logger.info("Validation service initialized")
    
    async def _close_service(self) -> None:
        """Close validation service"""
        # Cancel all active validations
        for validation_id, task in self._active_validations.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._active_validations.clear()
    
    async def execute_validation_pipeline(self, validation_run_id: str) -> None:
        """Execute validation pipeline for a validation run"""
        if validation_run_id in self._active_validations:
            self.logger.warning("Validation pipeline already running", 
                              validation_run_id=validation_run_id)
            return
        
        # Create and start validation task
        task = asyncio.create_task(self._run_validation_pipeline(validation_run_id))
        self._active_validations[validation_run_id] = task
        
        try:
            await task
        finally:
            # Clean up completed task
            self._active_validations.pop(validation_run_id, None)
    
    async def _run_validation_pipeline(self, validation_run_id: str) -> None:
        """Run the complete validation pipeline"""
        async with AsyncSessionLocal() as db:
            try:
                # Get validation run and project
                validation_run = await self._get_validation_run(db, validation_run_id)
                if not validation_run:
                    self.logger.error("Validation run not found", validation_run_id=validation_run_id)
                    return
                
                project = await self._get_project(db, validation_run.project_id)
                if not project:
                    self.logger.error("Project not found", project_id=validation_run.project_id)
                    return
                
                # Update status to running
                validation_run.status = ValidationStatus.RUNNING
                validation_run.started_at = self._get_timestamp()
                await db.commit()
                
                self.logger.info("Starting validation pipeline",
                               validation_run_id=validation_run_id,
                               project_name=project.name,
                               pr_number=validation_run.pr_number)
                
                # Get validation steps
                steps = await self._get_validation_steps(db, validation_run_id)
                
                # Execute each step
                overall_success = True
                total_score = 0.0
                total_weight = 0.0
                
                for step in steps:
                    try:
                        # Update current step
                        validation_run.current_step_index = step.step_index
                        await db.commit()
                        
                        # Execute step
                        step_success = await self._execute_validation_step(
                            db, validation_run, project, step
                        )
                        
                        if not step_success and step.is_critical:
                            overall_success = False
                            self.logger.warning("Critical validation step failed",
                                              validation_run_id=validation_run_id,
                                              step_name=step.step_name)
                            break
                        
                        # Update progress
                        progress = int(((step.step_index + 1) / len(steps)) * 100)
                        validation_run.progress_percentage = progress
                        await db.commit()
                        
                        # Calculate weighted score
                        if step.confidence_score is not None:
                            total_score += step.confidence_score * step.weight
                            total_weight += step.weight
                        
                    except Exception as e:
                        self.logger.error("Validation step execution failed",
                                        validation_run_id=validation_run_id,
                                        step_name=step.step_name,
                                        error=str(e))
                        
                        step.status = ValidationStepStatus.FAILED
                        step.error_message = str(e)
                        step.completed_at = self._get_timestamp()
                        
                        if step.is_critical:
                            overall_success = False
                            break
                
                # Calculate final results
                overall_score = (total_score / total_weight) if total_weight > 0 else 0.0
                
                # Update validation run with final results
                validation_run.status = ValidationStatus.COMPLETED if overall_success else ValidationStatus.FAILED
                validation_run.completed_at = self._get_timestamp()
                validation_run.overall_score = overall_score
                validation_run.progress_percentage = 100
                
                # Count step results
                passed_steps = sum(1 for step in steps if step.status == ValidationStepStatus.COMPLETED)
                failed_steps = sum(1 for step in steps if step.status == ValidationStepStatus.FAILED)
                skipped_steps = sum(1 for step in steps if step.status == ValidationStepStatus.SKIPPED)
                
                validation_run.passed_steps = passed_steps
                validation_run.failed_steps = failed_steps
                validation_run.skipped_steps = skipped_steps
                
                # Check auto-merge eligibility
                if (overall_success and 
                    project.auto_merge_enabled and 
                    overall_score >= project.auto_merge_threshold):
                    
                    validation_run.auto_merge_eligible = True
                    
                    # Execute auto-merge
                    try:
                        await self._execute_auto_merge(db, validation_run, project)
                        validation_run.auto_merge_executed = True
                        validation_run.auto_merge_reason = f"Score {overall_score:.1f}% >= threshold {project.auto_merge_threshold}%"
                    except Exception as e:
                        self.logger.error("Auto-merge failed",
                                        validation_run_id=validation_run_id,
                                        error=str(e))
                        validation_run.auto_merge_reason = f"Auto-merge failed: {str(e)}"
                
                await db.commit()
                
                self.logger.info("Validation pipeline completed",
                               validation_run_id=validation_run_id,
                               status=validation_run.status.value,
                               overall_score=overall_score,
                               auto_merge_executed=validation_run.auto_merge_executed)
                
            except Exception as e:
                self.logger.error("Validation pipeline failed",
                                validation_run_id=validation_run_id,
                                error=str(e))
                
                # Update validation run with error
                try:
                    validation_run = await self._get_validation_run(db, validation_run_id)
                    if validation_run:
                        validation_run.status = ValidationStatus.FAILED
                        validation_run.error_message = str(e)
                        validation_run.completed_at = self._get_timestamp()
                        await db.commit()
                except Exception as update_error:
                    self.logger.error("Failed to update validation run after error",
                                    validation_run_id=validation_run_id,
                                    error=str(update_error))
    
    async def _execute_validation_step(self,
                                     db: AsyncSession,
                                     validation_run: ValidationRun,
                                     project: Project,
                                     step: ValidationStep) -> bool:
        """Execute a single validation step"""
        try:
            step.status = ValidationStepStatus.RUNNING
            step.started_at = self._get_timestamp()
            await db.commit()
            
            self.logger.info("Executing validation step",
                           validation_run_id=str(validation_run.id),
                           step_name=step.step_name,
                           step_type=step.step_type.value)
            
            success = False
            
            if step.step_type == ValidationStepType.SNAPSHOT_CREATION:
                success = await self._execute_snapshot_creation(db, validation_run, project, step)
            
            elif step.step_type == ValidationStepType.CODE_CLONE:
                success = await self._execute_code_clone(db, validation_run, project, step)
            
            elif step.step_type == ValidationStepType.CODE_ANALYSIS:
                success = await self._execute_code_analysis(db, validation_run, project, step)
            
            elif step.step_type == ValidationStepType.DEPLOYMENT:
                success = await self._execute_deployment(db, validation_run, project, step)
            
            elif step.step_type == ValidationStepType.DEPLOYMENT_VALIDATION:
                success = await self._execute_deployment_validation(db, validation_run, project, step)
            
            elif step.step_type == ValidationStepType.UI_TESTING:
                success = await self._execute_ui_testing(db, validation_run, project, step)
            
            elif step.step_type == ValidationStepType.AUTO_MERGE:
                success = await self._execute_auto_merge_check(db, validation_run, project, step)
            
            else:
                self.logger.warning("Unknown validation step type",
                                  step_type=step.step_type.value)
                success = False
            
            # Update step status
            step.status = ValidationStepStatus.COMPLETED if success else ValidationStepStatus.FAILED
            step.completed_at = self._get_timestamp()
            
            if step.started_at:
                start_time = datetime.fromisoformat(step.started_at.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(step.completed_at.replace('Z', '+00:00'))
                step.duration_seconds = int((end_time - start_time).total_seconds())
            
            await db.commit()
            
            return success
            
        except Exception as e:
            self.logger.error("Validation step execution failed",
                            step_name=step.step_name,
                            error=str(e))
            
            step.status = ValidationStepStatus.FAILED
            step.error_message = str(e)
            step.completed_at = self._get_timestamp()
            await db.commit()
            
            return False
    
    async def _execute_snapshot_creation(self,
                                       db: AsyncSession,
                                       validation_run: ValidationRun,
                                       project: Project,
                                       step: ValidationStep) -> bool:
        """Execute snapshot creation step using grainchain"""
        try:
            if not project.grainchain_enabled:
                step.logs = "Grainchain disabled for project"
                step.confidence_score = 100.0
                return True
            
            async with GrainchainClient() as client:
                # Create sandbox snapshot
                snapshot_result = await client.create_snapshot(
                    project_name=project.name,
                    github_url=project.github_url,
                    branch=validation_run.pr_branch
                )
                
                validation_run.grainchain_snapshot_id = snapshot_result.get("snapshot_id")
                step.external_service_id = snapshot_result.get("snapshot_id")
                step.confidence_score = 95.0
                step.logs = f"Snapshot created: {snapshot_result.get('snapshot_id')}"
                
                await db.commit()
                
                return True
                
        except Exception as e:
            step.logs = f"Snapshot creation failed: {str(e)}"
            return False
    
    async def _execute_code_clone(self,
                                db: AsyncSession,
                                validation_run: ValidationRun,
                                project: Project,
                                step: ValidationStep) -> bool:
        """Execute code clone step"""
        try:
            if not validation_run.grainchain_snapshot_id:
                step.logs = "No snapshot available for code clone"
                return False
            
            async with GrainchainClient() as client:
                # Clone PR branch to sandbox
                clone_result = await client.clone_repository(
                    snapshot_id=validation_run.grainchain_snapshot_id,
                    repository_url=project.github_url,
                    branch=validation_run.pr_branch,
                    commit_sha=validation_run.pr_commit_sha
                )
                
                step.confidence_score = 95.0
                step.logs = f"Code cloned successfully: {clone_result.get('status')}"
                
                return True
                
        except Exception as e:
            step.logs = f"Code clone failed: {str(e)}"
            return False
    
    async def _execute_code_analysis(self,
                                   db: AsyncSession,
                                   validation_run: ValidationRun,
                                   project: Project,
                                   step: ValidationStep) -> bool:
        """Execute code analysis step using graph-sitter"""
        try:
            if not project.graph_sitter_enabled:
                step.logs = "Graph-sitter disabled for project"
                step.confidence_score = 100.0
                return True
            
            async with GraphSitterClient() as client:
                # Run code quality analysis
                analysis_result = await client.analyze_code_quality(
                    snapshot_id=validation_run.grainchain_snapshot_id,
                    project_path=f"/workspace/{project.name}"
                )
                
                # Use Gemini to analyze results
                async with GeminiClient() as gemini:
                    ai_analysis = await gemini.analyze_code_quality(
                        code_analysis_results=analysis_result,
                        project_context=f"Project: {project.name}, PR: #{validation_run.pr_number}"
                    )
                
                step.confidence_score = ai_analysis.get("overall_score", 75.0)
                step.logs = f"Code analysis completed. Score: {step.confidence_score}%"
                
                # Store detailed results
                await self._store_validation_result(
                    db, validation_run.id, "code_analysis", "quality_score", 
                    ai_analysis.get("overall_score", 75.0), ai_analysis
                )
                
                return True
                
        except Exception as e:
            step.logs = f"Code analysis failed: {str(e)}"
            return False
    
    async def _execute_deployment(self,
                                db: AsyncSession,
                                validation_run: ValidationRun,
                                project: Project,
                                step: ValidationStep) -> bool:
        """Execute deployment step"""
        try:
            if not validation_run.grainchain_snapshot_id:
                step.logs = "No snapshot available for deployment"
                return False
            
            async with GrainchainClient() as client:
                # Get project setup commands
                setup_commands = await self._get_project_setup_commands(db, project.id)
                
                # Execute deployment
                deployment_result = await client.execute_deployment(
                    snapshot_id=validation_run.grainchain_snapshot_id,
                    setup_commands=setup_commands,
                    project_path=f"/workspace/{project.name}"
                )
                
                step.confidence_score = 90.0 if deployment_result.get("success") else 0.0
                step.logs = deployment_result.get("logs", "Deployment executed")
                
                return deployment_result.get("success", False)
                
        except Exception as e:
            step.logs = f"Deployment failed: {str(e)}"
            return False
    
    async def _execute_deployment_validation(self,
                                           db: AsyncSession,
                                           validation_run: ValidationRun,
                                           project: Project,
                                           step: ValidationStep) -> bool:
        """Execute deployment validation step using Gemini AI"""
        try:
            if not validation_run.grainchain_snapshot_id:
                step.logs = "No snapshot available for deployment validation"
                return False
            
            async with GrainchainClient() as client:
                # Get deployment logs
                logs = await client.get_deployment_logs(
                    snapshot_id=validation_run.grainchain_snapshot_id
                )
            
            # Use Gemini to analyze deployment success
            async with GeminiClient() as gemini:
                analysis = await gemini.analyze_deployment_logs(
                    logs=logs,
                    project_context=f"Project: {project.name}, PR: #{validation_run.pr_number}"
                )
            
            step.confidence_score = analysis.get("confidence_score", 50.0)
            step.logs = f"Deployment validation: {analysis.get('status')} - {analysis.get('summary')}"
            
            # Store detailed results
            await self._store_validation_result(
                db, validation_run.id, "deployment_validation", "analysis", 
                analysis.get("confidence_score", 50.0), analysis
            )
            
            return analysis.get("status") == "success"
            
        except Exception as e:
            step.logs = f"Deployment validation failed: {str(e)}"
            return False
    
    async def _execute_ui_testing(self,
                                db: AsyncSession,
                                validation_run: ValidationRun,
                                project: Project,
                                step: ValidationStep) -> bool:
        """Execute UI testing step using web-eval-agent"""
        try:
            if not project.web_eval_enabled:
                step.logs = "Web-eval-agent disabled for project"
                step.confidence_score = 100.0
                return True
            
            async with WebEvalClient() as client:
                # Run UI tests
                test_result = await client.run_ui_tests(
                    snapshot_id=validation_run.grainchain_snapshot_id,
                    base_url=f"http://localhost:8000",  # Assuming standard port
                    test_scenarios=await self._get_ui_test_scenarios(db, project.id)
                )
                
                validation_run.web_eval_session_id = test_result.get("session_id")
                step.external_service_id = test_result.get("session_id")
            
            # Use Gemini to analyze UI test results
            async with GeminiClient() as gemini:
                analysis = await gemini.analyze_ui_test_results(
                    test_results=test_result,
                    project_context=f"Project: {project.name}, PR: #{validation_run.pr_number}"
                )
            
            step.confidence_score = analysis.get("overall_score", 75.0)
            step.logs = f"UI testing completed. Score: {step.confidence_score}%"
            
            # Store detailed results
            await self._store_validation_result(
                db, validation_run.id, "ui_testing", "test_results", 
                analysis.get("overall_score", 75.0), analysis
            )
            
            return analysis.get("test_status") != "failed"
            
        except Exception as e:
            step.logs = f"UI testing failed: {str(e)}"
            return False
    
    async def _execute_auto_merge_check(self,
                                      db: AsyncSession,
                                      validation_run: ValidationRun,
                                      project: Project,
                                      step: ValidationStep) -> bool:
        """Execute auto-merge eligibility check"""
        try:
            if not project.auto_merge_enabled:
                step.logs = "Auto-merge disabled for project"
                step.confidence_score = 100.0
                return True
            
            # This step just checks eligibility - actual merge happens later
            step.confidence_score = 100.0
            step.logs = f"Auto-merge check completed. Threshold: {project.auto_merge_threshold}%"
            
            return True
            
        except Exception as e:
            step.logs = f"Auto-merge check failed: {str(e)}"
            return False
    
    async def _execute_auto_merge(self,
                                db: AsyncSession,
                                validation_run: ValidationRun,
                                project: Project) -> None:
        """Execute auto-merge of the PR"""
        try:
            async with GitHubClient() as client:
                # Merge the PR
                merge_result = await client.merge_pull_request(
                    owner=project.github_owner,
                    repo=project.github_repo,
                    pr_number=validation_run.pr_number,
                    commit_title=f"Auto-merge PR #{validation_run.pr_number} (validation score: {validation_run.overall_score:.1f}%)",
                    merge_method="merge"
                )
                
                self.logger.info("PR auto-merged successfully",
                               validation_run_id=str(validation_run.id),
                               pr_number=validation_run.pr_number,
                               merge_sha=merge_result.get("sha"))
                
        except Exception as e:
            self.logger.error("Auto-merge failed",
                            validation_run_id=str(validation_run.id),
                            pr_number=validation_run.pr_number,
                            error=str(e))
            raise
    
    # Helper methods
    async def _get_validation_run(self, db: AsyncSession, validation_run_id: str) -> Optional[ValidationRun]:
        """Get validation run by ID"""
        query = select(ValidationRun).where(ValidationRun.id == validation_run_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_project(self, db: AsyncSession, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        query = select(Project).where(Project.id == project_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_validation_steps(self, db: AsyncSession, validation_run_id: str) -> List[ValidationStep]:
        """Get validation steps for a run"""
        query = select(ValidationStep).where(
            ValidationStep.validation_run_id == validation_run_id
        ).order_by(ValidationStep.step_index)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _get_project_setup_commands(self, db: AsyncSession, project_id: str) -> List[str]:
        """Get setup commands for a project"""
        # TODO: Get from project configurations
        return [
            "npm install",
            "npm run build",
            "npm start &"
        ]
    
    async def _get_ui_test_scenarios(self, db: AsyncSession, project_id: str) -> List[Dict[str, Any]]:
        """Get UI test scenarios for a project"""
        # TODO: Get from project configurations
        return [
            {
                "name": "Homepage Load Test",
                "url": "/",
                "checks": ["page_loads", "no_errors", "responsive"]
            },
            {
                "name": "Navigation Test",
                "url": "/",
                "checks": ["navigation_works", "links_functional"]
            }
        ]
    
    async def _store_validation_result(self,
                                     db: AsyncSession,
                                     validation_run_id: str,
                                     result_type: str,
                                     result_name: str,
                                     score: float,
                                     data: Dict[str, Any]) -> None:
        """Store validation result"""
        result = ValidationResult(
            validation_run_id=validation_run_id,
            result_type=result_type,
            result_name=result_name,
            score=score,
            data=data
        )
        
        db.add(result)
        await db.commit()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for validation service"""
        base_health = await super().health_check()
        base_health.update({
            "active_validations": len(self._active_validations),
            "validation_enabled": settings.is_feature_enabled("validation_pipeline")
        })
        return base_health

