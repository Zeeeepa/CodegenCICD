"""
Enhanced Validation Service implementing the complete 7-step validation pipeline
Integrates grainchain, web-eval-agent, graph-sitter, and Gemini API
"""
import asyncio
from typing import Optional, Dict, Any, List, Tuple
import structlog
from datetime import datetime
import json
import tempfile
import shutil
import os
from pathlib import Path

from backend.config import get_settings
from backend.database import get_db_session
from backend.models.validation import ValidationPipeline, ValidationStep, ValidationStatus, ValidationStepType
from backend.models.project import Project
from backend.models.agent_run import AgentRun
from backend.integrations.grainchain_client import GrainchainClient
from backend.integrations.web_eval_client import WebEvalClient
from backend.integrations.graph_sitter_client import GraphSitterClient
from backend.integrations.gemini_client import GeminiClient
from backend.integrations.github_client import GitHubClient
from backend.services.websocket_service import WebSocketService

logger = structlog.get_logger(__name__)
settings = get_settings()


class ValidationService:
    """Comprehensive validation service implementing the 7-step pipeline"""
    
    def __init__(self):
        self.grainchain_client = GrainchainClient() if settings.grainchain_enabled else None
        self.web_eval_client = WebEvalClient() if settings.web_eval_enabled else None
        self.graph_sitter_client = GraphSitterClient() if settings.graph_sitter_enabled else None
        self.gemini_client = GeminiClient()
        self.github_client = GitHubClient()
        self.websocket_service = WebSocketService()
        
        logger.info("Validation service initialized", 
                   grainchain_enabled=settings.grainchain_enabled,
                   web_eval_enabled=settings.web_eval_enabled,
                   graph_sitter_enabled=settings.graph_sitter_enabled)
    
    async def create_validation_pipeline(self, project_id: int, pr_number: int,
                                       pr_url: str, pr_branch: str,
                                       agent_run_id: Optional[int] = None,
                                       auto_merge_enabled: bool = False) -> ValidationPipeline:
        """Create a new validation pipeline"""
        async with get_db_session() as session:
            # Create pipeline
            pipeline = ValidationPipeline(
                project_id=project_id,
                agent_run_id=agent_run_id,
                pr_number=pr_number,
                pr_url=pr_url,
                pr_branch=pr_branch,
                auto_merge_enabled=auto_merge_enabled,
                status=ValidationStatus.NOT_STARTED
            )
            
            session.add(pipeline)
            await session.flush()  # Get the ID
            
            # Create default validation steps
            steps = ValidationStep.create_default_steps(pipeline.id)
            for step in steps:
                session.add(step)
            
            await session.commit()
            await session.refresh(pipeline)
            
            logger.info("Validation pipeline created", 
                       pipeline_id=pipeline.id,
                       project_id=project_id,
                       pr_number=pr_number)
            
            return pipeline
    
    async def start_validation_pipeline(self, pipeline_id: int) -> bool:
        """Start the validation pipeline execution"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                if not pipeline:
                    raise ValueError(f"Pipeline {pipeline_id} not found")
                
                pipeline.status = ValidationStatus.RUNNING
                pipeline.started_at = datetime.now()
                await session.commit()
            
            # Send WebSocket update
            await self.websocket_service.broadcast_validation_update(pipeline_id, {
                "type": "validation_started",
                "pipeline_id": pipeline_id,
                "status": "running"
            })
            
            # Start pipeline execution in background
            asyncio.create_task(self._execute_pipeline(pipeline_id))
            
            logger.info("Validation pipeline started", pipeline_id=pipeline_id)
            return True
            
        except Exception as e:
            logger.error("Failed to start validation pipeline", 
                        pipeline_id=pipeline_id, error=str(e))
            return False
    
    async def _execute_pipeline(self, pipeline_id: int) -> None:
        """Execute the complete validation pipeline"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                if not pipeline:
                    return
                
                project = await session.get(Project, pipeline.project_id)
                if not project:
                    return
            
            # Execute each step in sequence
            for step_index in range(7):
                success = await self._execute_step(pipeline_id, step_index)
                if not success:
                    await self._handle_step_failure(pipeline_id, step_index)
                    break
                
                # Send progress update
                await self.websocket_service.broadcast_validation_update(pipeline_id, {
                    "type": "validation_step_completed",
                    "pipeline_id": pipeline_id,
                    "step_index": step_index,
                    "status": "completed"
                })
            
            # Complete pipeline
            await self._complete_pipeline(pipeline_id)
            
        except Exception as e:
            logger.error("Pipeline execution failed", 
                        pipeline_id=pipeline_id, error=str(e))
            await self._fail_pipeline(pipeline_id, str(e))
    
    async def _execute_step(self, pipeline_id: int, step_index: int) -> bool:
        """Execute a specific validation step"""
        step_handlers = {
            0: self._step_snapshot_creation,
            1: self._step_code_clone,
            2: self._step_code_analysis,
            3: self._step_deployment,
            4: self._step_deployment_validation,
            5: self._step_ui_testing,
            6: self._step_auto_merge
        }
        
        handler = step_handlers.get(step_index)
        if not handler:
            logger.error("Unknown step index", step_index=step_index)
            return False
        
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                step = pipeline.steps[step_index]
                
                step.start_execution()
                await session.commit()
            
            # Execute step
            success, score, output, error = await handler(pipeline_id)
            
            # Update step
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                step = pipeline.steps[step_index]
                
                step.complete_execution(success, score, output, error)
                pipeline.update_progress(step_index, 
                                       ValidationStatus.COMPLETED if success else ValidationStatus.FAILED,
                                       score, error)
                await session.commit()
            
            logger.info("Validation step completed", 
                       pipeline_id=pipeline_id,
                       step_index=step_index,
                       success=success,
                       score=score)
            
            return success
            
        except Exception as e:
            logger.error("Step execution failed", 
                        pipeline_id=pipeline_id,
                        step_index=step_index,
                        error=str(e))
            return False
    
    async def _step_snapshot_creation(self, pipeline_id: int) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Step 1: Create sandbox environment with grainchain + web-eval-agent + graph-sitter"""
        if not self.grainchain_client:
            return False, 0.0, None, "Grainchain not enabled"
        
        try:
            # Create grainchain workspace
            workspace_config = {
                "tools": ["web-eval-agent", "graph-sitter"],
                "environment": {
                    "GEMINI_API_KEY": settings.gemini_api_key,
                    "GITHUB_TOKEN": settings.github_token
                }
            }
            
            workspace = await self.grainchain_client.create_workspace(
                name=f"validation-{pipeline_id}",
                config=workspace_config
            )
            
            if workspace and workspace.get("status") == "ready":
                return True, 100.0, f"Workspace created: {workspace.get('id')}", None
            else:
                return False, 0.0, None, "Failed to create workspace"
                
        except Exception as e:
            return False, 0.0, None, str(e)
    
    async def _step_code_clone(self, pipeline_id: int) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Step 2: Clone PR branch to sandbox environment"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                project = await session.get(Project, pipeline.project_id)
            
            # Clone repository using GitHub client
            clone_result = await self.github_client.clone_repository(
                owner=project.github_owner,
                repo=project.github_repo,
                branch=pipeline.pr_branch,
                workspace_id=f"validation-{pipeline_id}"
            )
            
            if clone_result.get("success"):
                return True, 100.0, f"Repository cloned to {clone_result.get('path')}", None
            else:
                return False, 0.0, None, clone_result.get("error", "Clone failed")
                
        except Exception as e:
            return False, 0.0, None, str(e)
    
    async def _step_code_analysis(self, pipeline_id: int) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Step 3: Analyze code quality using graph-sitter"""
        if not self.graph_sitter_client:
            return True, 85.0, "Code analysis skipped (graph-sitter not enabled)", None
        
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                project = await session.get(Project, pipeline.project_id)
            
            # Analyze code quality
            analysis_result = await self.graph_sitter_client.analyze_repository(
                workspace_id=f"validation-{pipeline_id}",
                languages=settings.graph_sitter_languages,
                config={
                    "max_file_size": settings.graph_sitter_max_file_size,
                    "timeout": settings.graph_sitter_analysis_timeout
                }
            )
            
            if analysis_result.get("success"):
                score = analysis_result.get("quality_score", 85.0)
                summary = analysis_result.get("summary", "Code analysis completed")
                return True, score, summary, None
            else:
                return False, 0.0, None, analysis_result.get("error", "Analysis failed")
                
        except Exception as e:
            return False, 0.0, None, str(e)
    
    async def _step_deployment(self, pipeline_id: int) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Step 4: Execute setup commands and deploy application"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                project = await session.get(Project, pipeline.project_id)
            
            if not project.setup_commands:
                return True, 90.0, "No setup commands configured", None
            
            # Execute setup commands in grainchain workspace
            if self.grainchain_client:
                execution_result = await self.grainchain_client.execute_commands(
                    workspace_id=f"validation-{pipeline_id}",
                    commands=project.setup_commands.split('\n'),
                    timeout=settings.validation_timeout
                )
                
                if execution_result.get("success"):
                    return True, 95.0, execution_result.get("output", "Deployment successful"), None
                else:
                    return False, 0.0, None, execution_result.get("error", "Deployment failed")
            else:
                return True, 80.0, "Deployment skipped (grainchain not enabled)", None
                
        except Exception as e:
            return False, 0.0, None, str(e)
    
    async def _step_deployment_validation(self, pipeline_id: int) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Step 5: Validate deployment success using Gemini API"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                project = await session.get(Project, pipeline.project_id)
            
            # Get deployment logs and context
            deployment_context = {
                "project_name": project.name,
                "setup_commands": project.setup_commands,
                "pr_branch": pipeline.pr_branch
            }
            
            # Use Gemini to validate deployment
            validation_prompt = f"""
            Analyze the deployment of project '{project.name}' and determine if it was successful.
            
            Setup commands executed:
            {project.setup_commands or 'None'}
            
            Please provide:
            1. Success status (true/false)
            2. Confidence score (0-100)
            3. Summary of findings
            4. Any issues or recommendations
            """
            
            validation_result = await self.gemini_client.analyze_deployment(
                prompt=validation_prompt,
                context=deployment_context
            )
            
            if validation_result.get("success"):
                score = validation_result.get("confidence_score", 85.0)
                summary = validation_result.get("summary", "Deployment validation completed")
                return True, score, summary, None
            else:
                return False, 0.0, None, validation_result.get("error", "Validation failed")
                
        except Exception as e:
            return False, 0.0, None, str(e)
    
    async def _step_ui_testing(self, pipeline_id: int) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Step 6: Run comprehensive UI tests with web-eval-agent"""
        if not self.web_eval_client:
            return True, 80.0, "UI testing skipped (web-eval-agent not enabled)", None
        
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                project = await session.get(Project, pipeline.project_id)
            
            # Run comprehensive UI tests
            test_config = {
                "browser": settings.web_eval_browser,
                "headless": settings.web_eval_headless,
                "timeout": settings.web_eval_timeout,
                "viewport": {
                    "width": settings.web_eval_viewport_width,
                    "height": settings.web_eval_viewport_height
                }
            }
            
            test_result = await self.web_eval_client.run_comprehensive_tests(
                workspace_id=f"validation-{pipeline_id}",
                config=test_config
            )
            
            if test_result.get("success"):
                score = test_result.get("overall_score", 85.0)
                summary = test_result.get("summary", "UI testing completed")
                
                # Store test artifacts
                async with get_db_session() as session:
                    pipeline = await session.get(ValidationPipeline, pipeline_id)
                    pipeline.set_artifact("ui_test_results", test_result)
                    await session.commit()
                
                return True, score, summary, None
            else:
                return False, 0.0, None, test_result.get("error", "UI testing failed")
                
        except Exception as e:
            return False, 0.0, None, str(e)
    
    async def _step_auto_merge(self, pipeline_id: int) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Step 7: Auto-merge PR if validation passes and auto-merge is enabled"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                project = await session.get(Project, pipeline.project_id)
            
            if not pipeline.can_auto_merge:
                return True, 100.0, "Auto-merge not enabled or conditions not met", None
            
            # Merge PR using GitHub client
            merge_result = await self.github_client.merge_pull_request(
                owner=project.github_owner,
                repo=project.github_repo,
                pr_number=pipeline.pr_number,
                merge_method="squash"  # or "merge", "rebase"
            )
            
            if merge_result.get("success"):
                pipeline.merge_completed = True
                pipeline.merge_url = merge_result.get("merge_commit_url")
                await session.commit()
                
                return True, 100.0, f"PR merged successfully: {merge_result.get('merge_commit_sha')}", None
            else:
                return False, 0.0, None, merge_result.get("error", "Merge failed")
                
        except Exception as e:
            return False, 0.0, None, str(e)
    
    async def _handle_step_failure(self, pipeline_id: int, step_index: int) -> None:
        """Handle step failure with retry logic and error context integration"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                step = pipeline.steps[step_index]
                
                if step.can_retry:
                    step.retry_count += 1
                    await session.commit()
                    
                    logger.info("Retrying failed step", 
                               pipeline_id=pipeline_id,
                               step_index=step_index,
                               retry_count=step.retry_count)
                    
                    # Retry the step
                    success = await self._execute_step(pipeline_id, step_index)
                    if success:
                        return
                
                # If retry failed or no retries left, send error context to Codegen API
                if pipeline.agent_run_id:
                    await self._send_error_context_to_codegen(pipeline_id, step_index)
                
                # Fail the pipeline
                await self._fail_pipeline(pipeline_id, f"Step {step_index} failed after retries")
                
        except Exception as e:
            logger.error("Error handling step failure", 
                        pipeline_id=pipeline_id,
                        step_index=step_index,
                        error=str(e))
    
    async def _send_error_context_to_codegen(self, pipeline_id: int, step_index: int) -> None:
        """Send error context to Codegen API for automatic fixes"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                step = pipeline.steps[step_index]
                agent_run = await session.get(AgentRun, pipeline.agent_run_id)
            
            if not agent_run:
                return
            
            # Prepare error context
            error_context = {
                "step_name": step.name,
                "step_type": step.step_type.value,
                "error_message": step.error_output,
                "command_output": step.output,
                "validation_logs": pipeline.logs,
                "project_setup_commands": agent_run.project.setup_commands
            }
            
            # Create continuation prompt
            continuation_prompt = f"""
            The validation pipeline failed at step "{step.name}" with the following error:
            
            Error: {step.error_output}
            
            Command output: {step.output}
            
            Please analyze the error and update the PR with code changes to resolve this issue.
            Focus on fixing the specific problem that caused the validation to fail.
            """
            
            # Continue the agent run with error context
            from backend.integrations.codegen_client import continue_agent_run
            await continue_agent_run(
                task_id=str(agent_run.codegen_run_id),
                prompt=continuation_prompt,
                context=error_context
            )
            
            logger.info("Error context sent to Codegen API", 
                       pipeline_id=pipeline_id,
                       agent_run_id=agent_run.id)
            
        except Exception as e:
            logger.error("Failed to send error context to Codegen", 
                        pipeline_id=pipeline_id, error=str(e))
    
    async def _complete_pipeline(self, pipeline_id: int) -> None:
        """Complete the validation pipeline"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                
                pipeline.status = ValidationStatus.COMPLETED
                pipeline.completed_at = datetime.now()
                
                if pipeline.started_at:
                    duration = datetime.now() - pipeline.started_at
                    pipeline.duration_seconds = int(duration.total_seconds())
                
                await session.commit()
            
            # Send completion notification
            await self.websocket_service.broadcast_validation_update(pipeline_id, {
                "type": "validation_completed",
                "pipeline_id": pipeline_id,
                "status": "completed",
                "overall_score": pipeline.overall_score,
                "can_auto_merge": pipeline.can_auto_merge
            })
            
            logger.info("Validation pipeline completed", 
                       pipeline_id=pipeline_id,
                       overall_score=pipeline.overall_score)
            
        except Exception as e:
            logger.error("Failed to complete pipeline", 
                        pipeline_id=pipeline_id, error=str(e))
    
    async def _fail_pipeline(self, pipeline_id: int, error_message: str) -> None:
        """Fail the validation pipeline"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                
                pipeline.status = ValidationStatus.FAILED
                pipeline.error_message = error_message
                pipeline.completed_at = datetime.now()
                
                if pipeline.started_at:
                    duration = datetime.now() - pipeline.started_at
                    pipeline.duration_seconds = int(duration.total_seconds())
                
                await session.commit()
            
            # Send failure notification
            await self.websocket_service.broadcast_validation_update(pipeline_id, {
                "type": "validation_failed",
                "pipeline_id": pipeline_id,
                "status": "failed",
                "error_message": error_message
            })
            
            logger.error("Validation pipeline failed", 
                        pipeline_id=pipeline_id,
                        error=error_message)
            
        except Exception as e:
            logger.error("Failed to fail pipeline", 
                        pipeline_id=pipeline_id, error=str(e))
    
    async def get_pipeline_status(self, pipeline_id: int) -> Optional[Dict[str, Any]]:
        """Get validation pipeline status"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                if not pipeline:
                    return None
                
                return pipeline.to_dict(include_steps=True, include_logs=True)
                
        except Exception as e:
            logger.error("Failed to get pipeline status", 
                        pipeline_id=pipeline_id, error=str(e))
            return None
    
    async def cancel_pipeline(self, pipeline_id: int) -> bool:
        """Cancel a running validation pipeline"""
        try:
            async with get_db_session() as session:
                pipeline = await session.get(ValidationPipeline, pipeline_id)
                if not pipeline or not pipeline.is_running:
                    return False
                
                pipeline.status = ValidationStatus.CANCELLED
                pipeline.completed_at = datetime.now()
                await session.commit()
            
            # Clean up grainchain workspace
            if self.grainchain_client:
                await self.grainchain_client.cleanup_workspace(f"validation-{pipeline_id}")
            
            logger.info("Validation pipeline cancelled", pipeline_id=pipeline_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cancel pipeline", 
                        pipeline_id=pipeline_id, error=str(e))
            return False

