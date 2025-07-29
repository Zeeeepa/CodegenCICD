"""
Enhanced Codegen API Client Usage Examples

This file demonstrates how to use all the advanced features of the enhanced Codegen API client.
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any

# Import the enhanced client and related modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.integrations.async_client import (
    AsyncCodegenClient, 
    create_development_client,
    create_production_client,
    create_client_from_env
)
from backend.integrations.config import ClientConfig, ConfigPresets
from backend.integrations.models import *
from backend.integrations.exceptions import *
from backend.integrations.webhooks import WebhookEvent


async def basic_usage_example():
    """Basic usage of the enhanced client"""
    print("=== Basic Usage Example ===")
    
    # Create client from environment variables
    client = create_client_from_env()
    
    async with client as c:
        try:
            # Get current user
            user = await c.get_current_user()
            print(f"Current user: {user.github_username} ({user.email})")
            
            # Get organization info
            org = await c.get_organization()
            print(f"Organization: {org.name}")
            
            # Create an agent run
            run = await c.create_agent_run(
                org_id=int(c.config.org_id),
                prompt="Review the latest PR and suggest improvements",
                metadata={"priority": "high", "source": "api_example"}
            )
            print(f"Created agent run: {run.id} (Status: {run.status})")
            
        except CodegenAPIError as e:
            print(f"API Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


async def advanced_configuration_example():
    """Advanced configuration and customization"""
    print("\n=== Advanced Configuration Example ===")
    
    # Create custom configuration
    config = ClientConfig(
        api_token="your-api-token",
        org_id="your-org-id",
        base_url="https://api.codegen.com/v1",
        
        # Performance settings
        timeout=45,
        max_retries=5,
        retry_backoff_factor=2.0,
        
        # Rate limiting
        rate_limit_requests_per_period=100,
        rate_limit_period_seconds=60,
        
        # Caching
        enable_caching=True,
        cache_ttl_seconds=600,  # 10 minutes
        cache_max_size=200,
        
        # Logging
        log_level="INFO",
        log_requests=True,
        log_responses=False,
        
        # Features
        enable_webhooks=True,
        enable_bulk_operations=True,
        enable_streaming=True,
        enable_metrics=True,
        
        # Bulk operations
        bulk_max_workers=10,
        bulk_batch_size=50
    )
    
    client = AsyncCodegenClient(config)
    
    async with client:
        # Get comprehensive metrics
        metrics = client.get_metrics_summary()
        print(f"Enabled features: {metrics['enabled_features']}")
        
        # Export metrics to JSON
        metrics_json = client.export_metrics('json')
        if metrics_json:
            print("Metrics exported successfully")


async def caching_example():
    """Demonstrate caching functionality"""
    print("\n=== Caching Example ===")
    
    config = ConfigPresets.production()
    config.api_token = "your-api-token"
    config.org_id = "your-org-id"
    config.enable_caching = True
    
    client = AsyncCodegenClient(config)
    
    async with client:
        # First call - will hit the API
        print("First call (cache miss)...")
        start_time = datetime.now()
        user1 = await client.get_current_user()
        first_duration = (datetime.now() - start_time).total_seconds()
        print(f"First call took: {first_duration:.3f} seconds")
        
        # Second call - will use cache
        print("Second call (cache hit)...")
        start_time = datetime.now()
        user2 = await client.get_current_user()
        second_duration = (datetime.now() - start_time).total_seconds()
        print(f"Second call took: {second_duration:.3f} seconds")
        
        print(f"Cache speedup: {first_duration / second_duration:.1f}x faster")


async def bulk_operations_example():
    """Demonstrate bulk operations"""
    print("\n=== Bulk Operations Example ===")
    
    client = create_development_client("your-api-token", "your-org-id")
    
    async with client:
        # Bulk fetch users
        user_ids = ["1", "2", "3", "4", "5"]
        
        print(f"Fetching {len(user_ids)} users in bulk...")
        result = await client.bulk_get_users("your-org-id", user_ids)
        
        print(f"Results: {result.successful_items}/{result.total_items} successful")
        print(f"Success rate: {result.success_rate:.1f}%")
        print(f"Duration: {result.duration_seconds:.2f} seconds")
        
        if result.errors:
            print(f"Errors encountered: {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"  - {error.get('error', 'Unknown error')}")
        
        # Bulk create agent runs
        run_configs = [
            {
                "prompt": "Review PR #123",
                "metadata": {"pr_number": 123}
            },
            {
                "prompt": "Fix linting issues",
                "metadata": {"task_type": "maintenance"}
            },
            {
                "prompt": "Update documentation",
                "metadata": {"task_type": "docs"}
            }
        ]
        
        print(f"\nCreating {len(run_configs)} agent runs in bulk...")
        bulk_result = await client.bulk_create_agent_runs(
            org_id=int(client.config.org_id),
            run_configs=run_configs
        )
        
        print(f"Created: {bulk_result.successful_items}/{bulk_result.total_items} runs")
        for i, run in enumerate(bulk_result.results):
            print(f"  Run {i+1}: ID {run.id} - {run.status}")


async def streaming_example():
    """Demonstrate streaming functionality"""
    print("\n=== Streaming Example ===")
    
    client = create_production_client("your-api-token", "your-org-id")
    
    async with client:
        print("Streaming all users...")
        user_count = 0
        
        async for user in client.get_users_stream("your-org-id"):
            user_count += 1
            print(f"  User {user_count}: {user.github_username}")
            
            # Limit output for demo
            if user_count >= 10:
                print("  ... (truncated)")
                break
        
        print(f"Streamed {user_count} users")
        
        print("\nStreaming all agent runs...")
        run_count = 0
        
        async for run in client.get_all_agent_runs(int(client.config.org_id)):
            run_count += 1
            print(f"  Run {run_count}: ID {run.id} - {run.status}")
            
            # Limit output for demo
            if run_count >= 5:
                print("  ... (truncated)")
                break
        
        print(f"Streamed {run_count} agent runs")


async def webhook_handling_example():
    """Demonstrate webhook handling"""
    print("\n=== Webhook Handling Example ===")
    
    config = ConfigPresets.production()
    config.api_token = "your-api-token"
    config.org_id = "your-org-id"
    config.enable_webhooks = True
    config.webhook_secret = "your-webhook-secret"
    
    client = AsyncCodegenClient(config)
    
    # Get webhook handler
    webhook_handler = client.get_webhook_handler()
    
    if webhook_handler:
        # Register custom event handlers
        async def on_agent_run_completed(event: WebhookEvent):
            run_data = event.data
            print(f"Agent run {run_data.get('id')} completed!")
            print(f"Result: {run_data.get('result', 'No result')[:100]}...")
            
            # You could trigger additional actions here
            # e.g., send notifications, update databases, etc.
        
        async def on_pr_created(event: WebhookEvent):
            pr_data = event.data.get('github_pull_request', {})
            print(f"New PR created: {pr_data.get('title')}")
            print(f"URL: {pr_data.get('url')}")
        
        # Register handlers
        webhook_handler.register_handler('agent_run.completed', on_agent_run_completed)
        webhook_handler.register_handler('github.pr.created', on_pr_created)
        
        # Simulate webhook processing
        test_webhook = {
            'event_type': 'agent_run.completed',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'id': 123,
                'status': 'completed',
                'result': 'Successfully implemented the requested feature with proper error handling and tests.',
                'github_pull_requests': [
                    {
                        'id': 456,
                        'title': 'Implement user authentication feature',
                        'url': 'https://github.com/org/repo/pull/456'
                    }
                ]
            }
        }
        
        result = await client.process_webhook(test_webhook)
        print(f"Webhook processed: {result['status']}")
        
        # Get webhook stats
        stats = webhook_handler.get_stats()
        print(f"Webhook stats: {stats['total_events']} events processed")


async def error_handling_example():
    """Demonstrate comprehensive error handling"""
    print("\n=== Error Handling Example ===")
    
    client = create_development_client("your-api-token", "your-org-id")
    
    async with client:
        # Example 1: Validation Error
        try:
            await client.create_agent_run(
                org_id=123,
                prompt="",  # Empty prompt will cause validation error
            )
        except ValidationError as e:
            print(f"Validation Error: {e.message}")
            if e.field_errors:
                for field, errors in e.field_errors.items():
                    print(f"  {field}: {', '.join(errors)}")
        
        # Example 2: Rate Limit Error
        try:
            # Simulate rapid requests that might hit rate limits
            for i in range(5):
                await client.get_current_user()
        except RateLimitError as e:
            print(f"Rate Limited: {e.message}")
            print(f"Retry after: {e.retry_after} seconds")
        
        # Example 3: Authentication Error
        try:
            # This would happen with invalid API token
            invalid_client = AsyncCodegenClient(ClientConfig(api_token="invalid-token"))
            async with invalid_client:
                await invalid_client.get_current_user()
        except AuthenticationError as e:
            print(f"Authentication Error: {e.message}")
        
        # Example 4: Generic API Error with context
        try:
            await client.get_user("invalid-org", "invalid-user")
        except CodegenAPIError as e:
            print(f"API Error: {e.message}")
            print(f"Status Code: {e.status_code}")
            print(f"Endpoint: {e.endpoint}")
            if e.request_id:
                print(f"Request ID: {e.request_id}")


async def monitoring_and_health_example():
    """Demonstrate monitoring and health checking"""
    print("\n=== Monitoring and Health Example ===")
    
    client = create_production_client("your-api-token", "your-org-id")
    
    async with client:
        # Perform health check
        health_result = await client.health_check()
        print(f"Overall health: {health_result['overall_status']}")
        
        for check_name, check_result in health_result['checks'].items():
            status = check_result['status']
            print(f"  {check_name}: {status}")
            
            if status == 'healthy' and 'response_time_ms' in check_result:
                print(f"    Response time: {check_result['response_time_ms']:.2f}ms")
        
        # Get comprehensive metrics
        metrics = client.get_metrics_summary()
        
        if 'monitoring' in metrics:
            monitoring_data = metrics['monitoring']
            if 'performance_stats' in monitoring_data:
                perf = monitoring_data['performance_stats']
                print(f"\nPerformance Stats:")
                print(f"  Total requests: {perf.get('total_requests', 0)}")
                print(f"  Success rate: {100 - perf.get('error_rate', 0):.1f}%")
                print(f"  Avg response time: {perf.get('average_response_time_ms', 0):.2f}ms")
        
        if 'bulk_operations' in metrics:
            bulk_stats = metrics['bulk_operations']
            print(f"\nBulk Operations Stats:")
            print(f"  Total operations: {bulk_stats.get('total_operations', 0)}")
            print(f"  Success rate: {bulk_stats.get('success_rate', 0):.1f}%")


async def wait_for_completion_example():
    """Demonstrate waiting for agent run completion"""
    print("\n=== Wait for Completion Example ===")
    
    client = create_development_client("your-api-token", "your-org-id")
    
    async with client:
        # Create an agent run
        run = await client.create_agent_run(
            org_id=int(client.config.org_id),
            prompt="Implement a comprehensive test suite for the authentication module",
            metadata={"estimated_duration": "30 minutes"}
        )
        
        print(f"Created agent run {run.id}")
        print("Waiting for completion...")
        
        try:
            # Wait for completion with timeout
            completed_run = await client.wait_for_agent_run_completion(
                org_id=int(client.config.org_id),
                run_id=run.id,
                timeout=1800,  # 30 minutes
                poll_interval=10  # Check every 10 seconds
            )
            
            print(f"Agent run completed with status: {completed_run.status}")
            if completed_run.result:
                print(f"Result: {completed_run.result[:200]}...")
            
            # Check for created PRs
            if completed_run.github_pull_requests:
                print("Created PRs:")
                for pr in completed_run.github_pull_requests:
                    print(f"  - {pr.title}: {pr.url}")
        
        except TimeoutError as e:
            print(f"Timeout waiting for completion: {e}")
        except Exception as e:
            print(f"Error waiting for completion: {e}")


async def configuration_management_example():
    """Demonstrate configuration management"""
    print("\n=== Configuration Management Example ===")
    
    # Load configuration from file (if it exists)
    try:
        config = ClientConfig.from_file("config.json")
        print("Loaded configuration from file")
    except FileNotFoundError:
        print("No config file found, using defaults")
        config = ConfigPresets.development()
        config.api_token = "your-api-token"
        config.org_id = "your-org-id"
    
    # Display current configuration (sensitive data redacted)
    config_dict = config.to_dict()
    print("Current configuration:")
    for key, value in config_dict.items():
        print(f"  {key}: {value}")
    
    # Update configuration at runtime
    client = AsyncCodegenClient(config)
    
    print("\nUpdating configuration...")
    client.update_config(
        timeout=60,
        max_retries=5,
        enable_caching=True,
        cache_ttl_seconds=900  # 15 minutes
    )
    
    print("Configuration updated successfully")
    
    # Save configuration to file
    try:
        config.save_to_file("config_backup.json")
        print("Configuration saved to config_backup.json")
    except Exception as e:
        print(f"Failed to save configuration: {e}")


async def main():
    """Run all examples"""
    print("Enhanced Codegen API Client Examples")
    print("=" * 50)
    
    examples = [
        basic_usage_example,
        advanced_configuration_example,
        caching_example,
        bulk_operations_example,
        streaming_example,
        webhook_handling_example,
        error_handling_example,
        monitoring_and_health_example,
        wait_for_completion_example,
        configuration_management_example
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Example failed: {e}")
        
        print()  # Add spacing between examples


if __name__ == "__main__":
    # Set up environment variables for examples
    import os
    
    # You should set these environment variables with your actual values
    os.environ.setdefault('CODEGEN_API_TOKEN', 'your-api-token-here')
    os.environ.setdefault('CODEGEN_ORG_ID', 'your-org-id-here')
    os.environ.setdefault('CODEGEN_BASE_URL', 'https://api.codegen.com/v1')
    
    # Run examples
    asyncio.run(main())

