"""
Web-eval-agent client for CodegenCICD Dashboard
"""
from typing import Dict, Any, Optional, List
import structlog

from .base_client import BaseClient, APIError
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebEvalClient(BaseClient):
    """Client for interacting with web-eval-agent service"""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use configured web-eval URL or default
        self.web_eval_url = base_url or getattr(settings, 'web_eval_url', 'http://localhost:8081')
        
        super().__init__(
            service_name="web_eval_agent",
            base_url=self.web_eval_url,
            timeout=180,  # Longer timeout for UI testing
            max_retries=3
        )
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for web-eval-agent requests"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def _health_check_request(self) -> None:
        """Health check by getting service status"""
        await self.get("/health")
    
    # Test Session Management
    async def create_test_session(self,
                                project_name: str,
                                base_url: str,
                                test_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new UI test session"""
        try:
            payload = {
                "project_name": project_name,
                "base_url": base_url,
                "session_type": "validation",
                "config": test_config or {}
            }
            
            self.logger.info("Creating web-eval test session",
                           project_name=project_name,
                           base_url=base_url)
            
            response = await self.post("/sessions", data=payload)
            
            session_id = response.get("session_id")
            self.logger.info("Web-eval test session created",
                           session_id=session_id,
                           project_name=project_name)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create test session",
                            project_name=project_name,
                            error=str(e))
            raise
    
    async def get_test_session(self, session_id: str) -> Dict[str, Any]:
        """Get test session details"""
        try:
            response = await self.get(f"/sessions/{session_id}")
            return response
        except Exception as e:
            self.logger.error("Failed to get test session",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def delete_test_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a test session"""
        try:
            response = await self.delete(f"/sessions/{session_id}")
            
            self.logger.info("Web-eval test session deleted",
                           session_id=session_id)
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to delete test session",
                            session_id=session_id,
                            error=str(e))
            raise
    
    # UI Testing
    async def run_ui_tests(self,
                          snapshot_id: str,
                          base_url: str,
                          test_scenarios: List[Dict[str, Any]],
                          browser: str = "chromium") -> Dict[str, Any]:
        """Run comprehensive UI tests"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "base_url": base_url,
                "test_scenarios": test_scenarios,
                "browser": browser,
                "test_type": "comprehensive"
            }
            
            self.logger.info("Running UI tests with web-eval-agent",
                           snapshot_id=snapshot_id,
                           base_url=base_url,
                           scenario_count=len(test_scenarios),
                           browser=browser)
            
            response = await self.post("/tests/run", data=payload)
            
            session_id = response.get("session_id")
            test_status = response.get("status")
            
            self.logger.info("UI tests completed",
                           session_id=session_id,
                           status=test_status,
                           total_tests=response.get("total_tests", 0),
                           passed_tests=response.get("passed_tests", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to run UI tests",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def run_accessibility_tests(self,
                                    session_id: str,
                                    pages: List[str]) -> Dict[str, Any]:
        """Run accessibility tests on specified pages"""
        try:
            payload = {
                "pages": pages,
                "test_type": "accessibility",
                "standards": ["WCAG2.1", "Section508"]
            }
            
            self.logger.info("Running accessibility tests",
                           session_id=session_id,
                           page_count=len(pages))
            
            response = await self.post(f"/sessions/{session_id}/accessibility", data=payload)
            
            self.logger.info("Accessibility tests completed",
                           session_id=session_id,
                           violations=response.get("total_violations", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to run accessibility tests",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def run_performance_tests(self,
                                  session_id: str,
                                  pages: List[str]) -> Dict[str, Any]:
        """Run performance tests on specified pages"""
        try:
            payload = {
                "pages": pages,
                "test_type": "performance",
                "metrics": ["FCP", "LCP", "CLS", "FID", "TTI"]
            }
            
            self.logger.info("Running performance tests",
                           session_id=session_id,
                           page_count=len(pages))
            
            response = await self.post(f"/sessions/{session_id}/performance", data=payload)
            
            self.logger.info("Performance tests completed",
                           session_id=session_id,
                           average_score=response.get("average_score", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to run performance tests",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def run_visual_regression_tests(self,
                                        session_id: str,
                                        baseline_session_id: Optional[str] = None) -> Dict[str, Any]:
        """Run visual regression tests"""
        try:
            payload = {
                "test_type": "visual_regression",
                "baseline_session_id": baseline_session_id
            }
            
            self.logger.info("Running visual regression tests",
                           session_id=session_id,
                           baseline_session_id=baseline_session_id)
            
            response = await self.post(f"/sessions/{session_id}/visual", data=payload)
            
            self.logger.info("Visual regression tests completed",
                           session_id=session_id,
                           differences_found=response.get("differences_found", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to run visual regression tests",
                            session_id=session_id,
                            error=str(e))
            raise
    
    # Functional Testing
    async def test_user_flows(self,
                            session_id: str,
                            user_flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test user flows and interactions"""
        try:
            payload = {
                "user_flows": user_flows,
                "test_type": "functional"
            }
            
            self.logger.info("Testing user flows",
                           session_id=session_id,
                           flow_count=len(user_flows))
            
            response = await self.post(f"/sessions/{session_id}/flows", data=payload)
            
            self.logger.info("User flow tests completed",
                           session_id=session_id,
                           successful_flows=response.get("successful_flows", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to test user flows",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def test_form_interactions(self,
                                   session_id: str,
                                   forms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test form interactions and validation"""
        try:
            payload = {
                "forms": forms,
                "test_type": "form_validation"
            }
            
            self.logger.info("Testing form interactions",
                           session_id=session_id,
                           form_count=len(forms))
            
            response = await self.post(f"/sessions/{session_id}/forms", data=payload)
            
            self.logger.info("Form interaction tests completed",
                           session_id=session_id,
                           passed_validations=response.get("passed_validations", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to test form interactions",
                            session_id=session_id,
                            error=str(e))
            raise
    
    # Cross-browser Testing
    async def run_cross_browser_tests(self,
                                    session_id: str,
                                    browsers: List[str],
                                    test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests across multiple browsers"""
        try:
            payload = {
                "browsers": browsers,
                "test_scenarios": test_scenarios,
                "test_type": "cross_browser"
            }
            
            self.logger.info("Running cross-browser tests",
                           session_id=session_id,
                           browser_count=len(browsers),
                           scenario_count=len(test_scenarios))
            
            response = await self.post(f"/sessions/{session_id}/cross-browser", data=payload)
            
            self.logger.info("Cross-browser tests completed",
                           session_id=session_id,
                           browser_results=response.get("browser_results", {}))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to run cross-browser tests",
                            session_id=session_id,
                            error=str(e))
            raise
    
    # Mobile Testing
    async def run_mobile_tests(self,
                             session_id: str,
                             devices: List[str],
                             test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests on mobile devices"""
        try:
            payload = {
                "devices": devices,
                "test_scenarios": test_scenarios,
                "test_type": "mobile"
            }
            
            self.logger.info("Running mobile tests",
                           session_id=session_id,
                           device_count=len(devices),
                           scenario_count=len(test_scenarios))
            
            response = await self.post(f"/sessions/{session_id}/mobile", data=payload)
            
            self.logger.info("Mobile tests completed",
                           session_id=session_id,
                           device_results=response.get("device_results", {}))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to run mobile tests",
                            session_id=session_id,
                            error=str(e))
            raise
    
    # Results and Reporting
    async def get_test_results(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive test results"""
        try:
            response = await self.get(f"/sessions/{session_id}/results")
            return response
        except Exception as e:
            self.logger.error("Failed to get test results",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def get_test_screenshots(self, session_id: str) -> List[Dict[str, Any]]:
        """Get test screenshots"""
        try:
            response = await self.get(f"/sessions/{session_id}/screenshots")
            return response.get("screenshots", [])
        except Exception as e:
            self.logger.error("Failed to get test screenshots",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def get_test_videos(self, session_id: str) -> List[Dict[str, Any]]:
        """Get test videos"""
        try:
            response = await self.get(f"/sessions/{session_id}/videos")
            return response.get("videos", [])
        except Exception as e:
            self.logger.error("Failed to get test videos",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def generate_test_report(self,
                                 session_id: str,
                                 report_format: str = "html") -> Dict[str, Any]:
        """Generate comprehensive test report"""
        try:
            payload = {
                "format": report_format,
                "include_screenshots": True,
                "include_metrics": True
            }
            
            response = await self.post(f"/sessions/{session_id}/report", data=payload)
            
            self.logger.info("Test report generated",
                           session_id=session_id,
                           format=report_format,
                           report_url=response.get("report_url"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to generate test report",
                            session_id=session_id,
                            error=str(e))
            raise
    
    # Monitoring and Metrics
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get session performance metrics"""
        try:
            response = await self.get(f"/sessions/{session_id}/metrics")
            return response
        except Exception as e:
            self.logger.error("Failed to get session metrics",
                            session_id=session_id,
                            error=str(e))
            raise
    
    async def get_real_time_status(self, session_id: str) -> Dict[str, Any]:
        """Get real-time test execution status"""
        try:
            response = await self.get(f"/sessions/{session_id}/status")
            return response
        except Exception as e:
            self.logger.error("Failed to get real-time status",
                            session_id=session_id,
                            error=str(e))
            raise
    
    # Configuration and Templates
    async def get_test_templates(self) -> List[Dict[str, Any]]:
        """Get available test templates"""
        try:
            response = await self.get("/templates")
            return response.get("templates", [])
        except Exception as e:
            self.logger.error("Failed to get test templates", error=str(e))
            raise
    
    async def create_test_template(self,
                                 name: str,
                                 template_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new test template"""
        try:
            payload = {
                "name": name,
                "config": template_config
            }
            
            response = await self.post("/templates", data=payload)
            
            self.logger.info("Test template created",
                           template_name=name,
                           template_id=response.get("template_id"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to create test template",
                            template_name=name,
                            error=str(e))
            raise

