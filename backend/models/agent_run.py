"""
Agent run related database models
"""
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel


class AgentRunStatus(enum.Enum):
    """Agent run status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRunType(enum.Enum):
    """Agent run type enumeration"""
    REGULAR = "regular"
    PLAN = "plan"
    PR_CREATION = "pr_creation"
    ERROR_FIX = "error_fix"


class AgentRun(BaseModel):
    """Agent run model representing a Codegen API agent execution"""
    __tablename__ = "agent_runs"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Agent run identification
    codegen_run_id = Column(String(255), unique=True, index=True)  # Codegen API run ID
    
    # Run configuration
    target = Column(Text, nullable=False)  # User's target/goal
    planning_statement = Column(Text)  # Prepended planning statement
    run_type = Column(Enum(AgentRunType), default=AgentRunType.REGULAR, nullable=False)
    
    # Run status and progress
    status = Column(Enum(AgentRunStatus), default=AgentRunStatus.PENDING, nullable=False, index=True)
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String(255))
    
    # Results and outputs
    final_response = Column(Text)
    error_message = Column(Text)
    pr_url = Column(String(500))  # GitHub PR URL if created
    pr_number = Column(Integer)  # GitHub PR number if created
    
    # Execution metadata
    execution_time_seconds = Column(Integer)
    tokens_used = Column(Integer)
    cost_usd = Column(String(20))  # Store as string to avoid floating point issues
    
    # Configuration and settings
    auto_confirm_plans = Column(Boolean, default=False, nullable=False)
    max_iterations = Column(Integer, default=10)
    
    # Metadata
    run_metadata = Column(JSON, default=dict)
    
    # Relationships
    project = relationship("Project", back_populates="agent_runs")
    steps = relationship("AgentRunStep", back_populates="agent_run", cascade="all, delete-orphan", order_by="AgentRunStep.step_number")
    responses = relationship("AgentRunResponse", back_populates="agent_run", cascade="all, delete-orphan", order_by="AgentRunResponse.sequence_number")
    validation_runs = relationship("ValidationRun", back_populates="agent_run", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<AgentRun(id={self.id}, status={self.status.value}, project_id={self.project_id})>"
    
    @property
    def is_active(self) -> bool:
        """Check if agent run is currently active"""
        return self.status in [AgentRunStatus.PENDING, AgentRunStatus.RUNNING, AgentRunStatus.WAITING_FOR_INPUT]
    
    @property
    def is_completed(self) -> bool:
        """Check if agent run is completed (success or failure)"""
        return self.status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]
    
    def get_latest_response(self) -> Optional["AgentRunResponse"]:
        """Get the latest response from this agent run"""
        if self.responses:
            return max(self.responses, key=lambda r: r.sequence_number)
        return None
    
    def add_step(self, step_name: str, step_data: Dict[str, Any]) -> "AgentRunStep":
        """Add a new step to this agent run"""
        step_number = len(self.steps) + 1
        step = AgentRunStep(
            agent_run_id=self.id,
            step_number=step_number,
            step_name=step_name,
            step_data=step_data
        )
        self.steps.append(step)
        return step


class AgentRunStep(BaseModel):
    """Individual steps within an agent run"""
    __tablename__ = "agent_run_steps"
    
    agent_run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=False)
    
    # Step information
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    step_description = Column(Text)
    
    # Step execution
    started_at = Column(String(50))  # ISO timestamp as string
    completed_at = Column(String(50))  # ISO timestamp as string
    duration_seconds = Column(Integer)
    
    # Step data and results
    step_data = Column(JSON, default=dict)
    result_data = Column(JSON, default=dict)
    error_message = Column(Text)
    
    # Step status
    is_completed = Column(Boolean, default=False, nullable=False)
    is_successful = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    agent_run = relationship("AgentRun", back_populates="steps")
    
    def __repr__(self) -> str:
        return f"<AgentRunStep(agent_run_id={self.agent_run_id}, step={self.step_number}, name={self.step_name})>"


class AgentRunResponse(BaseModel):
    """Responses from agent runs (for conversation-like interactions)"""
    __tablename__ = "agent_run_responses"
    
    agent_run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=False)
    
    # Response sequencing
    sequence_number = Column(Integer, nullable=False)
    
    # Response content
    response_type = Column(String(50), nullable=False)  # regular, plan, pr_created, error
    content = Column(Text, nullable=False)
    
    # Response metadata
    is_final = Column(Boolean, default=False, nullable=False)
    requires_user_input = Column(Boolean, default=False, nullable=False)
    
    # Plan-specific data (if response_type is 'plan')
    plan_data = Column(JSON, default=dict)
    
    # PR-specific data (if response_type is 'pr_created')
    pr_data = Column(JSON, default=dict)
    
    # Additional metadata
    step_metadata = Column(JSON, default=dict)
    
    # Relationships
    agent_run = relationship("AgentRun", back_populates="responses")
    
    def __repr__(self) -> str:
        return f"<AgentRunResponse(agent_run_id={self.agent_run_id}, seq={self.sequence_number}, type={self.response_type})>"
