import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
import json
import subprocess
import os
import tempfile
import shutil

class WebEvalAgentClient:
    """Client for Web-Eval-Agent service for comprehensive UI testing."""
    
    def __init__(self, base_url: str = None, gemini_api_key: str = None):
        self.base_url = base_url or "http://localhost:8003"
        self.gemini_api_key = gemini_api_key
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
        if gemini_api_key:
            self.headers["Authorization"] = f"Bearer {gemini_api_key}"
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Web-Eval-Agent service."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return {
                            "success": True,
                            "status": health_data.get("status", "healthy"),
                            "version": health_data.get("version", "unknown")
                        }
                    else:
                        raise Exception(f"Health check failed: {response.status}")
        except Exception as e:
            raise Exception(f"Web-Eval-Agent connection failed: {str(e)}")
    
    async def run_comprehensive_test(
        self, 
        base_url: str, 
        test_scenarios: List[str] = None
    ) -> Dict[str, Any]:
        """Run comprehensive UI testing on the application."""
        
        if test_scenarios is None:
            test_scenarios = [
                "homepage_functionality",
                "navigation_testing", 
                "form_validation",
                "responsive_design",
                "accessibility_check",
                "performance_test",
                "component_interaction",
                "error_handling",
                "data_persistence",
                "user_workflow"
            ]
        
        test_config = {
            "base_url": base_url,
            "scenarios": test_scenarios,
            "browser": "chromium",
            "headless": True,
            "timeout": 30000,
            "viewport": {"width": 1920, "height": 1080},
            "gemini_api_key": self.gemini_api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/test/comprehensive",
                    headers=self.headers,
                    json=test_config,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
                ) as response:
                    if response.status == 200:
                        test_results = await response.json()
                        return self._process_test_results(test_results)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Comprehensive test failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_results": [],
                "overall_score": 0
            }
    
    async def test_specific_component(
        self, 
        base_url: str, 
        component_selector: str,
        test_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Test a specific UI component."""
        
        test_config = {
            "base_url": base_url,
            "component_selector": component_selector,
            "actions": test_actions,
            "gemini_api_key": self.gemini_api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/test/component",
                    headers=self.headers,
                    json=test_config,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Component test failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "component_working": False
            }
    
    async def analyze_deployment(self, logs: List[str], context: str) -> Dict[str, Any]:
        """Analyze deployment logs using Gemini API."""
        
        analysis_config = {
            "logs": logs,
            "context": context,
            "analysis_type": "deployment_validation",
            "gemini_api_key": self.gemini_api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/analyze/deployment",
                    headers=self.headers,
                    json=analysis_config,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        analysis_result = await response.json()
                        return {
                            "deployment_successful": analysis_result.get("deployment_successful", False),
                            "confidence": analysis_result.get("confidence", 0),
                            "reason": analysis_result.get("reason", "Unknown"),
                            "recommendations": analysis_result.get("recommendations", [])
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Deployment analysis failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "deployment_successful": False,
                "confidence": 0,
                "reason": f"Analysis failed: {str(e)}",
                "recommendations": ["Check deployment logs manually"]
            }
    
    async def test_user_workflow(
        self, 
        base_url: str, 
        workflow_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Test a complete user workflow."""
        
        workflow_config = {
            "base_url": base_url,
            "workflow_steps": workflow_steps,
            "gemini_api_key": self.gemini_api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/test/workflow",
                    headers=self.headers,
                    json=workflow_config,
                    timeout=aiohttp.ClientTimeout(total=180)  # 3 minutes
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Workflow test failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workflow_completed": False,
                "failed_step": "unknown"
            }
    
    async def capture_screenshot(self, base_url: str, selector: str = None) -> Dict[str, Any]:
        """Capture screenshot of the application."""
        
        screenshot_config = {
            "base_url": base_url,
            "selector": selector,
            "full_page": selector is None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/screenshot",
                    headers=self.headers,
                    json=screenshot_config,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Screenshot capture failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "screenshot_url": None
            }
    
    def _process_test_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format test results."""
        
        test_results = raw_results.get("test_results", [])
        passed_tests = [t for t in test_results if t.get("passed", False)]
        failed_tests = [t for t in test_results if not t.get("passed", False)]
        
        # Calculate overall score
        if test_results:
            overall_score = (len(passed_tests) / len(test_results)) * 100
        else:
            overall_score = 0
        
        # Categorize results
        critical_failures = [t for t in failed_tests if t.get("severity") == "critical"]
        warnings = [t for t in test_results if t.get("severity") == "warning"]
        
        return {
            "success": len(critical_failures) == 0,
            "overall_score": round(overall_score, 2),
            "total_tests": len(test_results),
            "passed_tests": len(passed_tests),
            "failed_tests": len(failed_tests),
            "critical_failures": len(critical_failures),
            "warnings": len(warnings),
            "test_results": test_results,
            "summary": {
                "homepage_functional": any(t.get("name") == "homepage_functionality" and t.get("passed") for t in test_results),
                "navigation_working": any(t.get("name") == "navigation_testing" and t.get("passed") for t in test_results),
                "forms_validated": any(t.get("name") == "form_validation" and t.get("passed") for t in test_results),
                "responsive_design": any(t.get("name") == "responsive_design" and t.get("passed") for t in test_results),
                "accessibility_compliant": any(t.get("name") == "accessibility_check" and t.get("passed") for t in test_results),
                "performance_acceptable": any(t.get("name") == "performance_test" and t.get("passed") for t in test_results)
            },
            "recommendations": self._generate_recommendations(failed_tests),
            "timestamp": raw_results.get("timestamp"),
            "duration": raw_results.get("duration", 0)
        }
    
    def _generate_recommendations(self, failed_tests: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on failed tests."""
        recommendations = []
        
        for test in failed_tests:
            test_name = test.get("name", "unknown")
            error_message = test.get("error", "")
            
            if "homepage" in test_name:
                recommendations.append("Check homepage loading and basic functionality")
            elif "navigation" in test_name:
                recommendations.append("Verify navigation links and menu functionality")
            elif "form" in test_name:
                recommendations.append("Review form validation and submission handling")
            elif "responsive" in test_name:
                recommendations.append("Test responsive design across different screen sizes")
            elif "accessibility" in test_name:
                recommendations.append("Improve accessibility compliance (ARIA labels, keyboard navigation)")
            elif "performance" in test_name:
                recommendations.append("Optimize application performance (loading times, resource usage)")
            else:
                recommendations.append(f"Address issue in {test_name}: {error_message}")
        
        return list(set(recommendations))  # Remove duplicates

# Deployment functions for Web-Eval-Agent
async def deploy_web_eval_agent(gemini_api_key: str, port: int = 8003) -> Dict[str, Any]:
    """Deploy Web-Eval-Agent service locally."""
    
    try:
        # Clone the repository if it doesn't exist
        repo_dir = "/tmp/web-eval-agent"
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        
        # Clone the repository
        clone_result = subprocess.run([
            "git", "clone", "https://github.com/Zeeeepa/web-eval-agent.git", repo_dir
        ], capture_output=True, text=True, timeout=60)
        
        if clone_result.returncode != 0:
            raise Exception(f"Failed to clone web-eval-agent: {clone_result.stderr}")
        
        # Install dependencies
        install_result = subprocess.run([
            "npm", "install"
        ], cwd=repo_dir, capture_output=True, text=True, timeout=300)
        
        if install_result.returncode != 0:
            raise Exception(f"Failed to install dependencies: {install_result.stderr}")
        
        # Create environment file
        env_content = f"""
GEMINI_API_KEY={gemini_api_key}
PORT={port}
NODE_ENV=production
"""
        
        with open(os.path.join(repo_dir, ".env"), "w") as f:
            f.write(env_content)
        
        # Start the service in background
        start_result = subprocess.Popen([
            "npm", "start"
        ], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for the service to start
        await asyncio.sleep(5)
        
        # Test if service is running
        client = WebEvalAgentClient(f"http://localhost:{port}", gemini_api_key)
        try:
            await client.test_connection()
            return {
                "success": True,
                "service_url": f"http://localhost:{port}",
                "process_id": start_result.pid,
                "message": "Web-Eval-Agent deployed successfully"
            }
        except Exception as e:
            start_result.terminate()
            raise Exception(f"Service deployment failed: {str(e)}")
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to deploy Web-Eval-Agent"
        }

