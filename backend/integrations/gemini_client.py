"""
Gemini API client for AI validation and analysis
"""
import google.generativeai as genai
import structlog
from typing import Dict, Any, Optional, List
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GeminiClient:
    """Client for interacting with Gemini API"""
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def validate_deployment(self, deployment_logs: str, setup_commands: str, 
                                 context: str = None) -> Dict[str, Any]:
        """Validate deployment success using Gemini AI"""
        prompt = f"""
        Analyze the following deployment logs and determine if the deployment was successful.
        
        Setup Commands:
        {setup_commands}
        
        Deployment Logs:
        {deployment_logs}
        
        {f"Additional Context: {context}" if context else ""}
        
        Please provide:
        1. A boolean success status (true/false)
        2. A confidence score (0-100)
        3. A brief explanation of your assessment
        4. Any issues or errors found
        5. Recommendations for improvement (if any)
        
        Respond in JSON format:
        {{
            "success": boolean,
            "confidence": number,
            "explanation": "string",
            "issues": ["list of issues"],
            "recommendations": ["list of recommendations"]
        }}
        """
        
        try:
            response = await self._generate_content(prompt)
            
            # Parse JSON response
            import json
            result = json.loads(response)
            
            logger.info(
                "Deployment validation completed",
                success=result.get("success"),
                confidence=result.get("confidence")
            )
            
            return result
        except Exception as e:
            logger.error("Failed to validate deployment", error=str(e))
            return {
                "success": False,
                "confidence": 0,
                "explanation": f"Validation failed due to error: {str(e)}",
                "issues": ["AI validation service unavailable"],
                "recommendations": ["Retry validation or check manually"]
            }
    
    async def analyze_error_logs(self, error_logs: str, context: str = None) -> Dict[str, Any]:
        """Analyze error logs and provide suggestions"""
        prompt = f"""
        Analyze the following error logs and provide actionable insights.
        
        Error Logs:
        {error_logs}
        
        {f"Context: {context}" if context else ""}
        
        Please provide:
        1. Root cause analysis
        2. Severity level (low/medium/high/critical)
        3. Suggested fixes
        4. Prevention strategies
        
        Respond in JSON format:
        {{
            "root_cause": "string",
            "severity": "string",
            "suggested_fixes": ["list of fixes"],
            "prevention_strategies": ["list of strategies"],
            "confidence": number
        }}
        """
        
        try:
            response = await self._generate_content(prompt)
            
            import json
            result = json.loads(response)
            
            logger.info(
                "Error analysis completed",
                severity=result.get("severity"),
                confidence=result.get("confidence")
            )
            
            return result
        except Exception as e:
            logger.error("Failed to analyze error logs", error=str(e))
            return {
                "root_cause": "Unable to analyze due to AI service error",
                "severity": "unknown",
                "suggested_fixes": ["Manual investigation required"],
                "prevention_strategies": ["Ensure AI service availability"],
                "confidence": 0
            }
    
    async def generate_fix_prompt(self, error_context: str, code_context: str = None) -> str:
        """Generate a prompt for Codegen to fix issues"""
        prompt = f"""
        Based on the following error context, generate a clear and specific prompt that can be sent to a code generation AI to fix the issue.
        
        Error Context:
        {error_context}
        
        {f"Code Context: {code_context}" if code_context else ""}
        
        Generate a prompt that:
        1. Clearly describes the problem
        2. Provides specific instructions for the fix
        3. Includes any necessary context
        4. Is actionable and precise
        
        Return only the generated prompt, no additional formatting or explanation.
        """
        
        try:
            response = await self._generate_content(prompt)
            logger.info("Fix prompt generated", prompt_length=len(response))
            return response.strip()
        except Exception as e:
            logger.error("Failed to generate fix prompt", error=str(e))
            return f"Please fix the following error: {error_context}"
    
    async def validate_code_quality(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Validate code quality and provide suggestions"""
        prompt = f"""
        Analyze the following {language} code for quality, best practices, and potential issues.
        
        Code:
        {code}
        
        Please evaluate:
        1. Code quality (0-100 score)
        2. Security issues
        3. Performance concerns
        4. Best practice violations
        5. Maintainability issues
        
        Respond in JSON format:
        {{
            "quality_score": number,
            "security_issues": ["list of security issues"],
            "performance_issues": ["list of performance issues"],
            "best_practice_violations": ["list of violations"],
            "maintainability_issues": ["list of issues"],
            "overall_assessment": "string"
        }}
        """
        
        try:
            response = await self._generate_content(prompt)
            
            import json
            result = json.loads(response)
            
            logger.info(
                "Code quality validation completed",
                quality_score=result.get("quality_score")
            )
            
            return result
        except Exception as e:
            logger.error("Failed to validate code quality", error=str(e))
            return {
                "quality_score": 0,
                "security_issues": ["Unable to analyze"],
                "performance_issues": ["Unable to analyze"],
                "best_practice_violations": ["Unable to analyze"],
                "maintainability_issues": ["Unable to analyze"],
                "overall_assessment": f"Analysis failed: {str(e)}"
            }
    
    async def _generate_content(self, prompt: str) -> str:
        """Generate content using Gemini model"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error("Gemini content generation failed", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if Gemini API is accessible"""
        try:
            test_prompt = "Respond with 'OK' if you can process this request."
            response = await self._generate_content(test_prompt)
            return "OK" in response.upper()
        except Exception as e:
            logger.error("Gemini API health check failed", error=str(e))
            return False

