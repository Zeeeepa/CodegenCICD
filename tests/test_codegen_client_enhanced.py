"""
Comprehensive integration tests for enhanced Codegen API client
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import the enhanced client and related modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.integrations.async_client import AsyncCodegenClient, create_development_client
from backend.integrations.config import ClientConfig, ConfigPresets
from backend.integrations.models import *
from backend.integrations.exceptions import *
from backend.integrations.cache import AsyncTTLCache
from backend.integrations.rate_limiter import AsyncRateLimiter
from backend.integrations.webhooks import WebhookHandler, WebhookEvent
from backend.integrations.bulk_operations import BulkOperationResult


class TestAsyncCodegenClient:
    """Test suite for AsyncCodegenClient"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a test configuration"""
        config = ConfigPresets.testing()
        config.api_token = "test-token"
        config.org_id = "123"
        return config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create a test client"""
        return AsyncCodegenClient(mock_config)
    
    @pytest.fixture
    def mock_response_data(self):
        """Mock response data for API calls"""
        return {
            'user': {
                'id': 1,
                'email': 'test@example.com',
                'github_user_id': 'test-user',
                'github_username': 'testuser',
                'avatar_url': 'https://example.com/avatar.jpg',
                'full_name': 'Test User'
            },
            'agent_run': {
                'id': 123,
                'organization_id': 456,
                'status': 'completed',
                'created_at': '2024-01-01T00:00:00Z',
                'web_url': 'https://codegen.com/runs/123',
                'result': 'Task completed successfully',
                'source_type': 'API',
                'github_pull_requests': [],
                'metadata': {}
            },
            'organization': {
                'id': 456,
                'name': 'Test Organization',
                'settings': {}
            }
        }
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_config):
        """Test client initialization with configuration"""
        client = AsyncCodegenClient(mock_config)
        
        assert client.config.api_token == "test-token"
        assert client.config.org_id == "123"
        assert client.config.debug_mode is True
        assert hasattr(client, '_logger')
        assert hasattr(client, '_health_checker')
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager functionality"""
        async with client as c:
            assert c is client
            assert c._session is not None
    
    @pytest.mark.asyncio
    async def test_get_user_with_caching(self, client, mock_response_data):
        """Test user retrieval with caching"""
        with patch.object(client, '_make_request_enhanced', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data['user']
            
            # First call
            user1 = await client.get_user("123", "1")
            assert isinstance(user1, UserResponse)
            assert user1.id == 1
            assert user1.email == 'test@example.com'
            
            # Second call should use cache (mock should only be called once)
            user2 = await client.get_user("123", "1")
            assert user2.id == user1.id
            
            # Verify mock was called only once due to caching
            assert mock_request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_create_agent_run_validation(self, client, mock_response_data):
        """Test agent run creation with input validation"""
        with patch.object(client, '_make_request_enhanced', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data['agent_run']
            
            # Valid request
            run = await client.create_agent_run(
                org_id=123,
                prompt="Test prompt",
                metadata={"test": "data"}
            )
            
            assert isinstance(run, AgentRunResponse)
            assert run.id == 123
            assert run.status == AgentRunStatus.COMPLETED
            
            # Test validation error for empty prompt
            with pytest.raises(ValidationError):
                await client.create_agent_run(
                    org_id=123,
                    prompt="",  # Empty prompt should fail validation
                )
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test rate limiting functionality"""
        # Access the rate limiter
        rate_limiter = client._rate_limiter
        
        # Test that rate limiter is properly configured
        current_limit = await rate_limiter.get_current_limit()
        assert current_limit > 0
        
        # Test rate limit stats
        stats = await rate_limiter.get_stats()
        assert 'current_limit' in stats['adaptive']
        assert 'base' in stats
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, client, mock_response_data):
        """Test bulk operations functionality"""
        if not client.config.enable_bulk_operations:
            pytest.skip("Bulk operations disabled in test config")
        
        with patch.object(client, 'get_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = UserResponse(**mock_response_data['user'])
            
            user_ids = ["1", "2", "3"]
            result = await client.bulk_get_users("123", user_ids)
            
            assert isinstance(result, BulkOperationResult)
            assert result.total_items == 3
            assert result.successful_items <= 3
            assert len(result.results) <= 3
    
    @pytest.mark.asyncio
    async def test_streaming_users(self, client, mock_response_data):
        """Test streaming users functionality"""
        if not client.config.enable_streaming:
            pytest.skip("Streaming disabled in test config")
        
        # Mock the get_users method to return paginated data
        mock_users_response = UsersResponse(
            items=[UserResponse(**mock_response_data['user'])],
            total=1,
            page=1,
            size=1,
            pages=1
        )
        
        with patch.object(client, 'get_users', new_callable=AsyncMock) as mock_get_users:
            mock_get_users.return_value = mock_users_response
            
            users = []
            async for user in client.get_users_stream("123"):
                users.append(user)
                break  # Only get first user to avoid infinite loop
            
            assert len(users) == 1
            assert isinstance(users[0], UserResponse)
    
    @pytest.mark.asyncio
    async def test_health_check(self, client, mock_response_data):
        """Test health check functionality"""
        with patch.object(client, 'get_organization', new_callable=AsyncMock) as mock_get_org:
            mock_get_org.return_value = OrganizationResponse(**mock_response_data['organization'])
            
            health_result = await client.health_check()
            
            assert 'overall_status' in health_result
            assert 'checks' in health_result
            assert 'api_connectivity' in health_result['checks']
    
    @pytest.mark.asyncio
    async def test_webhook_processing(self, client):
        """Test webhook processing functionality"""
        if not client.config.enable_webhooks:
            pytest.skip("Webhooks disabled in test config")
        
        webhook_payload = {
            'event_type': 'agent_run.completed',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'id': 123,
                'status': 'completed',
                'result': 'Success'
            }
        }
        
        result = await client.process_webhook(webhook_payload)
        
        assert 'status' in result
        assert result['event_type'] == 'agent_run.completed'
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, client):
        """Test metrics collection functionality"""
        if not client.config.enable_metrics:
            pytest.skip("Metrics disabled in test config")
        
        metrics = client.get_metrics_summary()
        
        assert 'client_config' in metrics
        assert 'enabled_features' in metrics
        
        # Test metrics export
        exported = client.export_metrics('json')
        if exported:
            data = json.loads(exported)
            assert 'export_timestamp' in data
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test comprehensive error handling"""
        with patch.object(client, '_make_request_enhanced', new_callable=AsyncMock) as mock_request:
            # Test rate limit error
            mock_request.side_effect = RateLimitError("Rate limited", retry_after=60)
            
            with pytest.raises(RateLimitError) as exc_info:
                await client.get_user("123", "1")
            
            assert exc_info.value.retry_after == 60
            
            # Test validation error
            mock_request.side_effect = ValidationError("Invalid input", field_errors={'prompt': ['Required']})
            
            with pytest.raises(ValidationError) as exc_info:
                await client.get_user("123", "1")
            
            assert 'prompt' in exc_info.value.field_errors
    
    @pytest.mark.asyncio
    async def test_wait_for_completion(self, client, mock_response_data):
        """Test waiting for agent run completion"""
        # Mock agent run that completes after 2 calls
        completed_run = mock_response_data['agent_run'].copy()
        running_run = completed_run.copy()
        running_run['status'] = 'running'
        
        with patch.object(client, 'get_agent_run', new_callable=AsyncMock) as mock_get_run:
            mock_get_run.side_effect = [
                AgentRunResponse(**running_run),
                AgentRunResponse(**completed_run)
            ]
            
            result = await client.wait_for_agent_run_completion(
                org_id=123,
                run_id=123,
                timeout=30,
                poll_interval=0.1  # Fast polling for test
            )
            
            assert result.status == AgentRunStatus.COMPLETED
            assert mock_get_run.call_count == 2


class TestClientConfiguration:
    """Test client configuration functionality"""
    
    def test_config_presets(self):
        """Test predefined configuration presets"""
        dev_config = ConfigPresets.development()
        assert dev_config.debug_mode is True
        assert dev_config.log_level == "DEBUG"
        
        prod_config = ConfigPresets.production()
        assert prod_config.debug_mode is False
        assert prod_config.log_level == "INFO"
        
        test_config = ConfigPresets.testing()
        assert test_config.max_retries == 0
        assert test_config.mock_responses is True
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test missing API token
        with pytest.raises(ValueError, match="API token is required"):
            ClientConfig(api_token="")
        
        # Test invalid timeout
        with pytest.raises(ValueError, match="Timeout must be positive"):
            ClientConfig(api_token="test", timeout=-1)
        
        # Test invalid rate limit
        with pytest.raises(ValueError, match="Rate limit requests per period must be positive"):
            ClientConfig(api_token="test", rate_limit_requests_per_period=0)
    
    def test_config_from_environment(self):
        """Test loading configuration from environment variables"""
        with patch.dict(os.environ, {
            'CODEGEN_API_TOKEN': 'env-token',
            'CODEGEN_ORG_ID': 'env-org',
            'CODEGEN_TIMEOUT': '45',
            'CODEGEN_MAX_RETRIES': '5'
        }):
            config = ClientConfig()
            assert config.api_token == 'env-token'
            assert config.org_id == 'env-org'
            assert config.timeout == 45
            assert config.max_retries == 5


class TestCachingSystem:
    """Test caching functionality"""
    
    @pytest.mark.asyncio
    async def test_async_ttl_cache(self):
        """Test async TTL cache functionality"""
        cache = AsyncTTLCache(max_size=10, default_ttl=1)
        
        # Test set and get
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"
        
        # Test TTL expiration
        await cache.set("key2", "value2", ttl=0.1)  # 100ms TTL
        await asyncio.sleep(0.2)  # Wait for expiration
        value = await cache.get("key2")
        assert value is None
        
        # Test cache stats
        stats = await cache.get_stats()
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'size' in stats
    
    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        """Test cache eviction when max size is reached"""
        cache = AsyncTTLCache(max_size=2, default_ttl=60)
        
        # Fill cache to capacity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Add one more item (should evict LRU)
        await cache.set("key3", "value3")
        
        # key1 should be evicted
        value1 = await cache.get("key1")
        value3 = await cache.get("key3")
        
        assert value1 is None  # Evicted
        assert value3 == "value3"  # Still present


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_async_rate_limiter(self):
        """Test async rate limiter"""
        limiter = AsyncRateLimiter(requests_per_period=2, period_seconds=1)
        
        # First two requests should not wait
        wait1 = await limiter.wait_if_needed()
        wait2 = await limiter.wait_if_needed()
        
        assert wait1 == 0.0
        assert wait2 == 0.0
        
        # Third request should wait
        start_time = asyncio.get_event_loop().time()
        wait3 = await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()
        
        assert wait3 > 0
        assert (end_time - start_time) >= wait3 * 0.9  # Allow some timing tolerance
    
    @pytest.mark.asyncio
    async def test_rate_limiter_stats(self):
        """Test rate limiter statistics"""
        limiter = AsyncRateLimiter(requests_per_period=10, period_seconds=60)
        
        # Make some requests
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()
        
        stats = await limiter.get_stats()
        
        assert stats['current_usage']['requests_in_period'] == 2
        assert stats['total_requests'] == 2
        assert stats['blocked_requests'] == 0


class TestWebhookHandling:
    """Test webhook handling functionality"""
    
    @pytest.fixture
    def webhook_handler(self):
        """Create a webhook handler for testing"""
        from backend.integrations.webhooks import WebhookConfig
        config = WebhookConfig(secret="test-secret", verify_signatures=False)
        return WebhookHandler(config)
    
    @pytest.mark.asyncio
    async def test_webhook_event_processing(self, webhook_handler):
        """Test webhook event processing"""
        # Register a test handler
        events_received = []
        
        async def test_handler(event: WebhookEvent):
            events_received.append(event)
            return {"processed": True}
        
        webhook_handler.register_handler("test.event", test_handler)
        
        # Send test webhook
        payload = {
            "event_type": "test.event",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"test": "data"}
        }
        
        result = await webhook_handler.handle_webhook(payload)
        
        assert result["status"] == "processed"
        assert len(events_received) == 1
        assert events_received[0].event_type == "test.event"
    
    @pytest.mark.asyncio
    async def test_webhook_signature_verification(self):
        """Test webhook signature verification"""
        from backend.integrations.webhooks import WebhookConfig
        config = WebhookConfig(secret="test-secret", verify_signatures=True)
        handler = WebhookHandler(config)
        
        payload = b'{"event_type": "test", "timestamp": "2024-01-01T00:00:00Z", "data": {}}'
        
        # Test with invalid signature
        result = await handler.handle_webhook(payload, "invalid-signature")
        assert result["status"] == "error"
        assert "signature verification failed" in result["error"].lower()


class TestBulkOperations:
    """Test bulk operations functionality"""
    
    @pytest.mark.asyncio
    async def test_bulk_operation_success(self):
        """Test successful bulk operation"""
        from backend.integrations.bulk_operations import BulkOperationManager, BulkOperationConfig
        
        config = BulkOperationConfig(max_workers=2, fail_fast=False)
        manager = BulkOperationManager(config)
        
        async def mock_operation(item):
            await asyncio.sleep(0.01)  # Simulate async work
            return f"processed_{item}"
        
        items = ["item1", "item2", "item3"]
        result = await manager.execute_bulk_async(items, mock_operation)
        
        assert result.total_items == 3
        assert result.successful_items == 3
        assert result.failed_items == 0
        assert len(result.results) == 3
        assert result.success_rate == 100.0
    
    @pytest.mark.asyncio
    async def test_bulk_operation_partial_failure(self):
        """Test bulk operation with partial failures"""
        from backend.integrations.bulk_operations import BulkOperationManager, BulkOperationConfig
        
        config = BulkOperationConfig(max_workers=2, fail_fast=False)
        manager = BulkOperationManager(config)
        
        async def mock_operation(item):
            if item == "fail":
                raise ValueError("Simulated failure")
            return f"processed_{item}"
        
        items = ["item1", "fail", "item3"]
        result = await manager.execute_bulk_async(items, mock_operation)
        
        assert result.total_items == 3
        assert result.successful_items == 2
        assert result.failed_items == 1
        assert len(result.results) == 2
        assert len(result.errors) == 1
        assert result.success_rate == (2/3) * 100


class TestModelValidation:
    """Test Pydantic model validation"""
    
    def test_user_response_validation(self):
        """Test UserResponse model validation"""
        # Valid user data
        user_data = {
            "id": 1,
            "email": "test@example.com",
            "github_user_id": "123",
            "github_username": "testuser",
            "avatar_url": "https://example.com/avatar.jpg",
            "full_name": "Test User"
        }
        
        user = UserResponse(**user_data)
        assert user.id == 1
        assert user.email == "test@example.com"
        
        # Invalid email
        invalid_data = user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        with pytest.raises(ValueError, match="Invalid email format"):
            UserResponse(**invalid_data)
    
    def test_create_agent_run_request_validation(self):
        """Test CreateAgentRunRequest validation"""
        # Valid request
        request_data = {
            "prompt": "Test prompt",
            "images": ["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="],
            "metadata": {"test": "data"}
        }
        
        request = CreateAgentRunRequest(**request_data)
        assert request.prompt == "Test prompt"
        assert len(request.images) == 1
        
        # Invalid prompt (empty)
        invalid_data = request_data.copy()
        invalid_data["prompt"] = ""
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            CreateAgentRunRequest(**invalid_data)
        
        # Invalid image format
        invalid_data = request_data.copy()
        invalid_data["images"] = ["not-a-data-uri"]
        
        with pytest.raises(ValueError, match="Images must be base64 data URIs"):
            CreateAgentRunRequest(**invalid_data)


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_agent_run_workflow(self, mock_response_data):
        """Test complete agent run workflow"""
        config = ConfigPresets.testing()
        config.api_token = "test-token"
        config.org_id = "123"
        
        client = AsyncCodegenClient(config)
        
        with patch.object(client, '_make_request_enhanced', new_callable=AsyncMock) as mock_request:
            # Mock responses for different endpoints
            mock_request.side_effect = [
                mock_response_data['agent_run'],  # create_agent_run
                mock_response_data['agent_run'],  # get_agent_run (completed)
            ]
            
            async with client:
                # Create agent run
                run = await client.create_agent_run(
                    org_id=123,
                    prompt="Implement a new feature",
                    metadata={"priority": "high"}
                )
                
                assert run.id == 123
                assert run.status == AgentRunStatus.COMPLETED
                
                # Get run details
                run_details = await client.get_agent_run(123, run.id)
                assert run_details.id == run.id
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery and retry workflow"""
        config = ConfigPresets.testing()
        config.api_token = "test-token"
        config.org_id = "123"
        config.max_retries = 2
        
        client = AsyncCodegenClient(config)
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            # First call fails with rate limit, second succeeds
            mock_request.side_effect = [
                RateLimitError("Rate limited", retry_after=1),
                {"id": 1, "email": "test@example.com", "github_user_id": "123", "github_username": "test"}
            ]
            
            async with client:
                # This should succeed after retry
                user = await client.get_user("123", "1")
                assert user.id == 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

