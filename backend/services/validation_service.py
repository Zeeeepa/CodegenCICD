"""
Validation service for orchestrating the complete validation pipeline
"""
import asyncio
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from backend.models.validation import (
    ValidationRun, ValidationStep, ValidationResult, ValidationStatus, ValidationStepType
)
from backend.models.agent_run import AgentRun
from backend.models.project import Project
from backend.websocket.connection_manager import ConnectionManager
from backend.integrations.github_client import GitHubClient

logger = structlog.get_logger(__name__)


class ValidationService:
    """Service for managing validation pipeline execution"""
    
    def __init__(self, db: AsyncSession, connection_manager: ConnectionManager):
        self.db = db
        self.connection_manager = connection_manager
        self.github_client = GitHubClient()
    
    async def start_validation(self, agent_run: AgentRun) -> ValidationRun:
        """Start validation pipeline for an agent run"""
        try:
            # Get project configuration
            project = await self.db.get(Project, agent_run.project_id)
            if not project:
                raise ValueError(f"Project {agent_run.project_id} not found")
            
            # Create validation run
            validation_run = ValidationRun(
                project_id=agent_run.project_id,
                agent_run_id=agent_run.id,
                pr_number=agent_run.pr_number,
                pr_url=agent_run.pr_url,
                pr_branch=agent_run.pr_branch,
                validation_config=project.get_validation_config(),
                auto_merge_enabled=agent_run.auto_merge_enabled
            )
            
            self.db.add(validation_run)
            await self.db.commit()
            await self.db.refresh(validation_run)
            
            logger.info("Validation run created", validation_run_id=validation_run.id, 
                       agent_run_id=agent_run.id)
            
            # Start validation pipeline asynchronously
            asyncio.create_task(self._execute_validation_pipeline(validation_run))
            
            # Notify via WebSocket
            await self._notify_validation_update(validation_run)
            
            return validation_run
            
        except Exception as e:
            logger.error("Failed to start validation", agent_run_id=agent_run.id, error=str(e))
            await self.db.rollback()
            raise
    
    async def _execute_validation_pipeline(self, validation_run: ValidationRun):
        """Execute the complete validation pipeline"""
        try:
            validation_run.start_validation()
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            # Define validation steps based on project configuration
            steps = self._get_validation_steps(validation_run)
            
            # Execute each step
            for step_order, (step_type, step_name, step_func) in enumerate(steps, 1):
                step = await self._create_validation_step(
                    validation_run.id, step_type, step_name, step_order
                )
                
                try:
                    await step_func(validation_run, step)
                    
                    if step.status == ValidationStatus.FAILED:
                        # Step failed, stop pipeline
                        validation_run.complete_validation(False, step.error_message)
                        await self.db.commit()
                        await self._notify_validation_update(validation_run)
                        return
                        
                except Exception as e:
                    logger.error("Validation step failed", step_id=step.id, error=str(e))
                    step.complete_step(False, str(e))
                    validation_run.complete_validation(False, f"Step '{step_name}' failed: {str(e)}")
                    await self.db.commit()
                    await self._notify_validation_update(validation_run)
                    return
            
            # All steps completed successfully
            validation_run.complete_validation(True)
            validation_run.merge_ready = True
            await self.db.commit()
            
            # Trigger auto-merge if enabled
            if validation_run.auto_merge_enabled:
                await self._attempt_auto_merge(validation_run)
            
            await self._notify_validation_update(validation_run)
            logger.info("Validation pipeline completed successfully", 
                       validation_run_id=validation_run.id)
            
        except Exception as e:
            logger.error("Validation pipeline failed", validation_run_id=validation_run.id, error=str(e))
            validation_run.complete_validation(False, str(e))
            await self.db.commit()
            await self._notify_validation_update(validation_run)
    
    def _get_validation_steps(self, validation_run: ValidationRun) -> List[tuple]:
        """Get list of validation steps to execute"""
        steps = []
        config = validation_run.validation_config or {}
        
        # Always start with snapshot creation and code cloning
        steps.append((
            ValidationStepType.SNAPSHOT_CREATION,
            "Create Snapshot Environment",
            self._step_create_snapshot
        ))
        
        steps.append((
            ValidationStepType.CODE_CLONING,
            "Clone PR Code",
            self._step_clone_code
        ))
        
        steps.append((
            ValidationStepType.DEPLOYMENT,
            "Deploy Application",
            self._step_deploy_application
        ))
        
        # Add validation tools based on configuration
        if config.get("grainchain_enabled", True):
            steps.append((
                ValidationStepType.GRAINCHAIN_VALIDATION,
                "Grainchain Sandbox Validation",
                self._step_grainchain_validation
            ))
        
        if config.get("graph_sitter_enabled", True):
            steps.append((
                ValidationStepType.GRAPH_SITTER_ANALYSIS,
                "Graph-sitter Code Quality Analysis",
                self._step_graph_sitter_analysis
            ))
        
        if config.get("web_eval_agent_enabled", True):
            steps.append((
                ValidationStepType.WEB_EVAL_TESTING,
                "Web-eval-agent UI Testing",
                self._step_web_eval_testing
            ))
        
        # Final merge preparation
        steps.append((
            ValidationStepType.MERGE_PREPARATION,
            "Prepare for Merge",
            self._step_prepare_merge
        ))
        
        return steps
    
    async def _create_validation_step(self, validation_run_id: int, step_type: ValidationStepType,
                                    step_name: str, step_order: int) -> ValidationStep:
        """Create a validation step"""
        step = ValidationStep(
            validation_run_id=validation_run_id,
            step_type=step_type,
            step_name=step_name,
            step_order=step_order
        )
        
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        
        return step
    
    async def _step_create_snapshot(self, validation_run: ValidationRun, step: ValidationStep):
        """Create snapshot environment using grainchain"""
        step.start_step()
        await self.db.commit()
        
        try:
            # Update progress
            validation_run.update_progress(10, "Creating snapshot environment")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            # Call grainchain API to create snapshot
            from backend.integrations.grainchain_client import GrainchainClient
            grainchain_client = GrainchainClient()
            
            snapshot_result = await grainchain_client.create_snapshot({
                "project_id": validation_run.project_id,
                "pr_branch": validation_run.pr_branch,
                "pr_number": validation_run.pr_number
            })
            
            validation_run.snapshot_id = snapshot_result.get("snapshot_id")
            validation_run.snapshot_url = snapshot_result.get("snapshot_url")
            
            step.complete_step(True, output=f"Snapshot created: {validation_run.snapshot_id}")
            validation_run.update_progress(20, "Snapshot environment ready")
            
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
        except Exception as e:
            step.complete_step(False, str(e))
            await self.db.commit()
            raise
    
    async def _step_clone_code(self, validation_run: ValidationRun, step: ValidationStep):
        """Clone PR code into snapshot environment"""
        step.start_step()
        await self.db.commit()
        
        try:
            validation_run.update_progress(30, "Cloning PR code")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            # Get project details
            project = await self.db.get(Project, validation_run.project_id)
            
            # Clone code using grainchain
            from backend.integrations.grainchain_client import GrainchainClient
            grainchain_client = GrainchainClient()
            
            clone_result = await grainchain_client.clone_repository({
                "snapshot_id": validation_run.snapshot_id,
                "repository": project.full_name,
                "branch": validation_run.pr_branch,
                "commit_sha": validation_run.commit_sha
            })
            
            step.complete_step(True, output="Code cloned successfully")
            validation_run.update_progress(40, "Code cloned")
            
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
        except Exception as e:
            step.complete_step(False, str(e))
            await self.db.commit()
            raise
    
    async def _step_deploy_application(self, validation_run: ValidationRun, step: ValidationStep):
        """Deploy application using setup commands"""
        step.start_step()
        await self.db.commit()
        
        try:
            validation_run.update_progress(50, "Deploying application")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            # Get project setup commands
            project = await self.db.get(Project, validation_run.project_id)
            setup_commands = project.setup_commands
            
            if not setup_commands:
                step.complete_step(True, output="No setup commands configured")
                validation_run.update_progress(60, "Deployment skipped")
                await self.db.commit()
                return
            
            # Execute setup commands in snapshot
            from backend.integrations.grainchain_client import GrainchainClient
            grainchain_client = GrainchainClient()
            
            deploy_result = await grainchain_client.execute_commands({
                "snapshot_id": validation_run.snapshot_id,
                "commands": setup_commands.split("\\n"),
                "timeout": 300  # 5 minutes timeout
            })
            
            if deploy_result.get("success"):
                validation_run.deployment_url = deploy_result.get("deployment_url")
                validation_run.deployment_logs = deploy_result.get("logs")
                
                # Validate deployment with Gemini
                await self._validate_deployment_with_gemini(validation_run, deploy_result)
                
                step.complete_step(True, output="Application deployed successfully")
                validation_run.update_progress(60, "Application deployed")
            else:
                error_msg = deploy_result.get("error", "Deployment failed")
                step.complete_step(False, error_msg, deploy_result.get("logs"))
                
                # Try to fix deployment issues with Codegen
                await self._attempt_deployment_fix(validation_run, error_msg)
                return
            
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
        except Exception as e:
            step.complete_step(False, str(e))
            await self.db.commit()
            raise
    
    async def _step_grainchain_validation(self, validation_run: ValidationRun, step: ValidationStep):
        """Run grainchain sandbox validation"""
        step.start_step()
        await self.db.commit()
        
        try:
            validation_run.update_progress(70, "Running sandbox validation")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            from backend.integrations.grainchain_client import GrainchainClient
            grainchain_client = GrainchainClient()
            
            validation_result = await grainchain_client.run_validation({
                "snapshot_id": validation_run.snapshot_id,
                "validation_type": "security_and_isolation",
                "deployment_url": validation_run.deployment_url
            })
            
            # Store validation result
            result = ValidationResult(
                validation_run_id=validation_run.id,
                validator_name="grainchain",
                result_type="security_scan",
                passed=validation_result.get("passed", False),
                score=validation_result.get("score"),
                details=validation_result.get("details"),
                issues_count=validation_result.get("issues_count", 0),
                critical_issues=validation_result.get("critical_issues", 0),
                warning_issues=validation_result.get("warning_issues", 0)
            )
            
            self.db.add(result)
            
            if result.passed:
                step.complete_step(True, output="Grainchain validation passed")
            else:
                step.complete_step(False, f"Grainchain validation failed: {result.issues_count} issues found")
            
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
        except Exception as e:
            step.complete_step(False, str(e))
            await self.db.commit()
            raise
    
    async def _step_graph_sitter_analysis(self, validation_run: ValidationRun, step: ValidationStep):
        """Run graph-sitter code quality analysis"""
        step.start_step()
        await self.db.commit()
        
        try:
            validation_run.update_progress(80, "Running code quality analysis")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            from backend.integrations.graph_sitter_client import GraphSitterClient
            graph_sitter_client = GraphSitterClient()
            
            analysis_result = await graph_sitter_client.analyze_code({
                "snapshot_id": validation_run.snapshot_id,
                "analysis_types": ["syntax", "complexity", "security", "best_practices"]
            })
            
            # Store analysis result
            result = ValidationResult(
                validation_run_id=validation_run.id,
                validator_name="graph_sitter",
                result_type="code_quality",
                passed=analysis_result.get("passed", False),
                score=analysis_result.get("quality_score"),
                details=analysis_result.get("analysis_details"),
                issues_count=analysis_result.get("total_issues", 0),
                critical_issues=analysis_result.get("critical_issues", 0),
                warning_issues=analysis_result.get("warning_issues", 0)
            )
            
            self.db.add(result)
            
            if result.passed:
                step.complete_step(True, output=f"Code quality analysis passed (score: {result.score})")
            else:
                step.complete_step(False, f"Code quality issues found: {result.issues_count} total")
            
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
        except Exception as e:
            step.complete_step(False, str(e))
            await self.db.commit()
            raise
    
    async def _step_web_eval_testing(self, validation_run: ValidationRun, step: ValidationStep):
        """Run web-eval-agent UI testing"""
        step.start_step()
        await self.db.commit()
        
        try:
            validation_run.update_progress(90, "Running UI/UX testing")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            from backend.integrations.web_eval_client import WebEvalClient
            web_eval_client = WebEvalClient()
            
            testing_result = await web_eval_client.run_tests({
                "deployment_url": validation_run.deployment_url,
                "test_types": ["functionality", "ui_components", "user_flows", "accessibility"],
                "snapshot_id": validation_run.snapshot_id
            })
            
            # Store testing result
            result = ValidationResult(
                validation_run_id=validation_run.id,
                validator_name="web_eval_agent",
                result_type="ui_testing",
                passed=testing_result.get("passed", False),
                score=testing_result.get("test_score"),
                details=testing_result.get("test_results"),
                issues_count=testing_result.get("failed_tests", 0),
                critical_issues=testing_result.get("critical_failures", 0),
                warning_issues=testing_result.get("warnings", 0)
            )
            
            self.db.add(result)
            
            if result.passed:
                step.complete_step(True, output=f"UI testing passed ({testing_result.get('passed_tests', 0)} tests)")
            else:
                step.complete_step(False, f"UI testing failed: {result.issues_count} test failures")
            
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
        except Exception as e:
            step.complete_step(False, str(e))
            await self.db.commit()
            raise
    
    async def _step_prepare_merge(self, validation_run: ValidationRun, step: ValidationStep):
        """Prepare for merge by checking PR status"""
        step.start_step()
        await self.db.commit()
        
        try:
            validation_run.update_progress(95, "Preparing for merge")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
            # Get project details
            project = await self.db.get(Project, validation_run.project_id)
            
            # Check if PR is still mergeable
            is_mergeable = await self.github_client.is_pr_mergeable(
                project.github_owner,
                project.github_repo,
                validation_run.pr_number
            )
            
            if is_mergeable:
                step.complete_step(True, output="PR is ready for merge")
                validation_run.merge_ready = True
            else:
                step.complete_step(False, "PR is not mergeable (conflicts or failed checks)")
                validation_run.merge_ready = False
            
            validation_run.update_progress(100, "Validation complete")
            await self.db.commit()
            await self._notify_validation_update(validation_run)
            
        except Exception as e:
            step.complete_step(False, str(e))
            await self.db.commit()
            raise
    
    async def _validate_deployment_with_gemini(self, validation_run: ValidationRun, deploy_result: Dict[str, Any]):
        """Validate deployment success using Gemini API"""
        try:
            from backend.integrations.gemini_client import GeminiClient
            gemini_client = GeminiClient()
            
            validation_prompt = f"""
            Analyze this deployment result and determine if the deployment was successful:
            
            Deployment URL: {validation_run.deployment_url}
            Logs: {deploy_result.get('logs', '')}
            Exit Code: {deploy_result.get('exit_code', 0)}
            
            Please respond with:
            1. SUCCESS or FAILURE
            2. Brief explanation
            3. Any issues found
            """
            
            response = await gemini_client.analyze_text(validation_prompt)
            
            if "SUCCESS" in response.upper():
                logger.info("Gemini validated deployment success", validation_run_id=validation_run.id)
            else:
                logger.warning("Gemini detected deployment issues", 
                             validation_run_id=validation_run.id, response=response)
                
        except Exception as e:
            logger.error("Failed to validate deployment with Gemini", 
                        validation_run_id=validation_run.id, error=str(e))
    
    async def _attempt_deployment_fix(self, validation_run: ValidationRun, error_message: str):
        """Attempt to fix deployment issues using Codegen"""
        try:
            # Get the associated agent run
            agent_run = await self.db.get(AgentRun, validation_run.agent_run_id)
            if not agent_run:
                return
            
            # Create continuation to fix deployment
            from backend.services.agent_service import AgentService
            agent_service = AgentService(self.db, self.connection_manager)
            
            fix_prompt = f"""
            The deployment failed with the following error:
            {error_message}
            
            Deployment logs:
            {validation_run.deployment_logs}
            
            Please update the PR to fix these deployment issues.
            """
            
            await agent_service.continue_agent_run(agent_run.id, fix_prompt)
            
            logger.info("Initiated deployment fix", validation_run_id=validation_run.id)
            
        except Exception as e:
            logger.error("Failed to initiate deployment fix", 
                        validation_run_id=validation_run.id, error=str(e))
    
    async def _attempt_auto_merge(self, validation_run: ValidationRun):
        """Attempt to auto-merge the PR if all validations passed"""
        try:
            if not validation_run.merge_ready:
                return
            
            # Get project details
            project = await self.db.get(Project, validation_run.project_id)
            
            # Merge the PR
            merge_result = await self.github_client.merge_pull_request(
                project.github_owner,
                project.github_repo,
                validation_run.pr_number,
                commit_title=f"Auto-merge: {validation_run.pr_number}",
                commit_message="Automatically merged after successful validation pipeline"
            )
            
            if merge_result.get("merged"):
                validation_run.merge_url = merge_result.get("html_url")
                
                # Update associated agent run
                if validation_run.agent_run_id:
                    agent_run = await self.db.get(AgentRun, validation_run.agent_run_id)
                    if agent_run:
                        agent_run.merge_completed = True
                        agent_run.merge_url = validation_run.merge_url
                
                await self.db.commit()
                
                logger.info("PR auto-merged successfully", validation_run_id=validation_run.id,
                           pr_number=validation_run.pr_number)
                
                # Notify completion
                await self.connection_manager.broadcast_to_project(
                    validation_run.project_id,
                    {
                        "type": "pr_merged",
                        "validation_run_id": validation_run.id,
                        "pr_number": validation_run.pr_number,
                        "merge_url": validation_run.merge_url
                    }
                )
            
        except Exception as e:
            logger.error("Auto-merge failed", validation_run_id=validation_run.id, error=str(e))
    
    async def _notify_validation_update(self, validation_run: ValidationRun):
        """Notify clients of validation updates via WebSocket"""
        try:
            await self.connection_manager.broadcast_to_project(
                validation_run.project_id,
                {
                    "type": "validation_update",
                    "validation_run": validation_run.to_dict()
                }
            )
        except Exception as e:
            logger.error("Failed to notify validation update", 
                        validation_run_id=validation_run.id, error=str(e))
    
    async def get_validation_run(self, validation_run_id: int) -> Optional[ValidationRun]:
        """Get validation run by ID"""
        return await self.db.get(ValidationRun, validation_run_id)
    
    async def list_validation_runs(self, project_id: Optional[int] = None,
                                  status: Optional[ValidationStatus] = None,
                                  limit: int = 50, offset: int = 0) -> List[ValidationRun]:
        """List validation runs with filters"""
        try:
            query = select(ValidationRun)
            
            conditions = []
            if project_id:
                conditions.append(ValidationRun.project_id == project_id)
            if status:
                conditions.append(ValidationRun.status == status)
            
            if conditions:
                query = query.where(*conditions)
            
            query = query.order_by(ValidationRun.created_at.desc()).limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Failed to list validation runs", error=str(e))
            raise

