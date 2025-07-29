#!/usr/bin/env python3
"""
Demo script showcasing the Enhanced Codegen API Client features
"""

import os
import asyncio
from api import CodegenClient, AsyncCodegenClient, ConfigPresets

# Set credentials
os.environ["CODEGEN_ORG_ID"] = "323"
os.environ["CODEGEN_API_TOKEN"] = "sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99"

def demo_basic_usage():
    """Demonstrate basic usage"""
    print("🔧 Basic Usage Demo")
    print("-" * 40)
    
    with CodegenClient() as client:
        # Get current user
        user = client.get_current_user()
        print(f"✅ Current user: {user.github_username}")
        
        # Get organizations
        orgs = client.get_organizations()
        print(f"✅ Found {len(orgs.items)} organizations")
        
        # Create an agent run
        agent_run = client.create_agent_run(
            org_id=323,
            prompt="Create a simple Python function that calculates fibonacci numbers",
            metadata={"demo": True, "type": "fibonacci"}
        )
        print(f"✅ Created agent run: {agent_run.id}")
        
        # Get client statistics
        stats = client.get_stats()
        print(f"✅ Client made {stats['metrics']['total_requests']} requests")

def demo_configuration_presets():
    """Demonstrate configuration presets"""
    print("\n⚙️ Configuration Presets Demo")
    print("-" * 40)
    
    # Development configuration
    dev_config = ConfigPresets.development()
    with CodegenClient(dev_config) as client:
        print(f"✅ Development config: {client.config.log_level} logging, {client.config.max_retries} retries")
    
    # Production configuration
    prod_config = ConfigPresets.production()
    with CodegenClient(prod_config) as client:
        print(f"✅ Production config: {client.config.log_level} logging, {client.config.max_retries} retries")

def demo_caching_and_metrics():
    """Demonstrate caching and metrics"""
    print("\n📊 Caching & Metrics Demo")
    print("-" * 40)
    
    with CodegenClient() as client:
        # Make the same request twice to demonstrate caching
        print("Making first request...")
        user1 = client.get_current_user()
        
        print("Making second request (should be cached)...")
        user2 = client.get_current_user()
        
        # Show metrics
        stats = client.get_stats()
        print(f"✅ Total requests: {stats['metrics']['total_requests']}")
        print(f"✅ Average response time: {stats['metrics']['average_response_time']:.3f}s")
        print(f"✅ Cache size: {stats['cache']['current_size']}")

def demo_webhook_handling():
    """Demonstrate webhook handling"""
    print("\n🔗 Webhook Handling Demo")
    print("-" * 40)
    
    client = CodegenClient()
    
    # Register webhook handlers
    def on_agent_completed(payload):
        print(f"🎉 Agent run {payload['data']['id']} completed!")
    
    def on_agent_failed(payload):
        print(f"❌ Agent run {payload['data']['id']} failed!")
    
    client.webhook_handler.register_handler("agent_run.completed", on_agent_completed)
    client.webhook_handler.register_handler("agent_run.failed", on_agent_failed)
    
    # Simulate webhook events
    test_payloads = [
        {
            "event_type": "agent_run.completed",
            "data": {"id": 12345},
            "timestamp": "2024-01-01T00:00:00Z"
        },
        {
            "event_type": "agent_run.failed",
            "data": {"id": 12346},
            "timestamp": "2024-01-01T00:01:00Z"
        }
    ]
    
    for payload in test_payloads:
        client.webhook_handler.handle_webhook(payload)
    
    client.close()

async def demo_async_functionality():
    """Demonstrate async functionality"""
    print("\n🔄 Async Functionality Demo")
    print("-" * 40)
    
    async with AsyncCodegenClient() as client:
        # Async get current user
        user = await client.get_current_user()
        print(f"✅ Async current user: {user.github_username}")
        
        # Async create agent run
        agent_run = await client.create_agent_run(
            org_id=323,
            prompt="Create a simple async Python function",
            metadata={"demo": True, "type": "async"}
        )
        print(f"✅ Async agent run created: {agent_run.id}")

def demo_bulk_operations():
    """Demonstrate bulk operations"""
    print("\n⚡ Bulk Operations Demo")
    print("-" * 40)
    
    with CodegenClient() as client:
        # Create multiple agent runs in bulk
        run_configs = [
            {"prompt": "Create a sorting algorithm", "metadata": {"type": "sorting"}},
            {"prompt": "Create a search algorithm", "metadata": {"type": "search"}},
            {"prompt": "Create a data structure", "metadata": {"type": "data_structure"}}
        ]
        
        print("Creating multiple agent runs concurrently...")
        result = client.bulk_create_agent_runs(323, run_configs)
        
        print(f"✅ Bulk operation completed:")
        print(f"   - Total items: {result.total_items}")
        print(f"   - Successful: {result.successful_items}")
        print(f"   - Failed: {result.failed_items}")
        print(f"   - Success rate: {result.success_rate:.1%}")
        print(f"   - Duration: {result.duration_seconds:.2f}s")

def main():
    """Run all demos"""
    print("🚀 Enhanced Codegen API Client - Feature Demonstration")
    print("=" * 60)
    
    # Run synchronous demos
    demo_basic_usage()
    demo_configuration_presets()
    demo_caching_and_metrics()
    demo_webhook_handling()
    demo_bulk_operations()
    
    # Run async demo
    asyncio.run(demo_async_functionality())
    
    print("\n🎉 Demo completed! All features working correctly.")
    print("=" * 60)

if __name__ == "__main__":
    main()
