import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
import json
import subprocess
import os

class GraphSitterClient:
    """Client for Graph-Sitter static analysis and code quality metrics."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://localhost:8002"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "CodegenCICD-Dashboard/1.0"
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Graph-Sitter service."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return {
                            "success": True,
                            "status": health_data.get("status", "healthy"),
                            "version": health_data.get("version", "unknown"),
                            "supported_languages": health_data.get("supported_languages", [])
                        }
                    else:
                        raise Exception(f"Health check failed: {response.status}")
        except Exception as e:
            raise Exception(f"Graph-Sitter connection failed: {str(e)}")
    
    async def analyze_codebase(
        self, 
        codebase_path: str, 
        snapshot_id: str = None,
        analysis_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive static analysis on a codebase."""
        
        if analysis_config is None:
            analysis_config = {
                "include_patterns": ["**/*.py", "**/*.js", "**/*.ts", "**/*.tsx", "**/*.jsx"],
                "exclude_patterns": ["**/node_modules/**", "**/.git/**", "**/dist/**", "**/build/**"],
                "analysis_types": [
                    "syntax_analysis",
                    "complexity_metrics", 
                    "code_quality",
                    "security_scan",
                    "dependency_analysis",
                    "documentation_coverage"
                ],
                "quality_thresholds": {
                    "cyclomatic_complexity": 10,
                    "function_length": 50,
                    "file_length": 500,
                    "duplicate_code": 0.1
                }
            }
        
        analysis_request = {
            "codebase_path": codebase_path,
            "snapshot_id": snapshot_id,
            "config": analysis_config
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/analyze/codebase",
                    headers=self.headers,
                    json=analysis_request,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes
                ) as response:
                    if response.status == 200:
                        analysis_result = await response.json()
                        return self._process_analysis_results(analysis_result)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Codebase analysis failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "quality_score": 0,
                "critical_issues": [f"Analysis failed: {str(e)}"]
            }
    
    async def analyze_file(
        self, 
        file_path: str, 
        file_content: str = None,
        language: str = None
    ) -> Dict[str, Any]:
        """Analyze a single file."""
        
        analysis_request = {
            "file_path": file_path,
            "file_content": file_content,
            "language": language,
            "analysis_types": [
                "syntax_analysis",
                "complexity_metrics",
                "code_quality",
                "security_scan"
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/analyze/file",
                    headers=self.headers,
                    json=analysis_request,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"File analysis failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "issues": []
            }
    
    async def get_code_metrics(
        self, 
        codebase_path: str,
        snapshot_id: str = None
    ) -> Dict[str, Any]:
        """Get detailed code metrics for a codebase."""
        
        metrics_request = {
            "codebase_path": codebase_path,
            "snapshot_id": snapshot_id,
            "metrics": [
                "lines_of_code",
                "cyclomatic_complexity",
                "maintainability_index",
                "technical_debt",
                "test_coverage",
                "documentation_coverage"
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/metrics",
                    headers=self.headers,
                    json=metrics_request,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Metrics calculation failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metrics": {}
            }
    
    async def detect_code_smells(
        self, 
        codebase_path: str,
        snapshot_id: str = None
    ) -> Dict[str, Any]:
        """Detect code smells and anti-patterns."""
        
        detection_request = {
            "codebase_path": codebase_path,
            "snapshot_id": snapshot_id,
            "detection_rules": [
                "long_method",
                "large_class",
                "duplicate_code",
                "dead_code",
                "complex_conditional",
                "god_object",
                "feature_envy",
                "data_clumps"
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/detect/code-smells",
                    headers=self.headers,
                    json=detection_request,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Code smell detection failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "code_smells": []
            }
    
    async def security_scan(
        self, 
        codebase_path: str,
        snapshot_id: str = None
    ) -> Dict[str, Any]:
        """Perform security vulnerability scan."""
        
        security_request = {
            "codebase_path": codebase_path,
            "snapshot_id": snapshot_id,
            "scan_types": [
                "sql_injection",
                "xss_vulnerabilities",
                "insecure_dependencies",
                "hardcoded_secrets",
                "weak_cryptography",
                "path_traversal",
                "command_injection"
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/security/scan",
                    headers=self.headers,
                    json=security_request,
                    timeout=aiohttp.ClientTimeout(total=240)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Security scan failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "vulnerabilities": []
            }
    
    async def dependency_analysis(
        self, 
        codebase_path: str,
        snapshot_id: str = None
    ) -> Dict[str, Any]:
        """Analyze project dependencies for vulnerabilities and updates."""
        
        dependency_request = {
            "codebase_path": codebase_path,
            "snapshot_id": snapshot_id,
            "package_managers": ["npm", "pip", "composer", "maven", "gradle"],
            "check_vulnerabilities": True,
            "check_updates": True,
            "check_licenses": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/analyze/dependencies",
                    headers=self.headers,
                    json=dependency_request,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Dependency analysis failed: {response.status} - {error_text}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "dependencies": []
            }
    
    def _process_analysis_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format analysis results."""
        
        # Extract key metrics
        metrics = raw_results.get("metrics", {})
        issues = raw_results.get("issues", [])
        code_smells = raw_results.get("code_smells", [])
        security_issues = raw_results.get("security_issues", [])
        
        # Categorize issues by severity
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        major_issues = [i for i in issues if i.get("severity") == "major"]
        minor_issues = [i for i in issues if i.get("severity") == "minor"]
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(metrics, issues, code_smells, security_issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(critical_issues, major_issues, code_smells, security_issues)
        
        return {
            "success": len(critical_issues) == 0,
            "quality_score": quality_score,
            "metrics": {
                "lines_of_code": metrics.get("lines_of_code", 0),
                "cyclomatic_complexity": metrics.get("avg_cyclomatic_complexity", 0),
                "maintainability_index": metrics.get("maintainability_index", 0),
                "technical_debt_ratio": metrics.get("technical_debt_ratio", 0),
                "test_coverage": metrics.get("test_coverage", 0),
                "documentation_coverage": metrics.get("documentation_coverage", 0)
            },
            "issues_summary": {
                "total_issues": len(issues),
                "critical_issues": len(critical_issues),
                "major_issues": len(major_issues),
                "minor_issues": len(minor_issues),
                "code_smells": len(code_smells),
                "security_issues": len(security_issues)
            },
            "critical_issues": [
                {
                    "type": issue.get("type", "unknown"),
                    "message": issue.get("message", ""),
                    "file": issue.get("file", ""),
                    "line": issue.get("line", 0),
                    "severity": issue.get("severity", "unknown")
                }
                for issue in critical_issues
            ],
            "recommendations": recommendations,
            "detailed_results": raw_results,
            "timestamp": raw_results.get("timestamp"),
            "analysis_duration": raw_results.get("duration", 0)
        }
    
    def _calculate_quality_score(
        self, 
        metrics: Dict[str, Any], 
        issues: List[Dict[str, Any]],
        code_smells: List[Dict[str, Any]],
        security_issues: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall code quality score (0-100)."""
        
        base_score = 100.0
        
        # Deduct points for issues
        critical_issues = len([i for i in issues if i.get("severity") == "critical"])
        major_issues = len([i for i in issues if i.get("severity") == "major"])
        minor_issues = len([i for i in issues if i.get("severity") == "minor"])
        
        base_score -= critical_issues * 20  # 20 points per critical issue
        base_score -= major_issues * 10     # 10 points per major issue
        base_score -= minor_issues * 2      # 2 points per minor issue
        
        # Deduct points for code smells
        base_score -= len(code_smells) * 5  # 5 points per code smell
        
        # Deduct points for security issues
        base_score -= len(security_issues) * 15  # 15 points per security issue
        
        # Factor in complexity
        complexity = metrics.get("avg_cyclomatic_complexity", 0)
        if complexity > 10:
            base_score -= (complexity - 10) * 2
        
        # Factor in maintainability
        maintainability = metrics.get("maintainability_index", 100)
        if maintainability < 70:
            base_score -= (70 - maintainability) * 0.5
        
        # Factor in test coverage
        test_coverage = metrics.get("test_coverage", 0)
        if test_coverage < 80:
            base_score -= (80 - test_coverage) * 0.3
        
        return max(0.0, min(100.0, base_score))
    
    def _generate_recommendations(
        self, 
        critical_issues: List[Dict[str, Any]],
        major_issues: List[Dict[str, Any]],
        code_smells: List[Dict[str, Any]],
        security_issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis results."""
        
        recommendations = []
        
        # Critical issues
        if critical_issues:
            recommendations.append(f"🚨 Address {len(critical_issues)} critical issues immediately")
            for issue in critical_issues[:3]:  # Show top 3
                recommendations.append(f"  - {issue.get('message', 'Unknown issue')} in {issue.get('file', 'unknown file')}")
        
        # Security issues
        if security_issues:
            recommendations.append(f"🔒 Fix {len(security_issues)} security vulnerabilities")
            security_types = set(issue.get('type', 'unknown') for issue in security_issues)
            for sec_type in list(security_types)[:3]:
                recommendations.append(f"  - Address {sec_type} vulnerabilities")
        
        # Code smells
        if code_smells:
            smell_types = {}
            for smell in code_smells:
                smell_type = smell.get('type', 'unknown')
                smell_types[smell_type] = smell_types.get(smell_type, 0) + 1
            
            recommendations.append(f"🧹 Refactor code to address {len(code_smells)} code smells")
            for smell_type, count in list(smell_types.items())[:3]:
                recommendations.append(f"  - Fix {count} instances of {smell_type}")
        
        # Major issues
        if major_issues:
            recommendations.append(f"⚠️ Resolve {len(major_issues)} major issues")
        
        # General recommendations
        if not critical_issues and not security_issues:
            recommendations.append("✅ Code quality is good - consider minor improvements")
        
        return recommendations

# Local deployment functions for Graph-Sitter
async def deploy_graph_sitter_locally(port: int = 8002) -> Dict[str, Any]:
    """Deploy Graph-Sitter service locally."""
    
    try:
        # Clone the repository if it doesn't exist
        repo_dir = "/tmp/graph-sitter"
        if os.path.exists(repo_dir):
            import shutil
            shutil.rmtree(repo_dir)
        
        # Clone the repository
        clone_result = subprocess.run([
            "git", "clone", "https://github.com/Zeeeepa/graph-sitter.git", repo_dir
        ], capture_output=True, text=True, timeout=60)
        
        if clone_result.returncode != 0:
            raise Exception(f"Failed to clone graph-sitter: {clone_result.stderr}")
        
        # Install dependencies
        install_result = subprocess.run([
            "pip", "install", "-r", "requirements.txt"
        ], cwd=repo_dir, capture_output=True, text=True, timeout=300)
        
        if install_result.returncode != 0:
            raise Exception(f"Failed to install dependencies: {install_result.stderr}")
        
        # Start the service in background
        start_result = subprocess.Popen([
            "python", "main.py", "--port", str(port)
        ], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for the service to start
        await asyncio.sleep(5)
        
        # Test if service is running
        client = GraphSitterClient(f"http://localhost:{port}")
        try:
            await client.test_connection()
            return {
                "success": True,
                "service_url": f"http://localhost:{port}",
                "process_id": start_result.pid,
                "message": "Graph-Sitter deployed successfully"
            }
        except Exception as e:
            start_result.terminate()
            raise Exception(f"Service deployment failed: {str(e)}")
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to deploy Graph-Sitter"
        }

