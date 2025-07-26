#!/usr/bin/env python3
"""
Integration test script for CodegenCICD Dashboard
Tests the complete flow with actual API keys
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/ws/test_client"
AUTH_TOKEN = "sk-demo-token"

class CodegenCICDTester:
    def __init__(self):
        self.session = None
        self.ws = None
        self.project_id = None
        self.agent_run_id = None
    
    async def setup(self):
        """Setup test session"""
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        print("✅ Test session initialized")
    
    async def cleanup(self):
        """Cleanup test resources"""
        if self.session:
            await self.session.close()
        print("✅ Test session cleaned up")
    
    async def test_health_check(self):
        """Test health check endpoint"""
        print("\n🔍 Testing health check...")
        
        async with self.session.get(f"{API_BASE_URL.replace('/api/v1', '')}/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Health check passed: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {resp.status}")
                return False
    
    async def test_create_project(self):
        """Test project creation"""
        print("\n🔍 Testing project creation...")
        
        project_data = {
            "name": "Test Project",
            "description": "Integration test project",
            "repository_url": "https://github.com/Zeeeepa/CodegenCICD",
            "default_branch": "main",
            "auto_merge_enabled": False
        }
        
        async with self.session.post(f"{API_BASE_URL}/projects", json=project_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.project_id = data["id"]
                print(f"✅ Project created: {data['name']} (ID: {self.project_id})")
                return True
            else:
                error = await resp.text()
                print(f"❌ Project creation failed: {resp.status} - {error}")
                return False
    
    async def test_update_project_configuration(self):
        """Test project configuration update"""
        print("\n🔍 Testing project configuration...")
        
        if not self.project_id:
            print("❌ No project ID available")
            return False
        
        config_data = {
            "repository_rules": "- Use TypeScript for all new code\n- Follow existing patterns",
            "setup_commands": "echo 'Setting up test environment'\nnpm install\nnpm run build",
            "planning_statement": "You are working on a test project. Follow best practices.",
            "secrets": {
                "TEST_API_KEY": "test-value-123",
                "ENVIRONMENT": "test"
            }
        }
        
        async with self.session.put(
            f"{API_BASE_URL}/projects/{self.project_id}/configuration", 
            json=config_data
        ) as resp:
            if resp.status == 200:
                print("✅ Project configuration updated")
                return True
            else:
                error = await resp.text()
                print(f"❌ Configuration update failed: {resp.status} - {error}")
                return False
    
    async def test_create_agent_run(self):
        """Test agent run creation"""
        print("\n🔍 Testing agent run creation...")
        
        if not self.project_id:
            print("❌ No project ID available")
            return False
        
        agent_run_data = {
            "project_id": self.project_id,
            "prompt": "Create a simple test function that returns 'Hello, World!'",
            "use_planning_statement": True
        }
        
        async with self.session.post(f"{API_BASE_URL}/agent-runs", json=agent_run_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.agent_run_id = data["id"]
                print(f"✅ Agent run created: {data['status']} (ID: {self.agent_run_id})")
                return True
            else:
                error = await resp.text()
                print(f"❌ Agent run creation failed: {resp.status} - {error}")
                return False
    
    async def test_monitor_agent_run(self):
        """Monitor agent run progress"""
        print("\n🔍 Monitoring agent run progress...")
        
        if not self.agent_run_id:
            print("❌ No agent run ID available")
            return False
        
        # Poll for completion (max 5 minutes)
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            async with self.session.get(f"{API_BASE_URL}/agent-runs/{self.agent_run_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data["status"]
                    
                    print(f"📊 Agent run status: {status}")
                    
                    if status == "completed":
                        print(f"✅ Agent run completed successfully")
                        if data.get("response_type"):
                            print(f"   Response type: {data['response_type']}")
                        if data.get("pr_url"):
                            print(f"   PR URL: {data['pr_url']}")
                        return True
                    elif status == "failed":
                        print(f"❌ Agent run failed: {data.get('response_content', 'Unknown error')}")
                        return False
                    elif status in ["pending", "running"]:
                        await asyncio.sleep(5)
                        attempt += 1
                    else:
                        print(f"❓ Unknown status: {status}")
                        return False
                else:
                    print(f"❌ Failed to get agent run status: {resp.status}")
                    return False
        
        print("⏰ Agent run monitoring timed out")
        return False
    
    async def test_list_projects(self):
        """Test project listing"""
        print("\n🔍 Testing project listing...")
        
        async with self.session.get(f"{API_BASE_URL}/projects") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Found {len(data)} projects")
                for project in data:
                    print(f"   - {project['name']} ({project['id']})")
                return True
            else:
                error = await resp.text()
                print(f"❌ Project listing failed: {resp.status} - {error}")
                return False
    
    async def test_list_agent_runs(self):
        """Test agent run listing"""
        print("\n🔍 Testing agent run listing...")
        
        async with self.session.get(f"{API_BASE_URL}/agent-runs") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Found {len(data)} agent runs")
                for run in data:
                    print(f"   - {run['prompt'][:50]}... ({run['status']})")
                return True
            else:
                error = await resp.text()
                print(f"❌ Agent run listing failed: {resp.status} - {error}")
                return False
    
    async def test_webhook_events(self):
        """Test webhook events listing"""
        print("\n🔍 Testing webhook events...")
        
        async with self.session.get(f"{API_BASE_URL}/webhooks/events") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Found {len(data)} webhook events")
                return True
            else:
                error = await resp.text()
                print(f"❌ Webhook events listing failed: {resp.status} - {error}")
                return False
    
    async def test_cleanup_project(self):
        """Clean up test project"""
        print("\n🔍 Cleaning up test project...")
        
        if not self.project_id:
            print("❌ No project ID to clean up")
            return True
        
        async with self.session.delete(f"{API_BASE_URL}/projects/{self.project_id}") as resp:
            if resp.status == 200:
                print("✅ Test project deleted")
                return True
            else:
                error = await resp.text()
                print(f"❌ Project deletion failed: {resp.status} - {error}")
                return False
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting CodegenCICD Integration Tests")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Create Project", self.test_create_project),
            ("Update Configuration", self.test_update_project_configuration),
            ("Create Agent Run", self.test_create_agent_run),
            ("Monitor Agent Run", self.test_monitor_agent_run),
            ("List Projects", self.test_list_projects),
            ("List Agent Runs", self.test_list_agent_runs),
            ("Webhook Events", self.test_webhook_events),
            ("Cleanup Project", self.test_cleanup_project),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {str(e)}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        passed = 0
        failed = 0
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\nTotal: {len(results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(results)*100):.1f}%")
        
        return failed == 0


async def main():
    """Main test runner"""
    tester = CodegenCICDTester()
    
    try:
        await tester.setup()
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed! System is working correctly.")
            exit(0)
        else:
            print("\n💥 Some tests failed. Check the output above.")
            exit(1)
    
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

