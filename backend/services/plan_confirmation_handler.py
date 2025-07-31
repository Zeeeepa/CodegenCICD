"""
Plan Confirmation Handler - Manages user approval workflows for agent-generated plans
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel

from backend.database import get_db_session
from backend.models.agent_run import AgentRun, AgentRunStatus
from backend.services.agent_run_manager import AgentRunManager

logger = structlog.get_logger(__name__)


class PlanConfirmationRequest(BaseModel):
    """Request model for plan confirmation"""
    agent_run_id: int
    action: str  # "confirm", "modify", "reject"
    feedback: Optional[str] = None
    modifications: Optional[str] = None


class PlanConfirmationResponse(BaseModel):
    """Response model for plan confirmation"""
    success: bool
    message: str
    agent_run_id: int
    new_status: str
    requires_user_input: bool = False


class PlanAnalysis(BaseModel):
    """Analysis of a generated plan"""
    complexity_score: int  # 1-10
    estimated_duration: str
    risk_level: str  # "low", "medium", "high"
    key_components: List[str]
    potential_issues: List[str]
    recommendations: List[str]


class PlanConfirmationHandler:
    """
    Handles the plan confirmation workflow including:
    - Plan analysis and risk assessment
    - User notification and approval workflows
    - Plan modification handling
    - Integration with agent run manager
    """
    
    def __init__(self):
        self.agent_run_manager = AgentRunManager()
        self._pending_confirmations: Dict[int, Dict[str, Any]] = {}
    
    async def process_plan_confirmation(
        self, 
        request: PlanConfirmationRequest
    ) -> PlanConfirmationResponse:
        """
        Process a plan confirmation request from the user.
        
        Args:
            request: Plan confirmation request with action and feedback
            
        Returns:
            PlanConfirmationResponse with result and next steps
        """
        try:
            logger.info("Processing plan confirmation", 
                       agent_run_id=request.agent_run_id, 
                       action=request.action)
            
            # Get the agent run
            agent_run = await self.agent_run_manager.get_agent_run(request.agent_run_id)
            if not agent_run:
                return PlanConfirmationResponse(
                    success=False,
                    message=f"Agent run {request.agent_run_id} not found",
                    agent_run_id=request.agent_run_id,
                    new_status="error"
                )
            
            # Validate that the run is in a state that can accept confirmation
            if agent_run.status != AgentRunStatus.WAITING_FOR_INPUT:
                return PlanConfirmationResponse(
                    success=False,
                    message=f"Agent run is not waiting for input (current status: {agent_run.status})",
                    agent_run_id=request.agent_run_id,
                    new_status=agent_run.status.value
                )
            
            # Process based on action type
            if request.action == "confirm":
                return await self._handle_plan_confirmation(agent_run, request)
            elif request.action == "modify":
                return await self._handle_plan_modification(agent_run, request)
            elif request.action == "reject":
                return await self._handle_plan_rejection(agent_run, request)
            else:
                return PlanConfirmationResponse(
                    success=False,
                    message=f"Unknown action: {request.action}",
                    agent_run_id=request.agent_run_id,
                    new_status=agent_run.status.value
                )
                
        except Exception as e:
            logger.error("Error processing plan confirmation", 
                        agent_run_id=request.agent_run_id, 
                        error=str(e))
            return PlanConfirmationResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                agent_run_id=request.agent_run_id,
                new_status="error"
            )
    
    async def _handle_plan_confirmation(
        self, 
        agent_run: AgentRun, 
        request: PlanConfirmationRequest
    ) -> PlanConfirmationResponse:
        """Handle plan confirmation (user approves the plan)."""
        try:
            # Continue the agent run with confirmation
            confirmation_message = request.feedback or "Proceed with the plan as proposed."
            
            updated_run = await self.agent_run_manager.continue_agent_run(
                agent_run.id,
                confirmation_message,
                "confirm_plan"
            )
            
            # Remove from pending confirmations
            self._pending_confirmations.pop(agent_run.id, None)
            
            logger.info("Plan confirmed successfully", 
                       agent_run_id=agent_run.id)
            
            return PlanConfirmationResponse(
                success=True,
                message="Plan confirmed. Agent will proceed with implementation.",
                agent_run_id=agent_run.id,
                new_status=updated_run.status.value,
                requires_user_input=False
            )
            
        except Exception as e:
            logger.error("Error confirming plan", 
                        agent_run_id=agent_run.id, 
                        error=str(e))
            raise
    
    async def _handle_plan_modification(
        self, 
        agent_run: AgentRun, 
        request: PlanConfirmationRequest
    ) -> PlanConfirmationResponse:
        """Handle plan modification (user wants changes to the plan)."""
        try:
            if not request.modifications:
                return PlanConfirmationResponse(
                    success=False,
                    message="Modifications text is required for modify action",
                    agent_run_id=agent_run.id,
                    new_status=agent_run.status.value,
                    requires_user_input=True
                )
            
            # Create modification message
            modification_message = f"""Please modify the plan based on this feedback:

{request.modifications}

{request.feedback or ''}

Please provide an updated plan that addresses these concerns."""
            
            updated_run = await self.agent_run_manager.continue_agent_run(
                agent_run.id,
                modification_message,
                "modify_plan"
            )
            
            logger.info("Plan modification requested", 
                       agent_run_id=agent_run.id)
            
            return PlanConfirmationResponse(
                success=True,
                message="Modification request sent. Agent will provide an updated plan.",
                agent_run_id=agent_run.id,
                new_status=updated_run.status.value,
                requires_user_input=False
            )
            
        except Exception as e:
            logger.error("Error requesting plan modification", 
                        agent_run_id=agent_run.id, 
                        error=str(e))
            raise
    
    async def _handle_plan_rejection(
        self, 
        agent_run: AgentRun, 
        request: PlanConfirmationRequest
    ) -> PlanConfirmationResponse:
        """Handle plan rejection (user rejects the plan entirely)."""
        try:
            # Cancel the agent run
            cancelled_run = await self.agent_run_manager.cancel_agent_run(agent_run.id)
            
            # Remove from pending confirmations
            self._pending_confirmations.pop(agent_run.id, None)
            
            # Log rejection reason
            async with get_db_session() as session:
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == agent_run.id)
                    .values(
                        metadata=AgentRun.metadata.op('||')({
                            "rejection_reason": request.feedback or "Plan rejected by user",
                            "rejected_at": datetime.utcnow().isoformat()
                        })
                    )
                )
                await session.commit()
            
            logger.info("Plan rejected by user", 
                       agent_run_id=agent_run.id, 
                       reason=request.feedback)
            
            return PlanConfirmationResponse(
                success=True,
                message="Plan rejected. Agent run has been cancelled.",
                agent_run_id=agent_run.id,
                new_status=cancelled_run.status.value,
                requires_user_input=False
            )
            
        except Exception as e:
            logger.error("Error rejecting plan", 
                        agent_run_id=agent_run.id, 
                        error=str(e))
            raise
    
    async def analyze_plan(self, agent_run_id: int) -> Optional[PlanAnalysis]:
        """
        Analyze a generated plan to provide insights and risk assessment.
        
        Args:
            agent_run_id: ID of the agent run with the plan
            
        Returns:
            PlanAnalysis with complexity, risks, and recommendations
        """
        try:
            agent_run = await self.agent_run_manager.get_agent_run(agent_run_id)
            if not agent_run:
                return None
            
            # Get plan content from metadata
            plan_content = agent_run.metadata.get("plan_content", "")
            if not plan_content:
                return None
            
            # Analyze plan content (simplified analysis)
            analysis = self._perform_plan_analysis(plan_content)
            
            # Store analysis in pending confirmations for quick access
            self._pending_confirmations[agent_run_id] = {
                "analysis": analysis.dict(),
                "created_at": datetime.utcnow().isoformat(),
                "plan_content": plan_content
            }
            
            logger.info("Plan analysis completed", 
                       agent_run_id=agent_run_id, 
                       complexity=analysis.complexity_score)
            
            return analysis
            
        except Exception as e:
            logger.error("Error analyzing plan", 
                        agent_run_id=agent_run_id, 
                        error=str(e))
            return None
    
    def _perform_plan_analysis(self, plan_content: str) -> PlanAnalysis:
        """
        Perform analysis of plan content to assess complexity and risks.
        
        This is a simplified implementation. In production, this could use
        ML models or more sophisticated analysis techniques.
        """
        content_lower = plan_content.lower()
        
        # Calculate complexity score based on content analysis
        complexity_indicators = [
            "database", "migration", "api", "authentication", "security",
            "deployment", "testing", "integration", "microservice", "docker",
            "kubernetes", "cloud", "scaling", "performance", "monitoring"
        ]
        
        complexity_score = min(10, sum(1 for indicator in complexity_indicators 
                                     if indicator in content_lower))
        
        # Estimate duration based on complexity
        if complexity_score <= 3:
            estimated_duration = "1-2 hours"
            risk_level = "low"
        elif complexity_score <= 6:
            estimated_duration = "4-8 hours"
            risk_level = "medium"
        else:
            estimated_duration = "1-3 days"
            risk_level = "high"
        
        # Identify key components
        key_components = []
        component_keywords = {
            "Frontend": ["react", "vue", "angular", "ui", "component", "frontend"],
            "Backend": ["api", "server", "backend", "endpoint", "service"],
            "Database": ["database", "sql", "migration", "schema", "table"],
            "Authentication": ["auth", "login", "user", "permission", "security"],
            "Testing": ["test", "testing", "spec", "unit", "integration"],
            "Deployment": ["deploy", "docker", "kubernetes", "cloud", "ci/cd"]
        }
        
        for component, keywords in component_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                key_components.append(component)
        
        # Identify potential issues
        potential_issues = []
        if "database" in content_lower and "migration" in content_lower:
            potential_issues.append("Database migration may require downtime")
        if "breaking change" in content_lower:
            potential_issues.append("Breaking changes may affect existing functionality")
        if complexity_score > 7:
            potential_issues.append("High complexity may require additional testing")
        if "security" in content_lower:
            potential_issues.append("Security changes require careful review")
        
        # Generate recommendations
        recommendations = []
        if complexity_score > 5:
            recommendations.append("Consider breaking this into smaller phases")
        if "test" not in content_lower:
            recommendations.append("Ensure comprehensive testing is included")
        if "backup" not in content_lower and "database" in content_lower:
            recommendations.append("Consider database backup before migration")
        if risk_level == "high":
            recommendations.append("Recommend staging environment testing first")
        
        return PlanAnalysis(
            complexity_score=complexity_score,
            estimated_duration=estimated_duration,
            risk_level=risk_level,
            key_components=key_components,
            potential_issues=potential_issues,
            recommendations=recommendations
        )
    
    async def get_pending_confirmations(self) -> List[Dict[str, Any]]:
        """Get all agent runs pending plan confirmation."""
        async with get_db_session() as session:
            result = await session.execute(
                select(AgentRun)
                .where(
                    AgentRun.status == AgentRunStatus.WAITING_FOR_INPUT,
                    AgentRun.metadata.op('->>')('plan_detected_at').isnot(None)
                )
                .order_by(AgentRun.created_at.desc())
            )
            
            pending_runs = result.scalars().all()
            
            confirmations = []
            for run in pending_runs:
                confirmation_data = {
                    "agent_run_id": run.id,
                    "project_id": run.project_id,
                    "created_at": run.created_at.isoformat(),
                    "plan_content": run.metadata.get("plan_content", ""),
                    "user_prompt": run.user_prompt,
                    "analysis": self._pending_confirmations.get(run.id, {}).get("analysis")
                }
                confirmations.append(confirmation_data)
            
            return confirmations
    
    async def cleanup_old_confirmations(self, hours_old: int = 24):
        """Clean up old pending confirmations that are no longer relevant."""
        cutoff_time = datetime.utcnow().timestamp() - (hours_old * 3600)
        
        to_remove = []
        for agent_run_id, data in self._pending_confirmations.items():
            created_at = datetime.fromisoformat(data["created_at"]).timestamp()
            if created_at < cutoff_time:
                to_remove.append(agent_run_id)
        
        for agent_run_id in to_remove:
            del self._pending_confirmations[agent_run_id]
        
        logger.info("Cleaned up old pending confirmations", 
                   removed_count=len(to_remove))


# Global instance
plan_confirmation_handler = PlanConfirmationHandler()

