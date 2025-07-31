"""
Integrated Pipeline API Router
Provides endpoints for the unified CI/CD pipeline using all integrated libraries
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import structlog

from ..services.integrated_agent_manager import IntegratedAgentManager
from ..core.security import get_current_user, require_role, TokenData, UserRole

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/integrated", tags=["Integrated Pipeline"])


# Pydantic models for request/response validation
class PipelineRequest(BaseModel):
    """Request model for pipeline execution"""
    # Task identification
    task_id: Optional[str] = Field(None, description="Optional task identifier")
    description: str = Field(..., description="Task description")
    type: str = Field("integrated_pipeline", description="Task type")
    priority: str = Field("normal", description="Task priority (low, normal, high, urgent)")
    
    # Code analysis configuration
    repo_path: Optional[str] = Field(None, description="Repository path or URL for code analysis")
    code_analysis_enabled: bool = Field(True, description="Enable code analysis stage")
    include_diagnostics: bool = Field(True, description="Include diagnostic information")
    analyze_dependencies: bool = Field(False, description="Analyze project dependencies")
    use_analysis_cache: bool = Field(True, description="Use cached analysis results")
    
    # Sandbox execution configuration
    code_to_execute: Optional[str] = Field(None, description="Code to execute in sandbox")
    sandbox_execution_enabled: bool = Field(False, description="Enable sandbox execution stage")
    sandbox_provider: str = Field("local", description="Sandbox provider (local, e2b, daytona, morph)")
    execution_timeout: int = Field(300, description="Execution timeout in seconds")
    environment_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    create_snapshot: bool = Field(False, description="Create snapshot after execution")
    files_to_upload: List[Dict[str, str]] = Field(default_factory=list, description="Files to upload to sandbox")
    
    # UI testing configuration
    webapp_url: Optional[str] = Field(None, description="Web application URL for testing")
    ui_testing_enabled: bool = Field(False, description="Enable UI testing stage")
    ui_test_task: str = Field("Test the application functionality and user experience", description="UI test task description")
    headless_testing: bool = Field(True, description="Run browser in headless mode")
    ui_test_timeout: int = Field(300, description="UI test timeout in seconds")
    capture_screenshots: bool = Field(True, description="Capture screenshots during testing")
    capture_network: bool = Field(True, description="Capture network traffic")
    capture_console: bool = Field(True, description="Capture console logs")
    test_accessibility: bool = Field(False, description="Perform accessibility testing")
    accessibility_standards: List[str] = Field(default_factory=lambda: ["WCAG 2.1 AA"], description="Accessibility standards")
    test_performance: bool = Field(False, description="Perform performance testing")
    performance_metrics: Optional[List[str]] = Field(None, description="Performance metrics to collect")
    
    # Pipeline configuration
    create_agent_run: bool = Field(True, description="Create Codegen agent run")
    cleanup_resources: bool = Field(True, description="Cleanup resources after completion")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class PipelineResponse(BaseModel):
    """Response model for pipeline execution"""
    pipeline_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    execution_time: Optional[float] = None
    progress: int
    current_stage: str
    agent_run_id: Optional[str] = None
    stages: Dict[str, Any]
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]


class PipelineListResponse(BaseModel):
    """Response model for pipeline listing"""
    pipelines: List[Dict[str, Any]]
    total: int
    active_count: int
    completed_count: int
    failed_count: int
    timestamp: str


class ServiceHealthResponse(BaseModel):
    """Response model for service health"""
    overall_status: str
    healthy_services: int
    total_services: int
    services: Dict[str, Any]
    timestamp: str


# Pipeline execution endpoints
@router.post("/pipeline/execute", response_model=PipelineResponse)
async def execute_integrated_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Execute complete integrated pipeline with all libraries
    
    This endpoint orchestrates the full CI/CD pipeline including:
    - Code analysis with Graph-sitter
    - Sandbox execution with Grainchain  
    - UI testing with Web-eval-agent
    - Results integration with Codegen SDK
    """
    logger.info("Pipeline execution requested", 
               user_id=current_user.user_id,
               task_type=request.type,
               repo_path=request.repo_path,
               webapp_url=request.webapp_url)
    
    try:
        manager = IntegratedAgentManager()
        
        # Convert request to task data
        task_data = request.dict()
        
        # Execute pipeline
        result = await manager.execute_full_pipeline(task_data)
        
        logger.info("Pipeline execution completed", 
                   pipeline_id=result["pipeline_id"],
                   status=result["status"],
                   user_id=current_user.user_id)
        
        return PipelineResponse(**result)
        
    except Exception as e:
        logger.error("Pipeline execution failed", 
                    error=str(e),
                    user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/status/{pipeline_id}")
async def get_pipeline_status(
    pipeline_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get status of a specific pipeline"""
    try:
        manager = IntegratedAgentManager()
        status = await manager.get_pipeline_status(pipeline_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get pipeline status", 
                    pipeline_id=pipeline_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/cancel/{pipeline_id}")
async def cancel_pipeline(
    pipeline_id: str,
    current_user: TokenData = Depends(require_role(UserRole.USER))
):
    """Cancel a running pipeline"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.cancel_pipeline(pipeline_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to cancel pipeline"))
        
        logger.info("Pipeline cancelled", 
                   pipeline_id=pipeline_id,
                   cancelled_by=current_user.username)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel pipeline", 
                    pipeline_id=pipeline_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/list", response_model=PipelineListResponse)
async def list_pipelines(
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user)
):
    """List pipelines with optional status filtering"""
    try:
        manager = IntegratedAgentManager()
        
        # Parse status filter
        status_list = None
        if status_filter:
            status_list = [s.strip() for s in status_filter.split(",")]
        
        result = await manager.list_pipelines(
            status_filter=status_list,
            limit=limit
        )
        
        return PipelineListResponse(**result)
        
    except Exception as e:
        logger.error("Failed to list pipelines", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Individual service endpoints
@router.post("/grainchain/execute")
async def execute_in_sandbox(
    code: str,
    provider: str = "local",
    timeout: int = 300,
    environment_vars: Dict[str, str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Execute code in sandbox using Grainchain"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.grainchain.execute_code(
            code=code,
            provider=provider,
            timeout=timeout,
            environment_vars=environment_vars or {}
        )
        
        logger.info("Sandbox execution completed", 
                   provider=provider,
                   success=result.get("success"),
                   user_id=current_user.user_id)
        
        return result
        
    except Exception as e:
        logger.error("Sandbox execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grainchain/upload-file")
async def upload_file_to_sandbox(
    filename: str,
    content: str,
    provider: str = "local",
    current_user: TokenData = Depends(get_current_user)
):
    """Upload file to sandbox using Grainchain"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.grainchain.upload_file(
            filename=filename,
            content=content,
            provider=provider
        )
        
        return result
        
    except Exception as e:
        logger.error("File upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grainchain/create-snapshot")
async def create_sandbox_snapshot(
    provider: str = "local",
    description: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Create sandbox snapshot using Grainchain"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.grainchain.create_snapshot(
            provider=provider,
            description=description
        )
        
        return result
        
    except Exception as e:
        logger.error("Snapshot creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph-sitter/analyze")
async def analyze_codebase(
    repo_path: str,
    include_diagnostics: bool = True,
    use_cache: bool = True,
    current_user: TokenData = Depends(get_current_user)
):
    """Analyze codebase using Graph-sitter"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.graph_sitter.analyze_codebase(
            repo_path=repo_path,
            include_diagnostics=include_diagnostics,
            use_cache=use_cache
        )
        
        logger.info("Code analysis completed", 
                   repo_path=repo_path,
                   user_id=current_user.user_id)
        
        return result
        
    except Exception as e:
        logger.error("Code analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph-sitter/quality-metrics")
async def get_code_quality_metrics(
    repo_path: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get code quality metrics using Graph-sitter"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.graph_sitter.get_code_quality_metrics(repo_path)
        
        return result
        
    except Exception as e:
        logger.error("Quality metrics failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph-sitter/search")
async def search_code(
    repo_path: str,
    query: str,
    file_pattern: Optional[str] = None,
    language: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Search code using Graph-sitter"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.graph_sitter.search_code(
            repo_path=repo_path,
            query=query,
            file_pattern=file_pattern,
            language=language
        )
        
        return result
        
    except Exception as e:
        logger.error("Code search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-eval/test")
async def test_webapp(
    url: str,
    task: str,
    headless: bool = True,
    timeout: int = 300,
    capture_screenshots: bool = True,
    capture_network: bool = True,
    capture_console: bool = True,
    current_user: TokenData = Depends(get_current_user)
):
    """Test web application using Web-eval-agent"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.web_eval.evaluate_webapp(
            url=url,
            task=task,
            headless=headless,
            timeout=timeout,
            capture_screenshots=capture_screenshots,
            capture_network=capture_network,
            capture_console=capture_console
        )
        
        logger.info("Web evaluation completed", 
                   url=url,
                   success=result.get("success"),
                   user_id=current_user.user_id)
        
        return result
        
    except Exception as e:
        logger.error("Web evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-eval/test-local")
async def test_local_webapp(
    port: int = 3000,
    framework: Optional[str] = None,
    test_scenarios: Optional[List[str]] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Test local web application using Web-eval-agent"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.web_eval.test_local_webapp(
            port=port,
            framework=framework,
            test_scenarios=test_scenarios
        )
        
        return result
        
    except Exception as e:
        logger.error("Local webapp testing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-eval/accessibility")
async def validate_accessibility(
    url: str,
    standards: List[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Validate web accessibility using Web-eval-agent"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.web_eval.validate_accessibility(
            url=url,
            standards=standards or ["WCAG 2.1 AA"]
        )
        
        return result
        
    except Exception as e:
        logger.error("Accessibility validation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-eval/performance")
async def performance_audit(
    url: str,
    metrics: Optional[List[str]] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Perform performance audit using Web-eval-agent"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.web_eval.performance_audit(
            url=url,
            metrics=metrics
        )
        
        return result
        
    except Exception as e:
        logger.error("Performance audit failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/codegen-sdk/agent-run")
async def create_agent_run(
    task_data: Dict[str, Any],
    priority: str = "normal",
    timeout: Optional[int] = None,
    current_user: TokenData = Depends(require_role(UserRole.USER))
):
    """Create Codegen agent run"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.codegen_sdk.create_agent_run(
            task_data=task_data,
            priority=priority,
            timeout=timeout
        )
        
        return result
        
    except Exception as e:
        logger.error("Agent run creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/codegen-sdk/agent-run/{agent_run_id}")
async def get_agent_run_status(
    agent_run_id: str,
    include_logs: bool = False,
    current_user: TokenData = Depends(get_current_user)
):
    """Get Codegen agent run status"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.codegen_sdk.get_agent_run_status(
            agent_run_id=agent_run_id,
            include_logs=include_logs
        )
        
        return result
        
    except Exception as e:
        logger.error("Failed to get agent run status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Service health and status endpoints
@router.get("/health", response_model=ServiceHealthResponse)
async def get_service_health():
    """Get health status of all integrated services"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.get_service_health()
        
        return ServiceHealthResponse(**result)
        
    except Exception as e:
        logger.error("Failed to get service health", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grainchain/providers")
async def get_grainchain_providers():
    """Get available Grainchain sandbox providers"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.grainchain.get_provider_status()
        
        return result
        
    except Exception as e:
        logger.error("Failed to get Grainchain providers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grainchain/benchmark")
async def run_grainchain_benchmark(
    provider: str = "local",
    current_user: TokenData = Depends(get_current_user)
):
    """Run performance benchmark on Grainchain provider"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.grainchain.run_performance_benchmark(provider)
        
        return result
        
    except Exception as e:
        logger.error("Benchmark failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/graph-sitter/cache")
async def clear_graph_sitter_cache(
    repo_path: Optional[str] = None,
    current_user: TokenData = Depends(require_role(UserRole.USER))
):
    """Clear Graph-sitter analysis cache"""
    try:
        manager = IntegratedAgentManager()
        manager.graph_sitter.clear_cache(repo_path)
        
        return {
            "success": True,
            "message": f"Cache cleared for {repo_path if repo_path else 'all repositories'}",
            "timestamp": manager.graph_sitter.get_service_status()["timestamp"]
        }
        
    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-eval/setup-browser")
async def setup_browser_state(
    url: Optional[str] = None,
    timeout: int = 120,
    current_user: TokenData = Depends(get_current_user)
):
    """Setup browser state for Web-eval-agent"""
    try:
        manager = IntegratedAgentManager()
        result = await manager.web_eval.setup_browser_state(
            url=url,
            timeout=timeout
        )
        
        return result
        
    except Exception as e:
        logger.error("Browser setup failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

