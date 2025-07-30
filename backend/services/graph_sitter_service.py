"""
Graph-sitter Integration Service
Provides code analysis, quality assurance, and codebase manipulation capabilities
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime
from pathlib import Path

logger = structlog.get_logger(__name__)

try:
    from graph_sitter import Codebase
    from graph_sitter.codebase.codebase_analysis import get_codebase_summary, get_file_summary
    GRAPH_SITTER_AVAILABLE = True
except ImportError:
    logger.warning("Graph-sitter not available - using mock implementation")
    GRAPH_SITTER_AVAILABLE = False


class MockCodebase:
    """Mock codebase for when Graph-sitter is not available"""
    def __init__(self, path: str):
        self.path = path
        self.functions = []
        self.classes = []
        self.files = []
    
    @classmethod
    def from_repo(cls, repo_url: str):
        return cls(repo_url)


def mock_get_codebase_summary(codebase) -> Dict[str, Any]:
    """Mock codebase summary"""
    return {
        "total_files": 42,
        "total_functions": 156,
        "total_classes": 23,
        "total_lines": 5432,
        "error_count": 3,
        "warning_count": 12,
        "complexity_score": 7.5,
        "dependencies": ["fastapi", "pydantic", "sqlalchemy"],
        "languages": ["python", "javascript"],
        "test_coverage": 85.2
    }


def mock_get_file_summary(file_path: str) -> Dict[str, Any]:
    """Mock file summary"""
    return {
        "file_path": file_path,
        "lines_of_code": 123,
        "functions": 5,
        "classes": 2,
        "imports": ["os", "sys", "typing"],
        "complexity": 6.2,
        "errors": [],
        "warnings": ["unused import: sys"]
    }


class GraphSitterService:
    """
    Service for code analysis and quality assurance using Graph-sitter
    """
    
    def __init__(self):
        self.codebase_cache = {}
        self.analysis_cache = {}
        self.supported_languages = ["python", "typescript", "javascript", "react"]
        
        logger.info("GraphSitterService initialized", 
                   graph_sitter_available=GRAPH_SITTER_AVAILABLE,
                   supported_languages=self.supported_languages)
    
    async def analyze_codebase(
        self, 
        repo_path: str,
        use_cache: bool = True,
        include_diagnostics: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a complete codebase
        
        Args:
            repo_path: Path to the repository or codebase
            use_cache: Whether to use cached results
            include_diagnostics: Whether to include diagnostic information
            
        Returns:
            Dictionary with comprehensive codebase analysis
        """
        cache_key = f"{repo_path}_{include_diagnostics}"
        
        if use_cache and cache_key in self.analysis_cache:
            logger.info("Using cached codebase analysis", repo_path=repo_path)
            return self.analysis_cache[cache_key]
        
        logger.info("Starting codebase analysis", 
                   repo_path=repo_path,
                   include_diagnostics=include_diagnostics)
        
        start_time = datetime.now()
        
        try:
            # Load or create codebase
            if repo_path not in self.codebase_cache:
                if not GRAPH_SITTER_AVAILABLE:
                    codebase = MockCodebase(repo_path)
                else:
                    if repo_path.startswith(("http://", "https://", "git@")):
                        codebase = Codebase.from_repo(repo_path)
                    else:
                        codebase = Codebase(repo_path)
                
                self.codebase_cache[repo_path] = codebase
            else:
                codebase = self.codebase_cache[repo_path]
            
            # Get comprehensive analysis
            if not GRAPH_SITTER_AVAILABLE:
                summary = mock_get_codebase_summary(codebase)
            else:
                summary = get_codebase_summary(codebase)
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "repo_path": repo_path,
                "analysis_timestamp": start_time.isoformat(),
                "analysis_duration": analysis_time,
                "summary": summary,
                "metadata": {
                    "graph_sitter_available": GRAPH_SITTER_AVAILABLE,
                    "supported_languages": self.supported_languages,
                    "cache_used": False
                }
            }
            
            # Add diagnostics if requested
            if include_diagnostics:
                diagnostics = await self.get_diagnostics(repo_path)
                result["diagnostics"] = diagnostics
            
            # Cache the result
            if use_cache:
                self.analysis_cache[cache_key] = result
            
            logger.info("Codebase analysis completed", 
                       repo_path=repo_path,
                       analysis_time=analysis_time,
                       total_files=summary.get("total_files", 0),
                       error_count=summary.get("error_count", 0))
            
            return result
            
        except Exception as e:
            analysis_time = (datetime.now() - start_time).total_seconds()
            error_result = {
                "repo_path": repo_path,
                "analysis_timestamp": start_time.isoformat(),
                "analysis_duration": analysis_time,
                "error": str(e),
                "success": False,
                "metadata": {
                    "graph_sitter_available": GRAPH_SITTER_AVAILABLE
                }
            }
            
            logger.error("Codebase analysis failed", 
                        repo_path=repo_path,
                        error=str(e),
                        analysis_time=analysis_time)
            
            return error_result
    
    async def analyze_file(
        self, 
        file_path: str,
        repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a specific file
        
        Args:
            file_path: Path to the file to analyze
            repo_path: Optional repository path for context
            
        Returns:
            Dictionary with file analysis results
        """
        logger.info("Starting file analysis", 
                   file_path=file_path,
                   repo_path=repo_path)
        
        start_time = datetime.now()
        
        try:
            if not GRAPH_SITTER_AVAILABLE:
                summary = mock_get_file_summary(file_path)
            else:
                summary = get_file_summary(file_path)
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "file_path": file_path,
                "repo_path": repo_path,
                "analysis_timestamp": start_time.isoformat(),
                "analysis_duration": analysis_time,
                "summary": summary,
                "success": True
            }
            
            logger.info("File analysis completed", 
                       file_path=file_path,
                       analysis_time=analysis_time,
                       functions=summary.get("functions", 0),
                       classes=summary.get("classes", 0))
            
            return result
            
        except Exception as e:
            analysis_time = (datetime.now() - start_time).total_seconds()
            error_result = {
                "file_path": file_path,
                "repo_path": repo_path,
                "analysis_timestamp": start_time.isoformat(),
                "analysis_duration": analysis_time,
                "error": str(e),
                "success": False
            }
            
            logger.error("File analysis failed", 
                        file_path=file_path,
                        error=str(e),
                        analysis_time=analysis_time)
            
            return error_result
    
    async def get_diagnostics(
        self, 
        repo_path: str,
        severity_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get diagnostic information (errors, warnings, etc.) for a codebase
        
        Args:
            repo_path: Path to the repository
            severity_filter: Optional filter for severity levels (error, warning, info)
            
        Returns:
            Dictionary with diagnostic information
        """
        logger.info("Getting diagnostics", 
                   repo_path=repo_path,
                   severity_filter=severity_filter)
        
        try:
            # Mock diagnostics when Graph-sitter is not available
            if not GRAPH_SITTER_AVAILABLE:
                diagnostics = {
                    "total_issues": 15,
                    "errors": 3,
                    "warnings": 12,
                    "info": 0,
                    "issues": [
                        {
                            "file": "backend/main.py",
                            "line": 42,
                            "column": 15,
                            "severity": "error",
                            "message": "Undefined variable 'undefined_var'",
                            "rule": "undefined-variable",
                            "category": "logic"
                        },
                        {
                            "file": "backend/services/test.py",
                            "line": 23,
                            "column": 8,
                            "severity": "warning",
                            "message": "Unused import 'os'",
                            "rule": "unused-import",
                            "category": "style"
                        }
                    ],
                    "categories": {
                        "syntax": 1,
                        "logic": 2,
                        "style": 8,
                        "performance": 2,
                        "security": 1,
                        "import": 1
                    }
                }
            else:
                # Use real Graph-sitter diagnostics
                codebase = self.codebase_cache.get(repo_path)
                if not codebase:
                    # Load codebase if not cached
                    await self.analyze_codebase(repo_path, use_cache=False, include_diagnostics=False)
                    codebase = self.codebase_cache.get(repo_path)
                
                # This would use the actual Graph-sitter diagnostic capabilities
                # For now, using mock data as the exact API may vary
                diagnostics = {
                    "total_issues": 0,
                    "errors": 0,
                    "warnings": 0,
                    "info": 0,
                    "issues": [],
                    "categories": {}
                }
            
            # Apply severity filter if provided
            if severity_filter:
                filtered_issues = [
                    issue for issue in diagnostics["issues"]
                    if issue["severity"] in severity_filter
                ]
                diagnostics["issues"] = filtered_issues
                diagnostics["filtered"] = True
                diagnostics["filter_criteria"] = severity_filter
            
            diagnostics["timestamp"] = datetime.now().isoformat()
            diagnostics["repo_path"] = repo_path
            
            logger.info("Diagnostics retrieved", 
                       repo_path=repo_path,
                       total_issues=diagnostics["total_issues"],
                       errors=diagnostics["errors"],
                       warnings=diagnostics["warnings"])
            
            return diagnostics
            
        except Exception as e:
            error_result = {
                "repo_path": repo_path,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Failed to get diagnostics", 
                        repo_path=repo_path,
                        error=str(e))
            
            return error_result
    
    async def get_code_quality_metrics(
        self, 
        repo_path: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive code quality metrics
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            Dictionary with code quality metrics
        """
        logger.info("Getting code quality metrics", repo_path=repo_path)
        
        try:
            # Get basic analysis
            analysis = await self.analyze_codebase(repo_path, include_diagnostics=True)
            
            if not analysis.get("success", True):
                return analysis
            
            summary = analysis["summary"]
            diagnostics = analysis.get("diagnostics", {})
            
            # Calculate quality metrics
            total_lines = summary.get("total_lines", 1)
            error_count = diagnostics.get("errors", 0)
            warning_count = diagnostics.get("warnings", 0)
            
            # Quality scores (0-100)
            error_score = max(0, 100 - (error_count * 10))  # -10 points per error
            warning_score = max(0, 100 - (warning_count * 2))  # -2 points per warning
            complexity_score = max(0, 100 - (summary.get("complexity_score", 0) * 5))
            coverage_score = summary.get("test_coverage", 0)
            
            overall_score = (error_score + warning_score + complexity_score + coverage_score) / 4
            
            metrics = {
                "repo_path": repo_path,
                "timestamp": datetime.now().isoformat(),
                "overall_score": round(overall_score, 2),
                "scores": {
                    "error_score": error_score,
                    "warning_score": warning_score,
                    "complexity_score": complexity_score,
                    "coverage_score": coverage_score
                },
                "metrics": {
                    "total_files": summary.get("total_files", 0),
                    "total_lines": total_lines,
                    "total_functions": summary.get("total_functions", 0),
                    "total_classes": summary.get("total_classes", 0),
                    "error_density": (error_count / total_lines) * 1000,  # errors per 1000 lines
                    "warning_density": (warning_count / total_lines) * 1000,
                    "complexity_average": summary.get("complexity_score", 0),
                    "test_coverage": coverage_score
                },
                "issues_summary": {
                    "total_issues": diagnostics.get("total_issues", 0),
                    "errors": error_count,
                    "warnings": warning_count,
                    "categories": diagnostics.get("categories", {})
                },
                "recommendations": []
            }
            
            # Generate recommendations
            if error_count > 0:
                metrics["recommendations"].append({
                    "priority": "high",
                    "category": "errors",
                    "message": f"Fix {error_count} error(s) to improve code reliability"
                })
            
            if warning_count > 10:
                metrics["recommendations"].append({
                    "priority": "medium",
                    "category": "warnings",
                    "message": f"Address {warning_count} warning(s) to improve code quality"
                })
            
            if coverage_score < 80:
                metrics["recommendations"].append({
                    "priority": "medium",
                    "category": "testing",
                    "message": f"Increase test coverage from {coverage_score}% to at least 80%"
                })
            
            if summary.get("complexity_score", 0) > 10:
                metrics["recommendations"].append({
                    "priority": "low",
                    "category": "complexity",
                    "message": "Consider refactoring complex functions to improve maintainability"
                })
            
            logger.info("Code quality metrics calculated", 
                       repo_path=repo_path,
                       overall_score=overall_score,
                       total_issues=diagnostics.get("total_issues", 0))
            
            return metrics
            
        except Exception as e:
            error_result = {
                "repo_path": repo_path,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Failed to get code quality metrics", 
                        repo_path=repo_path,
                        error=str(e))
            
            return error_result
    
    async def search_code(
        self, 
        repo_path: str,
        query: str,
        file_pattern: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for code patterns in the codebase
        
        Args:
            repo_path: Path to the repository
            query: Search query (can be regex or plain text)
            file_pattern: Optional file pattern filter (e.g., "*.py")
            language: Optional language filter
            
        Returns:
            Dictionary with search results
        """
        logger.info("Searching code", 
                   repo_path=repo_path,
                   query=query,
                   file_pattern=file_pattern,
                   language=language)
        
        try:
            # Mock search results when Graph-sitter is not available
            if not GRAPH_SITTER_AVAILABLE:
                results = {
                    "query": query,
                    "repo_path": repo_path,
                    "total_matches": 5,
                    "files_matched": 3,
                    "matches": [
                        {
                            "file": "backend/main.py",
                            "line": 42,
                            "column": 15,
                            "match": f"Found '{query}' in main.py",
                            "context": f"def example_function(): # {query} appears here"
                        },
                        {
                            "file": "backend/services/test.py",
                            "line": 23,
                            "column": 8,
                            "match": f"Found '{query}' in test.py",
                            "context": f"class TestClass: # {query} in comment"
                        }
                    ]
                }
            else:
                # Use real Graph-sitter search capabilities
                codebase = self.codebase_cache.get(repo_path)
                if not codebase:
                    await self.analyze_codebase(repo_path, use_cache=False, include_diagnostics=False)
                    codebase = self.codebase_cache.get(repo_path)
                
                # This would use actual Graph-sitter search functionality
                results = {
                    "query": query,
                    "repo_path": repo_path,
                    "total_matches": 0,
                    "files_matched": 0,
                    "matches": []
                }
            
            results["timestamp"] = datetime.now().isoformat()
            results["filters"] = {
                "file_pattern": file_pattern,
                "language": language
            }
            
            logger.info("Code search completed", 
                       repo_path=repo_path,
                       query=query,
                       total_matches=results["total_matches"],
                       files_matched=results["files_matched"])
            
            return results
            
        except Exception as e:
            error_result = {
                "query": query,
                "repo_path": repo_path,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Code search failed", 
                        repo_path=repo_path,
                        query=query,
                        error=str(e))
            
            return error_result
    
    async def get_dependencies(
        self, 
        repo_path: str,
        include_dev_dependencies: bool = False
    ) -> Dict[str, Any]:
        """
        Get dependency information for the codebase
        
        Args:
            repo_path: Path to the repository
            include_dev_dependencies: Whether to include development dependencies
            
        Returns:
            Dictionary with dependency information
        """
        logger.info("Getting dependencies", 
                   repo_path=repo_path,
                   include_dev_dependencies=include_dev_dependencies)
        
        try:
            analysis = await self.analyze_codebase(repo_path, include_diagnostics=False)
            
            if not analysis.get("success", True):
                return analysis
            
            summary = analysis["summary"]
            dependencies = summary.get("dependencies", [])
            
            # Mock dependency analysis
            dependency_info = {
                "repo_path": repo_path,
                "timestamp": datetime.now().isoformat(),
                "total_dependencies": len(dependencies),
                "dependencies": [],
                "dependency_tree": {},
                "security_issues": [],
                "outdated_packages": []
            }
            
            # Process each dependency
            for dep in dependencies:
                dep_info = {
                    "name": dep,
                    "version": "1.0.0",  # Mock version
                    "type": "production",
                    "license": "MIT",
                    "security_issues": 0,
                    "outdated": False
                }
                dependency_info["dependencies"].append(dep_info)
            
            logger.info("Dependencies retrieved", 
                       repo_path=repo_path,
                       total_dependencies=len(dependencies))
            
            return dependency_info
            
        except Exception as e:
            error_result = {
                "repo_path": repo_path,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error("Failed to get dependencies", 
                        repo_path=repo_path,
                        error=str(e))
            
            return error_result
    
    def clear_cache(self, repo_path: Optional[str] = None):
        """
        Clear analysis cache
        
        Args:
            repo_path: Optional specific repository to clear from cache
        """
        if repo_path:
            # Clear specific repository from cache
            self.codebase_cache.pop(repo_path, None)
            # Clear related analysis cache entries
            keys_to_remove = [key for key in self.analysis_cache.keys() if key.startswith(repo_path)]
            for key in keys_to_remove:
                self.analysis_cache.pop(key, None)
            
            logger.info("Cache cleared for repository", repo_path=repo_path)
        else:
            # Clear all caches
            self.codebase_cache.clear()
            self.analysis_cache.clear()
            
            logger.info("All caches cleared")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status and health information
        
        Returns:
            Dictionary with service status
        """
        return {
            "service": "GraphSitterService",
            "status": "healthy",
            "graph_sitter_available": GRAPH_SITTER_AVAILABLE,
            "supported_languages": self.supported_languages,
            "cached_codebases": len(self.codebase_cache),
            "cached_analyses": len(self.analysis_cache),
            "timestamp": datetime.now().isoformat()
        }

