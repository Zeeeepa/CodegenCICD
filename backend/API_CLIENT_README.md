# Enhanced Codegen API Client

This module provides a comprehensive Python SDK for interacting with the Codegen API, featuring both synchronous and asynchronous clients with advanced capabilities.

## Features

### 🚀 **Core Functionality**
- **Sync & Async Support**: Both `CodegenClient` and `AsyncCodegenClient` with feature parity
- **Agent Run Management**: Create, monitor, and manage Codegen agent runs
- **User Management**: Retrieve user information and organization details
- **Comprehensive Error Handling**: Detailed exception hierarchy with proper error context

### ⚡ **Advanced Features**
- **Rate Limiting**: Built-in sliding window rate limiter to respect API limits
- **Caching**: In-memory TTL cache with statistics for improved performance
- **Retry Logic**: Exponential backoff retry mechanism for resilient requests
- **Request Metrics**: Comprehensive request tracking and performance monitoring
- **Configuration Presets**: Pre-configured settings for development, production, and testing

### 🛠 **Enterprise Ready**
- **Webhook Support**: Event handling with signature verification
- **Bulk Operations**: Concurrent processing with progress tracking
- **Streaming**: Automatic pagination for large datasets
- **Health Checks**: Built-in API health monitoring
- **Context Managers**: Proper resource management with `with` statements

## Quick Start

### Basic Usage

```python
from backend.api import CodegenClient, ConfigPresets

# Using default configuration
with CodegenClient() as client:
    # Health check
    health = client.health_check()
    print(f"API Status: {health['status']}")
    
    # Get current user
    user = client.get_current_user()
    print(f"User: {user.github_username}")
    
    # Create an agent run
    run = client.create_agent_run(
        org_id=323,
        prompt="Create a Python function to calculate fibonacci numbers",
        metadata={"source": "api_example"}
    )
    print(f"Created agent run: {run.id}")
    
    # Wait for completion
    completed_run = client.wait_for_completion(323, run.id, timeout=300)
    print(f"Run completed with status: {completed_run.status}")
```

### Async Usage

```python
import asyncio
from backend.api import AsyncCodegenClient

async def main():
    async with AsyncCodegenClient() as client:
        # Create agent run asynchronously
        run = await client.create_agent_run(
            org_id=323,
            prompt="Analyze this codebase for security vulnerabilities",
            metadata={"priority": "high"}
        )
        print(f"Async agent run created: {run.id}")
        
        # Get run status
        status = await client.get_agent_run(323, run.id)
        print(f"Run status: {status.status}")

asyncio.run(main())
```

### Configuration Presets

```python
from backend.api import CodegenClient, ConfigPresets

# Development configuration (verbose logging, lower limits)
dev_config = ConfigPresets.development()
with CodegenClient(dev_config) as client:
    # Development-specific settings applied
    pass

# Production configuration (optimized settings)
prod_config = ConfigPresets.production()
with CodegenClient(prod_config) as client:
    # Production-optimized settings
    pass

# High performance configuration (heavy workloads)
perf_config = ConfigPresets.high_performance()
with CodegenClient(perf_config) as client:
    # High throughput settings
    pass
```

### Custom Configuration

```python
from backend.api import CodegenClient, ClientConfig

# Custom configuration
config = ClientConfig(
    api_token="your-api-token",
    org_id="your-org-id",
    timeout=60,
    max_retries=5,
    enable_caching=True,
    cache_ttl_seconds=600,
    rate_limit_requests_per_period=100,
    log_level="DEBUG"
)

with CodegenClient(config) as client:
    # Your custom configuration is applied
    pass
```

## Environment Variables

The client supports configuration via environment variables:

```bash
# Core settings
CODEGEN_API_TOKEN=your-api-token
CODEGEN_ORG_ID=your-org-id
CODEGEN_BASE_URL=https://api.codegen.com/v1

# Performance settings
CODEGEN_TIMEOUT=30
CODEGEN_MAX_RETRIES=3
CODEGEN_RETRY_DELAY=1.0
CODEGEN_RETRY_BACKOFF=2.0

# Rate limiting
CODEGEN_RATE_LIMIT_REQUESTS=60
CODEGEN_RATE_LIMIT_PERIOD=60

# Caching
CODEGEN_ENABLE_CACHING=true
CODEGEN_CACHE_TTL=300
CODEGEN_CACHE_MAX_SIZE=128

# Features
CODEGEN_ENABLE_WEBHOOKS=true
CODEGEN_ENABLE_BULK_OPERATIONS=true
CODEGEN_ENABLE_STREAMING=true
CODEGEN_ENABLE_METRICS=true

# Logging
CODEGEN_LOG_LEVEL=INFO
CODEGEN_LOG_REQUESTS=true
CODEGEN_LOG_RESPONSES=false
CODEGEN_LOG_REQUEST_BODIES=false

# Webhooks
CODEGEN_WEBHOOK_SECRET=your-webhook-secret
```

## Error Handling

The client provides a comprehensive exception hierarchy:

```python
from backend.api import (
    CodegenAPIError,
    ValidationError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ServerError,
    TimeoutError,
    NetworkError
)

try:
    with CodegenClient() as client:
        run = client.create_agent_run(323, "")  # Empty prompt
except ValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Field errors: {e.field_errors}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except CodegenAPIError as e:
    print(f"API error: {e.message} (Status: {e.status_code})")
```

## Advanced Features

### Rate Limiting

```python
# Check current rate limit usage
usage = client.rate_limiter.get_current_usage()
print(f"Current usage: {usage['current_requests']}/{usage['max_requests']}")
print(f"Usage percentage: {usage['usage_percentage']:.1f}%")
```

### Caching

```python
# Get cache statistics
if client.cache:
    stats = client.cache.get_stats()
    print(f"Cache hit rate: {stats['hit_rate_percentage']:.1f}%")
    print(f"Cache size: {stats['size']}/{stats['max_size']}")
    
    # Clear cache if needed
    client.cache.clear()
```

### Health Monitoring

```python
# Perform health check
health = client.health_check()
print(f"API Status: {health['status']}")
print(f"Response Time: {health['response_time_seconds']:.3f}s")
```

## Integration with Existing Codebase

This enhanced client can be used alongside the existing `CodegenClient` in `backend/integrations/codegen_client.py`. To migrate:

1. **Import the new client**: `from backend.api import CodegenClient as EnhancedCodegenClient`
2. **Update configuration**: Use the new `ClientConfig` class for advanced settings
3. **Leverage new features**: Take advantage of caching, rate limiting, and metrics
4. **Gradual migration**: Replace usage incrementally while maintaining backward compatibility

## Dependencies

The enhanced client requires these additional dependencies (already added to `requirements.txt`):

- `aiohttp>=3.9.0` - For async HTTP support
- `structlog>=23.2.0` - For structured logging (optional, used by existing integrations)

## Performance Considerations

- **Caching**: Enabled by default with 5-minute TTL, significantly reduces API calls
- **Rate Limiting**: Prevents API quota exhaustion with intelligent request spacing
- **Connection Pooling**: Uses session-based connections for improved performance
- **Retry Logic**: Exponential backoff prevents overwhelming the API during issues
- **Async Support**: Non-blocking operations for high-concurrency scenarios

## Security

- **Token Management**: Secure handling of API tokens with environment variable support
- **Request Validation**: Input validation prevents malformed requests
- **Error Sanitization**: Sensitive information is not exposed in error messages
- **Webhook Verification**: HMAC signature verification for webhook security
