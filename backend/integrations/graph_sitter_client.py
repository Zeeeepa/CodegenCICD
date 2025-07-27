"""
Graph-sitter client for CodegenCICD Dashboard
"""
from typing import Dict, Any, Optional, List
import structlog

from .base_client import BaseClient, APIError
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GraphSitterClient(BaseClient):
    """Client for interacting with graph-sitter code analysis service"""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use configured graph-sitter URL or default
        self.graph_sitter_url = base_url or getattr(settings, 'graph_sitter_url', 'http://localhost:8082')
        
        super().__init__(
            service_name="graph_sitter",
            base_url=self.graph_sitter_url,
            timeout=120,  # Longer timeout for code analysis
            max_retries=3
        )
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for graph-sitter requests"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def _health_check_request(self) -> None:
        """Health check by getting service status"""
        await self.get("/health")
    
    # Code Analysis
    async def analyze_code_quality(self,
                                 snapshot_id: str,
                                 project_path: str,
                                 languages: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze code quality for a project"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "analysis_type": "quality",
                "languages": languages or ["python", "javascript", "typescript", "java", "go"]
            }
            
            self.logger.info("Analyzing code quality with graph-sitter",
                           snapshot_id=snapshot_id,
                           project_path=project_path,
                           languages=payload["languages"])
            
            response = await self.post("/analyze/quality", data=payload)
            
            overall_score = response.get("overall_score", 0)
            self.logger.info("Code quality analysis completed",
                           snapshot_id=snapshot_id,
                           overall_score=overall_score,
                           files_analyzed=response.get("files_analyzed", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze code quality",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def analyze_complexity(self,
                               snapshot_id: str,
                               project_path: str,
                               threshold: int = 10) -> Dict[str, Any]:
        """Analyze code complexity"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "analysis_type": "complexity",
                "complexity_threshold": threshold
            }
            
            self.logger.info("Analyzing code complexity",
                           snapshot_id=snapshot_id,
                           project_path=project_path,
                           threshold=threshold)
            
            response = await self.post("/analyze/complexity", data=payload)
            
            self.logger.info("Code complexity analysis completed",
                           snapshot_id=snapshot_id,
                           average_complexity=response.get("average_complexity", 0),
                           high_complexity_functions=response.get("high_complexity_count", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze code complexity",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def analyze_security(self,
                             snapshot_id: str,
                             project_path: str,
                             security_rules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze code for security issues"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "analysis_type": "security",
                "security_rules": security_rules or ["sql_injection", "xss", "hardcoded_secrets", "unsafe_functions"]
            }
            
            self.logger.info("Analyzing code security",
                           snapshot_id=snapshot_id,
                           project_path=project_path,
                           rules=payload["security_rules"])
            
            response = await self.post("/analyze/security", data=payload)
            
            self.logger.info("Code security analysis completed",
                           snapshot_id=snapshot_id,
                           vulnerabilities_found=response.get("vulnerabilities_count", 0),
                           security_score=response.get("security_score", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze code security",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def analyze_maintainability(self,
                                    snapshot_id: str,
                                    project_path: str) -> Dict[str, Any]:
        """Analyze code maintainability"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "analysis_type": "maintainability"
            }
            
            self.logger.info("Analyzing code maintainability",
                           snapshot_id=snapshot_id,
                           project_path=project_path)
            
            response = await self.post("/analyze/maintainability", data=payload)
            
            self.logger.info("Code maintainability analysis completed",
                           snapshot_id=snapshot_id,
                           maintainability_index=response.get("maintainability_index", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze code maintainability",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Test Coverage Analysis
    async def analyze_test_coverage(self,
                                  snapshot_id: str,
                                  project_path: str,
                                  test_framework: Optional[str] = None) -> Dict[str, Any]:
        """Analyze test coverage"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "analysis_type": "test_coverage",
                "test_framework": test_framework
            }
            
            self.logger.info("Analyzing test coverage",
                           snapshot_id=snapshot_id,
                           project_path=project_path,
                           test_framework=test_framework)
            
            response = await self.post("/analyze/coverage", data=payload)
            
            self.logger.info("Test coverage analysis completed",
                           snapshot_id=snapshot_id,
                           line_coverage=response.get("line_coverage", 0),
                           branch_coverage=response.get("branch_coverage", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze test coverage",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Documentation Analysis
    async def analyze_documentation(self,
                                  snapshot_id: str,
                                  project_path: str) -> Dict[str, Any]:
        """Analyze code documentation"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "analysis_type": "documentation"
            }
            
            self.logger.info("Analyzing code documentation",
                           snapshot_id=snapshot_id,
                           project_path=project_path)
            
            response = await self.post("/analyze/documentation", data=payload)
            
            self.logger.info("Documentation analysis completed",
                           snapshot_id=snapshot_id,
                           documentation_coverage=response.get("documentation_coverage", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze documentation",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Dependency Analysis
    async def analyze_dependencies(self,
                                 snapshot_id: str,
                                 project_path: str) -> Dict[str, Any]:
        """Analyze project dependencies"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "analysis_type": "dependencies"
            }
            
            self.logger.info("Analyzing dependencies",
                           snapshot_id=snapshot_id,
                           project_path=project_path)
            
            response = await self.post("/analyze/dependencies", data=payload)
            
            self.logger.info("Dependency analysis completed",
                           snapshot_id=snapshot_id,
                           total_dependencies=response.get("total_dependencies", 0),
                           outdated_dependencies=response.get("outdated_count", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze dependencies",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Code Metrics
    async def get_code_metrics(self,
                             snapshot_id: str,
                             project_path: str,
                             metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get comprehensive code metrics"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "metrics": metrics or [
                    "lines_of_code",
                    "cyclomatic_complexity",
                    "halstead_metrics",
                    "maintainability_index",
                    "technical_debt"
                ]
            }
            
            self.logger.info("Getting code metrics",
                           snapshot_id=snapshot_id,
                           project_path=project_path,
                           metrics=payload["metrics"])
            
            response = await self.post("/metrics", data=payload)
            
            self.logger.info("Code metrics retrieved",
                           snapshot_id=snapshot_id,
                           total_loc=response.get("total_lines_of_code", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to get code metrics",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Code Patterns and Anti-patterns
    async def detect_patterns(self,
                            snapshot_id: str,
                            project_path: str,
                            pattern_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Detect code patterns and anti-patterns"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "pattern_types": pattern_types or [
                    "design_patterns",
                    "anti_patterns",
                    "code_smells",
                    "best_practices"
                ]
            }
            
            self.logger.info("Detecting code patterns",
                           snapshot_id=snapshot_id,
                           project_path=project_path,
                           pattern_types=payload["pattern_types"])
            
            response = await self.post("/patterns", data=payload)
            
            self.logger.info("Pattern detection completed",
                           snapshot_id=snapshot_id,
                           patterns_found=response.get("patterns_count", 0),
                           anti_patterns_found=response.get("anti_patterns_count", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to detect patterns",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Code Duplication
    async def detect_duplication(self,
                               snapshot_id: str,
                               project_path: str,
                               min_lines: int = 6) -> Dict[str, Any]:
        """Detect code duplication"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "min_lines": min_lines,
                "analysis_type": "duplication"
            }
            
            self.logger.info("Detecting code duplication",
                           snapshot_id=snapshot_id,
                           project_path=project_path,
                           min_lines=min_lines)
            
            response = await self.post("/analyze/duplication", data=payload)
            
            self.logger.info("Code duplication detection completed",
                           snapshot_id=snapshot_id,
                           duplication_percentage=response.get("duplication_percentage", 0),
                           duplicate_blocks=response.get("duplicate_blocks_count", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to detect code duplication",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Language-specific Analysis
    async def analyze_python_code(self,
                                snapshot_id: str,
                                project_path: str) -> Dict[str, Any]:
        """Python-specific code analysis"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "language": "python",
                "python_specific_checks": [
                    "pep8_compliance",
                    "type_hints",
                    "docstring_coverage",
                    "import_organization"
                ]
            }
            
            response = await self.post("/analyze/python", data=payload)
            
            self.logger.info("Python code analysis completed",
                           snapshot_id=snapshot_id,
                           pep8_score=response.get("pep8_score", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze Python code",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    async def analyze_javascript_code(self,
                                    snapshot_id: str,
                                    project_path: str) -> Dict[str, Any]:
        """JavaScript-specific code analysis"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "language": "javascript",
                "javascript_specific_checks": [
                    "eslint_compliance",
                    "typescript_usage",
                    "modern_syntax",
                    "bundle_analysis"
                ]
            }
            
            response = await self.post("/analyze/javascript", data=payload)
            
            self.logger.info("JavaScript code analysis completed",
                           snapshot_id=snapshot_id,
                           eslint_score=response.get("eslint_score", 0))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to analyze JavaScript code",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Reporting
    async def generate_analysis_report(self,
                                     snapshot_id: str,
                                     project_path: str,
                                     report_format: str = "json") -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        try:
            payload = {
                "snapshot_id": snapshot_id,
                "project_path": project_path,
                "format": report_format,
                "include_recommendations": True,
                "include_metrics": True
            }
            
            response = await self.post("/reports/generate", data=payload)
            
            self.logger.info("Analysis report generated",
                           snapshot_id=snapshot_id,
                           format=report_format,
                           report_url=response.get("report_url"))
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to generate analysis report",
                            snapshot_id=snapshot_id,
                            error=str(e))
            raise
    
    # Configuration
    async def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration"""
        try:
            response = await self.get("/config")
            return response
        except Exception as e:
            self.logger.error("Failed to get analysis config", error=str(e))
            raise
    
    async def update_analysis_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update analysis configuration"""
        try:
            response = await self.put("/config", data=config)
            
            self.logger.info("Analysis configuration updated")
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to update analysis config", error=str(e))
            raise
    
    # Supported Languages
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages"""
        try:
            response = await self.get("/languages")
            return response.get("languages", [])
        except Exception as e:
            self.logger.error("Failed to get supported languages", error=str(e))
            raise

