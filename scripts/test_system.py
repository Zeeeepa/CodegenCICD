#!/usr/bin/env python3
"""
System validation script for CodegenCICD Dashboard
Tests all components and integrations
"""
import asyncio
import sys
import os
import httpx
import structlog
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.config import get_settings
from backend.database import init_db, AsyncSessionLocal
from backend.integrations import CodegenClient, GitHubClient, GeminiClient, CloudflareClient, GrainchainClient, WebEvalClient

logger = structlog.get_logger(__name__)


class SystemValidator:
    """Validates all system components"""
    
    def __init__(self):
        self.settings = get_settings()
        self.results = {}
    
    async def run_all_tests(self):
        """Run all system validation tests"""
        print("🚀 Starting CodegenCICD System Validation")
        print("=" * 50)
        
        tests = [
            ("Database Connection", self.test_database),
            ("Codegen API", self.test_codegen_api),
            ("GitHub API", self.test_github_api),
            ("Gemini API", self.test_gemini_api),
            ("Cloudflare API", self.test_cloudflare_api),
            ("Grainchain Service", self.test_grainchain),
            ("Web-Eval-Agent", self.test_web_eval),
            ("FastAPI Application", self.test_fastapi_app),
            ("WebSocket Endpoint", self.test_websocket),
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...")
            try:
                result = await test_func()
                self.results[test_name] = {"status": "PASS" if result else "FAIL", "details": ""}
                print(f"✅ {test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                self.results[test_name] = {"status": "ERROR", "details": str(e)}
                print(f"❌ {test_name}: ERROR - {str(e)}")
        
        self.print_summary()
        return self.get_overall_status()
    
    async def test_database(self) -> bool:
        """Test database connection and initialization"""
        try:
            await init_db()
            
            async with AsyncSessionLocal() as session:
                result = await session.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error("Database test failed", error=str(e))
            return False
    
    async def test_codegen_api(self) -> bool:
        """Test Codegen API connectivity"""
        try:
            client = CodegenClient()
            return await client.health_check()
        except Exception as e:
            logger.error("Codegen API test failed", error=str(e))
            return False
    
    async def test_github_api(self) -> bool:
        """Test GitHub API connectivity"""
        try:
            client = GitHubClient()
            return await client.health_check()
        except Exception as e:
            logger.error("GitHub API test failed", error=str(e))
            return False
    
    async def test_gemini_api(self) -> bool:
        """Test Gemini API connectivity"""
        try:
            client = GeminiClient()
            return await client.health_check()
        except Exception as e:
            logger.error("Gemini API test failed", error=str(e))
            return False
    
    async def test_cloudflare_api(self) -> bool:
        """Test Cloudflare API connectivity"""
        try:
            client = CloudflareClient()
            return await client.health_check()
        except Exception as e:
            logger.error("Cloudflare API test failed", error=str(e))
            return False
    
    async def test_grainchain(self) -> bool:
        """Test Grainchain service connectivity"""
        try:
            client = GrainchainClient()
            return await client.health_check()
        except Exception as e:
            logger.error("Grainchain test failed", error=str(e))
            return False
    
    async def test_web_eval(self) -> bool:
        """Test Web-Eval-Agent service connectivity"""
        try:
            client = WebEvalClient()
            return await client.health_check()
        except Exception as e:
            logger.error("Web-Eval-Agent test failed", error=str(e))
            return False
    
    async def test_fastapi_app(self) -> bool:
        """Test FastAPI application"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health")
                return response.status_code == 200
        except Exception as e:
            logger.error("FastAPI app test failed", error=str(e))
            return False
    
    async def test_websocket(self) -> bool:
        """Test WebSocket endpoint"""
        try:
            import websockets
            
            uri = "ws://localhost:8000/ws/test-client"
            async with websockets.connect(uri) as websocket:
                # Send ping
                await websocket.send('{"type": "ping"}')
                
                # Wait for pong
                response = await websocket.recv()
                return "pong" in response
        except Exception as e:
            logger.error("WebSocket test failed", error=str(e))
            return False
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 50)
        print("📊 SYSTEM VALIDATION SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in self.results.values() if r["status"] == "PASS")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAIL")
        errors = sum(1 for r in self.results.values() if r["status"] == "ERROR")
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"🚨 Errors: {errors}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, result in self.results.items():
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "🚨"}[result["status"]]
            print(f"{status_icon} {test_name}: {result['status']}")
            if result["details"]:
                print(f"   Details: {result['details']}")
    
    def get_overall_status(self) -> bool:
        """Get overall system status"""
        critical_tests = [
            "Database Connection",
            "FastAPI Application"
        ]
        
        # Check if all critical tests passed
        for test_name in critical_tests:
            if test_name in self.results and self.results[test_name]["status"] != "PASS":
                return False
        
        # Check if majority of tests passed
        passed = sum(1 for r in self.results.values() if r["status"] == "PASS")
        total = len(self.results)
        
        return (passed / total) >= 0.7  # 70% pass rate required


async def main():
    """Main validation function"""
    validator = SystemValidator()
    
    try:
        success = await validator.run_all_tests()
        
        if success:
            print("\n🎉 System validation PASSED! CodegenCICD is ready for deployment.")
            sys.exit(0)
        else:
            print("\n⚠️  System validation FAILED! Please check the errors above.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

