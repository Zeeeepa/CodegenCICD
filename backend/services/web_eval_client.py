"""
Web-Eval-Agent client for UI testing and browser automation
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
import structlog
import httpx
from datetime import datetime

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebEvalClient:
    """Client for interacting with Web-Eval-Agent service"""
    
    def __init__(self):
        self.base_url = settings.web_eval_agent_url or "http://localhost:8003"
        self.gemini_api_key = settings.gemini_api_key
        self.timeout = 300  # 5 minutes timeout for tests
    
    async def run_test_suite(self, scenarios: List[Dict[str, Any]], base_url: str, timeout: int = 180) -> Dict[str, Any]:
        """Run a complete test suite with multiple scenarios"""
        try:
            logger.info("Starting Web-Eval test suite", 
                       scenario_count=len(scenarios),
                       base_url=base_url)
            
            results = []
            overall_success = True
            
            for i, scenario in enumerate(scenarios):
                logger.info(f"Running test scenario {i+1}/{len(scenarios)}", 
                           scenario_name=scenario.get("name"))
                
                result = await self.run_single_test(scenario, base_url, timeout)
                results.append(result)
                
                if result.get("status") != "passed":
                    overall_success = False
            
            return {
                "overall_status": "passed" if overall_success else "failed",
                "total_scenarios": len(scenarios),
                "passed_scenarios": sum(1 for r in results if r.get("status") == "passed"),
                "failed_scenarios": sum(1 for r in results if r.get("status") == "failed"),
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Test suite execution failed", error=str(e))
            return {
                "overall_status": "error",
                "error": str(e),
                "results": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_single_test(self, scenario: Dict[str, Any], base_url: str, timeout: int = 180) -> Dict[str, Any]:
        """Run a single test scenario"""
        try:
            test_config = {
                "scenario": scenario,
                "base_url": base_url,
                "gemini_api_key": self.gemini_api_key,
                "timeout": timeout,
                "browser_config": {
                    "headless": True,
                    "viewport": {"width": 1920, "height": 1080},
                    "user_agent": "WebEvalAgent/1.0"
                }
            }
            
            async with httpx.AsyncClient(timeout=timeout + 30) as client:
                response = await client.post(
                    f"{self.base_url}/api/test/run",
                    json=test_config,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Test scenario completed", 
                               scenario_name=scenario.get("name"),
                               status=result.get("status"))
                    return result
                else:
                    error_msg = f"Web-Eval-Agent returned status {response.status_code}"
                    logger.error("Test scenario failed", 
                               scenario_name=scenario.get("name"),
                               error=error_msg)
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "scenario": scenario.get("name"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error("Single test execution failed", 
                        scenario_name=scenario.get("name"),
                        error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "scenario": scenario.get("name"),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def test_homepage_functionality(self, base_url: str) -> Dict[str, Any]:
        """Test basic homepage functionality"""
        scenario = {
            "name": "homepage_functionality",
            "description": "Test homepage loads and basic elements are present",
            "url": base_url,
            "checks": [
                {
                    "type": "page_load",
                    "description": "Page loads without errors",
                    "timeout": 30
                },
                {
                    "type": "element_exists",
                    "selector": "body",
                    "description": "Body element exists"
                },
                {
                    "type": "no_console_errors",
                    "description": "No JavaScript console errors"
                },
                {
                    "type": "response_time",
                    "max_time": 5000,
                    "description": "Page loads within 5 seconds"
                }
            ]
        }
        
        return await self.run_single_test(scenario, base_url)
    
    async def test_navigation_functionality(self, base_url: str, nav_links: List[str] = None) -> Dict[str, Any]:
        """Test navigation functionality"""
        if nav_links is None:
            nav_links = ["/", "/about", "/contact"]  # Default links
        
        scenario = {
            "name": "navigation_functionality",
            "description": "Test navigation links work correctly",
            "url": base_url,
            "checks": [
                {
                    "type": "navigation_test",
                    "links": nav_links,
                    "description": "All navigation links are functional"
                },
                {
                    "type": "back_button",
                    "description": "Browser back button works correctly"
                }
            ]
        }
        
        return await self.run_single_test(scenario, base_url)
    
    async def test_form_functionality(self, base_url: str, form_selectors: List[str] = None) -> Dict[str, Any]:
        """Test form functionality"""
        if form_selectors is None:
            form_selectors = ["form", "input[type='submit']", "button[type='submit']"]
        
        scenario = {
            "name": "form_functionality",
            "description": "Test form submissions and validation",
            "url": base_url,
            "checks": [
                {
                    "type": "form_validation",
                    "selectors": form_selectors,
                    "description": "Forms have proper validation"
                },
                {
                    "type": "form_submission",
                    "description": "Forms can be submitted successfully"
                }
            ]
        }
        
        return await self.run_single_test(scenario, base_url)
    
    async def test_responsive_design(self, base_url: str) -> Dict[str, Any]:
        """Test responsive design across different viewport sizes"""
        scenario = {
            "name": "responsive_design",
            "description": "Test responsive design on different screen sizes",
            "url": base_url,
            "checks": [
                {
                    "type": "responsive_test",
                    "viewports": [
                        {"width": 320, "height": 568, "name": "mobile"},
                        {"width": 768, "height": 1024, "name": "tablet"},
                        {"width": 1920, "height": 1080, "name": "desktop"}
                    ],
                    "description": "Layout works on all screen sizes"
                }
            ]
        }
        
        return await self.run_single_test(scenario, base_url)
    
    async def test_accessibility(self, base_url: str) -> Dict[str, Any]:
        """Test accessibility compliance"""
        scenario = {
            "name": "accessibility_test",
            "description": "Test accessibility compliance (WCAG guidelines)",
            "url": base_url,
            "checks": [
                {
                    "type": "accessibility_audit",
                    "standards": ["wcag2a", "wcag2aa"],
                    "description": "Page meets WCAG accessibility standards"
                },
                {
                    "type": "keyboard_navigation",
                    "description": "All interactive elements are keyboard accessible"
                },
                {
                    "type": "screen_reader",
                    "description": "Content is properly structured for screen readers"
                }
            ]
        }
        
        return await self.run_single_test(scenario, base_url)
    
    async def test_performance(self, base_url: str) -> Dict[str, Any]:
        """Test performance metrics"""
        scenario = {
            "name": "performance_test",
            "description": "Test page performance metrics",
            "url": base_url,
            "checks": [
                {
                    "type": "lighthouse_audit",
                    "categories": ["performance", "accessibility", "best-practices", "seo"],
                    "description": "Lighthouse audit scores"
                },
                {
                    "type": "core_web_vitals",
                    "description": "Core Web Vitals metrics"
                }
            ]
        }
        
        return await self.run_single_test(scenario, base_url)
    
    async def run_comprehensive_test_suite(self, base_url: str) -> Dict[str, Any]:
        """Run a comprehensive test suite covering all major areas"""
        try:
            logger.info("Starting comprehensive test suite", base_url=base_url)
            
            # Define comprehensive test scenarios
            scenarios = [
                {
                    "name": "homepage_load",
                    "description": "Test homepage loads correctly",
                    "url": base_url,
                    "checks": ["page_loads", "no_errors", "basic_elements"]
                },
                {
                    "name": "navigation_test",
                    "description": "Test navigation functionality",
                    "url": base_url,
                    "checks": ["navigation_works", "links_functional"]
                },
                {
                    "name": "form_functionality",
                    "description": "Test form submissions and interactions",
                    "url": base_url,
                    "checks": ["forms_work", "validation_works"]
                },
                {
                    "name": "responsive_design",
                    "description": "Test responsive design",
                    "url": base_url,
                    "checks": ["mobile_responsive", "tablet_responsive", "desktop_responsive"]
                },
                {
                    "name": "accessibility_check",
                    "description": "Test accessibility compliance",
                    "url": base_url,
                    "checks": ["wcag_compliance", "keyboard_navigation", "screen_reader_support"]
                },
                {
                    "name": "performance_audit",
                    "description": "Test performance metrics",
                    "url": base_url,
                    "checks": ["load_time", "core_web_vitals", "lighthouse_score"]
                }
            ]
            
            return await self.run_test_suite(scenarios, base_url)
            
        except Exception as e:
            logger.error("Comprehensive test suite failed", error=str(e))
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Web-Eval-Agent service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "service": "web-eval-agent",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "service": "web-eval-agent",
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error("Web-Eval-Agent health check failed", error=str(e))
            return {
                "status": "error",
                "service": "web-eval-agent",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get Web-Eval-Agent service information"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/api/info")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error("Failed to get Web-Eval-Agent service info", error=str(e))
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

