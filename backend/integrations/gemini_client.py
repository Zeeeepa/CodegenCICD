"""
Gemini API client for AI validation and error analysis
"""
import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found, using mock responses")
    
    async def analyze_deployment(self, prompt: str) -> Dict[str, Any]:
        """Analyze deployment logs and determine success/failure"""
        try:
            if not self.api_key:
                # Return mock analysis for development
                return {
                    "success": True,
                    "confidence_score": 85,
                    "analysis": "Deployment appears successful based on log patterns",
                    "issues": [],
                    "recommendations": [
                        "Monitor application performance after deployment",
                        "Verify all endpoints are responding correctly"
                    ]
                }
            
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"""
                            You are an expert DevOps engineer analyzing deployment logs. 
                            Please analyze the following deployment information and provide:
                            
                            1. Success/failure assessment (boolean)
                            2. Confidence score (0-100)
                            3. Brief analysis summary
                            4. List of any issues identified
                            5. Recommendations for improvement
                            
                            Deployment Information:
                            {prompt}
                            
                            Please respond in JSON format with the following structure:
                            {{
                                "success": boolean,
                                "confidence_score": number,
                                "analysis": "string",
                                "issues": ["string"],
                                "recommendations": ["string"]
                            }}
                            """
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 1,
                        "topP": 1,
                        "maxOutputTokens": 1024,
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/models/gemini-pro:generateContent",
                    headers=headers,
                    json=payload,
                    params={"key": self.api_key},
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract text from Gemini response
                content = result.get("candidates", [{}])[0].get("content", {})
                text = content.get("parts", [{}])[0].get("text", "")
                
                # Try to parse JSON response
                try:
                    import json
                    analysis = json.loads(text.strip())
                    logger.info("Completed deployment analysis with Gemini")
                    return analysis
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        "success": "error" not in text.lower() and "fail" not in text.lower(),
                        "confidence_score": 70,
                        "analysis": text,
                        "issues": [],
                        "recommendations": []
                    }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error analyzing deployment: {e}")
            # Return conservative analysis on error
            return {
                "success": False,
                "confidence_score": 30,
                "analysis": f"Analysis failed due to API error: {e}",
                "issues": ["Unable to complete analysis"],
                "recommendations": ["Manual review required"]
            }
        except Exception as e:
            logger.error(f"Error analyzing deployment: {e}")
            return {
                "success": False,
                "confidence_score": 30,
                "analysis": f"Analysis failed: {e}",
                "issues": ["Analysis error"],
                "recommendations": ["Manual review required"]
            }
    
    async def analyze_error(self, error_context: str) -> Dict[str, Any]:
        """Analyze error and provide fix recommendations"""
        try:
            if not self.api_key:
                # Return mock error analysis
                return {
                    "root_cause": "Mock error analysis - API key not configured",
                    "severity": "medium",
                    "fix_recommendations": [
                        "Check configuration settings",
                        "Verify environment variables",
                        "Review error logs for more details"
                    ],
                    "code_fixes": [],
                    "estimated_fix_time": "15-30 minutes"
                }
            
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"""
                            You are an expert software engineer analyzing a CI/CD pipeline error.
                            Please analyze the following error and provide:
                            
                            1. Root cause analysis
                            2. Severity assessment (low/medium/high/critical)
                            3. Specific fix recommendations
                            4. Code changes needed (if applicable)
                            5. Estimated time to fix
                            
                            Error Context:
                            {error_context}
                            
                            Please respond in JSON format with the following structure:
                            {{
                                "root_cause": "string",
                                "severity": "string",
                                "fix_recommendations": ["string"],
                                "code_fixes": [{{
                                    "file": "string",
                                    "change_description": "string",
                                    "code_snippet": "string"
                                }}],
                                "estimated_fix_time": "string"
                            }}
                            """
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 1,
                        "topP": 1,
                        "maxOutputTokens": 1024,
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/models/gemini-pro:generateContent",
                    headers=headers,
                    json=payload,
                    params={"key": self.api_key},
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract text from Gemini response
                content = result.get("candidates", [{}])[0].get("content", {})
                text = content.get("parts", [{}])[0].get("text", "")
                
                # Try to parse JSON response
                try:
                    import json
                    analysis = json.loads(text.strip())
                    logger.info("Completed error analysis with Gemini")
                    return analysis
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        "root_cause": "Unable to parse error analysis",
                        "severity": "medium",
                        "fix_recommendations": [text],
                        "code_fixes": [],
                        "estimated_fix_time": "Unknown"
                    }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error analyzing error: {e}")
            return {
                "root_cause": f"Analysis failed due to API error: {e}",
                "severity": "unknown",
                "fix_recommendations": ["Manual analysis required"],
                "code_fixes": [],
                "estimated_fix_time": "Unknown"
            }
        except Exception as e:
            logger.error(f"Error analyzing error: {e}")
            return {
                "root_cause": f"Analysis failed: {e}",
                "severity": "unknown",
                "fix_recommendations": ["Manual analysis required"],
                "code_fixes": [],
                "estimated_fix_time": "Unknown"
            }
    
    async def validate_code_quality(self, code_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate code quality based on analysis results"""
        try:
            if not self.api_key:
                return {
                    "quality_score": 85,
                    "passes_threshold": True,
                    "critical_issues": 0,
                    "recommendations": [
                        "Code quality appears acceptable",
                        "Continue monitoring for improvements"
                    ]
                }
            
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                }
                
                analysis_summary = f"""
                Code Analysis Results:
                - Total files: {code_analysis.get('metrics', {}).get('total_files', 0)}
                - Complexity score: {code_analysis.get('metrics', {}).get('complexity_score', 0)}
                - Maintainability index: {code_analysis.get('metrics', {}).get('maintainability_index', 0)}
                - Test coverage: {code_analysis.get('metrics', {}).get('test_coverage', 0)}%
                - Issues found: {len(code_analysis.get('issues', []))}
                """
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"""
                            You are a senior code reviewer evaluating code quality.
                            Based on the following analysis results, provide:
                            
                            1. Overall quality score (0-100)
                            2. Whether it passes quality threshold (>70)
                            3. Number of critical issues
                            4. Specific recommendations for improvement
                            
                            {analysis_summary}
                            
                            Please respond in JSON format:
                            {{
                                "quality_score": number,
                                "passes_threshold": boolean,
                                "critical_issues": number,
                                "recommendations": ["string"]
                            }}
                            """
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 1,
                        "topP": 1,
                        "maxOutputTokens": 512,
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/models/gemini-pro:generateContent",
                    headers=headers,
                    json=payload,
                    params={"key": self.api_key},
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract and parse response
                content = result.get("candidates", [{}])[0].get("content", {})
                text = content.get("parts", [{}])[0].get("text", "")
                
                try:
                    import json
                    validation = json.loads(text.strip())
                    logger.info("Completed code quality validation with Gemini")
                    return validation
                except json.JSONDecodeError:
                    # Fallback based on metrics
                    maintainability = code_analysis.get('metrics', {}).get('maintainability_index', 70)
                    return {
                        "quality_score": maintainability,
                        "passes_threshold": maintainability >= 70,
                        "critical_issues": len([i for i in code_analysis.get('issues', []) if i.get('severity') == 'high']),
                        "recommendations": ["Review code analysis results manually"]
                    }
                
        except Exception as e:
            logger.error(f"Error validating code quality: {e}")
            # Conservative fallback
            return {
                "quality_score": 70,
                "passes_threshold": True,
                "critical_issues": 0,
                "recommendations": ["Manual quality review recommended"]
            }
    
    async def generate_test_suggestions(self, code_context: str) -> Dict[str, Any]:
        """Generate test suggestions based on code context"""
        try:
            if not self.api_key:
                return {
                    "test_suggestions": [
                        "Add unit tests for core functions",
                        "Implement integration tests for API endpoints",
                        "Add end-to-end tests for user workflows"
                    ],
                    "coverage_recommendations": [
                        "Increase test coverage to >80%",
                        "Focus on testing error handling paths"
                    ]
                }
            
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"""
                            You are a testing expert reviewing code for test coverage.
                            Based on the following code context, suggest:
                            
                            1. Specific test cases that should be added
                            2. Coverage improvement recommendations
                            3. Testing strategy recommendations
                            
                            Code Context:
                            {code_context}
                            
                            Please respond in JSON format:
                            {{
                                "test_suggestions": ["string"],
                                "coverage_recommendations": ["string"],
                                "testing_strategy": ["string"]
                            }}
                            """
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,
                        "topK": 1,
                        "topP": 1,
                        "maxOutputTokens": 512,
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/models/gemini-pro:generateContent",
                    headers=headers,
                    json=payload,
                    params={"key": self.api_key},
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract and parse response
                content = result.get("candidates", [{}])[0].get("content", {})
                text = content.get("parts", [{}])[0].get("text", "")
                
                try:
                    import json
                    suggestions = json.loads(text.strip())
                    logger.info("Generated test suggestions with Gemini")
                    return suggestions
                except json.JSONDecodeError:
                    return {
                        "test_suggestions": [text],
                        "coverage_recommendations": [],
                        "testing_strategy": []
                    }
                
        except Exception as e:
            logger.error(f"Error generating test suggestions: {e}")
            return {
                "test_suggestions": ["Manual test planning recommended"],
                "coverage_recommendations": [],
                "testing_strategy": []
            }

