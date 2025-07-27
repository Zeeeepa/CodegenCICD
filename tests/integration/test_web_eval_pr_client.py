"""
Integration tests for Web-Eval-Agent PR Client
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.integrations.web_eval_pr_client import (
    WebEvalPRClient,
    PRTestScope,
    PRRiskLevel
)
from backend.services.resource_manager import ResourceType


class TestWebEvalPRClient:
    """Test suite for Web-Eval-Agent PR Client"""
    
    @pytest.fixture
    def pr_client(self):
        """Create test PR client instance"""
        return WebEvalPRClient("http://test-webeval:8081")
    
    @pytest.fixture
    def sample_changed_files(self):
        """Sample changed files for testing"""
        return [
            "src/components/Header.tsx",
            "src/components/Button.tsx", 
            "src/styles/main.scss",
            "src/pages/login.html",
            "package.json",
            "src/utils/api.ts",  # Non-UI file
            "README.md"  # Non-UI file
        ]
    
    def test_pr_client_initialization(self, pr_client):
        """Test PR client initialization"""
        assert pr_client.service_name == "web_eval_agent"
        assert pr_client.correlation_id is not None
        assert len(pr_client.pr_sessions) == 0
        assert len(pr_client.baseline_cache) == 0
    
    def test_analyze_ui_changes(self, pr_client, sample_changed_files):
        """Test UI change analysis"""
        ui_changes = pr_client._analyze_ui_changes(sample_changed_files)
        
        # Check components detection
        assert "Header.tsx" in str(ui_changes["components"])
        assert "Button.tsx" in str(ui_changes["components"])
        
        # Check styles detection
        assert "main.scss" in str(ui_changes["styles"])
        
        # Check templates detection
        assert "login.html" in str(ui_changes["templates"])
        
        # Check dependency changes
        assert "package.json" in str(ui_changes["dependency_changes"])
        
        # Check risk level calculation
        assert ui_changes["risk_level"] in ["low", "medium", "high"]
    
    def test_analyze_ui_changes_high_risk(self, pr_client):
        """Test high risk UI change detection"""
        high_risk_files = [
            f"src/components/Component{i}.tsx" for i in range(15)
        ] + ["package.json"]
        
        ui_changes = pr_client._analyze_ui_changes(high_risk_files)
        
        assert ui_changes["risk_level"] == "high"
        assert len(ui_changes["components"]) == 15
        assert len(ui_changes["dependency_changes"]) == 1
    
    def test_determine_test_scope_high_risk(self, pr_client):
        """Test test scope determination for high risk changes"""
        ui_changes = {"risk_level": "high"}
        test_scope = pr_client._determine_test_scope(ui_changes)
        
        assert test_scope["coverage"] == "comprehensive"
        assert test_scope["visual_regression"] == "full_page_and_components"
        assert test_scope["accessibility"] == "complete_audit"
        assert test_scope["performance"] == "full_analysis"
        assert test_scope["cross_browser"] == "all_supported"
        assert test_scope["mobile"] == "all_devices"
    
    def test_determine_test_scope_medium_risk(self, pr_client):
        """Test test scope determination for medium risk changes"""
        ui_changes = {"risk_level": "medium"}
        test_scope = pr_client._determine_test_scope(ui_changes)
        
        assert test_scope["coverage"] == "focused"
        assert test_scope["visual_regression"] == "affected_components"
        assert test_scope["accessibility"] == "changed_areas"
        assert test_scope["performance"] == "critical_metrics"
        assert test_scope["cross_browser"] == "primary_browsers"
        assert test_scope["mobile"] == "key_devices"
    
    def test_determine_test_scope_low_risk(self, pr_client):
        """Test test scope determination for low risk changes"""
        ui_changes = {"risk_level": "low"}
        test_scope = pr_client._determine_test_scope(ui_changes)
        
        assert test_scope["coverage"] == "minimal"
        assert test_scope["visual_regression"] == "component_level"
        assert test_scope["accessibility"] == "basic_checks"
        assert test_scope["performance"] == "core_vitals"
        assert test_scope["cross_browser"] == "chromium_only"
        assert test_scope["mobile"] == "single_device"
    
    @pytest.mark.asyncio
    async def test_create_pr_test_session(self, pr_client, sample_changed_files):
        """Test PR test session creation"""
        expected_response = {
            "session_id": "pr-session-123",
            "status": "created",
            "pr_number": 42
        }
        
        with patch.object(pr_client, '_execute_with_enhancements', return_value=expected_response):
            with patch('backend.integrations.web_eval_pr_client.resource_manager') as mock_rm:
                result = await pr_client.create_pr_test_session(
                    pr_number=42,
                    base_branch="main",
                    head_branch="feature/ui-updates",
                    repository_url="https://github.com/test/repo",
                    changed_files=sample_changed_files
                )
                
                assert result == expected_response
                
                # Verify resource manager registration
                mock_rm.register_resource.assert_called_once()
                call_args = mock_rm.register_resource.call_args
                assert call_args[1]["resource_id"] == "pr-session-123"
                assert call_args[1]["resource_type"] == ResourceType.PROCESS
                assert call_args[1]["metadata"]["pr_number"] == 42
                assert call_args[1]["metadata"]["session_type"] == "pr_validation"
                
                # Verify PR session tracking
                assert "pr-session-123" in pr_client.pr_sessions
                session_info = pr_client.pr_sessions["pr-session-123"]
                assert session_info["pr_number"] == 42
                assert session_info["base_branch"] == "main"
                assert session_info["head_branch"] == "feature/ui-updates"
    
    @pytest.mark.asyncio
    async def test_run_pr_ui_validation(self, pr_client):
        """Test PR UI validation execution"""
        # Set up session info
        pr_client.pr_sessions["test-session"] = {
            "ui_changes": {
                "components": ["Header.tsx", "Button.tsx"],
                "risk_level": "medium",
                "responsive_changes": ["mobile.scss"]
            }
        }
        
        expected_response = {
            "tests_executed": 15,
            "issues_found": 3,
            "visual_regression": {"differences_found": 2},
            "accessibility": {"violations": 1},
            "performance": {"budget_violations": 0}
        }
        
        with patch.object(pr_client, '_execute_with_enhancements', return_value=expected_response):
            result = await pr_client.run_pr_ui_validation(
                session_id="test-session",
                base_url="https://test.example.com",
                pr_preview_url="https://preview.example.com"
            )
            
            assert result == expected_response
            assert result["tests_executed"] == 15
            assert result["issues_found"] == 3
    
    def test_analyze_test_results_for_status_success(self, pr_client):
        """Test test result analysis for successful status"""
        test_results = {
            "visual_regression": {
                "critical_differences": 0,
                "minor_differences": 2,
                "total_comparisons": 10
            },
            "accessibility": {
                "critical_violations": 0,
                "warnings": 1,
                "total_checks": 15
            },
            "performance": {
                "budget_violations": 0,
                "performance_warnings": 0,
                "total_metrics": 5
            }
        }
        
        status = pr_client._analyze_test_results_for_status(test_results)
        
        assert status["state"] == "success"
        assert "3 minor warnings" in status["description"]
    
    def test_analyze_test_results_for_status_failure(self, pr_client):
        """Test test result analysis for failure status"""
        test_results = {
            "visual_regression": {
                "critical_differences": 2,
                "minor_differences": 1,
                "total_comparisons": 10
            },
            "accessibility": {
                "critical_violations": 1,
                "warnings": 2,
                "total_checks": 15
            },
            "performance": {
                "budget_violations": 1,
                "performance_warnings": 0,
                "total_metrics": 5
            }
        }
        
        status = pr_client._analyze_test_results_for_status(test_results)
        
        assert status["state"] == "failure"
        assert "4 critical issues" in status["description"]
    
    @pytest.mark.asyncio
    async def test_generate_pr_test_report(self, pr_client):
        """Test PR test report generation"""
        expected_response = {
            "report_url": "https://reports.example.com/pr-42.html",
            "github_comment_posted": True,
            "status_check_created": True
        }
        
        with patch.object(pr_client, '_execute_with_enhancements', return_value=expected_response):
            result = await pr_client.generate_pr_test_report(
                session_id="test-session",
                pr_number=42,
                include_github_integration=True
            )
            
            assert result == expected_response
            assert result["github_comment_posted"] is True
            assert "reports.example.com" in result["report_url"]
    
    @pytest.mark.asyncio
    async def test_create_github_status_check(self, pr_client):
        """Test GitHub status check creation"""
        test_results = {
            "visual_regression": {"critical_differences": 0, "total_comparisons": 5},
            "accessibility": {"critical_violations": 0, "total_checks": 10},
            "performance": {"budget_violations": 0, "total_metrics": 3},
            "report_url": "https://reports.example.com/test.html"
        }
        
        expected_response = {
            "status_check_id": "check-123",
            "state": "success",
            "created": True
        }
        
        with patch.object(pr_client, '_execute_with_enhancements', return_value=expected_response):
            result = await pr_client.create_github_status_check(
                session_id="test-session",
                pr_number=42,
                repository="test/repo",
                commit_sha="abc123",
                test_results=test_results
            )
            
            assert result == expected_response
            assert result["state"] == "success"
    
    @pytest.mark.asyncio
    async def test_run_automated_baseline_update(self, pr_client):
        """Test automated baseline update"""
        expected_response = {
            "baselines_updated": 5,
            "manual_approval_required": 2,
            "backup_created": True
        }
        
        with patch.object(pr_client, '_execute_with_enhancements', return_value=expected_response):
            result = await pr_client.run_automated_baseline_update(
                session_id="test-session",
                branch_name="feature/ui-updates",
                update_strategy="smart"
            )
            
            assert result == expected_response
            assert result["baselines_updated"] == 5
            assert result["manual_approval_required"] == 2
    
    @pytest.mark.asyncio
    async def test_run_component_isolation_tests(self, pr_client):
        """Test component isolation testing"""
        components = ["Header", "Button", "Modal"]
        
        expected_response = {
            "components_tested": 3,
            "issues_found": 1,
            "test_results": {
                "Header": {"status": "passed"},
                "Button": {"status": "passed"},
                "Modal": {"status": "failed", "issues": ["Accessibility violation"]}
            }
        }
        
        with patch.object(pr_client, '_execute_with_enhancements', return_value=expected_response):
            result = await pr_client.run_component_isolation_tests(
                session_id="test-session",
                components=components,
                test_config={"mock_dependencies": True}
            )
            
            assert result == expected_response
            assert result["components_tested"] == 3
            assert result["issues_found"] == 1
    
    def test_generate_pr_comment_markdown_success(self, pr_client):
        """Test PR comment markdown generation for successful tests"""
        test_results = {
            "visual_regression": {
                "differences_found": 0,
                "total_comparisons": 10
            },
            "accessibility": {
                "total_violations": 0,
                "total_checks": 15
            },
            "performance": {
                "budget_violations": 0,
                "average_score": 95,
                "total_metrics": 5
            },
            "report_url": "https://reports.example.com/test.html"
        }
        
        markdown = pr_client._generate_pr_comment_markdown(test_results)
        
        assert "✅ UI Test Results" in markdown
        assert "No visual regressions detected" in markdown
        assert "No accessibility regressions detected" in markdown
        assert "Performance within budget" in markdown
        assert "Score: 95/100" in markdown
        assert "View Detailed Report" in markdown
    
    def test_generate_pr_comment_markdown_with_issues(self, pr_client):
        """Test PR comment markdown generation with issues"""
        test_results = {
            "visual_regression": {
                "differences_found": 3,
                "critical_differences": 1,
                "minor_differences": 2,
                "total_comparisons": 10
            },
            "accessibility": {
                "total_violations": 2,
                "critical_violations": 1,
                "warnings": 1,
                "total_checks": 15
            },
            "performance": {
                "budget_violations": 1,
                "average_score": 72,
                "total_metrics": 5
            },
            "recommendations": [
                "Optimize image loading",
                "Fix color contrast issues",
                "Add ARIA labels"
            ]
        }
        
        markdown = pr_client._generate_pr_comment_markdown(test_results)
        
        assert "❌ UI Test Results" in markdown
        assert "Differences Found: 3" in markdown
        assert "Critical Changes: 1" in markdown
        assert "Total Violations: 2" in markdown
        assert "Budget Violations: 1" in markdown
        assert "💡 Recommendations" in markdown
        assert "Optimize image loading" in markdown
    
    @pytest.mark.asyncio
    async def test_create_pr_comment_with_results(self, pr_client):
        """Test PR comment creation with test results"""
        test_results = {
            "visual_regression": {"differences_found": 0},
            "accessibility": {"total_violations": 0},
            "performance": {"budget_violations": 0, "average_score": 95}
        }
        
        expected_response = {
            "comment_id": "comment-123",
            "comment_url": "https://github.com/test/repo/pull/42#issuecomment-123",
            "updated_existing": False
        }
        
        with patch.object(pr_client, '_execute_with_enhancements', return_value=expected_response):
            result = await pr_client.create_pr_comment_with_results(
                session_id="test-session",
                pr_number=42,
                test_results=test_results,
                repository="test/repo"
            )
            
            assert result == expected_response
            assert result["comment_id"] == "comment-123"


class TestPREnums:
    """Test PR-specific enum types"""
    
    def test_pr_test_scope_enum(self):
        """Test PRTestScope enum values"""
        assert PRTestScope.MINIMAL.value == "minimal"
        assert PRTestScope.FOCUSED.value == "focused"
        assert PRTestScope.COMPREHENSIVE.value == "comprehensive"
    
    def test_pr_risk_level_enum(self):
        """Test PRRiskLevel enum values"""
        assert PRRiskLevel.LOW.value == "low"
        assert PRRiskLevel.MEDIUM.value == "medium"
        assert PRRiskLevel.HIGH.value == "high"
        assert PRRiskLevel.CRITICAL.value == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
