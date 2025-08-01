#!/usr/bin/env python3
"""
Web-Eval-Agent Deployment and Testing Script
Deploys Web-Eval-Agent and runs comprehensive tests on the CodegenCICD dashboard
"""
import asyncio
import json
import subprocess
import time
import httpx
import structlog
from typing import Dict, Any, List
import os

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
GEMINI_API_KEY = "AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0"
WEB_EVAL_AGENT_PORT = 8003
DASHBOARD_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"

class WebEvalDeployment:
    """Handles Web-Eval-Agent deployment and testing"""
    
    def __init__(self):
        self.web_eval_url = f"http://localhost:{WEB_EVAL_AGENT_PORT}"
        self.container_name = "web-eval-agent-test"
    
    async def deploy_web_eval_agent(self) -> bool:
        """Deploy Web-Eval-Agent using Docker"""
        try:
            logger.info("Deploying Web-Eval-Agent container")
            
            # Stop existing container if running
            subprocess.run([
                "docker", "stop", self.container_name
            ], capture_output=True)
            
            subprocess.run([
                "docker", "rm", self.container_name
            ], capture_output=True)
            
            # Deploy new container
            cmd = [
                "docker", "run", "-d",
                "--name", self.container_name,
                "-p", f"{WEB_EVAL_AGENT_PORT}:8000",
                "-e", f"GEMINI_API_KEY={GEMINI_API_KEY}",
                "-e", "PYTHONUNBUFFERED=1",
                "zeeeepa/web-eval-agent:latest"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error("Failed to deploy Web-Eval-Agent", 
                           error=result.stderr,
                           stdout=result.stdout)
                return False
            
            logger.info("Web-Eval-Agent container deployed", 
                       container_id=result.stdout.strip()[:12])
            
            # Wait for service to be ready
            await self.wait_for_service()
            return True
            
        except Exception as e:
            logger.error("Web-Eval-Agent deployment failed", error=str(e))
            return False
    
    async def wait_for_service(self, max_attempts: int = 30) -> bool:
        """Wait for Web-Eval-Agent service to be ready"""
        logger.info("Waiting for Web-Eval-Agent service to be ready")
        
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.web_eval_url}/health")
                    if response.status_code == 200:
                        logger.info("Web-Eval-Agent service is ready")
                        return True
            except Exception:
                pass
            
            logger.info(f"Waiting for service... attempt {attempt + 1}/{max_attempts}")
            await asyncio.sleep(2)
        
        logger.error("Web-Eval-Agent service failed to start")
        return False
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on the CodegenCICD dashboard"""
        try:
            logger.info("Starting comprehensive dashboard tests")
            
            test_scenarios = [
                {
                    "name": "Homepage Load Test",
                    "description": "Test dashboard homepage loading and basic elements",
                    "actions": [
                        {"type": "navigate", "url": DASHBOARD_URL},
                        {"type": "wait", "selector": "[data-testid='dashboard-header']", "timeout": 10},
                        {"type": "check_element", "selector": "h1", "expected_text": "CodegenCICD Dashboard"},
                        {"type": "check_element", "selector": "[data-testid='project-selector']"},
                        {"type": "screenshot", "name": "homepage_loaded"}
                    ]
                },
                {
                    "name": "Project Selector Test",
                    "description": "Test GitHub project selector dropdown functionality",
                    "actions": [
                        {"type": "navigate", "url": DASHBOARD_URL},
                        {"type": "wait", "selector": "[data-testid='project-selector']", "timeout": 10},
                        {"type": "click", "selector": "[data-testid='project-selector']"},
                        {"type": "wait", "selector": "[data-testid='project-dropdown']", "timeout": 5},
                        {"type": "check_element", "selector": "[data-testid='project-dropdown']"},
                        {"type": "screenshot", "name": "project_selector_open"}
                    ]
                },
                {
                    "name": "Project Card Test",
                    "description": "Test project card functionality and buttons",
                    "actions": [
                        {"type": "navigate", "url": DASHBOARD_URL},
                        {"type": "wait", "selector": "[data-testid='project-card']", "timeout": 10},
                        {"type": "check_element", "selector": "[data-testid='run-button']"},
                        {"type": "check_element", "selector": "[data-testid='settings-button']"},
                        {"type": "screenshot", "name": "project_card_visible"}
                    ]
                },
                {
                    "name": "Agent Run Dialog Test",
                    "description": "Test agent run dialog opening and functionality",
                    "actions": [
                        {"type": "navigate", "url": DASHBOARD_URL},
                        {"type": "wait", "selector": "[data-testid='run-button']", "timeout": 10},
                        {"type": "click", "selector": "[data-testid='run-button']"},
                        {"type": "wait", "selector": "[data-testid='agent-run-dialog']", "timeout": 5},
                        {"type": "check_element", "selector": "[data-testid='target-text-input']"},
                        {"type": "check_element", "selector": "[data-testid='confirm-button']"},
                        {"type": "screenshot", "name": "agent_run_dialog_open"}
                    ]
                },
                {
                    "name": "Project Settings Dialog Test",
                    "description": "Test project settings dialog with all tabs",
                    "actions": [
                        {"type": "navigate", "url": DASHBOARD_URL},
                        {"type": "wait", "selector": "[data-testid='settings-button']", "timeout": 10},
                        {"type": "click", "selector": "[data-testid='settings-button']"},
                        {"type": "wait", "selector": "[data-testid='settings-dialog']", "timeout": 5},
                        {"type": "check_element", "selector": "[data-testid='general-tab']"},
                        {"type": "check_element", "selector": "[data-testid='planning-tab']"},
                        {"type": "check_element", "selector": "[data-testid='rules-tab']"},
                        {"type": "check_element", "selector": "[data-testid='commands-tab']"},
                        {"type": "check_element", "selector": "[data-testid='secrets-tab']"},
                        {"type": "screenshot", "name": "settings_dialog_open"}
                    ]
                },
                {
                    "name": "Responsive Design Test",
                    "description": "Test responsive design on different screen sizes",
                    "actions": [
                        {"type": "navigate", "url": DASHBOARD_URL},
                        {"type": "set_viewport", "width": 1920, "height": 1080},
                        {"type": "screenshot", "name": "desktop_view"},
                        {"type": "set_viewport", "width": 768, "height": 1024},
                        {"type": "screenshot", "name": "tablet_view"},
                        {"type": "set_viewport", "width": 375, "height": 667},
                        {"type": "screenshot", "name": "mobile_view"}
                    ]
                },
                {
                    "name": "API Connectivity Test",
                    "description": "Test backend API connectivity",
                    "actions": [
                        {"type": "api_call", "url": f"{BACKEND_URL}/health", "method": "GET"},
                        {"type": "api_call", "url": f"{BACKEND_URL}/api/projects/github-repos", "method": "GET"},
                        {"type": "api_call", "url": f"{BACKEND_URL}/api/validation/services", "method": "GET"}
                    ]
                },
                {
                    "name": "Performance Test",
                    "description": "Test page load performance and Core Web Vitals",
                    "actions": [
                        {"type": "navigate", "url": DASHBOARD_URL},
                        {"type": "measure_performance"},
                        {"type": "check_lighthouse_score", "min_performance": 80},
                        {"type": "check_lighthouse_score", "min_accessibility": 90}
                    ]
                }
            ]
            
            # Run tests via Web-Eval-Agent API
            async with httpx.AsyncClient(timeout=300) as client:
                test_payload = {
                    "base_url": DASHBOARD_URL,
                    "gemini_api_key": GEMINI_API_KEY,
                    "scenarios": test_scenarios,
                    "browser_config": {
                        "headless": True,
                        "viewport": {"width": 1920, "height": 1080},
                        "user_agent": "CodegenCICD-Test-Agent/1.0"
                    }
                }
                
                logger.info("Sending test request to Web-Eval-Agent")
                response = await client.post(
                    f"{self.web_eval_url}/api/test/comprehensive",
                    json=test_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    logger.info("Comprehensive tests completed", 
                               total_scenarios=results.get("total_scenarios"),
                               passed=results.get("passed_scenarios"),
                               failed=results.get("failed_scenarios"))
                    return results
                else:
                    logger.error("Test execution failed", 
                               status_code=response.status_code,
                               response=response.text)
                    return {"error": f"HTTP {response.status_code}: {response.text}"}
                    
        except Exception as e:
            logger.error("Comprehensive testing failed", error=str(e))
            return {"error": str(e)}
    
    async def run_component_specific_tests(self) -> Dict[str, Any]:
        """Run tests specific to each component"""
        try:
            logger.info("Running component-specific tests")
            
            component_tests = {
                "dashboard": await self.test_dashboard_component(),
                "project_cards": await self.test_project_cards(),
                "agent_run_dialog": await self.test_agent_run_dialog(),
                "settings_dialog": await self.test_settings_dialog(),
                "validation_pipeline": await self.test_validation_pipeline()
            }
            
            return component_tests
            
        except Exception as e:
            logger.error("Component testing failed", error=str(e))
            return {"error": str(e)}
    
    async def test_dashboard_component(self) -> Dict[str, Any]:
        """Test the main dashboard component"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                test_payload = {
                    "url": DASHBOARD_URL,
                    "gemini_api_key": GEMINI_API_KEY,
                    "test_type": "component",
                    "component": "dashboard",
                    "checks": [
                        "header_present",
                        "project_selector_visible",
                        "navigation_functional",
                        "responsive_layout"
                    ]
                }
                
                response = await client.post(
                    f"{self.web_eval_url}/api/test/component",
                    json=test_payload
                )
                
                return response.json() if response.status_code == 200 else {"error": response.text}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def test_project_cards(self) -> Dict[str, Any]:
        """Test project card functionality"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                test_payload = {
                    "url": DASHBOARD_URL,
                    "gemini_api_key": GEMINI_API_KEY,
                    "test_type": "component",
                    "component": "project_cards",
                    "checks": [
                        "cards_render",
                        "run_button_functional",
                        "settings_button_functional",
                        "status_indicators_visible"
                    ]
                }
                
                response = await client.post(
                    f"{self.web_eval_url}/api/test/component",
                    json=test_payload
                )
                
                return response.json() if response.status_code == 200 else {"error": response.text}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def test_agent_run_dialog(self) -> Dict[str, Any]:
        """Test agent run dialog functionality"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                test_payload = {
                    "url": DASHBOARD_URL,
                    "gemini_api_key": GEMINI_API_KEY,
                    "test_type": "component",
                    "component": "agent_run_dialog",
                    "checks": [
                        "dialog_opens",
                        "target_input_functional",
                        "confirm_button_works",
                        "response_handling"
                    ]
                }
                
                response = await client.post(
                    f"{self.web_eval_url}/api/test/component",
                    json=test_payload
                )
                
                return response.json() if response.status_code == 200 else {"error": response.text}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def test_settings_dialog(self) -> Dict[str, Any]:
        """Test project settings dialog with all tabs"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                test_payload = {
                    "url": DASHBOARD_URL,
                    "gemini_api_key": GEMINI_API_KEY,
                    "test_type": "component",
                    "component": "settings_dialog",
                    "checks": [
                        "dialog_opens",
                        "all_tabs_present",
                        "tab_switching_works",
                        "form_inputs_functional",
                        "save_functionality"
                    ]
                }
                
                response = await client.post(
                    f"{self.web_eval_url}/api/test/component",
                    json=test_payload
                )
                
                return response.json() if response.status_code == 200 else {"error": response.text}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def test_validation_pipeline(self) -> Dict[str, Any]:
        """Test validation pipeline functionality"""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                test_payload = {
                    "url": f"{BACKEND_URL}/api/validation/pipeline/test",
                    "gemini_api_key": GEMINI_API_KEY,
                    "test_type": "api",
                    "component": "validation_pipeline",
                    "checks": [
                        "pipeline_starts",
                        "services_respond",
                        "error_handling",
                        "status_updates"
                    ]
                }
                
                response = await client.post(
                    f"{self.web_eval_url}/api/test/api",
                    json=test_payload
                )
                
                return response.json() if response.status_code == 200 else {"error": response.text}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive test report"""
        try:
            report = []
            report.append("# CodegenCICD Dashboard - Web-Eval-Agent Test Report")
            report.append(f"Generated: {datetime.now().isoformat()}")
            report.append("")
            
            # Overall summary
            if "overall_status" in results:
                report.append(f"## Overall Status: {results['overall_status'].upper()}")
                report.append(f"- Total Scenarios: {results.get('total_scenarios', 0)}")
                report.append(f"- Passed: {results.get('passed_scenarios', 0)}")
                report.append(f"- Failed: {results.get('failed_scenarios', 0)}")
                report.append("")
            
            # Detailed results
            if "results" in results:
                report.append("## Test Results")
                for i, result in enumerate(results["results"]):
                    report.append(f"### {i+1}. {result.get('name', 'Unknown Test')}")
                    report.append(f"Status: {result.get('status', 'unknown').upper()}")
                    report.append(f"Duration: {result.get('duration', 0):.2f}s")
                    
                    if result.get("error"):
                        report.append(f"Error: {result['error']}")
                    
                    if result.get("screenshots"):
                        report.append("Screenshots:")
                        for screenshot in result["screenshots"]:
                            report.append(f"- {screenshot}")
                    
                    report.append("")
            
            # Component-specific results
            if "dashboard" in results:
                report.append("## Component Test Results")
                for component, result in results.items():
                    if isinstance(result, dict) and "status" in result:
                        report.append(f"### {component.title()}")
                        report.append(f"Status: {result.get('status', 'unknown').upper()}")
                        if result.get("details"):
                            report.append(f"Details: {result['details']}")
                        report.append("")
            
            report_content = "\n".join(report)
            
            # Save report to file
            with open("web_eval_test_report.md", "w") as f:
                f.write(report_content)
            
            logger.info("Test report generated", file="web_eval_test_report.md")
            return report_content
            
        except Exception as e:
            logger.error("Failed to generate test report", error=str(e))
            return f"Error generating report: {str(e)}"
    
    async def cleanup(self):
        """Clean up deployed resources"""
        try:
            logger.info("Cleaning up Web-Eval-Agent container")
            subprocess.run([
                "docker", "stop", self.container_name
            ], capture_output=True)
            
            subprocess.run([
                "docker", "rm", self.container_name
            ], capture_output=True)
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error("Cleanup failed", error=str(e))

async def main():
    """Main execution function"""
    deployment = WebEvalDeployment()
    
    try:
        # Deploy Web-Eval-Agent
        logger.info("Starting Web-Eval-Agent deployment and testing")
        
        if not await deployment.deploy_web_eval_agent():
            logger.error("Failed to deploy Web-Eval-Agent")
            return
        
        # Run comprehensive tests
        logger.info("Running comprehensive tests")
        comprehensive_results = await deployment.run_comprehensive_tests()
        
        # Run component-specific tests
        logger.info("Running component-specific tests")
        component_results = await deployment.run_component_specific_tests()
        
        # Combine results
        all_results = {
            **comprehensive_results,
            **component_results
        }
        
        # Generate report
        report = await deployment.generate_test_report(all_results)
        
        # Print summary
        print("\n" + "="*80)
        print("WEB-EVAL-AGENT TEST SUMMARY")
        print("="*80)
        print(report[:1000] + "..." if len(report) > 1000 else report)
        print("="*80)
        
        # Save results to JSON
        with open("web_eval_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        
        logger.info("Testing completed", 
                   results_file="web_eval_results.json",
                   report_file="web_eval_test_report.md")
        
    except Exception as e:
        logger.error("Testing failed", error=str(e))
    
    finally:
        # Cleanup
        await deployment.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

