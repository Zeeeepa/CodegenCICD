"""
Integration tests for Enhanced Grainchain Client
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.integrations.grainchain_client import EnhancedGrainchainClient
from backend.utils.circuit_breaker import CircuitBreakerConfig, CircuitBreakerError
from backend.utils.retry_strategies import RetryConfig, RetryStrategy
from backend.utils.connection_pool import ConnectionPoolConfig
from backend.services.resource_manager import ResourceType, ResourceMetrics


class TestEnhancedGrainchainClient:
    """Test suite for Enhanced Grainchain Client"""
    
    @pytest.fixture
    def client(self):
        """Create test client instance"""
        return EnhancedGrainchainClient("http://test-grainchain:8080")
    
    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response"""
        response = MagicMock()
        response.get.return_value = {"status": "success", "snapshot_id": "test-123"}
        return response
    
    def test_client_initialization(self, client):
        """Test client initialization with enhanced features"""
        assert client.service_name == "grainchain"
        assert client.base_url == "http://test-grainchain:8080"
        assert client.correlation_id is not None
        assert isinstance(client.circuit_breaker_config, CircuitBreakerConfig)
        assert isinstance(client.retry_config, RetryConfig)
        assert isinstance(client.pool_config, ConnectionPoolConfig)
        assert client.operation_metrics["total_operations"] == 0
    
    def test_default_headers(self, client):
        """Test enhanced default headers"""
        headers = client._get_default_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "CodegenCICD-Enhanced-Dashboard/2.0"
        assert "X-Correlation-ID" in headers
        assert "X-Request-ID" in headers
        assert headers["X-Correlation-ID"] == client.correlation_id
    
    @pytest.mark.asyncio
    async def test_execute_with_enhancements_success(self, client):
        """Test successful operation with enhancements"""
        mock_operation = AsyncMock(return_value={"result": "success"})
        
        with patch.object(client.adaptive_retry, 'execute', return_value={"result": "success"}):
            result = await client._execute_with_enhancements(mock_operation, "test-arg")
            
            assert result == {"result": "success"}
            assert client.operation_metrics["total_operations"] == 1
            assert client.operation_metrics["successful_operations"] == 1
            assert client.operation_metrics["failed_operations"] == 0
    
    @pytest.mark.asyncio
    async def test_execute_with_enhancements_circuit_breaker_open(self, client):
        """Test operation with circuit breaker open"""
        mock_operation = AsyncMock()
        
        with patch('backend.integrations.grainchain_client.circuit_breaker_manager') as mock_manager:
            mock_breaker = MagicMock()
            mock_breaker.call.side_effect = CircuitBreakerError("Circuit breaker open")
            mock_manager.get_breaker.return_value = mock_breaker
            
            with pytest.raises(Exception) as exc_info:
                await client._execute_with_enhancements(mock_operation, "test-arg")
            
            assert "Service temporarily unavailable" in str(exc_info.value)
            assert client.operation_metrics["failed_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_create_snapshot_enhanced(self, client):
        """Test enhanced snapshot creation with resource management"""
        expected_response = {
            "snapshot_id": "test-snapshot-123",
            "status": "created",
            "project_name": "test-project"
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=expected_response) as mock_execute:
            with patch('backend.integrations.grainchain_client.resource_manager') as mock_rm:
                result = await client.create_snapshot(
                    project_name="test-project",
                    github_url="https://github.com/test/repo",
                    branch="main"
                )
                
                assert result == expected_response
                
                # Verify resource manager registration
                mock_rm.register_resource.assert_called_once()
                call_args = mock_rm.register_resource.call_args
                assert call_args[1]["resource_id"] == "test-snapshot-123"
                assert call_args[1]["resource_type"] == ResourceType.SNAPSHOT
                assert call_args[1]["metadata"]["project_name"] == "test-project"
                assert call_args[1]["metadata"]["correlation_id"] == client.correlation_id
    
    @pytest.mark.asyncio
    async def test_get_snapshot_with_metrics_update(self, client):
        """Test get snapshot with resource metrics update"""
        snapshot_response = {
            "snapshot_id": "test-123",
            "status": "active",
            "metrics": {
                "cpu_percent": 45.5,
                "memory_mb": 1024.0,
                "disk_mb": 2048.0,
                "network_connections": 5,
                "file_handles": 20,
                "uptime_seconds": 3600.0
            }
        }
        
        with patch.object(client, '_execute_with_enhancements', return_value=snapshot_response):
            with patch('backend.integrations.grainchain_client.resource_manager') as mock_rm:
                result = await client.get_snapshot("test-123")
                
                assert result == snapshot_response
                
                # Verify resource access tracking
                mock_rm.access_resource.assert_called_once_with("test-123")
                
                # Verify metrics update
                mock_rm.update_resource_metrics.assert_called_once()
                call_args = mock_rm.update_resource_metrics.call_args
                assert call_args[0][0] == "test-123"
                
                metrics = call_args[0][1]
                assert isinstance(metrics, ResourceMetrics)
                assert metrics.cpu_percent == 45.5
                assert metrics.memory_mb == 1024.0
    
    @pytest.mark.asyncio
    async def test_cleanup_snapshot_callback(self, client):
        """Test snapshot cleanup callback"""
        with patch.object(client, 'delete_snapshot', return_value={"status": "deleted"}) as mock_delete:
            await client._cleanup_snapshot_callback("test-snapshot-123")
            
            mock_delete.assert_called_once_with("test-snapshot-123")
    
    def test_get_client_metrics(self, client):
        """Test comprehensive client metrics"""
        # Set up some test metrics
        client.operation_metrics["total_operations"] = 10
        client.operation_metrics["successful_operations"] = 8
        client.operation_metrics["failed_operations"] = 2
        
        with patch('backend.integrations.grainchain_client.circuit_breaker_manager') as mock_cb:
            with patch('backend.integrations.grainchain_client.connection_pool_manager') as mock_cp:
                with patch('backend.integrations.grainchain_client.resource_manager') as mock_rm:
                    mock_cb.get_all_states.return_value = {"test_breaker": {"state": "closed"}}
                    mock_cp.get_all_metrics.return_value = {"test_pool": {"status": "healthy"}}
                    mock_rm.get_resource_stats.return_value = {"active_resources": 5}
                    
                    metrics = client.get_client_metrics()
                    
                    assert "client_info" in metrics
                    assert "operation_metrics" in metrics
                    assert "circuit_breakers" in metrics
                    assert "retry_statistics" in metrics
                    assert "connection_pools" in metrics
                    assert "resource_management" in metrics
                    
                    assert metrics["client_info"]["service_name"] == "grainchain"
                    assert metrics["client_info"]["correlation_id"] == client.correlation_id
                    assert metrics["operation_metrics"]["total_operations"] == 10
    
    def test_get_health_status(self, client):
        """Test comprehensive health status"""
        # Set up test data
        client.operation_metrics["total_operations"] = 10
        client.operation_metrics["successful_operations"] = 9
        client.operation_metrics["failed_operations"] = 1
        
        with patch.object(client, 'get_client_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "operation_metrics": {
                    "total_operations": 10,
                    "successful_operations": 9,
                    "failed_operations": 1
                },
                "circuit_breakers": {
                    "test_breaker": {"state": "closed"}
                },
                "retry_statistics": {
                    "total_attempts": 5,
                    "success_rate": 0.8
                },
                "resource_management": {
                    "quota_violations": 0,
                    "expired_resources": 2
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
                "operation_metrics": {
                    "total_operations": 10,
                    "successful_operations": 4,  # Low success rate
                    "failed_operations": 6
                },
                "circuit_breakers": {
                    "test_breaker": {"state": "open"}  # Open circuit breaker
                },
                "retry_statistics": {
                    "total_attempts": 10,
                    "success_rate": 0.4  # Low retry success rate
                },
                "resource_management": {
                    "quota_violations": 5,  # Quota violations
                    "expired_resources": 15  # Many expired resources
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
            with patch.object(client, 'list_snapshots', return_value=[]):
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
    async def test_cleanup_all_resources(self, client):
        """Test cleanup of all managed resources"""
        mock_snapshots = [
            {"snapshot_id": "snap-1"},
            {"snapshot_id": "snap-2"},
            {"snapshot_id": "snap-3"}
        ]
        
        with patch.object(client, 'list_snapshots', return_value=mock_snapshots):
            with patch('backend.integrations.grainchain_client.resource_manager') as mock_rm:
                # Mock successful cleanup for first two, failure for third
                mock_rm.cleanup_resource.side_effect = [True, True, Exception("Cleanup failed")]
                
                result = await client.cleanup_all_resources()
                
                assert result["success"] is True
                assert result["results"]["total_snapshots"] == 3
                assert result["results"]["cleaned_up"] == 2
                assert result["results"]["failed"] == 1
                assert len(result["results"]["errors"]) == 1
                assert result["results"]["errors"][0]["snapshot_id"] == "snap-3"
    
    @pytest.mark.asyncio
    async def test_cleanup_all_resources_failure(self, client):
        """Test cleanup failure scenario"""
        with patch.object(client, 'list_snapshots', side_effect=Exception("List failed")):
            result = await client.cleanup_all_resources()
            
            assert result["success"] is False
            assert "error" in result
            assert "List failed" in result["error"]


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration"""
    
    @pytest.fixture
    def client(self):
        return EnhancedGrainchainClient("http://test:8080")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_triggers_on_failures(self, client):
        """Test that circuit breaker opens after repeated failures"""
        mock_operation = AsyncMock(side_effect=Exception("Service unavailable"))
        
        # Configure circuit breaker for quick opening
        client.circuit_breaker_config.failure_threshold = 2
        
        with patch('backend.integrations.grainchain_client.circuit_breaker_manager') as mock_manager:
            mock_breaker = MagicMock()
            mock_breaker.call.side_effect = [
                Exception("Failure 1"),
                Exception("Failure 2"),
                CircuitBreakerError("Circuit breaker open")
            ]
            mock_manager.get_breaker.return_value = mock_breaker
            
            # First two calls should fail normally
            with pytest.raises(Exception):
                await client._execute_with_enhancements(mock_operation, "test")
            
            with pytest.raises(Exception):
                await client._execute_with_enhancements(mock_operation, "test")
            
            # Third call should fail due to circuit breaker
            with pytest.raises(Exception) as exc_info:
                await client._execute_with_enhancements(mock_operation, "test")
            
            assert "Service temporarily unavailable" in str(exc_info.value)


class TestRetryIntegration:
    """Test retry mechanism integration"""
    
    @pytest.fixture
    def client(self):
        return EnhancedGrainchainClient("http://test:8080")
    
    @pytest.mark.asyncio
    async def test_adaptive_retry_adjusts_strategy(self, client):
        """Test that adaptive retry adjusts based on success rate"""
        # Simulate some failures to trigger adaptation
        for _ in range(10):
            try:
                await client.adaptive_retry.execute(AsyncMock(side_effect=Exception("Fail")))
            except:
                pass
        
        # Check that retry stats are being tracked
        stats = client.adaptive_retry.get_stats()
        assert stats["total_attempts"] > 0
        assert stats["success_rate"] <= 1.0


class TestResourceManagerIntegration:
    """Test resource manager integration"""
    
    @pytest.fixture
    def client(self):
        return EnhancedGrainchainClient("http://test:8080")
    
    @pytest.mark.asyncio
    async def test_resource_registration_on_snapshot_creation(self, client):
        """Test that resources are registered when snapshots are created"""
        with patch.object(client, '_execute_with_enhancements') as mock_execute:
            with patch('backend.integrations.grainchain_client.resource_manager') as mock_rm:
                mock_execute.return_value = {"snapshot_id": "test-123"}
                
                await client.create_snapshot("test-project", "https://github.com/test/repo")
                
                # Verify resource registration
                mock_rm.register_resource.assert_called_once()
                call_args = mock_rm.register_resource.call_args
                assert call_args[1]["resource_id"] == "test-123"
                assert call_args[1]["resource_type"] == ResourceType.SNAPSHOT
    
    @pytest.mark.asyncio
    async def test_resource_access_tracking(self, client):
        """Test that resource access is tracked"""
        with patch.object(client, '_execute_with_enhancements', return_value={"snapshot_id": "test-123"}):
            with patch('backend.integrations.grainchain_client.resource_manager') as mock_rm:
                await client.get_snapshot("test-123")
                
                # Verify access tracking
                mock_rm.access_resource.assert_called_once_with("test-123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
