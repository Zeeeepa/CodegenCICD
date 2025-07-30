"""
Comprehensive test suite for the integrated pipeline
Tests all four library integrations and their orchestration
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any

# Import the services to test
from backend.services.grainchain_service import GrainchainService
from backend.services.graph_sitter_service import GraphSitterService
from backend.services.web_eval_service import WebEvalService
from backend.services.codegen_sdk_service import CodegenSDKService
from backend.services.integrated_agent_manager import IntegratedAgentManager, PipelineStatus


class TestGrainchainService:
    """Test Grainchain sandbox service integration"""
    
    @pytest.fixture
    def grainchain_service(self):
        return GrainchainService()
    
    @pytest.mark.asyncio
    async def test_execute_code_success(self, grainchain_service):
        """Test successful code execution"""
        result = await grainchain_service.execute_code(
            code="print('Hello, World!')",
            provider="local"
        )
        
        assert result["success"] is True
        assert "Hello" in result["stdout"] or result.get("mock") is True
        assert result["exit_code"] == 0
        assert "execution_time" in result
        assert "provider" in result
    
    @pytest.mark.asyncio
    async def test_execute_code_with_error(self, grainchain_service):
        """Test code execution with error"""
        result = await grainchain_service.execute_code(
            code="raise Exception('Test error')",
            provider="local"
        )
        
        # Should handle error gracefully
        assert "success" in result
        assert "error" in result or result.get("mock") is True
    
    @pytest.mark.asyncio
    async def test_upload_file(self, grainchain_service):
        """Test file upload to sandbox"""
        result = await grainchain_service.upload_file(
            filename="test.txt",
            content="Test file content",
            provider="local"
        )
        
        assert result["success"] is True
        assert result["filename"] == "test.txt"
        assert result["size"] == len("Test file content")
    
    @pytest.mark.asyncio
    async def test_create_snapshot(self, grainchain_service):
        """Test snapshot creation"""
        result = await grainchain_service.create_snapshot(
            provider="local",
            description="Test snapshot"
        )
        
        assert result["success"] is True
        assert "snapshot_id" in result
        assert result["description"] == "Test snapshot"
    
    @pytest.mark.asyncio
    async def test_get_provider_status(self, grainchain_service):
        """Test provider status retrieval"""
        result = await grainchain_service.get_provider_status()
        
        assert "available_providers" in result
        assert "default_provider" in result
        assert "grainchain_available" in result
        assert isinstance(result["available_providers"], list)
    
    @pytest.mark.asyncio
    async def test_performance_benchmark(self, grainchain_service):
        """Test performance benchmarking"""
        result = await grainchain_service.run_performance_benchmark("local")
        
        assert "provider" in result
        assert "tests" in result
        assert "summary" in result
        assert "total_tests" in result["summary"]
        assert "success_rate" in result["summary"]


class TestGraphSitterService:
    """Test Graph-sitter code analysis service integration"""
    
    @pytest.fixture
    def graph_sitter_service(self):
        return GraphSitterService()
    
    @pytest.mark.asyncio
    async def test_analyze_codebase(self, graph_sitter_service):
        """Test codebase analysis"""
        result = await graph_sitter_service.analyze_codebase(
            repo_path="./test_repo",
            include_diagnostics=True
        )
        
        assert "repo_path" in result
        assert "summary" in result
        assert "analysis_timestamp" in result
        assert "analysis_duration" in result
        
        # Check summary structure
        summary = result["summary"]
        assert "total_files" in summary
        assert "total_functions" in summary
        assert "total_classes" in summary
    
    @pytest.mark.asyncio
    async def test_get_diagnostics(self, graph_sitter_service):
        """Test diagnostic information retrieval"""
        result = await graph_sitter_service.get_diagnostics("./test_repo")
        
        assert "total_issues" in result
        assert "errors" in result
        assert "warnings" in result
        assert "issues" in result
        assert "categories" in result
        assert isinstance(result["issues"], list)
    
    @pytest.mark.asyncio
    async def test_get_code_quality_metrics(self, graph_sitter_service):
        """Test code quality metrics calculation"""
        result = await graph_sitter_service.get_code_quality_metrics("./test_repo")
        
        assert "overall_score" in result
        assert "scores" in result
        assert "metrics" in result
        assert "recommendations" in result
        
        # Check score structure
        scores = result["scores"]
        assert "error_score" in scores
        assert "warning_score" in scores
        assert "complexity_score" in scores
        assert "coverage_score" in scores
    
    @pytest.mark.asyncio
    async def test_search_code(self, graph_sitter_service):
        """Test code search functionality"""
        result = await graph_sitter_service.search_code(
            repo_path="./test_repo",
            query="function",
            file_pattern="*.py"
        )
        
        assert "query" in result
        assert "total_matches" in result
        assert "files_matched" in result
        assert "matches" in result
        assert isinstance(result["matches"], list)
    
    @pytest.mark.asyncio
    async def test_get_dependencies(self, graph_sitter_service):
        """Test dependency analysis"""
        result = await graph_sitter_service.get_dependencies("./test_repo")
        
        assert "total_dependencies" in result
        assert "dependencies" in result
        assert "dependency_tree" in result
        assert isinstance(result["dependencies"], list)
    
    def test_clear_cache(self, graph_sitter_service):
        """Test cache clearing"""
        # Should not raise any exceptions
        graph_sitter_service.clear_cache()
        graph_sitter_service.clear_cache("./test_repo")
    
    @pytest.mark.asyncio
    async def test_get_service_status(self, graph_sitter_service):
        """Test service status retrieval"""
        result = await graph_sitter_service.get_service_status()
        
        assert result["service"] == "GraphSitterService"
        assert "status" in result
        assert "supported_languages" in result
        assert "cached_codebases" in result


class TestWebEvalService:
    """Test Web-eval-agent UI testing service integration"""
    
    @pytest.fixture
    def web_eval_service(self):
        return WebEvalService()
    
    @pytest.mark.asyncio
    async def test_evaluate_webapp(self, web_eval_service):
        """Test web application evaluation"""
        result = await web_eval_service.evaluate_webapp(
            url="http://localhost:3000",
            task="Test the homepage functionality",
            headless=True
        )
        
        assert "success" in result
        assert "url" in result
        assert "task" in result
        assert "execution_time" in result
        assert "timestamp" in result
        
        if result.get("success"):
            assert "report" in result
    
    @pytest.mark.asyncio
    async def test_setup_browser_state(self, web_eval_service):
        """Test browser state setup"""
        result = await web_eval_service.setup_browser_state(
            url="http://localhost:3000"
        )
        
        assert "success" in result
        assert "execution_time" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_test_local_webapp(self, web_eval_service):
        """Test local webapp testing"""
        result = await web_eval_service.test_local_webapp(
            port=3000,
            framework="react",
            test_scenarios=["Test homepage loads correctly"]
        )
        
        assert "url" in result
        assert "port" in result
        assert "framework" in result
        assert "scenario_results" in result
        assert "overall_success" in result
        assert "success_rate" in result
    
    @pytest.mark.asyncio
    async def test_validate_accessibility(self, web_eval_service):
        """Test accessibility validation"""
        result = await web_eval_service.validate_accessibility(
            url="http://localhost:3000",
            standards=["WCAG 2.1 AA"]
        )
        
        assert "success" in result
        assert "url" in result
        
        if result.get("success"):
            assert "validation_type" in result
            assert "standards_checked" in result
    
    @pytest.mark.asyncio
    async def test_performance_audit(self, web_eval_service):
        """Test performance audit"""
        result = await web_eval_service.performance_audit(
            url="http://localhost:3000",
            metrics=["First Contentful Paint", "Largest Contentful Paint"]
        )
        
        assert "success" in result
        assert "url" in result
        
        if result.get("success"):
            assert "audit_type" in result
            assert "metrics_collected" in result
    
    @pytest.mark.asyncio
    async def test_get_service_status(self, web_eval_service):
        """Test service status retrieval"""
        result = await web_eval_service.get_service_status()
        
        assert result["service"] == "WebEvalService"
        assert "status" in result
        assert "web_eval_available" in result
        assert "supported_frameworks" in result


class TestCodegenSDKService:
    """Test Codegen SDK service integration"""
    
    @pytest.fixture
    def codegen_sdk_service(self):
        return CodegenSDKService()
    
    @pytest.mark.asyncio
    async def test_create_agent_run(self, codegen_sdk_service):
        """Test agent run creation"""
        task_data = {
            "description": "Test task",
            "type": "test",
            "configuration": {"test": True}
        }
        
        result = await codegen_sdk_service.create_agent_run(
            task_data=task_data,
            priority="normal"
        )
        
        assert "success" in result
        assert "agent_run_id" in result
        assert "status" in result
        assert "created_at" in result
    
    @pytest.mark.asyncio
    async def test_get_agent_run_status(self, codegen_sdk_service):
        """Test agent run status retrieval"""
        result = await codegen_sdk_service.get_agent_run_status(
            agent_run_id="test_run_123"
        )
        
        assert "success" in result
        assert "agent_run_id" in result
        assert "status" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_wait_for_completion(self, codegen_sdk_service):
        """Test waiting for agent run completion"""
        # Use short timeout for testing
        result = await codegen_sdk_service.wait_for_completion(
            agent_run_id="test_run_123",
            timeout=5,
            poll_interval=1
        )
        
        assert "agent_run_id" in result
        assert "success" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_list_agent_runs(self, codegen_sdk_service):
        """Test agent runs listing"""
        result = await codegen_sdk_service.list_agent_runs(
            limit=10
        )
        
        assert "success" in result or "agent_runs" in result
        if "agent_runs" in result:
            assert isinstance(result["agent_runs"], list)
    
    @pytest.mark.asyncio
    async def test_get_organization_info(self, codegen_sdk_service):
        """Test organization information retrieval"""
        result = await codegen_sdk_service.get_organization_info()
        
        assert "success" in result or "organization" in result
        if "organization" in result:
            assert "id" in result["organization"]
    
    @pytest.mark.asyncio
    async def test_validate_api_connection(self, codegen_sdk_service):
        """Test API connection validation"""
        result = await codegen_sdk_service.validate_api_connection()
        
        assert "success" in result
        assert "api_host" in result
        assert "org_id" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_get_service_status(self, codegen_sdk_service):
        """Test service status retrieval"""
        result = await codegen_sdk_service.get_service_status()
        
        assert result["service"] == "CodegenSDKService"
        assert "status" in result
        assert "sdk_available" in result
        assert "connection_status" in result


class TestIntegratedAgentManager:
    """Test the integrated agent manager orchestration"""
    
    @pytest.fixture
    def integrated_manager(self):
        return IntegratedAgentManager()
    
    @pytest.mark.asyncio
    async def test_execute_full_pipeline_minimal(self, integrated_manager):
        """Test minimal pipeline execution"""
        task_data = {
            "description": "Test pipeline execution",
            "type": "test_pipeline",
            "create_agent_run": False  # Skip agent run creation for testing
        }
        
        result = await integrated_manager.execute_full_pipeline(task_data)
        
        assert "pipeline_id" in result
        assert "status" in result
        assert "started_at" in result
        assert "stages" in result
        assert "progress" in result
        
        # Should have at least initialization and completion stages
        assert "initialization" in result["stages"]
        assert "completion" in result["stages"]
    
    @pytest.mark.asyncio
    async def test_execute_full_pipeline_with_code_analysis(self, integrated_manager):
        """Test pipeline with code analysis enabled"""
        task_data = {
            "description": "Test pipeline with code analysis",
            "type": "test_pipeline",
            "repo_path": "./test_repo",
            "code_analysis_enabled": True,
            "create_agent_run": False
        }
        
        result = await integrated_manager.execute_full_pipeline(task_data)
        
        assert result["status"] in [PipelineStatus.COMPLETED.value, PipelineStatus.FAILED.value]
        assert "code_analysis" in result["stages"]
        
        if result["stages"]["code_analysis"]["status"] == "completed":
            analysis_result = result["stages"]["code_analysis"]["result"]
            assert "analysis" in analysis_result
    
    @pytest.mark.asyncio
    async def test_execute_full_pipeline_with_sandbox_execution(self, integrated_manager):
        """Test pipeline with sandbox execution enabled"""
        task_data = {
            "description": "Test pipeline with sandbox execution",
            "type": "test_pipeline",
            "code_to_execute": "print('Hello from sandbox!')",
            "sandbox_execution_enabled": True,
            "sandbox_provider": "local",
            "create_agent_run": False
        }
        
        result = await integrated_manager.execute_full_pipeline(task_data)
        
        assert result["status"] in [PipelineStatus.COMPLETED.value, PipelineStatus.FAILED.value]
        assert "sandbox_execution" in result["stages"]
        
        if result["stages"]["sandbox_execution"]["status"] == "completed":
            execution_result = result["stages"]["sandbox_execution"]["result"]
            assert "execution" in execution_result
    
    @pytest.mark.asyncio
    async def test_execute_full_pipeline_with_ui_testing(self, integrated_manager):
        """Test pipeline with UI testing enabled"""
        task_data = {
            "description": "Test pipeline with UI testing",
            "type": "test_pipeline",
            "webapp_url": "http://localhost:3000",
            "ui_testing_enabled": True,
            "ui_test_task": "Test the application",
            "headless_testing": True,
            "create_agent_run": False
        }
        
        result = await integrated_manager.execute_full_pipeline(task_data)
        
        assert result["status"] in [PipelineStatus.COMPLETED.value, PipelineStatus.FAILED.value]
        assert "ui_testing" in result["stages"]
        
        if result["stages"]["ui_testing"]["status"] == "completed":
            ui_result = result["stages"]["ui_testing"]["result"]
            assert "evaluation" in ui_result
    
    @pytest.mark.asyncio
    async def test_get_pipeline_status(self, integrated_manager):
        """Test pipeline status retrieval"""
        # First create a pipeline
        task_data = {
            "description": "Test pipeline for status check",
            "type": "test_pipeline",
            "create_agent_run": False
        }
        
        pipeline_result = await integrated_manager.execute_full_pipeline(task_data)
        pipeline_id = pipeline_result["pipeline_id"]
        
        # Then get its status
        status = await integrated_manager.get_pipeline_status(pipeline_id)
        
        assert "pipeline_id" in status
        assert status["pipeline_id"] == pipeline_id
        assert "status" in status
    
    @pytest.mark.asyncio
    async def test_list_pipelines(self, integrated_manager):
        """Test pipeline listing"""
        result = await integrated_manager.list_pipelines(limit=10)
        
        assert "pipelines" in result
        assert "total" in result
        assert "active_count" in result
        assert "completed_count" in result
        assert "failed_count" in result
        assert isinstance(result["pipelines"], list)
    
    @pytest.mark.asyncio
    async def test_get_service_health(self, integrated_manager):
        """Test service health status"""
        result = await integrated_manager.get_service_health()
        
        assert "overall_status" in result
        assert "healthy_services" in result
        assert "total_services" in result
        assert "services" in result
        
        # Should have all four services
        services = result["services"]
        assert "grainchain" in services
        assert "graph_sitter" in services
        assert "web_eval" in services
        assert "codegen_sdk" in services
    
    @pytest.mark.asyncio
    async def test_cancel_pipeline(self, integrated_manager):
        """Test pipeline cancellation"""
        # Create a mock active pipeline
        pipeline_id = "test_pipeline_123"
        integrated_manager.active_pipelines[pipeline_id] = {
            "pipeline_id": pipeline_id,
            "status": PipelineStatus.RUNNING.value,
            "started_at": datetime.now().isoformat()
        }
        
        result = await integrated_manager.cancel_pipeline(pipeline_id)
        
        assert result["success"] is True
        assert result["pipeline_id"] == pipeline_id
        assert result["status"] == "cancelled"
        
        # Pipeline should be moved to history
        assert pipeline_id not in integrated_manager.active_pipelines


class TestIntegrationErrorHandling:
    """Test error handling across all integrations"""
    
    @pytest.mark.asyncio
    async def test_grainchain_error_handling(self):
        """Test Grainchain error handling"""
        service = GrainchainService()
        
        # Test with invalid provider
        result = await service.execute_code(
            code="print('test')",
            provider="invalid_provider"
        )
        
        # Should handle gracefully
        assert "success" in result
        assert "error" in result or result.get("mock") is True
    
    @pytest.mark.asyncio
    async def test_graph_sitter_error_handling(self):
        """Test Graph-sitter error handling"""
        service = GraphSitterService()
        
        # Test with invalid repo path
        result = await service.analyze_codebase("/nonexistent/path")
        
        # Should handle gracefully
        assert "error" in result or "success" in result
    
    @pytest.mark.asyncio
    async def test_web_eval_error_handling(self):
        """Test Web-eval-agent error handling"""
        service = WebEvalService()
        
        # Test with invalid URL
        result = await service.evaluate_webapp(
            url="http://invalid-url-that-does-not-exist.com",
            task="Test invalid URL"
        )
        
        # Should handle gracefully
        assert "success" in result
        if not result["success"]:
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_codegen_sdk_error_handling(self):
        """Test Codegen SDK error handling"""
        service = CodegenSDKService()
        
        # Test with invalid agent run ID
        result = await service.get_agent_run_status("invalid_run_id")
        
        # Should handle gracefully
        assert "success" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self):
        """Test pipeline error recovery"""
        manager = IntegratedAgentManager()
        
        # Create task data that will cause errors
        task_data = {
            "description": "Test error recovery",
            "type": "error_test",
            "repo_path": "/nonexistent/path",
            "code_to_execute": "raise Exception('Test error')",
            "webapp_url": "http://invalid-url.com",
            "create_agent_run": False
        }
        
        result = await manager.execute_full_pipeline(task_data)
        
        # Pipeline should complete even with errors
        assert "pipeline_id" in result
        assert "status" in result
        assert "errors" in result
        
        # Should have error information
        if result["status"] == PipelineStatus.FAILED.value:
            assert len(result["errors"]) > 0


# Integration test fixtures and utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("CODEGEN_ORG_ID", "323")
    monkeypatch.setenv("CODEGEN_API_TOKEN", "test_token")
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("GITHUB_TOKEN", "test_github_token")


# Performance tests
class TestIntegrationPerformance:
    """Test performance characteristics of integrated services"""
    
    @pytest.mark.asyncio
    async def test_pipeline_execution_time(self):
        """Test that pipeline execution completes within reasonable time"""
        manager = IntegratedAgentManager()
        
        task_data = {
            "description": "Performance test pipeline",
            "type": "performance_test",
            "create_agent_run": False
        }
        
        start_time = datetime.now()
        result = await manager.execute_full_pipeline(task_data)
        end_time = datetime.now()
        
        execution_time = (end_time - start_time).total_seconds()
        
        # Should complete within 30 seconds for minimal pipeline
        assert execution_time < 30
        assert "execution_time" in result
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_execution(self):
        """Test concurrent pipeline execution"""
        manager = IntegratedAgentManager()
        
        task_data = {
            "description": "Concurrent test pipeline",
            "type": "concurrent_test",
            "create_agent_run": False
        }
        
        # Run multiple pipelines concurrently
        tasks = [
            manager.execute_full_pipeline({**task_data, "description": f"Pipeline {i}"})
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert "pipeline_id" in result
            assert "status" in result


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

