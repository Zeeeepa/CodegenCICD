"""
Web-eval-agent client for UI testing and interaction
"""
import httpx
import structlog
from typing import Dict, Any, Optional, List
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebEvalClient:
    """Client for interacting with web-eval-agent service"""
    
    def __init__(self):
        self.base_url = settings.web_eval_agent_api_url
        self.enabled = settings.web_eval_agent_enabled
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD/1.0.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to web-eval-agent API"""
        if not self.enabled:
            raise Exception("Web-eval-agent is disabled")
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Web-eval-agent API HTTP error",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                    endpoint=endpoint
                )
                raise
            except Exception as e:
                logger.error("Web-eval-agent API request failed", error=str(e), endpoint=endpoint)
                raise
    
    async def start_evaluation(self, url: str, test_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start a comprehensive web evaluation"""
        payload = {
            "url": url,
            "config": test_config or self._get_default_test_config()
        }
        
        try:
            response = await self._make_request("POST", "/evaluations", json=payload)
            logger.info("Web evaluation started", evaluation_id=response.get("id"), url=url)
            return response
        except Exception as e:
            logger.error("Failed to start web evaluation", url=url, error=str(e))
            raise
    
    async def get_evaluation(self, evaluation_id: str) -> Dict[str, Any]:
        """Get evaluation results"""
        try:
            response = await self._make_request("GET", f"/evaluations/{evaluation_id}")
            return response
        except Exception as e:
            logger.error("Failed to get evaluation", evaluation_id=evaluation_id, error=str(e))
            raise
    
    async def get_evaluation_status(self, evaluation_id: str) -> str:
        """Get evaluation status"""
        try:
            response = await self.get_evaluation(evaluation_id)
            return response.get("status", "unknown")
        except Exception as e:
            logger.error("Failed to get evaluation status", evaluation_id=evaluation_id, error=str(e))
            return "error"
    
    async def test_ui_components(self, url: str, components: List[str] = None) -> Dict[str, Any]:
        """Test specific UI components"""
        payload = {
            "url": url,
            "test_type": "components",
            "components": components or ["buttons", "forms", "navigation", "modals"]
        }
        
        try:
            response = await self._make_request("POST", "/tests/components", json=payload)
            logger.info("UI component testing started", url=url, components=components)
            return response
        except Exception as e:
            logger.error("Failed to test UI components", url=url, error=str(e))
            raise
    
    async def test_user_flows(self, url: str, flows: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Test user interaction flows"""
        payload = {
            "url": url,
            "test_type": "flows",
            "flows": flows or self._get_default_user_flows()
        }
        
        try:
            response = await self._make_request("POST", "/tests/flows", json=payload)
            logger.info("User flow testing started", url=url, flow_count=len(payload["flows"]))
            return response
        except Exception as e:
            logger.error("Failed to test user flows", url=url, error=str(e))
            raise
    
    async def test_accessibility(self, url: str) -> Dict[str, Any]:
        """Test accessibility compliance"""
        payload = {
            "url": url,
            "test_type": "accessibility",
            "standards": ["WCAG2.1", "Section508"]
        }
        
        try:
            response = await self._make_request("POST", "/tests/accessibility", json=payload)
            logger.info("Accessibility testing started", url=url)
            return response
        except Exception as e:
            logger.error("Failed to test accessibility", url=url, error=str(e))
            raise
    
    async def test_performance(self, url: str) -> Dict[str, Any]:
        """Test performance metrics"""
        payload = {
            "url": url,
            "test_type": "performance",
            "metrics": ["load_time", "first_paint", "largest_contentful_paint", "cumulative_layout_shift"]
        }
        
        try:
            response = await self._make_request("POST", "/tests/performance", json=payload)
            logger.info("Performance testing started", url=url)
            return response
        except Exception as e:
            logger.error("Failed to test performance", url=url, error=str(e))
            raise
    
    async def run_comprehensive_test(self, url: str, project_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run comprehensive testing suite"""
        payload = {
            "url": url,
            "test_suite": "comprehensive",
            "config": project_config or {},
            "tests": [
                "components",
                "flows", 
                "accessibility",
                "performance",
                "security",
                "responsive"
            ]
        }
        
        try:
            response = await self._make_request("POST", "/tests/comprehensive", json=payload)
            logger.info("Comprehensive testing started", url=url)
            return response
        except Exception as e:
            logger.error("Failed to run comprehensive test", url=url, error=str(e))
            raise
    
    async def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get test results"""
        try:
            response = await self._make_request("GET", f"/tests/{test_id}/results")
            return response
        except Exception as e:
            logger.error("Failed to get test results", test_id=test_id, error=str(e))
            raise
    
    async def get_test_screenshots(self, test_id: str) -> List[Dict[str, Any]]:
        """Get test screenshots"""
        try:
            response = await self._make_request("GET", f"/tests/{test_id}/screenshots")
            return response.get("screenshots", [])
        except Exception as e:
            logger.error("Failed to get test screenshots", test_id=test_id, error=str(e))
            return []
    
    async def cancel_test(self, test_id: str) -> bool:
        """Cancel a running test"""
        try:
            await self._make_request("POST", f"/tests/{test_id}/cancel")
            logger.info("Test cancelled", test_id=test_id)
            return True
        except Exception as e:
            logger.error("Failed to cancel test", test_id=test_id, error=str(e))
            return False
    
    def _get_default_test_config(self) -> Dict[str, Any]:
        """Get default test configuration"""
        return {
            "browser": "chromium",
            "viewport": {"width": 1920, "height": 1080},
            "timeout": 30000,
            "wait_for_network_idle": True,
            "take_screenshots": True,
            "record_video": False
        }
    
    def _get_default_user_flows(self) -> List[Dict[str, Any]]:
        """Get default user flows to test"""
        return [
            {
                "name": "Homepage Navigation",
                "steps": [
                    {"action": "goto", "url": "/"},
                    {"action": "wait", "selector": "body"},
                    {"action": "screenshot", "name": "homepage"}
                ]
            },
            {
                "name": "Form Interaction",
                "steps": [
                    {"action": "goto", "url": "/"},
                    {"action": "click", "selector": "button, input[type=submit]"},
                    {"action": "wait", "timeout": 2000},
                    {"action": "screenshot", "name": "form_interaction"}
                ]
            }
        ]
    
    async def health_check(self) -> bool:
        """Check if web-eval-agent service is accessible"""
        if not self.enabled:
            return False
        
        try:
            await self._make_request("GET", "/health")
            return True
        except Exception as e:
            logger.error("Web-eval-agent health check failed", error=str(e))
            return False

