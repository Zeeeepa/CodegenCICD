"""
Web-Eval-Agent Integration - Browser automation and UI validation for CICD pipeline
"""
import asyncio
import json
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class WebEvalTestResult:
    """Result from web-eval-agent test execution"""
    def __init__(
        self,
        success: bool,
        test_name: str,
        duration: float,
        details: Dict[str, Any],
        screenshots: List[str] = None,
        errors: List[str] = None
    ):
        self.success = success
        self.test_name = test_name
        self.duration = duration
        self.details = details
        self.screenshots = screenshots or []
        self.errors = errors or []
        self.timestamp = datetime.utcnow()


class WebEvalAgentIntegration:
    """
    Integration with web-eval-agent for comprehensive UI testing and validation.
    
    This service orchestrates browser automation tests to validate:
    - UI functionality and user flows
    - Component interactions and state management
    - Cross-browser compatibility
    - Performance and accessibility
    """
    
    def __init__(self):
        self.web_eval_path = "/tmp/web-eval-agent"
        self.test_timeout = 300  # 5 minutes per test
        self.max_concurrent_tests = 3
        self._active_tests: Dict[str, asyncio.Task] = {}
    
    async def validate_pr_deployment(
        self,
        project_name: str,
        pr_number: int,
        deployment_url: str,
        test_scenarios: List[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a PR deployment using comprehensive web-eval-agent testing.
        
        Args:
            project_name: Name of the project being tested
            pr_number: PR number for tracking
            deployment_url: URL of the deployed application
            test_scenarios: Specific test scenarios to run
            
        Returns:
            Comprehensive validation results
        """
        test_id = f"{project_name}-pr-{pr_number}-{int(datetime.utcnow().timestamp())}"
        
        try:
            logger.info("Starting PR validation", 
                       test_id=test_id,
                       project=project_name,
                       pr_number=pr_number,
                       url=deployment_url)
            
            # Default test scenarios if none provided
            if not test_scenarios:
                test_scenarios = [
                    "basic_navigation",
                    "component_interaction", 
                    "form_validation",
                    "responsive_design",
                    "accessibility_check"
                ]
            
            # Run all test scenarios
            test_results = []
            for scenario in test_scenarios:
                result = await self._run_test_scenario(
                    test_id, 
                    scenario, 
                    deployment_url,
                    project_name
                )
                test_results.append(result)
            
            # Analyze overall results
            validation_result = self._analyze_test_results(test_results)
            validation_result.update({
                "test_id": test_id,
                "project_name": project_name,
                "pr_number": pr_number,
                "deployment_url": deployment_url,
                "test_scenarios": test_scenarios,
                "completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info("PR validation completed", 
                       test_id=test_id,
                       overall_success=validation_result["overall_success"],
                       passed_tests=validation_result["passed_tests"],
                       total_tests=validation_result["total_tests"])
            
            return validation_result
            
        except Exception as e:
            logger.error("PR validation failed", 
                        test_id=test_id,
                        error=str(e))
            return {
                "test_id": test_id,
                "overall_success": False,
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
    
    async def _run_test_scenario(
        self,
        test_id: str,
        scenario: str,
        deployment_url: str,
        project_name: str
    ) -> WebEvalTestResult:
        """Run a specific test scenario using web-eval-agent."""
        start_time = datetime.utcnow()
        
        try:
            logger.info("Running test scenario", 
                       test_id=test_id,
                       scenario=scenario,
                       url=deployment_url)
            
            # Create test configuration
            test_config = self._create_test_config(scenario, deployment_url, project_name)
            
            # Execute web-eval-agent test
            result = await self._execute_web_eval_test(test_id, scenario, test_config)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return WebEvalTestResult(
                success=result.get("success", False),
                test_name=scenario,
                duration=duration,
                details=result,
                screenshots=result.get("screenshots", []),
                errors=result.get("errors", [])
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error("Test scenario failed", 
                        test_id=test_id,
                        scenario=scenario,
                        error=str(e))
            
            return WebEvalTestResult(
                success=False,
                test_name=scenario,
                duration=duration,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    def _create_test_config(
        self, 
        scenario: str, 
        deployment_url: str, 
        project_name: str
    ) -> Dict[str, Any]:
        """Create test configuration for specific scenario."""
        
        base_config = {
            "url": deployment_url,
            "project_name": project_name,
            "timeout": self.test_timeout,
            "screenshot_on_failure": True,
            "headless": True
        }
        
        # Scenario-specific configurations
        scenario_configs = {
            "basic_navigation": {
                "test_type": "navigation",
                "actions": [
                    {"action": "goto", "url": deployment_url},
                    {"action": "wait", "selector": "body", "timeout": 10000},
                    {"action": "screenshot", "name": "homepage"},
                    {"action": "check_title", "expected": project_name},
                    {"action": "check_responsive", "breakpoints": ["mobile", "tablet", "desktop"]}
                ]
            },
            "component_interaction": {
                "test_type": "interaction",
                "actions": [
                    {"action": "goto", "url": deployment_url},
                    {"action": "find_and_click", "selectors": ["button", "[role='button']", ".btn"]},
                    {"action": "check_forms", "validate_required": True},
                    {"action": "test_dropdowns", "validate_options": True},
                    {"action": "test_modals", "check_close": True}
                ]
            },
            "form_validation": {
                "test_type": "forms",
                "actions": [
                    {"action": "goto", "url": deployment_url},
                    {"action": "find_forms", "test_validation": True},
                    {"action": "test_required_fields", "expect_errors": True},
                    {"action": "test_input_types", "validate_formats": True},
                    {"action": "test_submit", "check_success": True}
                ]
            },
            "responsive_design": {
                "test_type": "responsive",
                "actions": [
                    {"action": "goto", "url": deployment_url},
                    {"action": "test_breakpoints", "sizes": [
                        {"width": 320, "height": 568, "name": "mobile"},
                        {"width": 768, "height": 1024, "name": "tablet"},
                        {"width": 1920, "height": 1080, "name": "desktop"}
                    ]},
                    {"action": "check_layout", "validate_overflow": True},
                    {"action": "test_navigation", "mobile_menu": True}
                ]
            },
            "accessibility_check": {
                "test_type": "accessibility",
                "actions": [
                    {"action": "goto", "url": deployment_url},
                    {"action": "check_aria_labels", "required": True},
                    {"action": "test_keyboard_navigation", "tab_order": True},
                    {"action": "check_color_contrast", "wcag_level": "AA"},
                    {"action": "validate_headings", "hierarchy": True},
                    {"action": "check_alt_text", "images": True}
                ]
            }
        }
        
        config = {**base_config, **scenario_configs.get(scenario, {})}
        return config
    
    async def _execute_web_eval_test(
        self, 
        test_id: str, 
        scenario: str, 
        test_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute web-eval-agent test with given configuration."""
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f, indent=2)
            config_file = f.name
        
        try:
            # Prepare web-eval-agent command
            cmd = [
                "python", "-m", "web_eval_agent.main",
                "--config", config_file,
                "--output-dir", f"/tmp/web-eval-results/{test_id}",
                "--scenario", scenario
            ]
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
                "PYTHONPATH": f"{self.web_eval_path}:{env.get('PYTHONPATH', '')}"
            })
            
            # Execute with timeout
            logger.info("Executing web-eval-agent", 
                       test_id=test_id,
                       scenario=scenario,
                       cmd=" ".join(cmd))
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.web_eval_path
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=self.test_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise Exception(f"Test timed out after {self.test_timeout} seconds")
            
            # Parse results
            if process.returncode == 0:
                result = self._parse_test_output(stdout.decode(), stderr.decode())
                result["success"] = True
            else:
                result = {
                    "success": False,
                    "error": stderr.decode(),
                    "stdout": stdout.decode(),
                    "return_code": process.returncode
                }
            
            return result
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(config_file)
            except:
                pass
    
    def _parse_test_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse web-eval-agent output into structured results."""
        result = {
            "stdout": stdout,
            "stderr": stderr,
            "screenshots": [],
            "errors": [],
            "metrics": {},
            "accessibility_issues": [],
            "performance_metrics": {}
        }
        
        # Try to parse JSON output if present
        try:
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.startswith('{') and line.endswith('}'):
                    parsed = json.loads(line)
                    result.update(parsed)
                    break
        except:
            pass
        
        # Extract screenshots from output
        screenshot_lines = [line for line in stdout.split('\n') if 'screenshot' in line.lower()]
        result["screenshots"] = screenshot_lines
        
        # Extract errors from stderr
        if stderr:
            result["errors"] = stderr.split('\n')
        
        # Extract performance metrics (simplified)
        if "load time" in stdout.lower():
            import re
            load_time_match = re.search(r'load time[:\s]+(\d+\.?\d*)', stdout.lower())
            if load_time_match:
                result["metrics"]["load_time"] = float(load_time_match.group(1))
        
        return result
    
    def _analyze_test_results(self, test_results: List[WebEvalTestResult]) -> Dict[str, Any]:
        """Analyze test results to determine overall validation status."""
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results if result.success)
        failed_tests = total_tests - passed_tests
        
        # Calculate overall success (require 80% pass rate)
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        overall_success = pass_rate >= 0.8
        
        # Collect all errors
        all_errors = []
        for result in test_results:
            all_errors.extend(result.errors)
        
        # Collect all screenshots
        all_screenshots = []
        for result in test_results:
            all_screenshots.extend(result.screenshots)
        
        # Calculate metrics
        total_duration = sum(result.duration for result in test_results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        
        # Categorize failures
        critical_failures = []
        minor_failures = []
        
        for result in test_results:
            if not result.success:
                if result.test_name in ["basic_navigation", "component_interaction"]:
                    critical_failures.append(result.test_name)
                else:
                    minor_failures.append(result.test_name)
        
        return {
            "overall_success": overall_success,
            "pass_rate": pass_rate,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "critical_failures": critical_failures,
            "minor_failures": minor_failures,
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "all_errors": all_errors,
            "screenshots": all_screenshots,
            "test_details": [
                {
                    "name": result.test_name,
                    "success": result.success,
                    "duration": result.duration,
                    "errors": result.errors
                }
                for result in test_results
            ]
        }
    
    async def test_cicd_dashboard_flow(self, dashboard_url: str) -> Dict[str, Any]:
        """
        Test the complete CICD dashboard flow to validate the system works end-to-end.
        
        This is a comprehensive test that validates:
        1. Project selection and configuration
        2. Agent run creation and monitoring
        3. Plan confirmation workflow
        4. Real-time status updates
        5. PR notification handling
        """
        test_id = f"cicd-dashboard-{int(datetime.utcnow().timestamp())}"
        
        try:
            logger.info("Starting CICD dashboard flow test", 
                       test_id=test_id,
                       url=dashboard_url)
            
            # Test configuration for CICD dashboard
            test_config = {
                "url": dashboard_url,
                "test_type": "cicd_flow",
                "timeout": 600,  # 10 minutes for full flow
                "actions": [
                    # 1. Load dashboard and verify components
                    {"action": "goto", "url": dashboard_url},
                    {"action": "wait", "selector": "[data-testid='dashboard']", "timeout": 10000},
                    {"action": "screenshot", "name": "dashboard_loaded"},
                    
                    # 2. Test project selector
                    {"action": "click", "selector": "[data-testid='project-selector']"},
                    {"action": "wait", "selector": "[data-testid='project-dropdown']"},
                    {"action": "screenshot", "name": "project_selector_open"},
                    
                    # 3. Select a project
                    {"action": "click", "selector": "[data-testid='project-option']:first-child"},
                    {"action": "wait", "selector": "[data-testid='project-card']"},
                    {"action": "screenshot", "name": "project_selected"},
                    
                    # 4. Test agent run dialog
                    {"action": "click", "selector": "[data-testid='agent-run-button']"},
                    {"action": "wait", "selector": "[data-testid='agent-run-dialog']"},
                    {"action": "type", "selector": "[data-testid='target-input']", "text": "Create a simple test component"},
                    {"action": "screenshot", "name": "agent_run_dialog"},
                    
                    # 5. Start agent run
                    {"action": "click", "selector": "[data-testid='confirm-agent-run']"},
                    {"action": "wait", "selector": "[data-testid='agent-run-status']"},
                    {"action": "screenshot", "name": "agent_run_started"},
                    
                    # 6. Monitor status updates
                    {"action": "wait_for_text", "text": "running", "timeout": 30000},
                    {"action": "screenshot", "name": "agent_run_running"},
                    
                    # 7. Test settings dialog
                    {"action": "click", "selector": "[data-testid='project-settings']"},
                    {"action": "wait", "selector": "[data-testid='settings-dialog']"},
                    {"action": "screenshot", "name": "settings_dialog"},
                    
                    # 8. Test secrets management
                    {"action": "click", "selector": "[data-testid='secrets-tab']"},
                    {"action": "wait", "selector": "[data-testid='secrets-panel']"},
                    {"action": "screenshot", "name": "secrets_panel"},
                    
                    # 9. Close dialogs and verify state
                    {"action": "click", "selector": "[data-testid='close-dialog']"},
                    {"action": "wait", "selector": "[data-testid='dashboard']"},
                    {"action": "screenshot", "name": "final_state"}
                ]
            }
            
            # Execute the test
            result = await self._execute_web_eval_test(test_id, "cicd_flow", test_config)
            
            # Analyze CICD-specific results
            cicd_analysis = self._analyze_cicd_flow_results(result)
            
            logger.info("CICD dashboard flow test completed", 
                       test_id=test_id,
                       success=cicd_analysis["success"])
            
            return cicd_analysis
            
        except Exception as e:
            logger.error("CICD dashboard flow test failed", 
                        test_id=test_id,
                        error=str(e))
            return {
                "test_id": test_id,
                "success": False,
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
    
    def _analyze_cicd_flow_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze CICD flow test results for specific workflow validation."""
        
        # Check for key workflow components
        workflow_checks = {
            "dashboard_loaded": "dashboard_loaded" in str(result.get("screenshots", [])),
            "project_selection": "project_selected" in str(result.get("screenshots", [])),
            "agent_run_creation": "agent_run_started" in str(result.get("screenshots", [])),
            "settings_access": "settings_dialog" in str(result.get("screenshots", [])),
            "secrets_management": "secrets_panel" in str(result.get("screenshots", []))
        }
        
        # Calculate workflow success
        passed_checks = sum(1 for check in workflow_checks.values() if check)
        total_checks = len(workflow_checks)
        workflow_success = passed_checks / total_checks >= 0.8
        
        return {
            "test_id": result.get("test_id"),
            "success": result.get("success", False) and workflow_success,
            "workflow_success": workflow_success,
            "workflow_checks": workflow_checks,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "errors": result.get("errors", []),
            "screenshots": result.get("screenshots", []),
            "raw_result": result,
            "completed_at": datetime.utcnow().isoformat()
        }


# Global instance
web_eval_agent_integration = WebEvalAgentIntegration()

