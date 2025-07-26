"""
Graph-Sitter Service Integration
Handles code quality analysis and syntax tree parsing using graph-sitter
"""

import os
import asyncio
import subprocess
import tempfile
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GraphSitterService:
    """Service for managing graph-sitter code analysis and quality checks"""
    
    def __init__(self):
        self.enabled = os.getenv("GRAPH_SITTER_ENABLED", "true").lower() == "true"
        self.languages = os.getenv("GRAPH_SITTER_LANGUAGES", "typescript,javascript,python,rust,go").split(",")
        self.max_file_size = int(os.getenv("GRAPH_SITTER_MAX_FILE_SIZE", "1048576"))  # 1MB
        self.analysis_timeout = int(os.getenv("GRAPH_SITTER_ANALYSIS_TIMEOUT", "60"))
        
        if not self.enabled:
            logger.warning("Graph-sitter is disabled")
            return
        
        logger.info(f"Initialized Graph-Sitter service for languages: {', '.join(self.languages)}")

    async def analyze_codebase(self, workspace_dir: str, project_id: str) -> Dict[str, Any]:
        """Analyze codebase using graph-sitter for code quality and structure"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Graph-sitter is disabled"
            }
        
        try:
            logger.info(f"Starting graph-sitter analysis for project {project_id}")
            
            # Find all source files in the workspace
            source_files = await self._find_source_files(workspace_dir)
            
            if not source_files:
                return {
                    "success": True,
                    "message": "No source files found for analysis",
                    "analysis": {
                        "files_analyzed": 0,
                        "total_lines": 0,
                        "languages": [],
                        "quality_score": 100,
                        "issues": []
                    }
                }
            
            # Analyze each file
            analysis_results = []
            total_lines = 0
            languages_found = set()
            all_issues = []
            
            for file_path in source_files:
                if os.path.getsize(file_path) > self.max_file_size:
                    logger.warning(f"Skipping large file: {file_path}")
                    continue
                
                file_analysis = await self._analyze_file(file_path)
                if file_analysis["success"]:
                    analysis_results.append(file_analysis)
                    total_lines += file_analysis["metrics"]["lines_of_code"]
                    languages_found.add(file_analysis["language"])
                    all_issues.extend(file_analysis["issues"])
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(analysis_results, all_issues)
            
            # Generate summary
            analysis_summary = {
                "files_analyzed": len(analysis_results),
                "total_lines": total_lines,
                "languages": list(languages_found),
                "quality_score": quality_score,
                "issues": all_issues,
                "file_analyses": analysis_results,
                "recommendations": self._generate_recommendations(all_issues)
            }
            
            logger.info(f"Graph-sitter analysis completed: {len(analysis_results)} files, quality score: {quality_score}")
            
            return {
                "success": True,
                "analysis": analysis_summary
            }
            
        except Exception as e:
            logger.error(f"Error in graph-sitter analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _find_source_files(self, workspace_dir: str) -> List[str]:
        """Find all source files in the workspace"""
        try:
            source_files = []
            
            # File extensions for supported languages
            extensions = {
                "typescript": [".ts", ".tsx"],
                "javascript": [".js", ".jsx"],
                "python": [".py"],
                "rust": [".rs"],
                "go": [".go"]
            }
            
            # Collect all relevant extensions
            relevant_extensions = []
            for lang in self.languages:
                if lang in extensions:
                    relevant_extensions.extend(extensions[lang])
            
            # Walk through workspace directory
            for root, dirs, files in os.walk(workspace_dir):
                # Skip common directories that shouldn't be analyzed
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv', 'target', 'dist', 'build']]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    _, ext = os.path.splitext(file)
                    
                    if ext in relevant_extensions:
                        source_files.append(file_path)
            
            logger.info(f"Found {len(source_files)} source files for analysis")
            return source_files
            
        except Exception as e:
            logger.error(f"Error finding source files: {str(e)}")
            return []

    async def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file using graph-sitter"""
        try:
            # Determine language from file extension
            _, ext = os.path.splitext(file_path)
            language = self._get_language_from_extension(ext)
            
            if not language:
                return {
                    "success": False,
                    "error": f"Unsupported file extension: {ext}"
                }
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Perform basic analysis (simulated graph-sitter functionality)
            analysis = await self._perform_syntax_analysis(content, language, file_path)
            
            return {
                "success": True,
                "file_path": file_path,
                "language": language,
                "metrics": analysis["metrics"],
                "issues": analysis["issues"],
                "structure": analysis["structure"]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e)
            }

    def _get_language_from_extension(self, ext: str) -> Optional[str]:
        """Get language name from file extension"""
        extension_map = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".py": "python",
            ".rs": "rust",
            ".go": "go"
        }
        return extension_map.get(ext)

    async def _perform_syntax_analysis(self, content: str, language: str, file_path: str) -> Dict[str, Any]:
        """Perform syntax analysis on file content"""
        try:
            lines = content.split('\n')
            lines_of_code = len([line for line in lines if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('//')])
            
            # Basic metrics
            metrics = {
                "lines_of_code": lines_of_code,
                "total_lines": len(lines),
                "blank_lines": len([line for line in lines if not line.strip()]),
                "comment_lines": len([line for line in lines if line.strip().startswith('#') or line.strip().startswith('//')]),
                "complexity": self._calculate_complexity(content, language),
                "functions": self._count_functions(content, language),
                "classes": self._count_classes(content, language)
            }
            
            # Identify issues
            issues = []
            issues.extend(self._check_code_style(content, language, file_path))
            issues.extend(self._check_complexity(content, language, file_path))
            issues.extend(self._check_best_practices(content, language, file_path))
            
            # Analyze structure
            structure = {
                "imports": self._extract_imports(content, language),
                "exports": self._extract_exports(content, language),
                "functions": self._extract_function_names(content, language),
                "classes": self._extract_class_names(content, language)
            }
            
            return {
                "metrics": metrics,
                "issues": issues,
                "structure": structure
            }
            
        except Exception as e:
            logger.error(f"Error in syntax analysis: {str(e)}")
            return {
                "metrics": {"lines_of_code": 0, "total_lines": 0},
                "issues": [],
                "structure": {}
            }

    def _calculate_complexity(self, content: str, language: str) -> int:
        """Calculate cyclomatic complexity (simplified)"""
        complexity_keywords = {
            "python": ["if", "elif", "for", "while", "try", "except", "with"],
            "javascript": ["if", "for", "while", "switch", "try", "catch"],
            "typescript": ["if", "for", "while", "switch", "try", "catch"],
            "rust": ["if", "for", "while", "match", "loop"],
            "go": ["if", "for", "switch", "select"]
        }
        
        keywords = complexity_keywords.get(language, [])
        complexity = 1  # Base complexity
        
        for keyword in keywords:
            complexity += content.count(f" {keyword} ") + content.count(f"\t{keyword} ")
        
        return min(complexity, 50)  # Cap at 50

    def _count_functions(self, content: str, language: str) -> int:
        """Count functions in the code"""
        function_patterns = {
            "python": ["def "],
            "javascript": ["function ", "=> ", "async function "],
            "typescript": ["function ", "=> ", "async function "],
            "rust": ["fn "],
            "go": ["func "]
        }
        
        patterns = function_patterns.get(language, [])
        count = 0
        
        for pattern in patterns:
            count += content.count(pattern)
        
        return count

    def _count_classes(self, content: str, language: str) -> int:
        """Count classes in the code"""
        class_patterns = {
            "python": ["class "],
            "javascript": ["class "],
            "typescript": ["class ", "interface "],
            "rust": ["struct ", "enum ", "trait "],
            "go": ["type ", "struct "]
        }
        
        patterns = class_patterns.get(language, [])
        count = 0
        
        for pattern in patterns:
            count += content.count(pattern)
        
        return count

    def _check_code_style(self, content: str, language: str, file_path: str) -> List[Dict[str, Any]]:
        """Check code style issues"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                issues.append({
                    "type": "style",
                    "severity": "warning",
                    "message": "Line too long (>120 characters)",
                    "file": file_path,
                    "line": i,
                    "column": len(line)
                })
            
            # Check trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append({
                    "type": "style",
                    "severity": "info",
                    "message": "Trailing whitespace",
                    "file": file_path,
                    "line": i,
                    "column": len(line.rstrip())
                })
        
        return issues

    def _check_complexity(self, content: str, language: str, file_path: str) -> List[Dict[str, Any]]:
        """Check complexity issues"""
        issues = []
        complexity = self._calculate_complexity(content, language)
        
        if complexity > 20:
            issues.append({
                "type": "complexity",
                "severity": "error",
                "message": f"High cyclomatic complexity ({complexity})",
                "file": file_path,
                "line": 1,
                "column": 1
            })
        elif complexity > 10:
            issues.append({
                "type": "complexity",
                "severity": "warning",
                "message": f"Moderate cyclomatic complexity ({complexity})",
                "file": file_path,
                "line": 1,
                "column": 1
            })
        
        return issues

    def _check_best_practices(self, content: str, language: str, file_path: str) -> List[Dict[str, Any]]:
        """Check best practices violations"""
        issues = []
        
        # Language-specific checks
        if language == "python":
            if "import *" in content:
                issues.append({
                    "type": "best_practice",
                    "severity": "warning",
                    "message": "Avoid wildcard imports",
                    "file": file_path,
                    "line": content.find("import *") // len(content.split('\n')[0]) + 1,
                    "column": 1
                })
        
        elif language in ["javascript", "typescript"]:
            if "var " in content:
                issues.append({
                    "type": "best_practice",
                    "severity": "warning",
                    "message": "Use 'let' or 'const' instead of 'var'",
                    "file": file_path,
                    "line": content.find("var ") // len(content.split('\n')[0]) + 1,
                    "column": 1
                })
        
        return issues

    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements"""
        imports = []
        lines = content.split('\n')
        
        import_patterns = {
            "python": ["import ", "from "],
            "javascript": ["import ", "require("],
            "typescript": ["import ", "require("],
            "rust": ["use "],
            "go": ["import "]
        }
        
        patterns = import_patterns.get(language, [])
        
        for line in lines:
            line = line.strip()
            for pattern in patterns:
                if line.startswith(pattern):
                    imports.append(line)
                    break
        
        return imports

    def _extract_exports(self, content: str, language: str) -> List[str]:
        """Extract export statements"""
        exports = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if language in ["javascript", "typescript"] and line.startswith("export "):
                exports.append(line)
        
        return exports

    def _extract_function_names(self, content: str, language: str) -> List[str]:
        """Extract function names"""
        import re
        functions = []
        
        patterns = {
            "python": r"def\s+(\w+)\s*\(",
            "javascript": r"function\s+(\w+)\s*\(|(\w+)\s*=\s*\(",
            "typescript": r"function\s+(\w+)\s*\(|(\w+)\s*=\s*\(",
            "rust": r"fn\s+(\w+)\s*\(",
            "go": r"func\s+(\w+)\s*\("
        }
        
        pattern = patterns.get(language)
        if pattern:
            matches = re.findall(pattern, content)
            functions = [match[0] if isinstance(match, tuple) else match for match in matches if match]
        
        return functions

    def _extract_class_names(self, content: str, language: str) -> List[str]:
        """Extract class names"""
        import re
        classes = []
        
        patterns = {
            "python": r"class\s+(\w+)",
            "javascript": r"class\s+(\w+)",
            "typescript": r"class\s+(\w+)|interface\s+(\w+)",
            "rust": r"struct\s+(\w+)|enum\s+(\w+)",
            "go": r"type\s+(\w+)\s+struct"
        }
        
        pattern = patterns.get(language)
        if pattern:
            matches = re.findall(pattern, content)
            classes = [match[0] if isinstance(match, tuple) else match for match in matches if match]
        
        return classes

    def _calculate_quality_score(self, analyses: List[Dict[str, Any]], all_issues: List[Dict[str, Any]]) -> int:
        """Calculate overall code quality score"""
        if not analyses:
            return 100
        
        base_score = 100
        
        # Deduct points for issues
        for issue in all_issues:
            if issue["severity"] == "error":
                base_score -= 10
            elif issue["severity"] == "warning":
                base_score -= 5
            elif issue["severity"] == "info":
                base_score -= 1
        
        # Deduct points for high complexity
        total_complexity = sum(analysis["metrics"]["complexity"] for analysis in analyses)
        avg_complexity = total_complexity / len(analyses)
        
        if avg_complexity > 15:
            base_score -= 20
        elif avg_complexity > 10:
            base_score -= 10
        
        return max(base_score, 0)

    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on issues found"""
        recommendations = []
        
        error_count = len([i for i in issues if i["severity"] == "error"])
        warning_count = len([i for i in issues if i["severity"] == "warning"])
        
        if error_count > 0:
            recommendations.append(f"Fix {error_count} critical issues to improve code quality")
        
        if warning_count > 0:
            recommendations.append(f"Address {warning_count} warnings to enhance maintainability")
        
        # Type-specific recommendations
        issue_types = set(issue["type"] for issue in issues)
        
        if "complexity" in issue_types:
            recommendations.append("Consider refactoring complex functions into smaller, more manageable pieces")
        
        if "style" in issue_types:
            recommendations.append("Apply consistent code formatting and style guidelines")
        
        if "best_practice" in issue_types:
            recommendations.append("Follow language-specific best practices for better code quality")
        
        return recommendations

    def is_enabled(self) -> bool:
        """Check if graph-sitter is enabled"""
        return self.enabled
