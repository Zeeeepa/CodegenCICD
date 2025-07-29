"""
Enhanced async Codegen API client with all advanced features
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from datetime import datetime
import structlog

from .config import ClientConfig, get_config_for_environment
from .models import *
from .exceptions import *
from .cache import AsyncTTLCache, async_cached, CachePresets
from .rate_limiter import AsyncRateLimiter, AdaptiveRateLimiter, rate_limited
from .monitoring import EnhancedLogger, HealthChecker
from .webhooks import WebhookHandler, create_webhook_handler
from .bulk_operations import (
    BulkOperationManager, PaginationHelper, StreamingPaginator,
    BulkOperationResult, ProgressTracker
)
from .base_client import BaseClient

logger = structlog.get_logger(__name__)


class AsyncCodegenClient(BaseClient):
    """Enhanced async Codegen API client with comprehensive features"""
    
    def __init__(self, 
                 config: Optional[ClientConfig] = None,
                 api_token: Optional[str] = None,
                 org_id: Optional[str] = None):
        # Initialize configuration
        if config is None:
            config = ClientConfig()
        
        if api_token:
            config.api_token = api_token
        if org_id:
            config.org_id = org_id
        
        self.config = config
        
        # Initialize base client
        super().__init__(
            service_name="codegen_api_enhanced",
            base_url=config.base_url,
            api_key=config.api_token,
            timeout=config.timeout,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay
        )
        
        # Initialize enhanced features
        self._setup_enhanced_features()
        
        logger.info("Enhanced Codegen client initialized", 
                   base_url=config.base_url,
                   org_id=config.org_id,
                   features_enabled=self._get_enabled_features())
    
    def _setup_enhanced_features(self):
        """Set up all enhanced features"""
        # Caching
        if self.config.enable_caching:
            self._user_cache = AsyncTTLCache(
                max_size=self.config.cache_max_size,
                default_ttl=self.config.cache_ttl_seconds
            )
            self._org_cache = AsyncTTLCache(
                max_size=50,
                default_ttl=1800  # 30 minutes for org data
            )
            self._run_cache = AsyncTTLCache(
                max_size=200,
                default_ttl=60  # 1 minute for run data
            )
        
        # Rate limiting
        if hasattr(self.config, 'rate_limit_requests_per_period'):
            self._rate_limiter = AdaptiveRateLimiter(
                initial_requests_per_period=self.config.rate_limit_requests_per_period,
                period_seconds=self.config.rate_limit_period_seconds
            )
        else:
            self._rate_limiter = AdaptiveRateLimiter()
        
        # Enhanced logging and monitoring
        self._logger = EnhancedLogger(
            service_name="codegen_client_enhanced",
            log_level=self.config.log_level,
            enable_metrics=self.config.enable_metrics,
            log_requests=self.config.log_requests,
            log_responses=self.config.log_responses,
            log_sensitive_data=self.config.log_sensitive_data
        )
        
        # Health checker
        self._health_checker = HealthChecker(self._logger)
        self._setup_health_checks()
        
        # Webhook handler
        if self.config.enable_webhooks:
            webhook_config = {
                'secret': self.config.webhook_secret,
                'timeout_seconds': self.config.webhook_timeout
            }
            self._webhook_handler = create_webhook_handler(webhook_config)
        
        # Bulk operations manager
        if self.config.enable_bulk_operations:
            from .bulk_operations import BulkOperationConfig
            bulk_config = BulkOperationConfig(
                max_workers=self.config.bulk_max_workers,
                batch_size=self.config.bulk_batch_size
            )
            self._bulk_manager = BulkOperationManager(bulk_config)
    
    def _setup_health_checks(self):
        """Set up health check functions"""
        async def api_health_check():
            """Check API connectivity"""
            try:
                await self.get_organization()
                return {"status": "healthy", "api_accessible": True}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}
        
        async def rate_limit_health_check():
            """Check rate limit status"""
            stats = await self._rate_limiter.get_stats()
            current_limit = await self._rate_limiter.get_current_limit()
            
            return {
                "current_limit": current_limit,
                "usage": stats['base']['current_usage']
            }
        
        self._health_checker.register_health_check("api_connectivity", api_health_check)
        self._health_checker.register_health_check("rate_limiting", rate_limit_health_check)
    
    def _get_enabled_features(self) -> List[str]:
        """Get list of enabled features"""
        features = []
        if self.config.enable_caching:
            features.append("caching")
        if self.config.enable_webhooks:
            features.append("webhooks")
        if self.config.enable_bulk_operations:
            features.append("bulk_operations")
        if self.config.enable_streaming:
            features.append("streaming")
        if self.config.enable_metrics:
            features.append("metrics")
        return features
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests"""
        return self.config.get_default_headers()
    
    async def _health_check_request(self) -> None:
        """Health check implementation"""
        await self.get_organization()
    
    async def _make_request_enhanced(self, 
                                   method: str, 
                                   endpoint: str, 
                                   **kwargs) -> Dict[str, Any]:
        """Enhanced request method with monitoring and rate limiting"""
        request_id = str(uuid.uuid4())
        
        # Apply rate limiting
        await self._rate_limiter.wait_if_needed()
        
        # Start request tracking
        request_context = self._logger.start_request(
            request_id=request_id,
            method=method,
            endpoint=endpoint,
            request_size=len(str(kwargs.get('data', '')))
        )
        
        try:
            # Make the actual request
            response = await self._make_request(method, endpoint, **kwargs)
            
            # Record successful request
            await self._rate_limiter.record_success()
            
            # End request tracking
            self._logger.end_request(
                request_id=request_id,
                status_code=200,  # Assume success if no exception
                response_size=len(str(response))
            )
            
            return response
            
        except RateLimitError as e:
            # Record rate limit event
            await self._rate_limiter.record_rate_limit(e.retry_after)
            self._logger.log_rate_limit(endpoint, e.retry_after, request_id)
            
            # End request tracking with error
            self._logger.end_request(
                request_id=request_id,
                status_code=429,
                error=e
            )
            raise
            
        except Exception as e:
            # End request tracking with error
            self._logger.end_request(
                request_id=request_id,
                error=e
            )
            raise
    
    # Enhanced API Methods with Caching
    
    @async_cached(ttl=600, max_size=100)  # 10 minutes cache
    async def get_user(self, org_id: str, user_id: str) -> UserResponse:
        """Get user details with caching"""
        response = await self._make_request_enhanced("GET", f"/organizations/{org_id}/users/{user_id}")
        return UserResponse(**response)
    
    @async_cached(ttl=300, max_size=50)  # 5 minutes cache
    async def get_current_user(self) -> UserResponse:
        """Get current user information with caching"""
        response = await self._make_request_enhanced("GET", "/users/me")
        return UserResponse(**response)
    
    async def get_users(self, org_id: str, skip: int = 0, limit: int = 100) -> UsersResponse:
        """Get paginated list of users"""
        if not (1 <= limit <= 100):
            raise ValidationError("Limit must be between 1 and 100")
        if skip < 0:
            raise ValidationError("Skip must be >= 0")
        
        response = await self._make_request_enhanced(
            "GET", 
            f"/organizations/{org_id}/users",
            params={"skip": skip, "limit": limit}
        )
        
        return UsersResponse(
            items=[UserResponse(**user) for user in response["items"]],
            total=response["total"],
            page=response["page"],
            size=response["size"],
            pages=response["pages"]
        )
    
    @async_cached(ttl=1800, max_size=10)  # 30 minutes cache
    async def get_organization(self) -> OrganizationResponse:
        """Get organization details with caching"""
        response = await self._make_request_enhanced("GET", f"/organizations/{self.config.org_id}")
        return OrganizationResponse(**response)
    
    async def get_organizations(self, skip: int = 0, limit: int = 100) -> OrganizationsResponse:
        """Get organizations for the authenticated user"""
        response = await self._make_request_enhanced(
            "GET", 
            "/organizations",
            params={"skip": skip, "limit": limit}
        )
        
        return OrganizationsResponse(
            items=[OrganizationResponse(**org) for org in response["items"]],
            total=response["total"],
            page=response["page"],
            size=response["size"],
            pages=response["pages"]
        )
    
    # Agent Run Methods
    
    async def create_agent_run(self, 
                              org_id: int,
                              prompt: str,
                              images: Optional[List[str]] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> AgentRunResponse:
        """Create a new agent run with validation"""
        # Validate request
        request_data = CreateAgentRunRequest(
            prompt=prompt,
            images=images,
            metadata=metadata
        )
        
        response = await self._make_request_enhanced(
            "POST",
            f"/organizations/{org_id}/agent/run",
            data=request_data.dict(exclude_none=True)
        )
        
        return AgentRunResponse(**response)
    
    async def get_agent_run(self, org_id: int, agent_run_id: int) -> AgentRunResponse:
        """Get agent run details"""
        response = await self._make_request_enhanced(
            "GET", 
            f"/organizations/{org_id}/agent/run/{agent_run_id}"
        )
        return AgentRunResponse(**response)
    
    async def list_agent_runs(self,
                             org_id: int,
                             user_id: Optional[int] = None,
                             source_type: Optional[SourceType] = None,
                             skip: int = 0,
                             limit: int = 100) -> AgentRunsResponse:
        """List agent runs with filtering"""
        params = {"skip": skip, "limit": limit}
        if user_id:
            params["user_id"] = user_id
        if source_type:
            params["source_type"] = source_type.value
        
        response = await self._make_request_enhanced(
            "GET",
            f"/organizations/{org_id}/agent/runs",
            params=params
        )
        
        return AgentRunsResponse(
            items=[AgentRunResponse(**run) for run in response["items"]],
            total=response["total"],
            page=response["page"],
            size=response["size"],
            pages=response["pages"]
        )
    
    async def resume_agent_run(self,
                              org_id: int,
                              agent_run_id: int,
                              prompt: str,
                              images: Optional[List[str]] = None) -> AgentRunResponse:
        """Resume a paused agent run"""
        request_data = ResumeAgentRunRequest(
            agent_run_id=agent_run_id,
            prompt=prompt,
            images=images
        )
        
        response = await self._make_request_enhanced(
            "POST",
            f"/organizations/{org_id}/agent/run/resume",
            data=request_data.dict(exclude_none=True)
        )
        
        return AgentRunResponse(**response)
    
    async def get_agent_run_logs(self,
                                org_id: int,
                                agent_run_id: int,
                                skip: int = 0,
                                limit: int = 100) -> AgentRunWithLogsResponse:
        """Get agent run with logs (Alpha endpoint)"""
        response = await self._make_request_enhanced(
            "GET",
            f"/alpha/organizations/{org_id}/agent/run/{agent_run_id}/logs",
            params={"skip": skip, "limit": limit}
        )
        
        return AgentRunWithLogsResponse(
            id=response["id"],
            organization_id=response["organization_id"],
            logs=[AgentRunLogResponse(**log) for log in response["logs"]],
            status=response.get("status"),
            created_at=response.get("created_at"),
            web_url=response.get("web_url"),
            result=response.get("result"),
            metadata=response.get("metadata"),
            total_logs=response.get("total_logs"),
            page=response.get("page"),
            size=response.get("size"),
            pages=response.get("pages")
        )
    
    # Streaming Methods
    
    async def get_users_stream(self, org_id: str) -> AsyncGenerator[UserResponse, None]:
        """Stream all users with automatic pagination"""
        if not self.config.enable_streaming:
            raise ValueError("Streaming is disabled in configuration")
        
        paginator = StreamingPaginator(
            lambda skip, limit: self.get_users(org_id, skip=skip, limit=limit)
        )
        
        async for user in paginator.stream_items():
            yield user
    
    async def get_all_agent_runs(self, org_id: int) -> AsyncGenerator[AgentRunResponse, None]:
        """Stream all agent runs with automatic pagination"""
        if not self.config.enable_streaming:
            raise ValueError("Streaming is disabled in configuration")
        
        paginator = StreamingPaginator(
            lambda skip, limit: self.list_agent_runs(org_id, skip=skip, limit=limit)
        )
        
        async for run in paginator.stream_items():
            yield run
    
    # Bulk Operations
    
    async def bulk_get_users(self, org_id: str, user_ids: List[str]) -> BulkOperationResult:
        """Fetch multiple users concurrently"""
        if not self.config.enable_bulk_operations:
            raise ValueError("Bulk operations are disabled in configuration")
        
        async def fetch_user(user_id):
            return await self.get_user(org_id, user_id)
        
        return await self._bulk_manager.execute_bulk_async(user_ids, fetch_user)
    
    async def bulk_create_agent_runs(self, 
                                   org_id: int,
                                   run_configs: List[Dict[str, Any]]) -> BulkOperationResult:
        """Create multiple agent runs concurrently"""
        if not self.config.enable_bulk_operations:
            raise ValueError("Bulk operations are disabled in configuration")
        
        async def create_run(config):
            return await self.create_agent_run(org_id, **config)
        
        return await self._bulk_manager.execute_bulk_async(run_configs, create_run)
    
    # Webhook Methods
    
    def get_webhook_handler(self) -> Optional[WebhookHandler]:
        """Get the webhook handler instance"""
        return getattr(self, '_webhook_handler', None)
    
    async def process_webhook(self, payload: Dict[str, Any], signature: Optional[str] = None) -> Dict[str, Any]:
        """Process incoming webhook payload"""
        if not self.config.enable_webhooks or not hasattr(self, '_webhook_handler'):
            raise ValueError("Webhooks are disabled in configuration")
        
        return await self._webhook_handler.handle_webhook(payload, signature)
    
    # Monitoring and Health
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return await self._health_checker.run_health_checks()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        summary = {
            'client_config': self.config.to_dict(),
            'enabled_features': self._get_enabled_features()
        }
        
        if self.config.enable_metrics:
            summary['monitoring'] = self._logger.get_metrics_summary()
        
        if hasattr(self, '_bulk_manager'):
            summary['bulk_operations'] = self._bulk_manager.get_stats()
        
        return summary
    
    def export_metrics(self, format: str = 'json') -> Optional[str]:
        """Export metrics data"""
        if not self.config.enable_metrics:
            return None
        
        return self._logger.export_metrics(format)
    
    # Context Manager Support
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    # Utility Methods
    
    def update_config(self, **kwargs):
        """Update client configuration"""
        self.config.update(**kwargs)
        # Re-setup features with new config
        self._setup_enhanced_features()
    
    async def wait_for_agent_run_completion(self,
                                          org_id: int,
                                          run_id: int,
                                          timeout: int = 1800,
                                          poll_interval: int = 5) -> AgentRunResponse:
        """Wait for agent run to complete with enhanced monitoring"""
        start_time = datetime.utcnow()
        
        while True:
            run_data = await self.get_agent_run(org_id, run_id)
            
            if run_data.status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info("Agent run completed",
                           run_id=run_id,
                           status=run_data.status,
                           duration_seconds=duration)
                return run_data
            
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                raise TimeoutError(f"Agent run {run_id} timed out after {timeout} seconds")
            
            await asyncio.sleep(poll_interval)


# Factory functions for different configurations

def create_development_client(api_token: str, org_id: str) -> AsyncCodegenClient:
    """Create client optimized for development"""
    from .config import ConfigPresets
    config = ConfigPresets.development()
    config.api_token = api_token
    config.org_id = org_id
    return AsyncCodegenClient(config)


def create_production_client(api_token: str, org_id: str) -> AsyncCodegenClient:
    """Create client optimized for production"""
    from .config import ConfigPresets
    config = ConfigPresets.production()
    config.api_token = api_token
    config.org_id = org_id
    return AsyncCodegenClient(config)


def create_high_performance_client(api_token: str, org_id: str) -> AsyncCodegenClient:
    """Create client optimized for high performance"""
    from .config import ConfigPresets
    config = ConfigPresets.high_performance()
    config.api_token = api_token
    config.org_id = org_id
    return AsyncCodegenClient(config)


def create_client_from_env() -> AsyncCodegenClient:
    """Create client from environment variables"""
    config = get_config_for_environment()
    return AsyncCodegenClient(config)

