#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced Codegen API client
Tests all major functionality with real API calls
"""

import os
import sys
import time
import asyncio
from typing import Dict, Any

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import (
    CodegenClient, 
    AsyncCodegenClient, 
    ConfigPresets,
    ValidationError,
    CodegenAPIError,
    RateLimitError,
    AuthenticationError,
    AIOHTTP_AVAILABLE
)

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"🧪 {title}")
    print('='*80)

def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n🔍 {title}")
    print('-'*60)

def test_basic_functionality():
    """Test basic API client functionality"""
    print_section("BASIC FUNCTIONALITY TESTS")
    
    try:
        with CodegenClient() as client:
            print_subsection("Health Check")
            health = client.health_check()
            print(f"✅ API Health: {health['status']}")
            print(f"⏱️  Response Time: {health['response_time_seconds']:.3f}s")
            
            print_subsection("Current User")
            user = client.get_current_user()
            print(f"👤 Username: {user.github_username}")
            print(f"📧 Email: {user.email or 'Not provided'}")
            print(f"🆔 User ID: {user.id}")
            print(f"🖼️  Avatar: {user.avatar_url or 'No avatar'}")
            
            print_subsection("Organizations")
            orgs = client.get_organizations()
            print(f"🏢 Total Organizations: {orgs.total}")
            for org in orgs.items[:3]:  # Show first 3
                print(f"   • {org.name} (ID: {org.id})")
            
            print_subsection("Users in Organization 323")
            users = client.get_users("323", limit=5)
            print(f"👥 Total Users: {users.total}")
            for user in users.items:
                print(f"   • {user.github_username} ({user.email or 'No email'})")
                
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")

def test_configuration_presets():
    """Test different configuration presets"""
    print_section("CONFIGURATION PRESETS TESTS")
    
    configs = {
        "Development": ConfigPresets.development(),
        "Production": ConfigPresets.production(), 
        "High Performance": ConfigPresets.high_performance(),
        "Testing": ConfigPresets.testing(),
    }
    
    for name, config in configs.items():
        print_subsection(f"{name} Configuration")
        print(f"⏱️  Timeout: {config.timeout}s")
        print(f"🔄 Max Retries: {config.max_retries}")
        print(f"🚦 Rate Limit: {config.rate_limit_requests_per_period}/min")
        print(f"💾 Cache TTL: {config.cache_ttl_seconds}s")
        print(f"📊 Log Level: {config.log_level}")
        print(f"🔧 Caching: {'✅' if config.enable_caching else '❌'}")
        print(f"🪝 Webhooks: {'✅' if config.enable_webhooks else '❌'}")
        print(f"📦 Bulk Ops: {'✅' if config.enable_bulk_operations else '❌'}")

def test_agent_operations():
    """Test agent run operations"""
    print_section("AGENT OPERATIONS TESTS")
    
    try:
        with CodegenClient(ConfigPresets.development()) as client:
            print_subsection("Creating Agent Run")
            
            # Create an agent run
            agent_run = client.create_agent_run(
                org_id=323,
                prompt="Write a simple Python function to calculate the factorial of a number",
                metadata={
                    "test_run": True,
                    "purpose": "comprehensive_testing",
                    "timestamp": time.time()
                }
            )
            
            print(f"✅ Created Agent Run:")
            print(f"   🆔 ID: {agent_run.id}")
            print(f"   📊 Status: {agent_run.status}")
            print(f"   🌐 Web URL: {agent_run.web_url}")
            print(f"   📅 Created: {agent_run.created_at}")
            
            print_subsection("Retrieving Agent Run")
            retrieved_run = client.get_agent_run(323, agent_run.id)
            print(f"✅ Retrieved Agent Run {retrieved_run.id}")
            print(f"   📊 Status: {retrieved_run.status}")
            print(f"   🔄 Source: {retrieved_run.source_type}")
            
            # Wait a bit and check again
            print_subsection("Monitoring Progress")
            time.sleep(3)
            updated_run = client.get_agent_run(323, agent_run.id)
            print(f"📊 Updated Status: {updated_run.status}")
            
            if updated_run.result:
                print(f"📝 Result Preview: {updated_run.result[:200]}...")
            
            return agent_run.id
            
    except Exception as e:
        print(f"❌ Agent operations test failed: {e}")
        return None

def test_advanced_features():
    """Test advanced client features"""
    print_section("ADVANCED FEATURES TESTS")
    
    try:
        config = ConfigPresets.production()
        with CodegenClient(config) as client:
            print_subsection("Client Statistics")
            stats = client.get_stats()
            
            print("📊 Configuration:")
            for key, value in stats["config"].items():
                print(f"   {key}: {value}")
            
            print_subsection("Cache Statistics")
            if client.cache:
                cache_stats = client.cache.get_stats()
                print(f"💾 Cache Size: {cache_stats['size']}/{cache_stats['max_size']}")
                print(f"🎯 Hit Rate: {cache_stats['hit_rate_percentage']:.1f}%")
                print(f"⏱️  TTL: {cache_stats['ttl_seconds']}s")
                print(f"✅ Hits: {cache_stats['hits']}")
                print(f"❌ Misses: {cache_stats['misses']}")
            
            print_subsection("Rate Limiter Status")
            rate_usage = client.rate_limiter.get_current_usage()
            print(f"🚦 Current Usage: {rate_usage['current_requests']}/{rate_usage['max_requests']}")
            print(f"📊 Usage Percentage: {rate_usage['usage_percentage']:.1f}%")
            print(f"⏱️  Period: {rate_usage['period_seconds']}s")
            
    except Exception as e:
        print(f"❌ Advanced features test failed: {e}")

def test_error_handling():
    """Test comprehensive error handling"""
    print_section("ERROR HANDLING TESTS")
    
    error_scenarios = [
        ("Empty prompt", lambda c: c.create_agent_run(323, "")),
        ("Oversized prompt", lambda c: c.create_agent_run(323, "x" * 60000)),
        ("Invalid pagination (negative skip)", lambda c: c.get_users("323", skip=-1)),
        ("Invalid pagination (large limit)", lambda c: c.get_users("323", limit=200)),
        ("Invalid organization ID", lambda c: c.get_users("-999")),
    ]
    
    with CodegenClient() as client:
        for scenario_name, scenario_func in error_scenarios:
            print_subsection(f"Testing: {scenario_name}")
            try:
                result = scenario_func(client)
                print(f"   ❌ Expected error but got result: {result}")
            except ValidationError as e:
                print(f"   ✅ Validation Error: {e.message}")
            except CodegenAPIError as e:
                print(f"   ✅ API Error: {e.message} (Status: {e.status_code})")
            except Exception as e:
                print(f"   ⚠️  Unexpected Error: {type(e).__name__}: {e}")

def test_streaming_operations():
    """Test streaming functionality"""
    print_section("STREAMING OPERATIONS TESTS")
    
    try:
        with CodegenClient() as client:
            print_subsection("Streaming Users")
            print("🌊 Streaming first 5 users:")
            
            count = 0
            for user in client.stream_all_users("323"):
                count += 1
                print(f"   {count}. {user.github_username} ({user.email or 'No email'})")
                if count >= 5:
                    print("   ... (truncated)")
                    break
            
            print(f"✅ Successfully streamed {count} users")
            
    except Exception as e:
        print(f"❌ Streaming operations test failed: {e}")

async def test_async_functionality():
    """Test async client functionality"""
    print_section("ASYNC CLIENT TESTS")
    
    if not AIOHTTP_AVAILABLE:
        print("❌ aiohttp not available - skipping async tests")
        return
    
    try:
        async with AsyncCodegenClient() as client:
            print_subsection("Async Current User")
            user = await client.get_current_user()
            print(f"👤 Async User: {user.github_username}")
            
            print_subsection("Async Agent Run Creation")
            run = await client.create_agent_run(
                org_id=323,
                prompt="Create a simple async function example in Python",
                metadata={"async_test": True}
            )
            print(f"🚀 Async Agent Run Created: {run.id}")
            print(f"📊 Status: {run.status}")
            
            print_subsection("Async Agent Run Retrieval")
            retrieved = await client.get_agent_run(323, run.id)
            print(f"✅ Retrieved Async Run: {retrieved.id}")
            print(f"📊 Status: {retrieved.status}")
            
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")

def test_performance_metrics():
    """Test performance and timing"""
    print_section("PERFORMANCE METRICS TESTS")
    
    try:
        with CodegenClient(ConfigPresets.high_performance()) as client:
            print_subsection("Performance Timing")
            
            # Time multiple requests
            start_time = time.time()
            
            # Make several requests
            user = client.get_current_user()
            orgs = client.get_organizations()
            users = client.get_users("323", limit=10)
            
            total_time = time.time() - start_time
            
            print(f"⏱️  Total Time for 3 requests: {total_time:.3f}s")
            print(f"📊 Average per request: {total_time/3:.3f}s")
            
            # Test caching performance
            print_subsection("Cache Performance")
            
            # First request (cache miss)
            start_time = time.time()
            user1 = client.get_current_user()
            first_request_time = time.time() - start_time
            
            # Second request (should be cached)
            start_time = time.time()
            user2 = client.get_current_user()
            second_request_time = time.time() - start_time
            
            print(f"🔄 First request: {first_request_time:.3f}s")
            print(f"⚡ Second request: {second_request_time:.3f}s")
            
            if second_request_time < first_request_time:
                print("✅ Caching appears to be working!")
            else:
                print("⚠️  Caching may not be working as expected")
                
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")

def main():
    """Run comprehensive tests"""
    print("🚀 COMPREHENSIVE CODEGEN API CLIENT TESTING")
    print(f"📅 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check environment variables
    api_token = os.getenv('CODEGEN_API_TOKEN')
    org_id = os.getenv('CODEGEN_ORG_ID')
    
    if not api_token or not org_id:
        print("❌ Missing required environment variables:")
        print("   CODEGEN_API_TOKEN and CODEGEN_ORG_ID must be set")
        return
    
    print(f"🔑 Using API Token: {api_token[:20]}...")
    print(f"🏢 Using Organization ID: {org_id}")
    
    # Run all tests
    test_basic_functionality()
    test_configuration_presets()
    agent_run_id = test_agent_operations()
    test_advanced_features()
    test_error_handling()
    test_streaming_operations()
    test_performance_metrics()
    
    # Run async tests
    if AIOHTTP_AVAILABLE:
        asyncio.run(test_async_functionality())
    else:
        print("\n❌ Skipping async tests - aiohttp not available")
    
    print_section("TEST SUMMARY")
    print("✅ Comprehensive testing completed!")
    print(f"📅 Finished at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if agent_run_id:
        print(f"🔗 Created test agent run: {agent_run_id}")
        print("   You can check its progress in the Codegen web interface")

if __name__ == "__main__":
    main()

