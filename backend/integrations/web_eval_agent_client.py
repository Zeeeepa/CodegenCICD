"""
Web-eval-agent client for UI testing and browser automation
"""
import os
import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class WebEvalAgentClient:
    def __init__(self):
        self.base_url = os.getenv("WEB_EVAL_AGENT_API_URL", "http://localhost:8082")
        self.api_key = os.getenv("WEB_EVAL_AGENT_API_KEY")
        self.enabled = os.getenv("WEB_EVAL_AGENT_ENABLED", "true").lower() == "true"
    
    async def run_tests(self, snapshot_id: str, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive UI tests on the deployed application"""
        try:
            if not self.enabled:
                # Return mock test results for development
                return {
                    "status": "completed",
                    "url": test_config.get("url", "http://localhost:3000"),
                    "total_tests": 15,
                    "passed_tests": 14,
                    "failed_tests": 1,
                    "duration": 45.2,
                    "results": [
                        {
                            "test_name": "component_rendering",
                            "passed": True,
                            "duration": 2.1,
                            "details": "All components rendered successfully"
                        },
                        {
                            "test_name": "user_flows",
                            "passed": True,
                            "duration": 15.3,
                            "details": "User authentication and navigation flows work correctly"
                        },
                        {
                            "test_name": "accessibility",
                            "passed": True,
                            "duration": 8.7,
                            "details": "WCAG 2.1 AA compliance verified"
                        },
                        {
                            "test_name": "performance",
                            "passed": False,
                            "duration": 12.4,
                            "details": "Page load time exceeds 3 seconds",
                            "error": "Performance threshold not met"
                        },
                        {
                            "test_name": "responsive_design",
                            "passed": True,
                            "duration": 6.7,
                            "details": "Responsive design works on all tested screen sizes"
                        }
                    ],
                    "screenshots": [
                        {"name": "homepage", "url": "/screenshots/homepage.png"},
                        {"name": "dashboard", "url": "/screenshots/dashboard.png"}
                    ],
                    "performance_metrics": {
                        "first_contentful_paint": 1.2,
                        "largest_contentful_paint": 2.8,
                        "cumulative_layout_shift": 0.05,
                        "time_to_interactive": 3.4
                    }
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "snapshot_id": snapshot_id,
                    "url": test_config.get("url"),
                    "tests": test_config.get("tests", []),
                    "browser_config": {
                        "headless": True,
                        "viewport": {"width": 1920, "height": 1080},
                        "user_agent": "WebEvalAgent/1.0"
                    },
                    "test_config": {
                        "timeout": 30,
                        "retry_count": 2,
                        "screenshot_on_failure": True,
                        "performance_budget": {
                            "first_contentful_paint": 2.0,
                            "largest_contentful_paint": 4.0,
                            "time_to_interactive": 5.0
                        }
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/test",
                    headers=headers,
                    json=payload,
                    timeout=300.0  # 5 minutes for comprehensive testing
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Completed UI tests for snapshot {snapshot_id}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error running UI tests: {e}")
            raise Exception(f"Failed to run UI tests: {e}")
        except Exception as e:
            logger.error(f"Error running UI tests: {e}")
            # Return mock results for development
            return {
                "status": "error",
                "error": str(e),
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0
            }
    
    async def test_component_rendering(self, snapshot_id: str, url: str, components: List[str] = None) -> Dict[str, Any]:
        """Test that all components render correctly"""
        try:
            if not self.enabled:
                return {
                    "status": "passed",
                    "components_tested": components or ["Dashboard", "ProjectCard", "AgentRunDialog"],
                    "all_rendered": True,
                    "details": "All components rendered without errors"
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "snapshot_id": snapshot_id,
                    "url": url,
                    "components": components or [],
                    "check_console_errors": True,
                    "check_network_errors": True
                }
                
                response = await client.post(
                    f"{self.base_url}/test/components",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error testing component rendering: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_user_flows(self, snapshot_id: str, url: str, flows: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Test user interaction flows"""
        try:
            if not self.enabled:
                return {
                    "status": "passed",
                    "flows_tested": len(flows) if flows else 3,
                    "all_passed": True,
                    "details": "All user flows completed successfully",
                    "flows": [
                        {"name": "project_creation", "status": "passed", "duration": 5.2},
                        {"name": "agent_run", "status": "passed", "duration": 8.7},
                        {"name": "configuration", "status": "passed", "duration": 3.1}
                    ]
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                default_flows = [
                    {
                        "name": "project_creation",
                        "steps": [
                            {"action": "click", "selector": "[data-testid='add-project-button']"},
                            {"action": "type", "selector": "input[name='name']", "text": "Test Project"},
                            {"action": "click", "selector": "button[type='submit']"}
                        ]
                    },
                    {
                        "name": "agent_run",
                        "steps": [
                            {"action": "click", "selector": "[data-testid='agent-run-button']"},
                            {"action": "type", "selector": "textarea[name='target']", "text": "Create a test component"},
                            {"action": "click", "selector": "button[data-testid='start-run']"}
                        ]
                    }
                ]
                
                payload = {
                    "snapshot_id": snapshot_id,
                    "url": url,
                    "flows": flows or default_flows,
                    "wait_for_navigation": True,
                    "capture_screenshots": True
                }
                
                response = await client.post(
                    f"{self.base_url}/test/flows",
                    headers=headers,
                    json=payload,
                    timeout=180.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error testing user flows: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_accessibility(self, snapshot_id: str, url: str) -> Dict[str, Any]:
        """Test accessibility compliance"""
        try:
            if not self.enabled:
                return {
                    "status": "passed",
                    "wcag_level": "AA",
                    "compliance_score": 95,
                    "issues": [
                        {
                            "type": "warning",
                            "rule": "color-contrast",
                            "element": "button.secondary",
                            "message": "Color contrast ratio could be improved"
                        }
                    ],
                    "recommendations": [
                        "Increase color contrast for secondary buttons",
                        "Add aria-labels to icon buttons"
                    ]
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "snapshot_id": snapshot_id,
                    "url": url,
                    "wcag_level": "AA",
                    "include_best_practices": True,
                    "check_keyboard_navigation": True
                }
                
                response = await client.post(
                    f"{self.base_url}/test/accessibility",
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error testing accessibility: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_performance(self, snapshot_id: str, url: str, budget: Dict[str, float] = None) -> Dict[str, Any]:
        """Test performance metrics"""
        try:
            if not self.enabled:
                return {
                    "status": "passed",
                    "metrics": {
                        "first_contentful_paint": 1.2,
                        "largest_contentful_paint": 2.8,
                        "cumulative_layout_shift": 0.05,
                        "time_to_interactive": 3.4,
                        "total_blocking_time": 150
                    },
                    "budget_met": True,
                    "lighthouse_score": 92,
                    "recommendations": [
                        "Optimize images for better loading performance",
                        "Consider code splitting for JavaScript bundles"
                    ]
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                default_budget = {
                    "first_contentful_paint": 2.0,
                    "largest_contentful_paint": 4.0,
                    "time_to_interactive": 5.0,
                    "cumulative_layout_shift": 0.1
                }
                
                payload = {
                    "snapshot_id": snapshot_id,
                    "url": url,
                    "performance_budget": budget or default_budget,
                    "run_lighthouse": True,
                    "network_throttling": "3G",
                    "cpu_throttling": 4
                }
                
                response = await client.post(
                    f"{self.base_url}/test/performance",
                    headers=headers,
                    json=payload,
                    timeout=180.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error testing performance: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_responsive_design(self, snapshot_id: str, url: str, viewports: List[Dict[str, int]] = None) -> Dict[str, Any]:
        """Test responsive design across different screen sizes"""
        try:
            if not self.enabled:
                return {
                    "status": "passed",
                    "viewports_tested": 4,
                    "all_responsive": True,
                    "results": [
                        {"viewport": "mobile", "width": 375, "height": 667, "status": "passed"},
                        {"viewport": "tablet", "width": 768, "height": 1024, "status": "passed"},
                        {"viewport": "desktop", "width": 1920, "height": 1080, "status": "passed"},
                        {"viewport": "large", "width": 2560, "height": 1440, "status": "passed"}
                    ]
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                default_viewports = [
                    {"name": "mobile", "width": 375, "height": 667},
                    {"name": "tablet", "width": 768, "height": 1024},
                    {"name": "desktop", "width": 1920, "height": 1080},
                    {"name": "large", "width": 2560, "height": 1440}
                ]
                
                payload = {
                    "snapshot_id": snapshot_id,
                    "url": url,
                    "viewports": viewports or default_viewports,
                    "check_layout_shifts": True,
                    "capture_screenshots": True
                }
                
                response = await client.post(
                    f"{self.base_url}/test/responsive",
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error testing responsive design: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_screenshot(self, snapshot_id: str, url: str, selector: str = None) -> Dict[str, Any]:
        """Take a screenshot of the application"""
        try:
            if not self.enabled:
                return {
                    "status": "success",
                    "screenshot_url": "/mock/screenshot.png",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "snapshot_id": snapshot_id,
                    "url": url,
                    "selector": selector,
                    "full_page": selector is None,
                    "format": "png"
                }
                
                response = await client.post(
                    f"{self.base_url}/screenshot",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return {"status": "error", "error": str(e)}

