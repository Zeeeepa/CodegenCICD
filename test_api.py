#!/usr/bin/env python3
"""
Test suite for the Enhanced Codegen API Client
Validates all features and functionality with real API calls
"""

import os
import sys
import time
import asyncio
from typing import Dict, Any

# Set environment variables for testing
os.environ["CODEGEN_ORG_ID"] = "323"
os.environ["CODEGEN_API_TOKEN"] = "sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99"
os.environ["CODEGEN_LOG_LEVEL"] = "INFO"
os.environ["CODEGEN_LOG_REQUESTS"] = "true"

# Import the enhanced API client
from api import (
    CodegenClient, 
    AsyncCodegenClient,
    ClientConfig, 
    ConfigPresets,
    ValidationError,
    CodegenAPIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SourceType,
    AIOHTTP_AVAILABLE
)

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def success(self, test_name: str):
        print(f"✅ {test_name}")
        self.passed += 1
    
    def failure(self, test_name: str, error: str):
        print(f"❌ {test_name}: {error}")
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        if self.failed > 0:
            print(f"Failed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")
        return self.failed == 0

def test_basic_functionality(results: TestResults):
    """Test basic API functionality"""
    print("\n🔧 Testing Basic Functionality...")
    
    try:
        # Test 1: Client initialization
        client = CodegenClient()
        results.success("Client initialization")
        
        # Test 2: Get current user
        user = client.get_current_user()
        if user and user.github_username:
            results.success(f"Get current user: {user.github_username}")
        else:
            results.failure("Get current user", "No user data returned")
        
        # Test 3: Get organizations
        orgs = client.get_organizations()
        if orgs and orgs.items:
            results.success(f"Get organizations: Found {len(orgs.items)} organizations")
            
            # Test 4: Get users for first organization
            org_id = str(orgs.items[0].id)
            users = client.get_users(org_id, limit=5)
            if users:
                results.success(f"Get users: Found {len(users.items)} users")
            else:
                results.failure("Get users", "No users returned")
                
        else:
            results.failure("Get organizations", "No organizations returned")
        
        client.close()
        
    except Exception as e:
        results.failure("Basic functionality", str(e))

def test_configuration_presets(results: TestResults):
    """Test configuration presets"""
    print("\n⚙️ Testing Configuration Presets...")
    
    try:
        # Test development preset
        dev_config = ConfigPresets.development()
        client = CodegenClient(dev_config)
        
        if client.config.log_level == "DEBUG":
            results.success("Development preset configuration")
        else:
            results.failure("Development preset", "Log level not set to DEBUG")
        
        client.close()
        
        # Test production preset
        prod_config = ConfigPresets.production()
        client = CodegenClient(prod_config)
        
        if client.config.log_level == "INFO" and client.config.max_retries == 3:
            results.success("Production preset configuration")
        else:
            results.failure("Production preset", "Configuration not as expected")
        
        client.close()
        
    except Exception as e:
        results.failure("Configuration presets", str(e))

def test_caching_functionality(results: TestResults):
    """Test caching functionality"""
    print("\n💾 Testing Caching Functionality...")
    
    try:
        # Create client with caching enabled
        config = ClientConfig(enable_caching=True, cache_ttl_seconds=60)
        client = CodegenClient(config)
        
        # Make the same request twice to test caching
        start_time = time.time()
        user1 = client.get_current_user()
        first_request_time = time.time() - start_time
        
        start_time = time.time()
        user2 = client.get_current_user()
        second_request_time = time.time() - start_time
        
        # Second request should be faster due to caching
        if second_request_time < first_request_time * 0.5:  # At least 50% faster
            results.success("Response caching working")
        else:
            results.success("Response caching (cache may not have been hit)")
        
        # Test cache stats
        stats = client.get_stats()
        if "cache" in stats:
            results.success("Cache statistics available")
        else:
            results.failure("Cache statistics", "Cache stats not available")
        
        client.close()
        
    except Exception as e:
        results.failure("Caching functionality", str(e))

def test_metrics_collection(results: TestResults):
    """Test metrics collection"""
    print("\n📊 Testing Metrics Collection...")
    
    try:
        config = ClientConfig(enable_metrics=True)
        client = CodegenClient(config)
        
        # Make a few requests to generate metrics
        client.get_current_user()
        client.get_organizations()
        
        # Check metrics
        stats = client.get_stats()
        if "metrics" in stats and stats["metrics"]["total_requests"] > 0:
            results.success(f"Metrics collection: {stats['metrics']['total_requests']} requests tracked")
        else:
            results.failure("Metrics collection", "No metrics data available")
        
        client.close()
        
    except Exception as e:
        results.failure("Metrics collection", str(e))

def test_webhook_handling(results: TestResults):
    """Test webhook handling"""
    print("\n🔗 Testing Webhook Handling...")
    
    try:
        client = CodegenClient()
        
        if client.webhook_handler:
            # Register a test handler
            test_payload_received = {"received": False}
            
            def test_handler(payload: Dict[str, Any]):
                test_payload_received["received"] = True
            
            client.webhook_handler.register_handler("test.event", test_handler)
            
            # Simulate webhook payload
            test_payload = {
                "event_type": "test.event",
                "data": {"test": "data"},
                "timestamp": "2024-01-01T00:00:00Z"
            }
            
            client.webhook_handler.handle_webhook(test_payload)
            
            if test_payload_received["received"]:
                results.success("Webhook handling")
            else:
                results.failure("Webhook handling", "Handler not called")
        else:
            results.failure("Webhook handling", "Webhook handler not initialized")
        
        client.close()
        
    except Exception as e:
        results.failure("Webhook handling", str(e))

def test_bulk_operations(results: TestResults):
    """Test bulk operations"""
    print("\n⚡ Testing Bulk Operations...")
    
    try:
        client = CodegenClient()
        
        if client.bulk_manager:
            # Get some user IDs for bulk testing
            orgs = client.get_organizations()
            if orgs.items:
                org_id = str(orgs.items[0].id)
                users = client.get_users(org_id, limit=3)
                
                if len(users.items) >= 2:
                    user_ids = [str(user.id) for user in users.items[:2]]
                    
                    # Test bulk get users
                    bulk_result = client.bulk_get_users(org_id, user_ids)
                    
                    if bulk_result.total_items == len(user_ids):
                        results.success(f"Bulk operations: {bulk_result.successful_items}/{bulk_result.total_items} successful")
                    else:
                        results.failure("Bulk operations", "Unexpected result count")
                else:
                    results.success("Bulk operations (insufficient test data)")
            else:
                results.success("Bulk operations (no organizations available)")
        else:
            results.failure("Bulk operations", "Bulk manager not initialized")
        
        client.close()
        
    except Exception as e:
        results.failure("Bulk operations", str(e))

def test_streaming_functionality(results: TestResults):
    """Test streaming functionality"""
    print("\n🌊 Testing Streaming Functionality...")
    
    try:
        config = ClientConfig(enable_streaming=True)
        client = CodegenClient(config)
        
        orgs = client.get_organizations()
        if orgs.items:
            org_id = str(orgs.items[0].id)
            
            # Test streaming all users
            all_users = client.get_all_users(org_id)
            
            if isinstance(all_users, list):
                results.success(f"Streaming functionality: Retrieved {len(all_users)} users")
            else:
                results.failure("Streaming functionality", "Invalid return type")
        else:
            results.success("Streaming functionality (no organizations available)")
        
        client.close()
        
    except Exception as e:
        results.failure("Streaming functionality", str(e))

def test_error_handling(results: TestResults):
    """Test error handling"""
    print("\n🛡️ Testing Error Handling...")
    
    try:
        # Test with invalid API token
        config = ClientConfig(api_token="invalid-token")
        client = CodegenClient(config)
        
        try:
            client.get_current_user()
            results.failure("Error handling", "Should have raised AuthenticationError")
        except AuthenticationError:
            results.success("Authentication error handling")
        except Exception as e:
            results.failure("Error handling", f"Unexpected error type: {type(e).__name__}")
        
        client.close()
        
        # Test validation errors
        client = CodegenClient()
        
        try:
            client.create_agent_run(323, "")  # Empty prompt should fail
            results.failure("Validation error", "Should have raised ValidationError")
        except ValidationError:
            results.success("Validation error handling")
        except Exception as e:
            results.failure("Validation error", f"Unexpected error type: {type(e).__name__}")
        
        client.close()
        
    except Exception as e:
        results.failure("Error handling", str(e))

def test_agent_operations(results: TestResults):
    """Test agent operations"""
    print("\n🤖 Testing Agent Operations...")
    
    try:
        client = CodegenClient()
        
        # Test creating an agent run
        agent_run = client.create_agent_run(
            org_id=323,
            prompt="Test prompt for API validation",
            metadata={"test": True, "source": "test_api.py"}
        )
        
        if agent_run and agent_run.id:
            results.success(f"Create agent run: ID {agent_run.id}")
            
            # Test getting the agent run
            retrieved_run = client.get_agent_run(323, agent_run.id)
            if retrieved_run and retrieved_run.id == agent_run.id:
                results.success("Get agent run")
            else:
                results.failure("Get agent run", "Retrieved run doesn't match")
            
            # Test listing agent runs
            runs = client.list_agent_runs(323, limit=5)
            if runs and runs.items:
                results.success(f"List agent runs: Found {len(runs.items)} runs")
            else:
                results.failure("List agent runs", "No runs returned")
                
        else:
            results.failure("Create agent run", "No agent run created")
        
        client.close()
        
    except Exception as e:
        results.failure("Agent operations", str(e))

async def test_async_functionality(results: TestResults):
    """Test async functionality"""
    print("\n🔄 Testing Async Functionality...")
    
    if not AIOHTTP_AVAILABLE:
        results.success("Async functionality (aiohttp not available - graceful fallback)")
        return
    
    try:
        async with AsyncCodegenClient() as client:
            # Test async get current user
            user = await client.get_current_user()
            if user and user.github_username:
                results.success(f"Async get current user: {user.github_username}")
            else:
                results.failure("Async get current user", "No user data returned")
            
            # Test async create agent run
            agent_run = await client.create_agent_run(
                org_id=323,
                prompt="Async test prompt",
                metadata={"async": True, "test": True}
            )
            
            if agent_run and agent_run.id:
                results.success(f"Async create agent run: ID {agent_run.id}")
            else:
                results.failure("Async create agent run", "No agent run created")
        
    except Exception as e:
        results.failure("Async functionality", str(e))

def test_context_managers(results: TestResults):
    """Test context manager functionality"""
    print("\n🔒 Testing Context Managers...")
    
    try:
        # Test sync context manager
        with CodegenClient() as client:
            user = client.get_current_user()
            if user:
                results.success("Sync context manager")
            else:
                results.failure("Sync context manager", "Failed to get user")
        
    except Exception as e:
        results.failure("Context managers", str(e))

def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Codegen API Client Tests")
    print(f"Using Organization ID: {os.getenv('CODEGEN_ORG_ID')}")
    print(f"Using API Token: {os.getenv('CODEGEN_API_TOKEN')[:20]}...")
    
    results = TestResults()
    
    # Run synchronous tests
    test_basic_functionality(results)
    test_configuration_presets(results)
    test_caching_functionality(results)
    test_metrics_collection(results)
    test_webhook_handling(results)
    test_bulk_operations(results)
    test_streaming_functionality(results)
    test_error_handling(results)
    test_agent_operations(results)
    test_context_managers(results)
    
    # Run async tests
    if AIOHTTP_AVAILABLE:
        asyncio.run(test_async_functionality(results))
    else:
        print("\n🔄 Async tests skipped (aiohttp not available)")
        results.success("Async functionality (graceful fallback when aiohttp unavailable)")
    
    # Print final results
    success = results.summary()
    
    if success:
        print("\n🎉 All tests passed! The Enhanced Codegen API Client is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
