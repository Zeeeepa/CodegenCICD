# Enhanced Codegen API Client

A comprehensive, production-ready Python client for the Codegen API with advanced features including async support, caching, rate limiting, bulk operations, webhooks, and comprehensive monitoring.

## Features

### 🚀 Core Features
- **Async/Await Support**: Full async/await support with context managers
- **Type Safety**: Complete Pydantic models with validation
- **Error Handling**: Comprehensive error handling with custom exceptions
- **Configuration Management**: Environment-based configuration with presets

### ⚡ Performance Features
- **Response Caching**: TTL-based caching with automatic invalidation
- **Rate Limiting**: Adaptive rate limiting with burst handling
- **Bulk Operations**: Concurrent bulk operations with progress tracking
- **Streaming**: Memory-efficient streaming for large datasets

### 📊 Monitoring & Observability
- **Structured Logging**: Comprehensive logging with metrics collection
- **Health Checks**: Built-in health monitoring and diagnostics
- **Performance Metrics**: Request timing, success rates, and error tracking
- **Export Capabilities**: Metrics export in multiple formats

### 🔗 Integration Features
- **Webhook Support**: Event handling with signature verification
- **Retry Logic**: Exponential backoff with jitter
- **Connection Pooling**: Efficient HTTP connection management
- **Circuit Breaker**: Automatic failure detection and recovery

## Quick Start

### Installation

```python
# The enhanced client is part of the backend.integrations package
from backend.integrations import AsyncCodegenClient, create_production_client
```

### Basic Usage

```python
import asyncio
from backend.integrations import create_production_client

async def main():
    # Create client from environment variables
    client = create_production_client("your-api-token", "your-org-id")
    
    async with client as c:
        # Get current user
        user = await c.get_current_user()
        print(f"Hello, {user.github_username}!")
        
        # Create an agent run
        run = await c.create_agent_run(
            org_id=123,
            prompt="Review the latest PR and suggest improvements",
            metadata={"priority": "high"}
        )
        
        # Wait for completion
        completed_run = await c.wait_for_agent_run_completion(
            org_id=123,
            run_id=run.id,
            timeout=1800  # 30 minutes
        )
        
        print(f"Run completed: {completed_run.status}")

asyncio.run(main())
```

## Configuration

### Environment Variables

```bash
# Core Configuration
CODEGEN_API_TOKEN=your-api-token
CODEGEN_ORG_ID=your-org-id
CODEGEN_BASE_URL=https://api.codegen.com/v1

# Performance Tuning
CODEGEN_TIMEOUT=30
CODEGEN_MAX_RETRIES=3
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
```

### Programmatic Configuration

```python
from backend.integrations import ClientConfig, AsyncCodegenClient

config = ClientConfig(
    api_token="your-api-token",
    org_id="your-org-id",
    timeout=45,
    max_retries=5,
    enable_caching=True,
    cache_ttl_seconds=600,
    rate_limit_requests_per_period=100,
    bulk_max_workers=10
)

client = AsyncCodegenClient(config)
```

### Configuration Presets

```python
from backend.integrations import ConfigPresets, AsyncCodegenClient

# Development configuration
dev_config = ConfigPresets.development()
dev_config.api_token = "your-token"
dev_config.org_id = "your-org"

# Production configuration  
prod_config = ConfigPresets.production()
prod_config.api_token = "your-token"
prod_config.org_id = "your-org"

# High performance configuration
perf_config = ConfigPresets.high_performance()
perf_config.api_token = "your-token"
perf_config.org_id = "your-org"
```

## Advanced Features

### Caching

```python
async with client as c:
    # First call hits the API
    user1 = await c.get_current_user()
    
    # Second call uses cache (much faster)
    user2 = await c.get_current_user()
    
    # Cache is automatically invalidated after TTL
```

### Bulk Operations

```python
async with client as c:
    # Bulk fetch users
    user_ids = ["1", "2", "3", "4", "5"]
    result = await c.bulk_get_users("org-id", user_ids)
    
    print(f"Success rate: {result.success_rate}%")
    print(f"Duration: {result.duration_seconds}s")
    
    # Bulk create agent runs
    run_configs = [
        {"prompt": "Review PR #123", "metadata": {"pr": 123}},
        {"prompt": "Fix linting issues", "metadata": {"type": "maintenance"}},
        {"prompt": "Update docs", "metadata": {"type": "docs"}}
    ]
    
    bulk_result = await c.bulk_create_agent_runs(123, run_configs)
```

### Streaming

```python
async with client as c:
    # Stream all users (memory efficient)
    async for user in c.get_users_stream("org-id"):
        print(f"User: {user.github_username}")
    
    # Stream all agent runs
    async for run in c.get_all_agent_runs(123):
        print(f"Run {run.id}: {run.status}")
```

### Webhook Handling

```python
from backend.integrations import WebhookEvent

# Get webhook handler
webhook_handler = client.get_webhook_handler()

# Register event handlers
async def on_agent_run_completed(event: WebhookEvent):
    run_data = event.data
    print(f"Agent run {run_data['id']} completed!")
    
    # Trigger additional actions
    if run_data.get('github_pull_requests'):
        # Send notification, update database, etc.
        pass

webhook_handler.register_handler('agent_run.completed', on_agent_run_completed)

# Process incoming webhook
result = await client.process_webhook(webhook_payload, signature)
```

### Error Handling

```python
from backend.integrations import (
    ValidationError, RateLimitError, AuthenticationError,
    NotFoundError, ServerError, TimeoutError
)

async with client as c:
    try:
        run = await c.create_agent_run(
            org_id=123,
            prompt="",  # Invalid empty prompt
        )
    except ValidationError as e:
        print(f"Validation failed: {e.message}")
        for field, errors in e.field_errors.items():
            print(f"  {field}: {', '.join(errors)}")
    
    except RateLimitError as e:
        print(f"Rate limited. Retry after {e.retry_after} seconds")
    
    except AuthenticationError as e:
        print(f"Authentication failed: {e.message}")
    
    except TimeoutError as e:
        print(f"Request timed out: {e.message}")
```

### Monitoring & Health Checks

```python
async with client as c:
    # Comprehensive health check
    health = await c.health_check()
    print(f"Overall status: {health['overall_status']}")
    
    for check_name, result in health['checks'].items():
        print(f"  {check_name}: {result['status']}")
    
    # Get performance metrics
    metrics = c.get_metrics_summary()
    
    if 'monitoring' in metrics:
        perf = metrics['monitoring']['performance_stats']
        print(f"Total requests: {perf['total_requests']}")
        print(f"Average response time: {perf['average_response_time_ms']}ms")
        print(f"Success rate: {100 - perf['error_rate']}%")
    
    # Export metrics
    metrics_json = c.export_metrics('json')
    with open('metrics.json', 'w') as f:
        f.write(metrics_json)
```

## API Reference

### Client Classes

- **`AsyncCodegenClient`**: Main enhanced async client
- **`CodegenClient`**: Legacy sync client (deprecated)

### Factory Functions

- **`create_development_client(token, org_id)`**: Development-optimized client
- **`create_production_client(token, org_id)`**: Production-optimized client  
- **`create_client_from_env()`**: Client from environment variables

### Configuration

- **`ClientConfig`**: Main configuration class
- **`ConfigPresets`**: Predefined configuration presets

### Models

- **`UserResponse`**: User information
- **`AgentRunResponse`**: Agent run details
- **`OrganizationResponse`**: Organization information
- **`CreateAgentRunRequest`**: Agent run creation request
- **`WebhookEvent`**: Webhook event payload

### Exceptions

- **`CodegenAPIError`**: Base API error
- **`ValidationError`**: Request validation error
- **`RateLimitError`**: Rate limiting error
- **`AuthenticationError`**: Authentication error
- **`NotFoundError`**: Resource not found error
- **`ServerError`**: Server-side error
- **`TimeoutError`**: Request timeout error

## Migration Guide

### From Legacy Client

```python
# Old way (legacy client)
from backend.integrations import CodegenClient

client = CodegenClient()
run = await client.create_agent_run(
    target="Fix the bug",
    repo_name="my-repo"
)

# New way (enhanced client)
from backend.integrations import create_production_client

client = create_production_client("token", "org-id")
async with client as c:
    run = await c.create_agent_run(
        org_id=123,
        prompt="Fix the bug",
        metadata={"repo": "my-repo"}
    )
```

### Gradual Migration

```python
# Use the factory method in existing CodegenClient
from backend.integrations import CodegenClient

# Create enhanced client from legacy client
enhanced_client = CodegenClient.create_enhanced_client()

async with enhanced_client as c:
    # Use all enhanced features
    result = await c.bulk_get_users("org-id", user_ids)
```

## Performance Considerations

### Caching Strategy

- **User data**: 10 minutes TTL (frequently accessed, rarely changes)
- **Organization data**: 30 minutes TTL (rarely changes)
- **Agent runs**: 1 minute TTL (frequently changing)

### Rate Limiting

- **Default**: 60 requests per minute
- **Adaptive**: Automatically adjusts based on server responses
- **Burst handling**: Allows temporary spikes in traffic

### Bulk Operations

- **Concurrency**: Configurable worker pool (default: 5 workers)
- **Batch size**: Configurable batch processing (default: 100 items)
- **Error handling**: Partial failure support with detailed error reporting

## Testing

```python
# Run the comprehensive test suite
python -m pytest tests/test_codegen_client_enhanced.py -v

# Run specific test categories
python -m pytest tests/test_codegen_client_enhanced.py::TestAsyncCodegenClient -v
python -m pytest tests/test_codegen_client_enhanced.py::TestCachingSystem -v
python -m pytest tests/test_codegen_client_enhanced.py::TestBulkOperations -v
```

## Examples

See `examples/enhanced_client_usage.py` for comprehensive usage examples covering:

- Basic usage patterns
- Advanced configuration
- Caching strategies
- Bulk operations
- Streaming data
- Webhook handling
- Error handling
- Monitoring and health checks
- Performance optimization

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation and examples
4. Ensure backward compatibility where possible
5. Add appropriate logging and error handling

## License

This enhanced client is part of the CodegenCICD project and follows the same licensing terms.

