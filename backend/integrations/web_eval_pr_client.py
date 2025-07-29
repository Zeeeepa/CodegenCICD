"""
PR-specific Web-Eval-Agent client for enhanced UI testing in CI/CD workflows
"""
import asyncio
import uuid
import re
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
import structlog

from .web_eval_client import EnhancedWebEvalClient, TestType, BrowserType, DeviceType
from backend.services.resource_manager import resource_manager, ResourceType
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class PRTestScope(Enum):
    """Test scope levels for PR validation"""
    MINIMAL = "minimal"
    FOCUSED = "focused"
    COMPREHENSIVE = "comprehensive"


class PRRiskLevel(Enum):
    """Risk levels for PR changes"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WebEvalPRClient(EnhancedWebEvalClient):
    """Enhanced Web-Eval-Agent client specialized for PR-based UI testing"""
    
    def __init__(self, base_url: Optional[str] = None):
        super().__init__(base_url)
        
        # PR-specific tracking
        self.pr_sessions = {}
        self.baseline_cache = {}
        
        self.logger = logger.bind(
            service="web_eval_pr_agent",
            correlation_id=self.correlation_id
        )
    
    async def create_pr_test_session(self,
                                   pr_number: int,
                                   base_branch: str,
                                   head_branch: str,
                                   repository_url: str,
                                   changed_files: List[str],
                                   test_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a specialized test session for PR validation"""
        
        # Analyze changed files to determine test scope
        ui_changes = self._analyze_ui_changes(changed_files)
        
        # Default PR test configuration
        default_config = {
            "session_type": "pr_validation",
            "pr_context": {
                "pr_number": pr_number,
                "base_branch": base_branch,
                "head_branch": head_branch,
                "repository_url": repository_url,
                "changed_files": changed_files,
                "ui_changes": ui_changes
            },
            "test_strategy": "smart_selective",
            "baseline_management": "automatic",
            "visual_regression": {
                "enabled": True,
                "sensitivity": "high",
                "focus_on_changes": True,
                "component_isolation": True
            },
            "accessibility_testing": {
                "enabled": True,
                "focus_on_modified_components": True,
                "regression_detection": True
            },
            "performance_testing": {
                "enabled": True,
                "compare_with_baseline": True,
                "budget_enforcement": True,
                "focus_on_critical_paths": True
            },
            "cross_browser_testing": {
                "enabled": len(ui_changes["components"]) > 0,
                "browsers": ["chromium", "firefox", "webkit"],
                "focus_on_compatibility_risks": True
            },
            "mobile_testing": {
                "enabled": len(ui_changes["responsive_changes"]) > 0,
                "devices": ["iPhone 12", "Pixel 5", "iPad Pro"],
                "focus_on_responsive_changes": True
            },
            "reporting": {
                "pr_comment_integration": True,
                "github_status_checks": True,
                "detailed_diff_analysis": True,
                "component_level_results": True
            }
        }
        
        # Merge with user config
        merged_config = {**default_config, **(test_config or {})}
        
        payload = {
            "project_name": f"PR-{pr_number}",
            "base_url": merged_config.get("base_url", "http://localhost:3000"),
            "correlation_id": self.correlation_id,
            "config": merged_config
        }
        
        self.logger.info("Creating PR-specific test session",
                       pr_number=pr_number,
                       base_branch=base_branch,
                       head_branch=head_branch,
                       ui_changes=len(ui_changes["components"]),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            "/sessions/pr-validation",
            data=payload
        )
        
        session_id = response.get("session_id")
        
        # Register session with enhanced PR metadata
        if session_id:
            cleanup_callback = lambda sid: self._cleanup_session_callback(sid)
            resource_manager.register_resource(
                resource_id=session_id,
                resource_type=ResourceType.PROCESS,
                metadata={
                    "session_type": "pr_validation",
                    "pr_number": pr_number,
                    "base_branch": base_branch,
                    "head_branch": head_branch,
                    "repository_url": repository_url,
                    "ui_changes": ui_changes,
                    "created_by": "web_eval_pr_client",
                    "correlation_id": self.correlation_id
                },
                cleanup_callbacks=[cleanup_callback]
            )
            
            # Track PR session
            self.pr_sessions[session_id] = {
                "session_type": "pr_validation",
                "pr_number": pr_number,
                "base_branch": base_branch,
                "head_branch": head_branch,
                "created_at": datetime.utcnow(),
                "status": "active",
                "ui_changes": ui_changes
            }
        
        self.logger.info("PR test session created",
                       session_id=session_id,
                       pr_number=pr_number,
                       correlation_id=self.correlation_id)
        
        return response
    
    def _analyze_ui_changes(self, changed_files: List[str]) -> Dict[str, Any]:
        """Analyze changed files to identify UI-related modifications"""
        
        ui_file_patterns = [
            r'\.tsx?$', r'\.jsx?$', r'\.vue$', r'\.svelte$',  # Component files
            r'\.css$', r'\.scss$', r'\.sass$', r'\.less$',    # Style files
            r'\.html$', r'\.htm$',                            # Template files
            r'\.json$',                                       # Config files
            r'package\.json$', r'yarn\.lock$', r'package-lock\.json$'  # Dependencies
        ]
        
        ui_changes = {
            "components": [],
            "styles": [],
            "templates": [],
            "responsive_changes": [],
            "accessibility_changes": [],
            "performance_changes": [],
            "dependency_changes": [],
            "risk_level": "low"
        }
        
        for file_path in changed_files:
            # Check if file is UI-related
            is_ui_file = any(re.search(pattern, file_path, re.IGNORECASE) 
                           for pattern in ui_file_patterns)
            
            if is_ui_file:
                if any(ext in file_path.lower() for ext in ['.tsx', '.jsx', '.vue', '.svelte']):
                    ui_changes["components"].append(file_path)
                elif any(ext in file_path.lower() for ext in ['.css', '.scss', '.sass', '.less']):
                    ui_changes["styles"].append(file_path)
                elif any(ext in file_path.lower() for ext in ['.html', '.htm']):
                    ui_changes["templates"].append(file_path)
                elif 'package' in file_path.lower():
                    ui_changes["dependency_changes"].append(file_path)
                
                # Analyze file content patterns
                file_lower = file_path.lower()
                
                if any(pattern in file_lower for pattern in ['responsive', 'mobile', 'breakpoint']):
                    ui_changes["responsive_changes"].append(file_path)
                
                if any(pattern in file_lower for pattern in ['accessibility', 'a11y', 'aria']):
                    ui_changes["accessibility_changes"].append(file_path)
                
                if any(pattern in file_lower for pattern in ['performance', 'lazy', 'bundle']):
                    ui_changes["performance_changes"].append(file_path)
        
        # Determine risk level
        total_ui_files = (len(ui_changes["components"]) + 
                         len(ui_changes["styles"]) + 
                         len(ui_changes["templates"]))
        
        if total_ui_files > 10 or len(ui_changes["dependency_changes"]) > 0:
            ui_changes["risk_level"] = "high"
        elif total_ui_files > 5 or len(ui_changes["responsive_changes"]) > 0:
            ui_changes["risk_level"] = "medium"
        else:
            ui_changes["risk_level"] = "low"
        
        return ui_changes
    
    async def run_pr_ui_validation(self,
                                 session_id: str,
                                 base_url: str,
                                 pr_preview_url: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive UI validation for a PR"""
        
        session_info = self.pr_sessions.get(session_id, {})
        ui_changes = session_info.get("ui_changes", {})
        
        # Determine test scope based on changes
        test_scope = self._determine_test_scope(ui_changes)
        
        payload = {
            "base_url": base_url,
            "pr_preview_url": pr_preview_url,
            "test_scope": test_scope,
            "validation_config": {
                "visual_regression": {
                    "enabled": True,
                    "component_isolation": True,
                    "focus_areas": ui_changes.get("components", []),
                    "baseline_strategy": "auto_baseline"
                },
                "accessibility_validation": {
                    "enabled": True,
                    "standards": ["WCAG2.1", "Section508"],
                    "focus_on_changes": True,
                    "regression_detection": True
                },
                "performance_validation": {
                    "enabled": True,
                    "metrics": ["FCP", "LCP", "CLS", "FID", "TTI"],
                    "budget_enforcement": True,
                    "baseline_comparison": True
                },
                "responsive_validation": {
                    "enabled": len(ui_changes.get("responsive_changes", [])) > 0,
                    "breakpoints": ["mobile", "tablet", "desktop"],
                    "focus_on_changes": ui_changes.get("responsive_changes", [])
                },
                "cross_browser_validation": {
                    "enabled": ui_changes.get("risk_level") in ["medium", "high"],
                    "browsers": ["chromium", "firefox", "webkit"],
                    "compatibility_focus": True
                }
            },
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Running PR UI validation",
                       session_id=session_id,
                       test_scope=test_scope,
                       risk_level=ui_changes.get("risk_level", "unknown"),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/pr-validation",
            data=payload
        )
        
        self.logger.info("PR UI validation completed",
                       session_id=session_id,
                       tests_executed=response.get("tests_executed", 0),
                       issues_found=response.get("issues_found", 0),
                       correlation_id=self.correlation_id)
        
        return response
    
    def _determine_test_scope(self, ui_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal test scope based on UI changes"""
        
        risk_level = ui_changes.get("risk_level", "low")
        
        if risk_level == "high":
            return {
                "coverage": "comprehensive",
                "visual_regression": "full_page_and_components",
                "accessibility": "complete_audit",
                "performance": "full_analysis",
                "cross_browser": "all_supported",
                "mobile": "all_devices"
            }
        elif risk_level == "medium":
            return {
                "coverage": "focused",
                "visual_regression": "affected_components",
                "accessibility": "changed_areas",
                "performance": "critical_metrics",
                "cross_browser": "primary_browsers",
                "mobile": "key_devices"
            }
        else:
            return {
                "coverage": "minimal",
                "visual_regression": "component_level",
                "accessibility": "basic_checks",
                "performance": "core_vitals",
                "cross_browser": "chromium_only",
                "mobile": "single_device"
            }
    
    async def generate_pr_test_report(self,
                                    session_id: str,
                                    pr_number: int,
                                    include_github_integration: bool = True) -> Dict[str, Any]:
        """Generate PR-specific test report with GitHub integration"""
        
        report_config = {
            "format": "github_markdown",
            "include_screenshots": True,
            "include_diff_analysis": True,
            "include_recommendations": True,
            "sections": [
                "pr_summary",
                "visual_changes_detected",
                "accessibility_impact",
                "performance_impact",
                "cross_browser_compatibility",
                "mobile_responsiveness",
                "recommendations",
                "detailed_results"
            ],
            "github_integration": {
                "enabled": include_github_integration,
                "pr_comment": True,
                "status_checks": True,
                "review_suggestions": True
            },
            "comparison_baseline": "main_branch"
        }
        
        payload = {
            "pr_number": pr_number,
            "report_config": report_config,
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Generating PR test report",
                       session_id=session_id,
                       pr_number=pr_number,
                       github_integration=include_github_integration,
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/reports/pr-report",
            data=payload
        )
        
        self.logger.info("PR test report generated",
                       session_id=session_id,
                       pr_number=pr_number,
                       report_url=response.get("report_url"),
                       github_comment_posted=response.get("github_comment_posted", False),
                       correlation_id=self.correlation_id)
        
        return response
    
    async def create_github_status_check(self,
                                       session_id: str,
                                       pr_number: int,
                                       repository: str,
                                       commit_sha: str,
                                       test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create GitHub status check for PR UI tests"""
        
        # Analyze test results to determine overall status
        overall_status = self._analyze_test_results_for_status(test_results)
        
        payload = {
            "pr_number": pr_number,
            "repository": repository,
            "commit_sha": commit_sha,
            "status_check": {
                "context": "ui-tests/web-eval-agent",
                "state": overall_status["state"],  # success, failure, pending, error
                "description": overall_status["description"],
                "target_url": test_results.get("report_url"),
                "details": {
                    "visual_regression": test_results.get("visual_regression", {}),
                    "accessibility": test_results.get("accessibility", {}),
                    "performance": test_results.get("performance", {}),
                    "cross_browser": test_results.get("cross_browser", {}),
                    "mobile": test_results.get("mobile", {})
                }
            },
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Creating GitHub status check",
                       session_id=session_id,
                       pr_number=pr_number,
                       status=overall_status["state"],
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/github/status-check",
            data=payload
        )
        
        return response
    
    def _analyze_test_results_for_status(self, test_results: Dict[str, Any]) -> Dict[str, str]:
        """Analyze test results to determine GitHub status check state"""
        
        critical_failures = 0
        warnings = 0
        total_tests = 0
        
        # Analyze visual regression results
        visual_results = test_results.get("visual_regression", {})
        if visual_results.get("critical_differences", 0) > 0:
            critical_failures += visual_results["critical_differences"]
        warnings += visual_results.get("minor_differences", 0)
        total_tests += visual_results.get("total_comparisons", 0)
        
        # Analyze accessibility results
        accessibility_results = test_results.get("accessibility", {})
        if accessibility_results.get("critical_violations", 0) > 0:
            critical_failures += accessibility_results["critical_violations"]
        warnings += accessibility_results.get("warnings", 0)
        total_tests += accessibility_results.get("total_checks", 0)
        
        # Analyze performance results
        performance_results = test_results.get("performance", {})
        if performance_results.get("budget_violations", 0) > 0:
            critical_failures += performance_results["budget_violations"]
        warnings += performance_results.get("performance_warnings", 0)
        total_tests += performance_results.get("total_metrics", 0)
        
        # Determine overall status
        if critical_failures > 0:
            return {
                "state": "failure",
                "description": f"UI tests failed: {critical_failures} critical issues found"
            }
        elif warnings > 5:
            return {
                "state": "failure",
                "description": f"UI tests failed: {warnings} warnings exceed threshold"
            }
        elif warnings > 0:
            return {
                "state": "success",
                "description": f"UI tests passed with {warnings} minor warnings"
            }
        else:
            return {
                "state": "success",
                "description": f"All UI tests passed ({total_tests} checks completed)"
            }
    
    async def run_automated_baseline_update(self,
                                          session_id: str,
                                          branch_name: str,
                                          update_strategy: str = "smart") -> Dict[str, Any]:
        """Automatically update visual baselines for approved changes"""
        
        payload = {
            "branch_name": branch_name,
            "update_strategy": update_strategy,  # smart, force, selective
            "baseline_config": {
                "auto_approve_minor_changes": True,
                "require_manual_approval_threshold": 0.1,  # 10% difference
                "preserve_critical_baselines": True,
                "backup_previous_baselines": True
            },
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Running automated baseline update",
                       session_id=session_id,
                       branch_name=branch_name,
                       strategy=update_strategy,
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/baselines/auto-update",
            data=payload
        )
        
        self.logger.info("Automated baseline update completed",
                       session_id=session_id,
                       baselines_updated=response.get("baselines_updated", 0),
                       manual_approval_required=response.get("manual_approval_required", 0),
                       correlation_id=self.correlation_id)
        
        return response
    
    async def run_component_isolation_tests(self,
                                          session_id: str,
                                          components: List[str],
                                          test_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run isolated tests on specific components affected by PR"""
        
        default_config = {
            "isolation_strategy": "component_sandbox",
            "test_types": ["visual", "accessibility", "interaction"],
            "mock_dependencies": True,
            "capture_component_states": True,
            "test_props_variations": True
        }
        
        merged_config = {**default_config, **(test_config or {})}
        
        payload = {
            "components": components,
            "isolation_config": merged_config,
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Running component isolation tests",
                       session_id=session_id,
                       components=len(components),
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/component-isolation",
            data=payload
        )
        
        self.logger.info("Component isolation tests completed",
                       session_id=session_id,
                       components_tested=response.get("components_tested", 0),
                       issues_found=response.get("issues_found", 0),
                       correlation_id=self.correlation_id)
        
        return response
    
    async def create_pr_comment_with_results(self,
                                           session_id: str,
                                           pr_number: int,
                                           test_results: Dict[str, Any],
                                           repository: str) -> Dict[str, Any]:
        """Create a comprehensive PR comment with test results"""
        
        # Generate markdown comment content
        comment_content = self._generate_pr_comment_markdown(test_results)
        
        payload = {
            "pr_number": pr_number,
            "repository": repository,
            "comment_content": comment_content,
            "comment_type": "ui_test_results",
            "update_existing": True,  # Update existing comment if present
            "correlation_id": self.correlation_id
        }
        
        self.logger.info("Creating PR comment with test results",
                       session_id=session_id,
                       pr_number=pr_number,
                       repository=repository,
                       correlation_id=self.correlation_id)
        
        response = await self._execute_with_enhancements(
            self.post,
            f"/sessions/{session_id}/github/pr-comment",
            data=payload
        )
        
        self.logger.info("PR comment created",
                       session_id=session_id,
                       pr_number=pr_number,
                       comment_id=response.get("comment_id"),
                       correlation_id=self.correlation_id)
        
        return response
    
    def _generate_pr_comment_markdown(self, test_results: Dict[str, Any]) -> str:
        """Generate markdown content for PR comment"""
        
        # Extract key metrics
        visual_results = test_results.get("visual_regression", {})
        accessibility_results = test_results.get("accessibility", {})
        performance_results = test_results.get("performance", {})
        
        # Determine overall status emoji
        critical_issues = (
            visual_results.get("critical_differences", 0) +
            accessibility_results.get("critical_violations", 0) +
            performance_results.get("budget_violations", 0)
        )
        
        status_emoji = "✅" if critical_issues == 0 else "❌"
        
        markdown = f"""## {status_emoji} UI Test Results

### 📊 Test Summary
- **Visual Regression**: {visual_results.get('total_comparisons', 0)} comparisons
- **Accessibility**: {accessibility_results.get('total_checks', 0)} checks
- **Performance**: {performance_results.get('total_metrics', 0)} metrics
- **Critical Issues**: {critical_issues}

### 👁️ Visual Changes
"""
        
        if visual_results.get("differences_found", 0) > 0:
            markdown += f"""
- **Differences Found**: {visual_results.get('differences_found', 0)}
- **Critical Changes**: {visual_results.get('critical_differences', 0)}
- **Minor Changes**: {visual_results.get('minor_differences', 0)}
"""
        else:
            markdown += "- ✅ No visual regressions detected\n"
        
        markdown += "\n### ♿ Accessibility Impact\n"
        
        if accessibility_results.get("total_violations", 0) > 0:
            markdown += f"""
- **Total Violations**: {accessibility_results.get('total_violations', 0)}
- **Critical**: {accessibility_results.get('critical_violations', 0)}
- **Warnings**: {accessibility_results.get('warnings', 0)}
"""
        else:
            markdown += "- ✅ No accessibility regressions detected\n"
        
        markdown += "\n### ⚡ Performance Impact\n"
        
        if performance_results.get("budget_violations", 0) > 0:
            markdown += f"""
- **Budget Violations**: {performance_results.get('budget_violations', 0)}
- **Performance Score**: {performance_results.get('average_score', 0)}/100
"""
        else:
            markdown += f"- ✅ Performance within budget (Score: {performance_results.get('average_score', 100)}/100)\n"
        
        # Add recommendations if any
        recommendations = test_results.get("recommendations", [])
        if recommendations:
            markdown += "\n### 💡 Recommendations\n"
            for rec in recommendations[:3]:  # Limit to top 3
                markdown += f"- {rec}\n"
        
        # Add links to detailed reports
        report_url = test_results.get("report_url")
        if report_url:
            markdown += f"\n📋 [View Detailed Report]({report_url})\n"
        
        markdown += "\n---\n*Generated by Web-Eval-Agent PR Testing*"
        
        return markdown
