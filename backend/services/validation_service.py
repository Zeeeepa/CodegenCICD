"""
Validation pipeline service for managing the 7-step validation process
"""
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from backend.integrations.grainchain_client import GrainchainClient
from backend.integrations.graph_sitter_client import GraphSitterClient
from backend.integrations.web_eval_agent_client import WebEvalAgentClient
from backend.integrations.gemini_client import GeminiClient
from backend.services.github_service import GitHubService
from backend.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

class ValidationStep(Enum):
    SNAPSHOT_CREATION = "snapshot_creation"
    CODE_CLONE = "code_clone"
    CODE_ANALYSIS = "code_analysis"
    DEPLOYMENT = "deployment"
    DEPLOYMENT_VALIDATION = "deployment_validation"
    UI_TESTING = "ui_testing"
    AUTO_MERGE = "auto_merge"

class ValidationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ValidationService:
    def __init__(self):
        self.grainchain = GrainchainClient()
        self.graph_sitter = GraphSitterClient()
        self.web_eval_agent = WebEvalAgentClient()
        self.gemini = GeminiClient()
        self.github = GitHubService()
        self.connection_manager = ConnectionManager()
    
    async def start_validation_pipeline(self, agent_run_id: int) -> Dict[str, Any]:
        """Start the complete 7-step validation pipeline"""
        try:
            from backend.database import AsyncSessionLocal
            from backend.models.agent_run import AgentRun, ValidationStatus as DBValidationStatus
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                # Get agent run
                result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
                agent_run = result.scalar_one()
                
                if not agent_run.pr_url:
                    raise Exception("No PR URL found for validation")
                
                # Initialize validation status
                agent_run.validation_status = DBValidationStatus.SNAPSHOT_CREATING
                await db.commit()
                
                # Start validation in background
                asyncio.create_task(self._run_validation_pipeline(agent_run_id))
                
                return {"status": "started", "agent_run_id": agent_run_id}
                
        except Exception as e:
            logger.error(f"Failed to start validation pipeline: {e}")
            raise
    
    async def _run_validation_pipeline(self, agent_run_id: int):
        """Run the complete validation pipeline"""
        from backend.database import AsyncSessionLocal
        from backend.models.agent_run import AgentRun
        from backend.models.project import Project
        from sqlalchemy import select
        
        validation_logs = []
        current_step = 0
        
        steps = [
            (ValidationStep.SNAPSHOT_CREATION, self._step_snapshot_creation),
            (ValidationStep.CODE_CLONE, self._step_code_clone),
            (ValidationStep.CODE_ANALYSIS, self._step_code_analysis),
            (ValidationStep.DEPLOYMENT, self._step_deployment),
            (ValidationStep.DEPLOYMENT_VALIDATION, self._step_deployment_validation),
            (ValidationStep.UI_TESTING, self._step_ui_testing),
            (ValidationStep.AUTO_MERGE, self._step_auto_merge),
        ]
        
        try:
            async with AsyncSessionLocal() as db:
                # Get agent run and project
                result = await db.execute(
                    select(AgentRun, Project)
                    .join(Project)
                    .where(AgentRun.id == agent_run_id)
                )
                agent_run, project = result.one()
                
                context = {
                    "agent_run": agent_run,
                    "project": project,
                    "snapshot_id": None,
                    "deployment_url": None,
                    "validation_logs": validation_logs
                }
                
                # Send initial update
                await self._send_validation_update(
                    agent_run.project_id,
                    agent_run_id,
                    "running",
                    current_step,
                    steps,
                    validation_logs
                )
                
                # Execute each step
                for i, (step_enum, step_func) in enumerate(steps):
                    current_step = i
                    step_name = step_enum.value
                    
                    logger.info(f"Starting validation step {i+1}/7: {step_name}")
                    
                    # Update step status to running
                    await self._send_validation_update(
                        agent_run.project_id,
                        agent_run_id,
                        "running",
                        current_step,
                        steps,
                        validation_logs,
                        step_status="running"
                    )
                    
                    try:
                        # Execute step
                        step_result = await step_func(context)
                        
                        # Log success
                        validation_logs.append({
                            "step": step_name,
                            "status": "completed",
                            "timestamp": datetime.utcnow().isoformat(),
                            "result": step_result,
                            "duration": step_result.get("duration", 0)
                        })
                        
                        # Update step status to completed
                        await self._send_validation_update(
                            agent_run.project_id,
                            agent_run_id,
                            "running",
                            current_step,
                            steps,
                            validation_logs,
                            step_status="completed"
                        )
                        
                    except Exception as step_error:
                        logger.error(f"Validation step {step_name} failed: {step_error}")
                        
                        # Log failure
                        validation_logs.append({
                            "step": step_name,
                            "status": "failed",
                            "timestamp": datetime.utcnow().isoformat(),
                            "error": str(step_error)
                        })
                        
                        # Update step status to failed
                        await self._send_validation_update(
                            agent_run.project_id,
                            agent_run_id,
                            "failed",
                            current_step,
                            steps,
                            validation_logs,
                            step_status="failed"
                        )
                        
                        # Handle error recovery
                        recovery_success = await self._handle_step_failure(
                            context, step_name, str(step_error)
                        )
                        
                        if not recovery_success:
                            # Update database
                            async with AsyncSessionLocal() as db:
                                result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
                                agent_run = result.scalar_one()
                                agent_run.validation_status = "failed"
                                agent_run.validation_error = str(step_error)
                                agent_run.validation_logs = validation_logs
                                await db.commit()
                            
                            return
                
                # All steps completed successfully
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
                    agent_run = result.scalar_one()
                    agent_run.validation_status = "completed"
                    agent_run.validation_logs = validation_logs
                    await db.commit()
                
                # Send final update
                await self._send_validation_update(
                    agent_run.project_id,
                    agent_run_id,
                    "completed",
                    len(steps),
                    steps,
                    validation_logs
                )
                
                logger.info(f"Validation pipeline completed successfully for agent run {agent_run_id}")
                
        except Exception as e:
            logger.error(f"Validation pipeline failed: {e}")
            
            # Update database
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
                agent_run = result.scalar_one()
                agent_run.validation_status = "failed"
                agent_run.validation_error = str(e)
                agent_run.validation_logs = validation_logs
                await db.commit()
    
    async def _step_snapshot_creation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: Create grainchain snapshot with required tools"""
        start_time = datetime.utcnow()
        
        # Create snapshot with grainchain + web-eval-agent + graph-sitter
        snapshot_config = {
            "tools": ["grainchain", "web-eval-agent", "graph-sitter"],
            "environment_variables": await self._get_project_secrets(context["project"].id)
        }
        
        snapshot_id = await self.grainchain.create_snapshot(snapshot_config)
        context["snapshot_id"] = snapshot_id
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "snapshot_id": snapshot_id,
            "duration": duration,
            "message": "Snapshot created successfully with required tools"
        }
    
    async def _step_code_clone(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: Clone PR codebase to sandbox"""
        start_time = datetime.utcnow()
        
        agent_run = context["agent_run"]
        project = context["project"]
        
        # Extract PR branch from PR URL
        pr_info = await self.github.get_pull_request(
            project.github_owner,
            project.github_repo,
            agent_run.pr_number
        )
        
        if not pr_info:
            raise Exception("Could not retrieve PR information")
        
        # Clone the PR branch
        clone_result = await self.grainchain.clone_repository(
            context["snapshot_id"],
            f"https://github.com/{project.github_owner}/{project.github_repo}.git",
            pr_info["head"]["ref"]
        )
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "clone_result": clone_result,
            "branch": pr_info["head"]["ref"],
            "duration": duration,
            "message": f"Successfully cloned PR branch: {pr_info['head']['ref']}"
        }
    
    async def _step_code_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Run graph-sitter code analysis"""
        start_time = datetime.utcnow()
        
        # Run code quality analysis
        analysis_result = await self.graph_sitter.analyze_codebase(
            context["snapshot_id"],
            languages=["typescript", "javascript", "python", "rust", "go"]
        )
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "analysis_result": analysis_result,
            "duration": duration,
            "message": "Code analysis completed successfully"
        }
    
    async def _step_deployment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Execute deployment commands"""
        start_time = datetime.utcnow()
        
        # Get setup commands from project configuration
        setup_commands = await self._get_setup_commands(context["project"].id)
        
        if not setup_commands:
            return {
                "duration": 0,
                "message": "No setup commands configured, skipping deployment"
            }
        
        # Execute commands in sandbox
        deployment_result = await self.grainchain.execute_commands(
            context["snapshot_id"],
            setup_commands.split('\n')
        )
        
        # Store deployment URL if available
        context["deployment_url"] = deployment_result.get("url")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "deployment_result": deployment_result,
            "deployment_url": context["deployment_url"],
            "duration": duration,
            "message": "Deployment completed successfully"
        }
    
    async def _step_deployment_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 5: Validate deployment using Gemini API"""
        start_time = datetime.utcnow()
        
        deployment_logs = context.get("validation_logs", [])
        deployment_url = context.get("deployment_url")
        
        # Use Gemini to analyze deployment success
        validation_prompt = f"""
        Analyze the following deployment logs and determine if the deployment was successful:
        
        Deployment URL: {deployment_url or 'Not available'}
        
        Recent logs:
        {deployment_logs[-3:] if deployment_logs else 'No logs available'}
        
        Please provide:
        1. Success/failure assessment
        2. Confidence score (0-100)
        3. Any issues identified
        4. Recommendations if failed
        """
        
        validation_result = await self.gemini.analyze_deployment(validation_prompt)
        
        # Check if validation passed
        confidence_score = validation_result.get("confidence_score", 0)
        if confidence_score < 70:
            raise Exception(f"Deployment validation failed: {validation_result.get('issues', 'Low confidence score')}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "validation_result": validation_result,
            "confidence_score": confidence_score,
            "duration": duration,
            "message": f"Deployment validated successfully (confidence: {confidence_score}%)"
        }
    
    async def _step_ui_testing(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 6: Run comprehensive UI testing with web-eval-agent"""
        start_time = datetime.utcnow()
        
        deployment_url = context.get("deployment_url")
        
        if not deployment_url:
            # Try to determine URL from deployment logs or use localhost
            deployment_url = "http://localhost:3000"
        
        # Run comprehensive UI tests
        test_config = {
            "url": deployment_url,
            "tests": [
                "component_rendering",
                "user_flows",
                "accessibility",
                "performance",
                "responsive_design"
            ]
        }
        
        test_results = await self.web_eval_agent.run_tests(
            context["snapshot_id"],
            test_config
        )
        
        # Check if tests passed
        failed_tests = [test for test in test_results.get("results", []) if not test.get("passed")]
        if failed_tests:
            raise Exception(f"UI tests failed: {len(failed_tests)} test(s) failed")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "test_results": test_results,
            "passed_tests": len(test_results.get("results", [])) - len(failed_tests),
            "failed_tests": len(failed_tests),
            "duration": duration,
            "message": f"UI testing completed: {len(test_results.get('results', []))} tests passed"
        }
    
    async def _step_auto_merge(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 7: Auto-merge PR if enabled and validation passed"""
        start_time = datetime.utcnow()
        
        agent_run = context["agent_run"]
        project = context["project"]
        
        if not agent_run.auto_merge_enabled:
            return {
                "duration": 0,
                "message": "Auto-merge disabled, skipping merge step"
            }
        
        # Merge the PR
        merge_result = await self.github.merge_pull_request(
            project.github_owner,
            project.github_repo,
            agent_run.pr_number,
            commit_title=f"Auto-merge: {agent_run.target_text[:50]}...",
            commit_message="Automatically merged after successful validation pipeline"
        )
        
        # Update agent run
        from backend.database import AsyncSessionLocal
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AgentRun).where(AgentRun.id == agent_run.id))
            db_agent_run = result.scalar_one()
            db_agent_run.merge_completed = True
            db_agent_run.merge_url = merge_result.get("html_url")
            await db.commit()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "merge_result": merge_result,
            "merge_url": merge_result.get("html_url"),
            "duration": duration,
            "message": f"PR #{agent_run.pr_number} merged successfully"
        }
    
    async def _handle_step_failure(self, context: Dict[str, Any], step_name: str, error: str) -> bool:
        """Handle validation step failure with automatic recovery"""
        try:
            # Use Gemini to analyze the error and suggest fixes
            recovery_prompt = f"""
            A validation step failed in our CI/CD pipeline:
            
            Step: {step_name}
            Error: {error}
            
            Please analyze this error and provide:
            1. Root cause analysis
            2. Specific fix recommendations
            3. Code changes needed (if applicable)
            
            Context: This is part of an automated validation pipeline for a GitHub PR.
            """
            
            recovery_analysis = await self.gemini.analyze_error(recovery_prompt)
            
            # If Gemini suggests code fixes, attempt to apply them via Codegen API
            if recovery_analysis.get("code_fixes"):
                # TODO: Implement automatic code fix application
                # This would involve continuing the agent run with the suggested fixes
                pass
            
            # For now, return False to indicate manual intervention needed
            return False
            
        except Exception as e:
            logger.error(f"Error recovery failed: {e}")
            return False
    
    async def _send_validation_update(self, project_id: int, agent_run_id: int, 
                                    overall_status: str, current_step: int, 
                                    steps: List, validation_logs: List,
                                    step_status: str = None):
        """Send validation update via WebSocket"""
        try:
            update_data = {
                "type": "validation_update",
                "agent_run_id": agent_run_id,
                "overall_status": overall_status,
                "current_step": current_step,
                "total_steps": len(steps),
                "steps": [
                    {
                        "name": step[0].value,
                        "status": "completed" if i < current_step else 
                                "running" if i == current_step and step_status == "running" else
                                "failed" if i == current_step and step_status == "failed" else
                                "pending"
                    }
                    for i, step in enumerate(steps)
                ],
                "logs": validation_logs[-5:],  # Last 5 log entries
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.connection_manager.broadcast_to_project(project_id, update_data)
            
        except Exception as e:
            logger.error(f"Failed to send validation update: {e}")
    
    async def _get_project_secrets(self, project_id: int) -> Dict[str, str]:
        """Get decrypted project secrets"""
        try:
            from backend.database import AsyncSessionLocal
            from backend.models.configuration import ProjectSecret
            from backend.utils.encryption import decrypt_value
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ProjectSecret).where(ProjectSecret.project_id == project_id)
                )
                secrets = result.scalars().all()
                
                decrypted_secrets = {}
                for secret in secrets:
                    try:
                        decrypted_value = decrypt_value(secret.value)
                        decrypted_secrets[secret.key] = decrypted_value
                    except Exception as e:
                        logger.error(f"Failed to decrypt secret {secret.key}: {e}")
                
                return decrypted_secrets
                
        except Exception as e:
            logger.error(f"Failed to get project secrets: {e}")
            return {}
    
    async def _get_setup_commands(self, project_id: int) -> Optional[str]:
        """Get setup commands for a project"""
        try:
            from backend.database import AsyncSessionLocal
            from backend.models.configuration import ProjectConfiguration
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
                )
                config = result.scalar_one_or_none()
                
                return config.setup_commands if config else None
                
        except Exception as e:
            logger.error(f"Failed to get setup commands: {e}")
            return None

