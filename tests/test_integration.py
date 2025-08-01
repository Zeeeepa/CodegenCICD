#!/usr/bin/env python3
"""
Integration test script for CodegenCICD Dashboard
Tests all key endpoints and functionality
"""
import asyncio
import json
import sys
import time
from pathlib import Path
import subprocess
import requests
import signal
import os

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class IntegrationTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.server_process = None
        
    def start_server(self):
        """Start the FastAPI server"""
        print("Starting FastAPI server...")
        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite+aiosqlite:///./codegencd.db"
        
        self.server_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd="backend",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(5)
        print("Server started!")
        
    def stop_server(self):
        """Stop the FastAPI server"""
        if self.server_process:
            print("Stopping server...")
            self.server_process.terminate()
            self.server_process.wait()
            print("Server stopped!")
    
    def test_endpoint(self, endpoint, method="GET", data=None, expected_status=200):
        """Test a single endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"Testing {method} {endpoint}...")
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == expected_status:
                print(f"✅ {endpoint} - Status: {response.status_code}")
                return True, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            else:
                print(f"❌ {endpoint} - Expected: {expected_status}, Got: {response.status_code}")
                return False, response.text
                
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
            return False, str(e)
    
    def run_tests(self):
        """Run all integration tests"""
        print("🚀 Starting CodegenCICD Integration Tests")
        print("=" * 50)
        
        results = []
        
        # Test basic endpoints
        test_cases = [
            # Basic API endpoints
            ("/", "GET", None, 200),
            ("/health", "GET", None, 200),
            ("/health/detailed", "GET", None, 200),
            
            # API endpoints
            ("/api/projects", "GET", None, 200),
            ("/api/github-repos", "GET", None, 200),
            ("/api/agent-runs", "GET", None, 200),
            
            # Frontend serving
            ("/dashboard", "GET", None, 200),
            
            # Monitoring endpoints
            ("/metrics", "GET", None, 200),
        ]
        
        for endpoint, method, data, expected_status in test_cases:
            success, response = self.test_endpoint(endpoint, method, data, expected_status)
            results.append((endpoint, success))
        
        # Test POST endpoints
        print("\nTesting POST endpoints...")
        
        # Test project creation
        project_data = {
            "name": "Test Project",
            "github_owner": "testuser",
            "github_repo": "testrepo",
            "auto_merge_enabled": False,
            "auto_confirm_plans": True
        }
        success, response = self.test_endpoint("/api/projects", "POST", project_data, 200)
        results.append(("/api/projects (POST)", success))
        
        # Test agent run creation
        agent_run_data = {
            "project_id": 1,
            "target_text": "Create a test component",
            "planning_statement": "Focus on React best practices"
        }
        success, response = self.test_endpoint("/api/agent-runs", "POST", agent_run_data, 200)
        results.append(("/api/agent-runs (POST)", success))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for endpoint, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {endpoint}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! The application is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the logs above for details.")
            return False

def main():
    """Main function"""
    tester = IntegrationTester()
    
    try:
        tester.start_server()
        success = tester.run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        sys.exit(1)
    finally:
        tester.stop_server()

if __name__ == "__main__":
    main()
