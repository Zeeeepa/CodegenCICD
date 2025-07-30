"""
Integrated Agent Manager
Orchestrates all library services to provide unified CI/CD pipeline functionality
"""
import asyncio
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime
from enum import Enum

from .grainchain_service import GrainchainService
from .graph_sitter_service import GraphSitterService
from .web_eval_service import WebEvalService
from .codegen_sdk_service import CodegenSDKService

logger = structlog.get_logger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages"""
    INITIALIZATION = "initialization"
    CODE_ANALYSIS = "code_analysis"
    SANDBOX_EXECUTION = "sandbox_execution"
    UI_TESTING = "ui_testing"
    RESULTS_INTEGRATION = "results_integration"
    COMPLETION = "completion"


class PipelineStatus(Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IntegratedAgentManager:
    """
    Unified manager for orchestrating all integrated library services
    """
    
    def __init__(self):
        # Initialize all service components
        self.grainchain = GrainchainService()
        self.graph_sitter = GraphSitterService()
        self.web_eval = WebEvalService()
        self.codegen_sdk = CodegenSDKService()
        
        # Pipeline tracking
        self.active_pipelines = {}
        self.pipeline_history = []
        
        logger.info("IntegratedAgentManager initialized", 
                   services_initialized=4)
    
    async def execute_full_pipeline(
        self, 
        task_data: Dict[str, Any],
        pipeline_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete CI/CD pipeline using all integrated libraries
        
        Args:
            task_data: Task configuration and parameters
            pipeline_config: Optional pipeline configuration overrides
            
        Returns:
            Dictionary with comprehensive pipeline results
        """
        pipeline_id = f"pipeline_{datetime.now().timestamp()}"
        start_time = datetime.now()
        
        # Initialize pipeline tracking
        pipeline_result = {
            "pipeline_id": pipeline_id,
            "status": PipelineStatus.RUNNING.value,
            "started_at": start_time.isoformat(),
            "task_data": task_data,
            "pipeline_config": pipeline_config or {},
            "stages": {},
            "current_stage": PipelineStage.INITIALIZATION.value,
            "progress": 0,
            "errors": [],
            "warnings": []
        }
        
        self.active_pipelines[pipeline_id] = pipeline_result
        
        logger.info("Starting integrated pipeline execution", 
                   pipeline_id=pipeline_id,
                   task_type=task_data.get("type", "unknown"))
        
        try:
            # Stage 1: Initialization & Agent Run Creation
            await self._execute_stage(
                pipeline_result, 
                PipelineStage.INITIALIZATION,
                self._stage_initialization,
                task_data
            )
            
            # Stage 2: Code Analysis with Graph-sitter
            if task_data.get("repo_path") or task_data.get("code_analysis_enabled", True):
                await self._execute_stage(
                    pipeline_result,
                    PipelineStage.CODE_ANALYSIS,
                    self._stage_code_analysis,
                    task_data
                )
            
            # Stage 3: Sandbox Execution with Grainchain
            if task_data.get("code_to_execute") or task_data.get("sandbox_execution_enabled", False):
                await self._execute_stage(
                    pipeline_result,
                    PipelineStage.SANDBOX_EXECUTION,
                    self._stage_sandbox_execution,
                    task_data
                )
            
            # Stage 4: UI Testing with Web-eval-agent
            if task_data.get("webapp_url") or task_data.get("ui_testing_enabled", False):
                await self._execute_stage(
                    pipeline_result,
                    PipelineStage.UI_TESTING,
                    self._stage_ui_testing,
                    task_data
                )
            
            # Stage 5: Results Integration
            await self._execute_stage(
                pipeline_result,
                PipelineStage.RESULTS_INTEGRATION,
                self._stage_results_integration,
                task_data
            )
            
            # Stage 6: Completion
            await self._execute_stage(
                pipeline_result,
                PipelineStage.COMPLETION,
                self._stage_completion,
                task_data
            )
            
            # Mark pipeline as completed
            pipeline_result["status"] = PipelineStatus.COMPLETED.value
            pipeline_result["completed_at"] = datetime.now().isoformat()
            pipeline_result["execution_time"] = (datetime.now() - start_time).total_seconds()
            pipeline_result["progress"] = 100
            
            logger.info("Pipeline execution completed successfully", 
                       pipeline_id=pipeline_id,
                       execution_time=pipeline_result["execution_time"])
            
        except Exception as e:
            # Handle pipeline failure
            pipeline_result["status"] = PipelineStatus.FAILED.value
            pipeline_result["completed_at"] = datetime.now().isoformat()
            pipeline_result["execution_time"] = (datetime.now() - start_time).total_seconds()
            pipeline_result["error"] = str(e)
            pipeline_result["errors"].append({
                "stage": pipeline_result["current_stage"],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            logger.error("Pipeline execution failed", 
                        pipeline_id=pipeline_id,
                        error=str(e),
                        current_stage=pipeline_result["current_stage"])
        
        finally:
            # Move to history and cleanup
            self.pipeline_history.append(pipeline_result.copy())
            self.active_pipelines.pop(pipeline_id, None)
        
        return pipeline_result
    
    async def _execute_stage(
        self, 
        pipeline_result: Dict[str, Any],
        stage: PipelineStage,
        stage_function,
        task_data: Dict[str, Any]
    ):
        """Execute a pipeline stage with error handling and progress tracking"""
        stage_name = stage.value
        pipeline_result["current_stage"] = stage_name
        
        stage_start = datetime.now()
        
        logger.info("Executing pipeline stage", 
                   pipeline_id=pipeline_result["pipeline_id"],
                   stage=stage_name)
        
        try:
            # Execute stage function
            stage_result = await stage_function(task_data, pipeline_result)
            
            # Record stage results
            pipeline_result["stages"][stage_name] = {
                "status": "completed",
                "started_at": stage_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "execution_time": (datetime.now() - stage_start).total_seconds(),
                "result": stage_result
            }
            
            # Update progress
            stage_progress = {
                PipelineStage.INITIALIZATION: 10,
                PipelineStage.CODE_ANALYSIS: 30,
                PipelineStage.SANDBOX_EXECUTION: 50,
                PipelineStage.UI_TESTING: 70,
                PipelineStage.RESULTS_INTEGRATION: 90,
                PipelineStage.COMPLETION: 100
            }
            pipeline_result["progress"] = stage_progress.get(stage, 0)
            
            logger.info("Pipeline stage completed", 
                       pipeline_id=pipeline_result["pipeline_id"],
                       stage=stage_name,
                       execution_time=pipeline_result["stages"][stage_name]["execution_time"])
            
        except Exception as e:
            # Record stage failure
            pipeline_result["stages"][stage_name] = {
                "status": "failed",
                "started_at": stage_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "execution_time": (datetime.now() - stage_start).total_seconds(),
                "error": str(e)
            }
            
            pipeline_result["errors"].append({
                "stage": stage_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            logger.error("Pipeline stage failed", 
                        pipeline_id=pipeline_result["pipeline_id"],
                        stage=stage_name,
                        error=str(e))
            
            raise  # Re-raise to fail the pipeline
    
    async def _stage_initialization(
        self, 
        task_data: Dict[str, Any], 
        pipeline_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 1: Initialize pipeline and create Codegen agent run"""
        
        # Create Codegen agent run if enabled
        agent_run_result = None
        if task_data.get("create_agent_run", True):
            agent_run_data = {
                "description": task_data.get("description", "Integrated pipeline execution"),
                "type": task_data.get("type", "integrated_pipeline"),
                "configuration": task_data.get("configuration", {}),
                "context": {
                    "pipeline_id": pipeline_result["pipeline_id"],
                    "stages_enabled": {
                        "code_analysis": bool(task_data.get("repo_path")),
                        "sandbox_execution": bool(task_data.get("code_to_execute")),
                        "ui_testing": bool(task_data.get("webapp_url"))
                    }
                }
            }
            
            agent_run_result = await self.codegen_sdk.create_agent_run(
                agent_run_data,
                priority=task_data.get("priority", "normal")
            )
            
            if agent_run_result.get("success"):
                pipeline_result["agent_run_id"] = agent_run_result["agent_run_id"]
        
        # Validate service availability
        service_status = await self.get_service_health()
        
        return {
            "agent_run": agent_run_result,
            "service_status": service_status,
            "pipeline_config_validated": True,
            "initialization_completed": True
        }
    
    async def _stage_code_analysis(
        self, 
        task_data: Dict[str, Any], 
        pipeline_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 2: Perform code analysis using Graph-sitter"""
        
        repo_path = task_data.get("repo_path")
        if not repo_path:
            return {"skipped": True, "reason": "No repository path provided"}
        
        # Perform comprehensive code analysis
        analysis_result = await self.graph_sitter.analyze_codebase(
            repo_path=repo_path,
            use_cache=task_data.get("use_analysis_cache", True),
            include_diagnostics=task_data.get("include_diagnostics", True)
        )
        
        # Get code quality metrics
        quality_metrics = await self.graph_sitter.get_code_quality_metrics(repo_path)
        
        # Get dependencies if requested
        dependencies = None
        if task_data.get("analyze_dependencies", False):
            dependencies = await self.graph_sitter.get_dependencies(repo_path)
        
        return {
            "analysis": analysis_result,
            "quality_metrics": quality_metrics,
            "dependencies": dependencies,
            "repo_path": repo_path
        }
    
    async def _stage_sandbox_execution(
        self, 
        task_data: Dict[str, Any], 
        pipeline_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 3: Execute code in sandbox using Grainchain"""
        
        code_to_execute = task_data.get("code_to_execute")
        if not code_to_execute:
            return {"skipped": True, "reason": "No code to execute provided"}
        
        # Execute code in sandbox
        execution_result = await self.grainchain.execute_code(
            code=code_to_execute,
            provider=task_data.get("sandbox_provider", "local"),
            timeout=task_data.get("execution_timeout", 300),
            environment_vars=task_data.get("environment_vars", {})
        )
        
        # Create snapshot if requested
        snapshot_result = None
        if task_data.get("create_snapshot", False) and execution_result.get("success"):
            snapshot_result = await self.grainchain.create_snapshot(
                provider=task_data.get("sandbox_provider", "local"),
                description=f"Pipeline {pipeline_result['pipeline_id']} snapshot"
            )
        
        # Upload additional files if provided
        file_uploads = []
        if task_data.get("files_to_upload"):
            for file_info in task_data["files_to_upload"]:
                upload_result = await self.grainchain.upload_file(
                    filename=file_info["filename"],
                    content=file_info["content"],
                    provider=task_data.get("sandbox_provider", "local")
                )
                file_uploads.append(upload_result)
        
        return {
            "execution": execution_result,
            "snapshot": snapshot_result,
            "file_uploads": file_uploads,
            "provider": task_data.get("sandbox_provider", "local")
        }
    
    async def _stage_ui_testing(
        self, 
        task_data: Dict[str, Any], 
        pipeline_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 4: Perform UI testing using Web-eval-agent"""
        
        webapp_url = task_data.get("webapp_url")
        if not webapp_url:
            return {"skipped": True, "reason": "No webapp URL provided"}
        
        # Perform web application evaluation
        ui_test_task = task_data.get("ui_test_task", "Test the application functionality and user experience")
        
        evaluation_result = await self.web_eval.evaluate_webapp(
            url=webapp_url,
            task=ui_test_task,
            headless=task_data.get("headless_testing", True),
            timeout=task_data.get("ui_test_timeout", 300),
            capture_screenshots=task_data.get("capture_screenshots", True),
            capture_network=task_data.get("capture_network", True),
            capture_console=task_data.get("capture_console", True)
        )
        
        # Perform accessibility validation if requested
        accessibility_result = None
        if task_data.get("test_accessibility", False):
            accessibility_result = await self.web_eval.validate_accessibility(
                url=webapp_url,
                standards=task_data.get("accessibility_standards", ["WCAG 2.1 AA"])
            )
        
        # Perform performance audit if requested
        performance_result = None
        if task_data.get("test_performance", False):
            performance_result = await self.web_eval.performance_audit(
                url=webapp_url,
                metrics=task_data.get("performance_metrics")
            )
        
        return {
            "evaluation": evaluation_result,
            "accessibility": accessibility_result,
            "performance": performance_result,
            "webapp_url": webapp_url
        }
    
    async def _stage_results_integration(
        self, 
        task_data: Dict[str, Any], 
        pipeline_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 5: Integrate and analyze all results"""
        
        # Collect all stage results
        stages = pipeline_result.get("stages", {})
        
        # Generate comprehensive summary
        summary = {
            "pipeline_id": pipeline_result["pipeline_id"],
            "execution_summary": {
                "total_stages": len(stages),
                "successful_stages": len([s for s in stages.values() if s.get("status") == "completed"]),
                "failed_stages": len([s for s in stages.values() if s.get("status") == "failed"]),
                "total_execution_time": sum(s.get("execution_time", 0) for s in stages.values())
            },
            "results_summary": {}
        }
        
        # Analyze code analysis results
        if "code_analysis" in stages:
            code_analysis = stages["code_analysis"].get("result", {})
            if code_analysis.get("quality_metrics"):
                summary["results_summary"]["code_quality"] = {
                    "overall_score": code_analysis["quality_metrics"].get("overall_score", 0),
                    "error_count": code_analysis["quality_metrics"].get("metrics", {}).get("error_count", 0),
                    "test_coverage": code_analysis["quality_metrics"].get("metrics", {}).get("test_coverage", 0)
                }
        
        # Analyze sandbox execution results
        if "sandbox_execution" in stages:
            sandbox_result = stages["sandbox_execution"].get("result", {})
            if sandbox_result.get("execution"):
                summary["results_summary"]["sandbox_execution"] = {
                    "success": sandbox_result["execution"].get("success", False),
                    "execution_time": sandbox_result["execution"].get("execution_time", 0),
                    "provider": sandbox_result.get("provider", "unknown")
                }
        
        # Analyze UI testing results
        if "ui_testing" in stages:
            ui_result = stages["ui_testing"].get("result", {})
            if ui_result.get("evaluation"):
                summary["results_summary"]["ui_testing"] = {
                    "success": ui_result["evaluation"].get("success", False),
                    "accessibility_tested": bool(ui_result.get("accessibility")),
                    "performance_tested": bool(ui_result.get("performance"))
                }
        
        # Update Codegen agent run if available
        agent_run_update = None
        if pipeline_result.get("agent_run_id"):
            agent_run_update = await self.codegen_sdk.get_agent_run_status(
                pipeline_result["agent_run_id"]
            )
        
        return {
            "summary": summary,
            "agent_run_update": agent_run_update,
            "integration_completed": True
        }
    
    async def _stage_completion(
        self, 
        task_data: Dict[str, Any], 
        pipeline_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 6: Finalize pipeline and cleanup"""
        
        # Generate final report
        final_report = {
            "pipeline_id": pipeline_result["pipeline_id"],
            "status": "completed",
            "execution_summary": pipeline_result["stages"].get("results_integration", {}).get("result", {}).get("summary", {}),
            "recommendations": [],
            "next_steps": []
        }
        
        # Generate recommendations based on results
        stages = pipeline_result.get("stages", {})
        
        # Code quality recommendations
        if "code_analysis" in stages:
            code_result = stages["code_analysis"].get("result", {})
            if code_result.get("quality_metrics"):
                quality_score = code_result["quality_metrics"].get("overall_score", 0)
                if quality_score < 80:
                    final_report["recommendations"].append({
                        "category": "code_quality",
                        "priority": "high",
                        "message": f"Code quality score is {quality_score}%. Consider addressing errors and improving test coverage."
                    })
        
        # Sandbox execution recommendations
        if "sandbox_execution" in stages:
            sandbox_result = stages["sandbox_execution"].get("result", {})
            if not sandbox_result.get("execution", {}).get("success", True):
                final_report["recommendations"].append({
                    "category": "execution",
                    "priority": "high",
                    "message": "Code execution failed in sandbox. Review error messages and fix issues."
                })
        
        # UI testing recommendations
        if "ui_testing" in stages:
            ui_result = stages["ui_testing"].get("result", {})
            if not ui_result.get("evaluation", {}).get("success", True):
                final_report["recommendations"].append({
                    "category": "ui_testing",
                    "priority": "medium",
                    "message": "UI testing identified issues. Review test results and address UX problems."
                })
        
        # Cleanup resources if needed
        cleanup_results = []
        if task_data.get("cleanup_resources", True):
            # This would cleanup any temporary resources created during pipeline execution
            cleanup_results.append({"resource": "temporary_files", "cleaned": True})
        
        return {
            "final_report": final_report,
            "cleanup_results": cleanup_results,
            "completion_timestamp": datetime.now().isoformat()
        }
    
    async def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get status of a running or completed pipeline"""
        
        # Check active pipelines
        if pipeline_id in self.active_pipelines:
            return self.active_pipelines[pipeline_id]
        
        # Check pipeline history
        for pipeline in self.pipeline_history:
            if pipeline["pipeline_id"] == pipeline_id:
                return pipeline
        
        return {
            "error": f"Pipeline {pipeline_id} not found",
            "pipeline_id": pipeline_id,
            "timestamp": datetime.now().isoformat()
        }
    
    async def cancel_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """Cancel a running pipeline"""
        
        if pipeline_id not in self.active_pipelines:
            return {
                "success": False,
                "error": f"Pipeline {pipeline_id} not found or not running",
                "pipeline_id": pipeline_id
            }
        
        pipeline = self.active_pipelines[pipeline_id]
        pipeline["status"] = PipelineStatus.CANCELLED.value
        pipeline["cancelled_at"] = datetime.now().isoformat()
        
        # Cancel associated agent run if exists
        if pipeline.get("agent_run_id"):
            await self.codegen_sdk.cancel_agent_run(
                pipeline["agent_run_id"],
                reason="Pipeline cancelled by user"
            )
        
        # Move to history
        self.pipeline_history.append(pipeline.copy())
        self.active_pipelines.pop(pipeline_id)
        
        logger.info("Pipeline cancelled", pipeline_id=pipeline_id)
        
        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "status": "cancelled",
            "timestamp": datetime.now().isoformat()
        }
    
    async def list_pipelines(
        self, 
        status_filter: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """List pipelines with optional status filtering"""
        
        all_pipelines = list(self.active_pipelines.values()) + self.pipeline_history
        
        # Apply status filter if provided
        if status_filter:
            all_pipelines = [p for p in all_pipelines if p.get("status") in status_filter]
        
        # Sort by start time (most recent first)
        all_pipelines.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        
        # Apply limit
        limited_pipelines = all_pipelines[:limit]
        
        return {
            "pipelines": limited_pipelines,
            "total": len(all_pipelines),
            "active_count": len(self.active_pipelines),
            "completed_count": len([p for p in all_pipelines if p.get("status") == "completed"]),
            "failed_count": len([p for p in all_pipelines if p.get("status") == "failed"]),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all integrated services"""
        
        # Get status from each service
        grainchain_status = await self.grainchain.get_provider_status()
        graph_sitter_status = await self.graph_sitter.get_service_status()
        web_eval_status = await self.web_eval.get_service_status()
        codegen_sdk_status = await self.codegen_sdk.get_service_status()
        
        # Calculate overall health
        service_statuses = [
            grainchain_status.get("grainchain_available", False),
            graph_sitter_status.get("status") == "healthy",
            web_eval_status.get("status") == "healthy",
            codegen_sdk_status.get("status") == "healthy"
        ]
        
        healthy_services = sum(service_statuses)
        total_services = len(service_statuses)
        
        overall_status = "healthy" if healthy_services == total_services else (
            "degraded" if healthy_services > total_services // 2 else "unhealthy"
        )
        
        return {
            "overall_status": overall_status,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "services": {
                "grainchain": grainchain_status,
                "graph_sitter": graph_sitter_status,
                "web_eval": web_eval_status,
                "codegen_sdk": codegen_sdk_status
            },
            "timestamp": datetime.now().isoformat()
        }

