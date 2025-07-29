"""
Graph-Sitter client for static analysis and code quality metrics
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


class GraphSitterClient:
    """Client for interacting with Graph-Sitter service"""
    
    def __init__(self):
        self.base_url = settings.graph_sitter_url or "http://localhost:8002"
        self.timeout = 120  # 2 minutes timeout for analysis
    
    async def analyze_codebase(self, codebase_path: str, language: str = "auto") -> Dict[str, Any]:
        """Analyze a codebase for quality metrics and issues"""
        try:
            logger.info("Starting codebase analysis", path=codebase_path, language=language)
            
            analysis_config = {
                "path": codebase_path,
                "language": language,
                "include_metrics": True,
                "include_issues": True,
                "include_dependencies": True,
                "recursive": True,
                "exclude_patterns": [
                    "node_modules",
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    ".env",
                    "dist",
                    "build"
                ]
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/analyze",
                    json=analysis_config,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Codebase analysis completed", 
                               files_analyzed=result.get("files_analyzed", 0),
                               issues_found=len(result.get("issues", [])))
                    return result
                else:
                    logger.error("Codebase analysis failed", 
                               status_code=response.status_code,
                               response=response.text)
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "files_analyzed": 0,
                        "issues": [],
                        "metrics": {}
                    }
                    
        except Exception as e:
            logger.error("Codebase analysis failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "files_analyzed": 0,
                "issues": [],
                "metrics": {}
            }
    
    async def analyze_file(self, file_path: str, language: str = "auto") -> Dict[str, Any]:
        """Analyze a single file"""
        try:
            logger.info("Analyzing file", file_path=file_path, language=language)
            
            analysis_config = {
                "file_path": file_path,
                "language": language,
                "include_ast": True,
                "include_metrics": True,
                "include_issues": True
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/api/analyze/file",
                    json=analysis_config,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("File analysis completed", 
                               file_path=file_path,
                               issues_found=len(result.get("issues", [])))
                    return result
                else:
                    logger.error("File analysis failed", 
                               file_path=file_path,
                               status_code=response.status_code)
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "issues": [],
                        "metrics": {}
                    }
                    
        except Exception as e:
            logger.error("File analysis failed", file_path=file_path, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "issues": [],
                "metrics": {}
            }
    
    async def get_code_metrics(self, codebase_path: str) -> Dict[str, Any]:
        """Get code quality metrics for a codebase"""
        try:
            logger.info("Getting code metrics", path=codebase_path)
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(
                    f"{self.base_url}/api/metrics",
                    params={"path": codebase_path}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Code metrics retrieved", 
                               total_lines=result.get("total_lines", 0),
                               complexity_score=result.get("complexity_score", 0))
                    return result
                else:
                    logger.error("Failed to get code metrics", 
                               status_code=response.status_code)
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "metrics": {}
                    }
                    
        except Exception as e:
            logger.error("Failed to get code metrics", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "metrics": {}
            }
    
    async def find_security_issues(self, codebase_path: str) -> Dict[str, Any]:
        """Find security issues in the codebase"""
        try:
            logger.info("Scanning for security issues", path=codebase_path)
            
            scan_config = {
                "path": codebase_path,
                "scan_types": [
                    "sql_injection",
                    "xss",
                    "hardcoded_secrets",
                    "insecure_random",
                    "path_traversal",
                    "command_injection"
                ],
                "severity_threshold": "low"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/security/scan",
                    json=scan_config,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Security scan completed", 
                               issues_found=len(result.get("security_issues", [])))
                    return result
                else:
                    logger.error("Security scan failed", 
                               status_code=response.status_code)
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "security_issues": []
                    }
                    
        except Exception as e:
            logger.error("Security scan failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "security_issues": []
            }
    
    async def get_dependency_analysis(self, codebase_path: str) -> Dict[str, Any]:
        """Analyze dependencies and their security status"""
        try:
            logger.info("Analyzing dependencies", path=codebase_path)
            
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.get(
                    f"{self.base_url}/api/dependencies",
                    params={"path": codebase_path}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Dependency analysis completed", 
                               total_dependencies=len(result.get("dependencies", [])),
                               vulnerable_dependencies=len(result.get("vulnerabilities", [])))
                    return result
                else:
                    logger.error("Dependency analysis failed", 
                               status_code=response.status_code)
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "dependencies": [],
                        "vulnerabilities": []
                    }
                    
        except Exception as e:
            logger.error("Dependency analysis failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "dependencies": [],
                "vulnerabilities": []
            }
    
    async def generate_code_report(self, codebase_path: str) -> Dict[str, Any]:
        """Generate a comprehensive code quality report"""
        try:
            logger.info("Generating code report", path=codebase_path)
            
            # Run all analyses
            analysis_result = await self.analyze_codebase(codebase_path)
            metrics_result = await self.get_code_metrics(codebase_path)
            security_result = await self.find_security_issues(codebase_path)
            dependency_result = await self.get_dependency_analysis(codebase_path)
            
            # Combine results
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "codebase_path": codebase_path,
                "analysis": analysis_result,
                "metrics": metrics_result.get("metrics", {}),
                "security_issues": security_result.get("security_issues", []),
                "dependencies": dependency_result.get("dependencies", []),
                "vulnerabilities": dependency_result.get("vulnerabilities", []),
                "summary": {
                    "total_files": analysis_result.get("files_analyzed", 0),
                    "total_issues": len(analysis_result.get("issues", [])),
                    "security_issues": len(security_result.get("security_issues", [])),
                    "vulnerable_dependencies": len(dependency_result.get("vulnerabilities", [])),
                    "overall_score": self._calculate_overall_score(
                        analysis_result, metrics_result, security_result, dependency_result
                    )
                }
            }
            
            logger.info("Code report generated", 
                       overall_score=report["summary"]["overall_score"])
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate code report", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _calculate_overall_score(self, analysis: Dict, metrics: Dict, security: Dict, dependencies: Dict) -> float:
        """Calculate an overall code quality score (0-100)"""
        try:
            score = 100.0
            
            # Deduct points for issues
            total_issues = len(analysis.get("issues", []))
            score -= min(total_issues * 2, 30)  # Max 30 points deduction
            
            # Deduct points for security issues
            security_issues = len(security.get("security_issues", []))
            score -= min(security_issues * 5, 40)  # Max 40 points deduction
            
            # Deduct points for vulnerable dependencies
            vulnerabilities = len(dependencies.get("vulnerabilities", []))
            score -= min(vulnerabilities * 3, 20)  # Max 20 points deduction
            
            # Consider complexity (if available)
            complexity = metrics.get("metrics", {}).get("complexity_score", 0)
            if complexity > 10:
                score -= min((complexity - 10) * 2, 10)  # Max 10 points deduction
            
            return max(score, 0.0)
            
        except Exception:
            return 50.0  # Default score if calculation fails
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Graph-Sitter service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "service": "graph-sitter",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "service": "graph-sitter",
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error("Graph-Sitter health check failed", error=str(e))
            return {
                "status": "error",
                "service": "graph-sitter",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get Graph-Sitter service information"""
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
            logger.error("Failed to get Graph-Sitter service info", error=str(e))
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

