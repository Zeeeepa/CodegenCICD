"""
Integration tests for Enhanced Web-Eval-Agent Client
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.integrations.web_eval_client import (
    EnhancedWebEvalClient, 
    TestType, 
    BrowserType, 
    DeviceType
)
from backend.utils.circuit_breaker import CircuitBreakerConfig, CircuitBreakerError
from backend.utils.retry_strategies import RetryConfig, RetryStrategy
from backend.services.resource_manager import ResourceType, ResourceMetrics


class TestEnhancedWebEvalClient:
    """Test suite for Enhanced Web-Eval-Agent Client"""
    
    @pytest.fixture
    def client(self):
        """Create test client instance"""
        return EnhancedWebEvalClient("http://test-webeval:8081")
    
    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response"""
        response = MagicMock()
        response.get.return_value = {"status": "success", "session_id": "test-session-123"}
        return response
    
    def test_client_initialization(self, client):
        """Test client initialization with enhanced features"""
        assert client.service_name == "web_eval_agent"
        assert client.base_url == "http://test-webeval:8081"
        assert client.correlation_id is not None
        assert isinstance(client.circuit_breaker_config, CircuitBreakerConfig)
        assert isinstance(client.retry_config, RetryConfig)
        assert client.test_metrics["total_tests"] == 0
        assert len(client.active_sessions) == 0
    
    def test_default_headers(self, client):
        """Test enhanced default headers"""
        headers = client._get_default_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "CodegenCICD-Enhanced-WebEval/2.0"
        assert "X-Correlation-ID" in headers
        assert "X-Request-ID" in headers
        assert "X-Test-Session" in headers
        assert headers["X-Correlation-ID"] == client.correlation_id
        assert headers["X-Test-Session"] == "enhanced"
    
    @pytest.mark.asyncio
    async def test_execute_with_enhancements_success(self, client):
        """Test successful operation with enhancements"""
        mock_operation = AsyncMock(return_value={"result": "success"})
        
        with patch.object(client.adaptive_retry, 'execute', return_value={"result": "success"}):
            result = await client._execute_with_enhancements(mock_operation, "test-arg")
            
            assert result == {"result": "success"}
            assert client.test_metrics["total_tests"] == 1
            assert client.test_metrics["successful_tests"] == 1
            assert client.test_metrics["failed_tests"] == 0
    
    @pytest.mark.asyncio
    async def test_create_comprehensive_test_session(self, client):
        """Test comprehensive test session creation"""
        expected_response = {
            "session_id": "test-session-123",
            "status": "created",
            "project_name": "test-project"
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response) as mock_execute:
            with patch('backend.integrations.web_eval_client.resource_manager') as mock_rm:
                result = await client.create_comprehensive_test_session(
                    project_name="test-project",
                    base_url="https://test.example.com",
                    browsers=[BrowserType.CHROMIUM, BrowserType.FIREFOX],
                    devices=[DeviceType.IPHONE_12, DeviceType.PIXEL_5],
                    test_types=[TestType.FUNCTIONAL, TestType.ACCESSIBILITY]
                )
                
                assert result == expected_response
                
                # Verify resource manager registration
                mock_rm.register_resource.assert_called_once()
                call_args = mock_rm.register_resource.call_args
                assert call_args[1]["resource_id"] == "test-session-123"
                assert call_args[1]["resource_type"] == ResourceType.PROCESS
                assert call_args[1]["metadata"]["project_name"] == "test-project"
                assert call_args[1]["metadata"]["correlation_id"] == client.correlation_id
                
                # Verify session tracking
                assert "test-session-123" in client.active_sessions
                assert client.active_sessions["test-session-123"]["project_name"] == "test-project"
    
    @pytest.mark.asyncio
    async def test_generate_ai_test_scenarios(self, client):
        """Test AI-powered test scenario generation"""
        expected_response = {
            "scenarios_count": 15,
            "scenarios": [
                {
                    "name": "Login Flow Test",
                    "type": "functional",
                    "steps": ["Navigate to login", "Enter credentials", "Submit form"]
                }
            ],
            "ai_insights": ["Form validation detected", "Accessibility issues found"]
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response):
            result = await client.generate_ai_test_scenarios(
                session_id="test-session-123",
                page_url="https://test.example.com/login",
                test_objectives=["functional_validation", "accessibility_compliance"],
                user_personas=[{
                    "name": "Power User",
                    "description": "Experienced user",
                    "behavior": "efficient navigation"
                }]
            )
            
            assert result == expected_response
            assert result["scenarios_count"] == 15
            assert len(result["ai_insights"]) == 2
    
    @pytest.mark.asyncio
    async def test_run_ai_powered_testing(self, client):
        """Test AI-powered comprehensive testing"""
        expected_response = {
            "tests_executed": 25,
            "success_rate": 0.92,
            "ai_insights": [
                "Performance bottleneck detected in checkout flow",
                "Accessibility improvements needed for form labels"
            ],
            "test_results": {
                "functional": {"passed": 18, "failed": 2},
                "accessibility": {"passed": 3, "failed": 1},
                "performance": {"passed": 1, "failed": 0}
            }
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response):
            result = await client.run_ai_powered_testing(
                session_id="test-session-123",
                target_pages=["https://test.example.com", "https://test.example.com/checkout"],
                testing_strategy="comprehensive"
            )
            
            assert result == expected_response
            assert result["tests_executed"] == 25
            assert result["success_rate"] == 0.92
            assert len(result["ai_insights"]) == 2
    
    @pytest.mark.asyncio
    async def test_run_advanced_visual_regression(self, client):
        """Test advanced visual regression testing"""
        expected_response = {
            "differences_found": 3,
            "ai_insights": [
                "Layout shift detected in header section",
                "Color contrast improved in button elements"
            ],
            "comparison_results": {
                "pixel_differences": 0.05,
                "layout_changes": 2,
                "content_changes": 1
            }
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response):
            result = await client.run_advanced_visual_regression(
                session_id="test-session-123",
                pages=["https://test.example.com", "https://test.example.com/about"],
                baseline_session_id="baseline-session-456",
                visual_config={
                    "sensitivity_level": "high",
                    "ignore_regions": [{"x": 0, "y": 0, "width": 100, "height": 50}]
                }
            )
            
            assert result == expected_response
            assert result["differences_found"] == 3
            assert len(result["ai_insights"]) == 2
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_accessibility_audit(self, client):
        """Test comprehensive accessibility audit"""
        expected_response = {
            "total_violations": 8,
            "compliance_score": 85,
            "violations_by_level": {
                "A": 2,
                "AA": 4,
                "AAA": 2
            },
            "remediation_suggestions": [
                "Add alt text to images",
                "Improve color contrast ratios",
                "Add ARIA labels to form controls"
            ]
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response):
            result = await client.run_comprehensive_accessibility_audit(
                session_id="test-session-123",
                pages=["https://test.example.com", "https://test.example.com/contact"],
                standards=["WCAG2.1", "Section508", "ADA"]
            )
            
            assert result == expected_response
            assert result["total_violations"] == 8
            assert result["compliance_score"] == 85
            assert len(result["remediation_suggestions"]) == 3
    
    @pytest.mark.asyncio
    async def test_run_performance_profiling(self, client):
        """Test comprehensive performance profiling"""
        expected_response = {
            "average_score": 78,
            "budget_violations": 2,
            "metrics": {
                "FCP": 1800,
                "LCP": 3200,
                "CLS": 0.08,
                "FID": 85,
                "TTI": 4200
            },
            "recommendations": [
                "Optimize image loading",
                "Reduce JavaScript bundle size",
                "Implement lazy loading"
            ]
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response):
            result = await client.run_performance_profiling(
                session_id="test-session-123",
                pages=["https://test.example.com", "https://test.example.com/products"],
                performance_config={
                    "budgets": {
                        "FCP": 2000,
                        "LCP": 4000,
                        "CLS": 0.1
                    }
                }
            )
            
            assert result == expected_response
            assert result["average_score"] == 78
            assert result["budget_violations"] == 2
            assert len(result["recommendations"]) == 3
    
    @pytest.mark.asyncio
    async def test_cleanup_session_callback(self, client):
        """Test session cleanup callback"""
        client.active_sessions["test-session-123"] = {
            "project_name": "test-project",
            "created_at": datetime.utcnow()
        }
        
        with patch.object(client, 'delete_test_session', return_value={"status": "deleted"}) as mock_delete:
            await client._cleanup_session_callback("test-session-123")
            
            mock_delete.assert_called_once_with("test-session-123")
            assert "test-session-123" not in client.active_sessions
    
    def test_get_client_metrics(self, client):
        """Test comprehensive client metrics"""
        # Set up some test metrics
        client.test_metrics["total_tests"] = 50
        client.test_metrics["successful_tests"] = 45
        client.test_metrics["failed_tests"] = 5
        client.active_sessions["session-1"] = {"project": "test1"}
        client.active_sessions["session-2"] = {"project": "test2"}
        
        with patch('backend.integrations.web_eval_client.circuit_breaker_manager') as mock_cb:
            with patch('backend.integrations.web_eval_client.resource_manager') as mock_rm:
                mock_cb.get_all_states.return_value = {"test_breaker": {"state": "closed"}}
                mock_rm.get_resource_stats.return_value = {"active_resources": 3}
                
                metrics = client.get_client_metrics()
                
                assert "client_info" in metrics
                assert "test_metrics" in metrics
                assert "active_sessions" in metrics
                assert "circuit_breakers" in metrics
                assert "retry_statistics" in metrics
                assert "resource_management" in metrics
                
                assert metrics["client_info"]["service_name"] == "web_eval_agent"
                assert metrics["client_info"]["correlation_id"] == client.correlation_id
                assert metrics["test_metrics"]["total_tests"] == 50
                assert metrics["active_sessions"]["count"] == 2
    
    def test_get_health_status(self, client):
        """Test comprehensive health status"""
        # Set up test data
        client.test_metrics["total_tests"] = 100
        client.test_metrics["successful_tests"] = 85
        client.test_metrics["failed_tests"] = 15
        
        with patch.object(client, 'get_client_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "test_metrics": {
                    "total_tests": 100,
                    "successful_tests": 85,
                    "failed_tests": 15
                },
                "circuit_breakers": {
                    "test_breaker": {"state": "closed"}
                },
                "retry_statistics": {
                    "total_attempts": 20,
                    "success_rate": 0.9
                },
                "active_sessions": {
                    "count": 3
                }
            }
            
            health = client.get_health_status()
            
            assert "status" in health
            assert "health_score" in health
            assert "issues" in health
            assert "last_check" in health
            assert "detailed_metrics" in health
            
            # Should be healthy with good metrics
            assert health["status"] == "healthy"
            assert health["health_score"] >= 80
    
    def test_get_health_status_degraded(self, client):
        """Test health status with degraded conditions"""
        with patch.object(client, 'get_client_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "test_metrics": {
                    "total_tests": 100,
                    "successful_tests": 30,  # Low success rate
                    "failed_tests": 70
                },
                "circuit_breakers": {
                    "test_breaker": {"state": "open"}  # Open circuit breaker
                },
                "retry_statistics": {
                    "total_attempts": 50,
                    "success_rate": 0.4  # Low retry success rate
                },
                "active_sessions": {
                    "count": 15  # High number of active sessions
                }
            }
            
            health = client.get_health_status()
            
            assert health["status"] in ["degraded", "unhealthy"]
            assert health["health_score"] < 80
            assert len(health["issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_perform_health_check_success(self, client):
        """Test successful health check"""
        with patch.object(client, '_health_check_request', return_value=None):
            with patch.object(client, 'get_test_templates', return_value=[]):
                result = await client.perform_health_check()
                
                assert result["service_available"] is True
                assert "response_time" in result
                assert "timestamp" in result
                assert "correlation_id" in result
                assert result["correlation_id"] == client.correlation_id
    
    @pytest.mark.asyncio
    async def test_perform_health_check_failure(self, client):
        """Test failed health check"""
        with patch.object(client, '_health_check_request', side_effect=Exception("Connection failed")):
            result = await client.perform_health_check()
            
            assert result["service_available"] is False
            assert "error" in result
            assert "Connection failed" in result["error"]
            assert "response_time" in result
            assert "correlation_id" in result
    
    @pytest.mark.asyncio
    async def test_cleanup_all_sessions(self, client):
        """Test cleanup of all managed sessions"""
        # Set up active sessions
        client.active_sessions = {
            "session-1": {"project": "test1"},
            "session-2": {"project": "test2"},
            "session-3": {"project": "test3"}
        }
        
        with patch('backend.integrations.web_eval_client.resource_manager') as mock_rm:
            # Mock successful cleanup for first two, failure for third
            mock_rm.cleanup_resource.side_effect = [True, True, Exception("Cleanup failed")]
            
            result = await client.cleanup_all_sessions()
            
            assert result["success"] is True
            assert result["results"]["total_sessions"] == 3
            assert result["results"]["cleaned_up"] == 2
            assert result["results"]["failed"] == 1
            assert len(result["results"]["errors"]) == 1
            assert result["results"]["errors"][0]["session_id"] == "session-3"
    
    @pytest.mark.asyncio
    async def test_generate_comprehensive_report(self, client):
        """Test comprehensive report generation"""
        expected_response = {
            "report_urls": {
                "html": "https://reports.example.com/session-123.html",
                "pdf": "https://reports.example.com/session-123.pdf",
                "json": "https://reports.example.com/session-123.json"
            },
            "report_sections": [
                "executive_summary",
                "test_coverage",
                "performance_analysis",
                "accessibility_audit"
            ],
            "generation_time": 45.2
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response):
            result = await client.generate_comprehensive_report(
                session_id="test-session-123",
                report_config={
                    "include_ai_insights": True,
                    "export_formats": ["html", "pdf", "json"]
                }
            )
            
            assert result == expected_response
            assert len(result["report_urls"]) == 3
            assert "html" in result["report_urls"]
            assert "pdf" in result["report_urls"]
            assert "json" in result["report_urls"]


class TestEnumTypes:
    """Test enum types for web-eval client"""
    
    def test_test_type_enum(self):
        """Test TestType enum values"""
        assert TestType.FUNCTIONAL.value == "functional"
        assert TestType.ACCESSIBILITY.value == "accessibility"
        assert TestType.PERFORMANCE.value == "performance"
        assert TestType.VISUAL_REGRESSION.value == "visual_regression"
        assert TestType.AI_GENERATED.value == "ai_generated"
    
    def test_browser_type_enum(self):
        """Test BrowserType enum values"""
        assert BrowserType.CHROMIUM.value == "chromium"
        assert BrowserType.FIREFOX.value == "firefox"
        assert BrowserType.WEBKIT.value == "webkit"
        assert BrowserType.SAFARI.value == "safari"
    
    def test_device_type_enum(self):
        """Test DeviceType enum values"""
        assert DeviceType.IPHONE_12.value == "iPhone 12"
        assert DeviceType.PIXEL_5.value == "Pixel 5"
        assert DeviceType.GALAXY_S21.value == "Galaxy S21"
        assert DeviceType.IPAD_PRO.value == "iPad Pro"


class TestBackwardCompatibility:
    """Test backward compatibility features"""
    
    @pytest.mark.asyncio
    async def test_legacy_create_test_session(self, client):
        """Test legacy create_test_session method"""
        expected_response = {
            "session_id": "legacy-session-123",
            "status": "created"
        }
        
        with patch.object(client, 'create_comprehensive_test_session', return_value=expected_response) as mock_comprehensive:
            result = await client.create_test_session(
                project_name="legacy-project",
                base_url="https://legacy.example.com",
                test_config={"timeout": 30}
            )
            
            assert result == expected_response
            
            # Verify it calls the comprehensive method with defaults
            mock_comprehensive.assert_called_once_with(
                project_name="legacy-project",
                base_url="https://legacy.example.com",
                test_config={"timeout": 30},
                browsers=[BrowserType.CHROMIUM],
                test_types=[TestType.FUNCTIONAL]
            )
    
    def test_webeval_client_alias(self):
        """Test that WebEvalClient is an alias for EnhancedWebEvalClient"""
        from backend.integrations.web_eval_client import WebEvalClient, EnhancedWebEvalClient
        
        assert WebEvalClient is EnhancedWebEvalClient


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
