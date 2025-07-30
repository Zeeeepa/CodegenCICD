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

### Advanced Configuration

```python
from backend.api import CodegenClient, CodegenConfig, ConfigPresets

# Custom configuration
config = CodegenConfig(
    base_url="https://api.codegen.com",
    api_token="your-api-token",
    timeout=30,
    max_retries=3,
    rate_limit_requests=100,
    rate_limit_window=60,
    enable_caching=True,
    cache_ttl=300
)

client = CodegenClient(config)

# Or use presets
dev_client = CodegenClient(ConfigPresets.development())
prod_client = CodegenClient(ConfigPresets.production())
```

### Async Usage

```python
import asyncio
from backend.api import AsyncCodegenClient

async def main():
    async with AsyncCodegenClient() as client:
        # All the same methods as sync client
        user = await client.get_current_user()
        run = await client.create_agent_run(323, "Create a REST API")
        
        # Stream agent runs with automatic pagination
        async for run in client.stream_agent_runs(323):
            print(f"Run {run.id}: {run.status}")

asyncio.run(main())
```

## Advanced Features

### Bulk Operations

```python
# Create multiple agent runs concurrently
configs = [
    {"prompt": "Create a user model", "metadata": {"type": "model"}},
    {"prompt": "Create a user service", "metadata": {"type": "service"}},
    {"prompt": "Create user tests", "metadata": {"type": "test"}}
]

with client.bulk_operations() as bulk:
    results = bulk.create_agent_runs(323, configs, max_concurrent=5)
    
    for result in results:
        if result.success:
            print(f"Created run {result.data.id}")
        else:
            print(f"Failed: {result.error}")
```

### Webhook Handling

```python
from backend.api import WebhookHandler

handler = WebhookHandler(secret="your-webhook-secret")

@handler.on("agent_run.completed")
def handle_completion(payload):
    print(f"Agent run {payload['id']} completed!")

@handler.on("agent_run.failed")
def handle_failure(payload):
    print(f"Agent run {payload['id']} failed: {payload['error']}")

# In your web framework
def webhook_endpoint(request):
    handler.handle_request(request.body, request.headers)
```

### Streaming and Pagination

```python
# Stream all agent runs with automatic pagination
for run in client.stream_agent_runs(323, status="completed"):
    print(f"Completed run: {run.id}")

# Manual pagination
page = 1
while True:
    runs = client.get_agent_runs(323, page=page, per_page=50)
    if not runs.items:
        break
    
    for run in runs.items:
        print(f"Run {run.id}: {run.status}")
    
    page += 1
```

### Health Monitoring

```python
# Basic health check
health = client.health_check()
print(f"API Health: {health['status']}")

# Detailed health monitoring
monitor = client.create_health_monitor(interval=30)
monitor.on_healthy(lambda: print("API is healthy"))
monitor.on_unhealthy(lambda: print("API is down!"))
monitor.start()
```

## Configuration Options

### Environment Variables

```bash
# Basic configuration
CODEGEN_API_TOKEN=your-api-token
CODEGEN_ORG_ID=323
CODEGEN_BASE_URL=https://api.codegen.com

# Advanced configuration
CODEGEN_TIMEOUT=30
CODEGEN_MAX_RETRIES=3
CODEGEN_RATE_LIMIT_REQUESTS=100
CODEGEN_RATE_LIMIT_WINDOW=60
CODEGEN_ENABLE_CACHING=true
CODEGEN_CACHE_TTL=300
CODEGEN_LOG_LEVEL=INFO
```

### Configuration Presets

```python
# Development preset
dev_config = ConfigPresets.development()
# - Lower rate limits
# - Verbose logging
# - Shorter timeouts
# - Caching disabled

# Production preset
prod_config = ConfigPresets.production()
# - Higher rate limits
# - Error-only logging
# - Longer timeouts
# - Caching enabled

# Testing preset
test_config = ConfigPresets.testing()
# - Mock responses
# - No rate limiting
# - Fast timeouts
# - Caching disabled
```

## Error Handling

### Exception Hierarchy

```python
from backend.api import (
    CodegenAPIError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    ServerError
)

try:
    run = client.create_agent_run(323, "Invalid prompt")
except AuthenticationError:
    print("Invalid API token")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Validation failed: {e.details}")
except NotFoundError:
    print("Organization not found")
except ServerError:
    print("Server error, please try again")
except CodegenAPIError as e:
    print(f"API error: {e}")
```

### Retry Logic

```python
# Automatic retries with exponential backoff
config = CodegenConfig(
    max_retries=5,
    retry_backoff_factor=2.0,
    retry_on_status=[429, 500, 502, 503, 504]
)

client = CodegenClient(config)

# Manual retry control
from backend.api import retry_on_error

@retry_on_error(max_attempts=3, backoff_factor=1.5)
def create_run_with_retry():
    return client.create_agent_run(323, "Create a function")
```

## Performance and Monitoring

### Request Metrics

```python
# Get client statistics
stats = client.get_stats()
print(f"Total requests: {stats.total_requests}")
print(f"Success rate: {stats.success_rate:.2%}")
print(f"Average response time: {stats.avg_response_time:.2f}s")
print(f"Cache hit rate: {stats.cache_hit_rate:.2%}")

# Reset statistics
client.reset_stats()
```

### Caching

```python
# Enable caching with custom TTL
config = CodegenConfig(
    enable_caching=True,
    cache_ttl=600,  # 10 minutes
    cache_max_size=1000
)

client = CodegenClient(config)

# Cache statistics
cache_stats = client.get_cache_stats()
print(f"Cache hits: {cache_stats.hits}")
print(f"Cache misses: {cache_stats.misses}")
print(f"Cache size: {cache_stats.size}")

# Clear cache
client.clear_cache()
```

### Rate Limiting

```python
# Configure rate limiting
config = CodegenConfig(
    rate_limit_requests=100,  # 100 requests
    rate_limit_window=60,     # per 60 seconds
    rate_limit_strategy="sliding_window"
)

client = CodegenClient(config)

# Check rate limit status
rate_limit = client.get_rate_limit_status()
print(f"Remaining requests: {rate_limit.remaining}")
print(f"Reset time: {rate_limit.reset_time}")
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from backend.api import CodegenClient, get_codegen_client

app = FastAPI()

@app.get("/agent-runs/{org_id}")
async def get_agent_runs(
    org_id: int,
    client: CodegenClient = Depends(get_codegen_client)
):
    runs = client.get_agent_runs(org_id)
    return {"runs": [run.dict() for run in runs.items]}

@app.post("/agent-runs/{org_id}")
async def create_agent_run(
    org_id: int,
    prompt: str,
    client: CodegenClient = Depends(get_codegen_client)
):
    run = client.create_agent_run(org_id, prompt)
    return run.dict()
```

### Django Integration

```python
# settings.py
CODEGEN_CONFIG = {
    'api_token': 'your-token',
    'org_id': 323,
    'timeout': 30
}

# views.py
from django.http import JsonResponse
from backend.api import CodegenClient
from django.conf import settings

def create_agent_run(request):
    client = CodegenClient.from_settings(settings.CODEGEN_CONFIG)
    run = client.create_agent_run(
        settings.CODEGEN_CONFIG['org_id'],
        request.POST['prompt']
    )
    return JsonResponse(run.dict())
```

## Testing

### Mock Client

```python
from backend.api import MockCodegenClient

# Use mock client for testing
client = MockCodegenClient()
client.set_mock_response("create_agent_run", {"id": 123, "status": "pending"})

run = client.create_agent_run(323, "test prompt")
assert run.id == 123
assert run.status == "pending"
```

### Test Utilities

```python
from backend.api.testing import CodegenTestCase

class MyTestCase(CodegenTestCase):
    def test_agent_run_creation(self):
        # Mock responses are automatically set up
        run = self.client.create_agent_run(323, "test")
        self.assertEqual(run.status, "pending")
        
    def test_with_custom_response(self):
        self.mock_response("get_agent_run", {"id": 1, "status": "completed"})
        run = self.client.get_agent_run(323, 1)
        self.assertEqual(run.status, "completed")
```

## Best Practices

### 1. Use Context Managers

```python
# Ensures proper cleanup
with CodegenClient() as client:
    # Your code here
    pass
```

### 2. Handle Rate Limits Gracefully

```python
from backend.api import RateLimitError
import time

try:
    run = client.create_agent_run(323, prompt)
except RateLimitError as e:
    time.sleep(e.retry_after)
    run = client.create_agent_run(323, prompt)
```

### 3. Use Bulk Operations for Multiple Requests

```python
# Instead of multiple individual requests
configs = [{"prompt": f"Task {i}"} for i in range(10)]
results = client.bulk_create_agent_runs(323, configs)
```

### 4. Monitor Performance

```python
# Regular health checks
if not client.health_check()['healthy']:
    # Handle unhealthy API
    pass

# Monitor statistics
stats = client.get_stats()
if stats.error_rate > 0.1:  # 10% error rate
    # Alert or take action
    pass
```

### 5. Use Appropriate Configuration

```python
# Development
client = CodegenClient(ConfigPresets.development())

# Production
client = CodegenClient(ConfigPresets.production())

# Custom for specific needs
config = CodegenConfig(
    timeout=60,  # Long-running operations
    max_retries=5,  # High reliability needed
    enable_caching=True  # Performance critical
)
client = CodegenClient(config)
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API token is correct
   - Check token permissions
   - Ensure organization access

2. **Rate Limiting**
   - Implement exponential backoff
   - Use bulk operations
   - Consider caching

3. **Timeouts**
   - Increase timeout for long operations
   - Use async client for better concurrency
   - Implement proper retry logic

4. **Memory Usage**
   - Clear cache periodically
   - Use streaming for large datasets
   - Limit concurrent operations

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

config = CodegenConfig(log_level="DEBUG")
client = CodegenClient(config)

# All requests/responses will be logged
```

## API Reference

For complete API documentation, see the generated docs or use:

```python
help(CodegenClient)
help(AsyncCodegenClient)
```

