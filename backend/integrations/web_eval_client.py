"""
Enhanced Web-eval-agent client for comprehensive UI element testing
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
import structlog

from .base_client import BaseClient, APIError
from backend.config import get_settings
from backend.utils.circuit_breaker import (
    circuit_breaker_manager, 
    CircuitBreakerConfig
)
from backend.utils.retry_strategies import (
    RetryHandler, 
    RetryConfig, 
    RetryStrategy, 
    AdaptiveRetryHandler
)
from backend.services.resource_manager import (
    resource_manager, 
    ResourceType, 
    ResourceMetrics
)

logger = structlog.get_logger(__name__)
settings = get_settings()


class TestType(Enum):
    """Types of UI tests available"""
    FUNCTIONAL = "functional"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    VISUAL_REGRESSION = "visual_regression"
    CROSS_BROWSER = "cross_browser"
    MOBILE_RESPONSIVE = "mobile_responsive"
    SECURITY = "security"
    LOAD_TESTING = "load_testing"
    AI_GENERATED = "ai_generated"


class BrowserType(Enum):
    """Supported browser types"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    CHROME = "chrome"
    EDGE = "edge"
    SAFARI = "safari"


class DeviceType(Enum):
    """Mobile device types for testing"""
    IPHONE_12 = "iPhone 12"
    IPHONE_13_PRO = "iPhone 13 Pro"
    PIXEL_5 = "Pixel 5"
    GALAXY_S21 = "Galaxy S21"
    IPAD_PRO = "iPad Pro"
    TABLET_ANDROID = "Android Tablet"


class EnhancedWebEvalClient(BaseClient):
    """Enhanced client for comprehensive UI element testing with advanced capabilities"""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use configured web-eval URL or default
        self.web_eval_url = base_url or getattr(settings, 'web_eval_url', 'http://localhost:8081')
        
        super().__init__(
            service_name="web_eval_agent",
            base_url=self.web_eval_url,
            timeout=300,  # Extended timeout for comprehensive testing
            max_retries=3
        )
        
        # Enhanced features
        self.correlation_id = str(uuid.uuid4())
        self.logger = logger.bind(
            service="web_eval_agent",
            correlation_id=self.correlation_id
        )
        
        # Circuit breaker configuration for UI testing
        self.circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=120,
            success_threshold=2,
            timeout=300
        )
        
        # Retry configuration for UI operations
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=60.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=True,
            backoff_multiplier=2.0,
            retryable_exceptions=[ConnectionError, TimeoutError, APIError]
        )
        
        # Initialize adaptive retry handler
        self.adaptive_retry = AdaptiveRetryHandler(self.retry_config)
        
        # Test session tracking
        self.active_sessions = {}
        
        # Performance metrics
        self.test_metrics = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "average_test_duration": 0.0,
            "last_test": None
        }
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for web-eval-agent requests"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Enhanced-WebEval/2.0",
            "X-Correlation-ID": self.correlation_id,
            "X-Request-ID": str(uuid.uuid4()),
            "X-Test-Session": "enhanced"
        }
    
    async def _health_check_request(self) -> None:
        """Health check by getting service status"""
        await self._execute_with_enhancements(self.get, "/health")
    
    async def _execute_with_enhancements(self, 
                                       operation: Callable,
                                       *args, 
                                       **kwargs) -> Any:
        """Execute operation with circuit breaker, retry, and monitoring"""
        operation_start = datetime.utcnow()
        operation_name = f"{operation.__name__}_{args[0] if args else 'unknown'}"
        
        # Get circuit breaker
        circuit_breaker = circuit_breaker_manager.get_breaker(
            f"web_eval_{operation_name}",
            self.circuit_breaker_config
        )
        
        try:
            self.test_metrics["total_tests"] += 1
            
            # Execute with circuit breaker and retry
            result = await circuit_breaker.call(
                self.adaptive_retry.execute,
                operation,
                *args,
                **kwargs
            )
            
            # Update success metrics
            self.test_metrics["successful_tests"] += 1
            operation_duration = (datetime.utcnow() - operation_start).total_seconds()
            
            # Update average test duration
            total_tests = self.test_metrics["total_tests"]
            current_avg = self.test_metrics["average_test_duration"]
            self.test_metrics["average_test_duration"] = (
                (current_avg * (total_tests - 1) + operation_duration) / total_tests
            )
            
            self.test_metrics["last_test"] = operation_start.isoformat()
            
            self.logger.info("UI test operation completed successfully",
                           operation=operation_name,
                           duration=operation_duration,
                           correlation_id=self.correlation_id)
            
            return result
            
        except Exception as e:
            self.test_metrics["failed_tests"] += 1
            operation_duration = (datetime.utcnow() - operation_start).total_seconds()
            
            self.logger.error("UI test operation failed",
                            operation=operation_name,
                            duration=operation_duration,
                            error=str(e),
                            correlation_id=self.correlation_id)
            raise
    
    # Enhanced Test Session Management
    async def create_comprehensive_test_session(self,
                                               project_name: str,
                                               base_url: str,
                                               test_config: Optional[Dict[str, Any]] = None,
                                               browsers: Optional[List[BrowserType]] = None,
                                               devices: Optional[List[DeviceType]] = None,
                                               test_types: Optional[List[TestType]] = None) -> Dict[str, Any]:
        """Create a comprehensive UI test session with advanced configuration"""
        
        # Default comprehensive test configuration
        default_config = {
            "session_type": "comprehensive",
            "ai_powered": True,
            "visual_regression": True,
            "accessibility_standards": ["WCAG2.1", "Section508", "ADA"],
            "performance_budgets": {
                "FCP": 2000,  # First Contentful Paint
                "LCP": 4000,  # Largest Contentful Paint
                "CLS": 0.1,   # Cumulative Layout Shift
                "FID": 100,   # First Input Delay
                "TTI": 5000   # Time to Interactive
            },
            "viewport_sizes": [
                {"width": 1920, "height": 1080},  # Desktop
                {"width": 1366, "height": 768},   # Laptop
                {"width": 768, "height": 1024},   # Tablet
                {"width": 375, "height": 667}     # Mobile
            ],
            "screenshot_options": {
                "full_page": True,
                "quality": 90,
                "format": "png"
            },
            "video_recording": {
                "enabled": True,
                "quality": "high",
                "fps": 30
            },
            "network_conditions": [
                {"name": "Fast 3G", "download": 1600, "upload": 750, "latency": 150},
                {"name": "Slow 3G", "download": 500, "upload": 500, "latency": 400}
            ]
        }
        
        # Merge with user config
        merged_config = {**default_config, **(test_config or {})}
        
        payload = {
            "project_name": project_name,
            "base_url": base_url,
            "correlation_id": self.correlation_id,
            "config": merged_config,
            "browsers": [b.value for b in (browsers or [BrowserType.CHROMIUM, BrowserType.FIREFOX])],
            "devices": [d.value for d in (devices or [DeviceType.IPHONE_12, DeviceType.PIXEL_5])],
            "test_types": [t.value for t in (test_types or [
                TestType.FUNCTIONAL, 
                TestType.ACCESSIBILITY, 
                TestType.PERFORMANCE,
                TestType.VISUAL_REGRESSION
            ])]
        }
        
        self.logger.info("Creating comprehensive web-eval test session",
                       project_name=project_name,
                       base_url=base_url,
                       browsers=len(payload["browsers"]),
                       devices=len(payload["devices"]),
                       test_types=len(payload["test_types"]),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post, 
            "/sessions/comprehensive", 
            data=payload
        )
        
        session_id = response.get("session_id")
        
        # Register session with resource manager
        if session_id:
            cleanup_callback = lambda sid: self._cleanup_session_callback(sid)
            resource_manager.register_resource(
                resource_id=session_id,
                resource_type=ResourceType.PROCESS,  # UI test session as process
                metadata={
                    "project_name": project_name,
                    "base_url": base_url,
                    "session_type": "comprehensive",
                    "created_by": "web_eval_client",
                    "correlation_id": self.correlation_id,
                    "browsers": payload["browsers"],
                    "test_types": payload["test_types"]
                },
                cleanup_callbacks=[cleanup_callback]
            )
            
            # Track active session
            self.active_sessions[session_id] = {
                "project_name": project_name,
                "base_url": base_url,
                "created_at": datetime.utcnow(),
                "status": "active"
            }
        
        self.logger.info("Comprehensive web-eval test session created",
                       session_id=session_id,
                       project_name=project_name,
                       correlation_id=self.correlation_id)
        
        return response
    
    async def _cleanup_session_callback(self, session_id: str):
        """Cleanup callback for test session resources"""
        try:
            await self.delete_test_session(session_id)
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            self.logger.info("Test session cleaned up via callback",
                           session_id=session_id,
                           correlation_id=self.correlation_id)
        except Exception as e:
            self.logger.error("Failed to cleanup test session via callback",
                            session_id=session_id,
                            error=str(e),
                            correlation_id=self.correlation_id)
    
    # Legacy method for backward compatibility
    async def create_test_session(self,
                                project_name: str,
                                base_url: str,
                                test_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a basic UI test session (legacy method)"""
        return await self.create_comprehensive_test_session(
            project_name=project_name,
            base_url=base_url,
            test_config=test_config,
            browsers=[BrowserType.CHROMIUM],
            test_types=[TestType.FUNCTIONAL]
        )
    
    async def get_test_session(self, session_id: str) -> Dict[str, Any]:
        """Get test session details with enhanced monitoring"""
        # Mark resource as accessed
        resource_manager.access_resource(session_id)
        
        response = await self._execute_with_enhancements(
            self.get, 
            f"/sessions/{session_id}"
        )
        
        # Update session tracking
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_accessed"] = datetime.utcnow()
        
        return response
    
    # AI-Powered Testing Capabilities
    async def generate_ai_test_scenarios(self,
                                       session_id: str,
                                       page_url: str,
                                       test_objectives: Optional[List[str]] = None,
                                       user_personas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate AI-powered test scenarios based on page analysis"""
        
        default_objectives = [
            "functional_validation",
            "user_experience_optimization", 
            "accessibility_compliance",
            "performance_validation",
            "security_testing"
        ]
        
        default_personas = [
            {
                "name": "Power User",
                "description": "Experienced user who knows the system well",
                "behavior": "efficient, direct navigation, uses shortcuts"
            },
            {
                "name": "New User", 
                "description": "First-time user exploring the interface",
                "behavior": "cautious, reads instructions, explores features"
            },
            {
                "name": "Accessibility User",
                "description": "User with accessibility needs",
                "behavior": "relies on screen readers, keyboard navigation"
            }
        ]
        
        payload = {
            "page_url": page_url,
            "test_objectives": test_objectives or default_objectives,
            "user_personas": user_personas or default_personas,
            "ai_config": {
                "analysis_depth": "comprehensive",
                "include_edge_cases": True,
                "generate_negative_tests": True,
                "consider_mobile_scenarios": True,
                "include_performance_tests": True
            },
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Generating AI test scenarios",
                       session_id=session_id,
                       page_url=page_url,
                       objectives=len(payload["test_objectives"]),
                       personas=len(payload["user_personas"]),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/ai/generate-scenarios",
            data=payload
        )
        
        self.logger.info("AI test scenarios generated",
                       session_id=session_id,
                       scenarios_count=response.get("scenarios_count", 0),
                       correlation_id=self.correlation_id)
        
        return response
    
    async def run_ai_powered_testing(self,
                                   session_id: str,
                                   target_pages: List[str],
                                   testing_strategy: str = "comprehensive") -> Dict[str, Any]:
        """Run AI-powered comprehensive testing"""
        
        payload = {
            "target_pages": target_pages,
            "strategy": testing_strategy,
            "ai_features": {
                "smart_element_detection": True,
                "intelligent_interaction_patterns": True,
                "adaptive_wait_strategies": True,
                "context_aware_assertions": True,
                "automatic_error_recovery": True,
                "visual_ai_validation": True
            },
            "test_coverage": {
                "functional_flows": True,
                "edge_case_scenarios": True,
                "error_handling": True,
                "performance_under_load": True,
                "accessibility_compliance": True,
                "security_vulnerabilities": True
            },
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Starting AI-powered testing",
                       session_id=session_id,
                       pages=len(target_pages),
                       strategy=testing_strategy,
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/ai/run-tests",
            data=payload
        )
        
        self.logger.info("AI-powered testing completed",
                       session_id=session_id,
                       tests_executed=response.get("tests_executed", 0),
                       success_rate=response.get("success_rate", 0),
                       correlation_id=self.correlation_id)
        
        return response
    
    async def delete_test_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a test session with cleanup"""
        response = await self._execute_with_enhancements(
            self.delete, 
            f"/sessions/{session_id}"
        )
        
        # Clean up local tracking
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        self.logger.info("Web-eval test session deleted",
                       session_id=session_id,
                       correlation_id=self.correlation_id)
        
        return response
    
    # Advanced Visual Testing
    async def run_advanced_visual_regression(self,
                                           session_id: str,
                                           pages: List[str],
                                           baseline_session_id: Optional[str] = None,
                                           visual_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run advanced visual regression testing with AI-powered analysis"""
        
        default_visual_config = {
            "comparison_algorithm": "ai_enhanced",
            "sensitivity_level": "medium",
            "ignore_regions": [],
            "focus_regions": [],
            "threshold_settings": {
                "pixel_difference": 0.1,
                "layout_shift": 0.05,
                "color_variance": 0.02
            },
            "ai_analysis": {
                "detect_layout_issues": True,
                "identify_content_changes": True,
                "analyze_visual_hierarchy": True,
                "check_responsive_behavior": True
            },
            "capture_settings": {
                "full_page": True,
                "wait_for_animations": True,
                "stabilization_time": 2000,
                "multiple_viewports": True
            }
        }
        
        merged_config = {**default_visual_config, **(visual_config or {})}
        
        payload = {
            "pages": pages,
            "baseline_session_id": baseline_session_id,
            "visual_config": merged_config,
            "test_type": "advanced_visual_regression",
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Running advanced visual regression testing",
                       session_id=session_id,
                       pages=len(pages),
                       baseline_session=baseline_session_id,
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/visual/advanced",
            data=payload
        )
        
        self.logger.info("Advanced visual regression testing completed",
                       session_id=session_id,
                       differences_found=response.get("differences_found", 0),
                       ai_insights=len(response.get("ai_insights", [])),
                       correlation_id=self.correlation_id)
        
        return response
    
    async def run_comprehensive_accessibility_audit(self,
                                                  session_id: str,
                                                  pages: List[str],
                                                  standards: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run comprehensive accessibility audit with advanced analysis"""
        
        default_standards = ["WCAG2.1", "Section508", "ADA", "EN301549"]
        
        payload = {
            "pages": pages,
            "standards": standards or default_standards,
            "audit_config": {
                "check_levels": ["A", "AA", "AAA"],
                "include_manual_checks": True,
                "test_with_assistive_tech": True,
                "keyboard_navigation_test": True,
                "screen_reader_simulation": True,
                "color_contrast_analysis": True,
                "focus_management_test": True,
                "semantic_structure_analysis": True
            },
            "reporting": {
                "include_remediation_suggestions": True,
                "priority_ranking": True,
                "impact_assessment": True,
                "code_examples": True
            },
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Running comprehensive accessibility audit",
                       session_id=session_id,
                       pages=len(pages),
                       standards=len(payload["standards"]),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/accessibility/comprehensive",
            data=payload
        )
        
        self.logger.info("Comprehensive accessibility audit completed",
                       session_id=session_id,
                       violations=response.get("total_violations", 0),
                       compliance_score=response.get("compliance_score", 0),
                       correlation_id=self.correlation_id)
        
        return response
    
    async def run_performance_profiling(self,
                                      session_id: str,
                                      pages: List[str],
                                      performance_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run comprehensive performance profiling"""
        
        default_config = {
            "metrics": [
                "FCP", "LCP", "CLS", "FID", "TTI", "TBT", "SI",  # Core Web Vitals + more
                "TTFB", "DOMContentLoaded", "Load", "NetworkIdle"
            ],
            "network_conditions": [
                {"name": "Fast 3G", "download": 1600, "upload": 750, "latency": 150},
                {"name": "Slow 3G", "download": 500, "upload": 500, "latency": 400},
                {"name": "2G", "download": 250, "upload": 250, "latency": 800}
            ],
            "device_profiles": [
                {"name": "Desktop", "cpu_slowdown": 1},
                {"name": "Mid-tier Mobile", "cpu_slowdown": 4},
                {"name": "Low-end Mobile", "cpu_slowdown": 6}
            ],
            "analysis": {
                "resource_analysis": True,
                "render_blocking_analysis": True,
                "javascript_profiling": True,
                "memory_usage_tracking": True,
                "lighthouse_audit": True
            },
            "budgets": {
                "FCP": 2000,
                "LCP": 4000,
                "CLS": 0.1,
                "FID": 100,
                "TTI": 5000,
                "bundle_size": 250000  # 250KB
            }
        }
        
        merged_config = {**default_config, **(performance_config or {})}
        
        payload = {
            "pages": pages,
            "performance_config": merged_config,
            "test_type": "comprehensive_performance",
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Running comprehensive performance profiling",
                       session_id=session_id,
                       pages=len(pages),
                       metrics=len(merged_config["metrics"]),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/performance/comprehensive",
            data=payload
        )
        
        self.logger.info("Comprehensive performance profiling completed",
                       session_id=session_id,
                       average_score=response.get("average_score", 0),
                       budget_violations=response.get("budget_violations", 0),
                       correlation_id=self.correlation_id)
        
        return response
    
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
    
    # Enhanced Monitoring and Analytics
    
    def get_client_metrics(self) -> Dict[str, Any]:
        """Get comprehensive client performance metrics"""
        # Get circuit breaker states
        circuit_breaker_states = circuit_breaker_manager.get_all_states()
        
        # Get retry statistics
        retry_stats = self.adaptive_retry.get_stats()
        
        # Get resource manager stats
        resource_stats = resource_manager.get_resource_stats()
        
        return {
            "client_info": {
                "service_name": self.service_name,
                "base_url": self.base_url,
                "correlation_id": self.correlation_id,
                "created_at": datetime.utcnow().isoformat()
            },
            "test_metrics": self.test_metrics.copy(),
            "active_sessions": {
                "count": len(self.active_sessions),
                "sessions": list(self.active_sessions.keys())
            },
            "circuit_breakers": circuit_breaker_states,
            "retry_statistics": retry_stats,
            "resource_management": resource_stats
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the web-eval client"""
        metrics = self.get_client_metrics()
        
        health_score = 100
        issues = []
        
        # Check test success rate
        total_tests = metrics["test_metrics"]["total_tests"]
        if total_tests > 0:
            success_rate = metrics["test_metrics"]["successful_tests"] / total_tests
            if success_rate < 0.5:
                health_score -= 40
                issues.append(f"Low test success rate: {success_rate:.2%}")
            elif success_rate < 0.8:
                health_score -= 20
                issues.append(f"Moderate test success rate: {success_rate:.2%}")
        
        # Check circuit breaker states
        for breaker_name, breaker_state in metrics["circuit_breakers"].items():
            if breaker_state["state"] == "open":
                health_score -= 30
                issues.append(f"Circuit breaker {breaker_name} is open")
            elif breaker_state["state"] == "half_open":
                health_score -= 15
                issues.append(f"Circuit breaker {breaker_name} is half-open")
        
        # Check retry statistics
        retry_stats = metrics["retry_statistics"]
        if retry_stats["total_attempts"] > 0:
            retry_success_rate = retry_stats["success_rate"]
            if retry_success_rate < 0.7:
                health_score -= 25
                issues.append(f"Low retry success rate: {retry_success_rate:.2%}")
        
        # Check active sessions
        active_sessions = metrics["active_sessions"]["count"]
        if active_sessions > 10:
            health_score -= 15
            issues.append(f"High number of active sessions: {active_sessions}")
        
        # Determine overall status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "health_score": max(0, health_score),
            "issues": issues,
            "last_check": datetime.utcnow().isoformat(),
            "detailed_metrics": metrics
        }
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform active health check against web-eval-agent service"""
        health_check_start = datetime.utcnow()
        
        try:
            # Test basic connectivity
            await self._health_check_request()
            
            # Test template listing (lightweight operation)
            await self.get_test_templates()
            
            health_check_duration = (datetime.utcnow() - health_check_start).total_seconds()
            
            return {
                "service_available": True,
                "response_time": health_check_duration,
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": self.correlation_id
            }
            
        except Exception as e:
            health_check_duration = (datetime.utcnow() - health_check_start).total_seconds()
            
            return {
                "service_available": False,
                "error": str(e),
                "response_time": health_check_duration,
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": self.correlation_id
            }
    
    async def cleanup_all_sessions(self, force: bool = False) -> Dict[str, Any]:
        """Clean up all managed test sessions"""
        cleanup_start = datetime.utcnow()
        
        try:
            cleanup_results = {
                "total_sessions": len(self.active_sessions),
                "cleaned_up": 0,
                "failed": 0,
                "errors": []
            }
            
            for session_id in list(self.active_sessions.keys()):
                try:
                    await resource_manager.cleanup_resource(session_id, force=force)
                    cleanup_results["cleaned_up"] += 1
                except Exception as e:
                    cleanup_results["failed"] += 1
                    cleanup_results["errors"].append({
                        "session_id": session_id,
                        "error": str(e)
                    })
            
            cleanup_duration = (datetime.utcnow() - cleanup_start).total_seconds()
            
            self.logger.info("Session cleanup completed",
                           duration=cleanup_duration,
                           results=cleanup_results,
                           correlation_id=self.correlation_id)
            
            return {
                "success": True,
                "duration": cleanup_duration,
                "results": cleanup_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            cleanup_duration = (datetime.utcnow() - cleanup_start).total_seconds()
            
            self.logger.error("Session cleanup failed",
                            duration=cleanup_duration,
                            error=str(e),
                            correlation_id=self.correlation_id)
            
            return {
                "success": False,
                "duration": cleanup_duration,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_comprehensive_report(self,
                                          session_id: str,
                                          report_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive test report with advanced analytics"""
        
        default_config = {
            "format": "html",
            "include_screenshots": True,
            "include_videos": True,
            "include_metrics": True,
            "include_ai_insights": True,
            "include_recommendations": True,
            "sections": [
                "executive_summary",
                "test_coverage",
                "performance_analysis",
                "accessibility_audit",
                "visual_regression",
                "security_findings",
                "recommendations",
                "detailed_results"
            ],
            "charts_and_graphs": True,
            "export_formats": ["html", "pdf", "json"]
        }
        
        merged_config = {**default_config, **(report_config or {})}
        
        payload = {
            "report_config": merged_config,
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Generating comprehensive test report",
                       session_id=session_id,
                       sections=len(merged_config["sections"]),
                       formats=len(merged_config["export_formats"]),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/reports/comprehensive",
            data=payload
        )
        
        self.logger.info("Comprehensive test report generated",
                       session_id=session_id,
                       report_urls=response.get("report_urls", {}),
                       correlation_id=self.correlation_id)
        
        return response


# Maintain backward compatibility
WebEvalClient = EnhancedWebEvalClient
