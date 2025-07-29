"""
Enhanced Pydantic models for Codegen API with comprehensive validation
"""
import re
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, validator, root_validator


class SourceType(str, Enum):
    """Source types for agent runs"""
    LOCAL = "LOCAL"
    SLACK = "SLACK"
    GITHUB = "GITHUB"
    GITHUB_CHECK_SUITE = "GITHUB_CHECK_SUITE"
    LINEAR = "LINEAR"
    API = "API"
    CHAT = "CHAT"
    JIRA = "JIRA"


class MessageType(str, Enum):
    """Message types for agent run logs"""
    ACTION = "ACTION"
    PLAN_EVALUATION = "PLAN_EVALUATION"
    FINAL_ANSWER = "FINAL_ANSWER"
    ERROR = "ERROR"
    USER_MESSAGE = "USER_MESSAGE"
    USER_GITHUB_ISSUE_COMMENT = "USER_GITHUB_ISSUE_COMMENT"
    INITIAL_PR_GENERATION = "INITIAL_PR_GENERATION"
    DETECT_PR_ERRORS = "DETECT_PR_ERRORS"
    FIX_PR_ERRORS = "FIX_PR_ERRORS"
    PR_CREATION_FAILED = "PR_CREATION_FAILED"
    PR_EVALUATION = "PR_EVALUATION"
    COMMIT_EVALUATION = "COMMIT_EVALUATION"
    AGENT_RUN_LINK = "AGENT_RUN_LINK"


class AgentRunStatus(str, Enum):
    """Agent run status values"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class UserResponse(BaseModel):
    """User information from API responses"""
    id: int = Field(..., description="Unique user identifier")
    email: Optional[str] = Field(None, description="User email address")
    github_user_id: str = Field(..., description="GitHub user ID")
    github_username: str = Field(..., description="GitHub username")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    full_name: Optional[str] = Field(None, description="User's full name")

    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @validator('avatar_url')
    def validate_avatar_url(cls, v):
        """Validate avatar URL format"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Avatar URL must be a valid HTTP/HTTPS URL')
        return v

    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True


class GithubPullRequestResponse(BaseModel):
    """GitHub pull request information"""
    id: int = Field(..., description="Pull request ID")
    title: str = Field(..., description="Pull request title")
    url: str = Field(..., description="Pull request URL")
    created_at: str = Field(..., description="Creation timestamp")

    @validator('url')
    def validate_url(cls, v):
        """Validate GitHub PR URL format"""
        if not v.startswith('https://github.com/'):
            raise ValueError('Must be a valid GitHub URL')
        return v

    class Config:
        use_enum_values = True
        validate_assignment = True


class AgentRunResponse(BaseModel):
    """Agent run information from API responses"""
    id: int = Field(..., description="Unique agent run identifier")
    organization_id: int = Field(..., description="Organization ID")
    status: Optional[AgentRunStatus] = Field(None, description="Current run status")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    web_url: Optional[str] = Field(None, description="Web interface URL")
    result: Optional[str] = Field(None, description="Run result or output")
    source_type: Optional[SourceType] = Field(None, description="Source that triggered the run")
    github_pull_requests: Optional[List[GithubPullRequestResponse]] = Field(
        default_factory=list, description="Associated GitHub PRs"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator('web_url')
    def validate_web_url(cls, v):
        """Validate web URL format"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Web URL must be a valid HTTP/HTTPS URL')
        return v

    class Config:
        use_enum_values = True
        validate_assignment = True


class AgentRunLogResponse(BaseModel):
    """Agent run log entry"""
    agent_run_id: int = Field(..., description="Associated agent run ID")
    created_at: str = Field(..., description="Log entry timestamp")
    message_type: MessageType = Field(..., description="Type of log message")
    thought: Optional[str] = Field(None, description="Agent's thought process")
    tool_name: Optional[str] = Field(None, description="Tool that was used")
    tool_input: Optional[Dict[str, Any]] = Field(None, description="Input to the tool")
    tool_output: Optional[Dict[str, Any]] = Field(None, description="Output from the tool")
    observation: Optional[Union[Dict[str, Any], str]] = Field(None, description="Agent's observation")

    class Config:
        use_enum_values = True
        validate_assignment = True


class OrganizationSettings(BaseModel):
    """Organization settings configuration"""
    # Add specific settings fields as they become available
    max_concurrent_runs: Optional[int] = Field(None, description="Maximum concurrent agent runs")
    default_timeout: Optional[int] = Field(None, description="Default timeout for runs")
    webhook_url: Optional[str] = Field(None, description="Webhook endpoint URL")
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        """Validate webhook URL format"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Webhook URL must be a valid HTTP/HTTPS URL')
        return v

    class Config:
        use_enum_values = True
        validate_assignment = True


class OrganizationResponse(BaseModel):
    """Organization information"""
    id: int = Field(..., description="Unique organization identifier")
    name: str = Field(..., description="Organization name")
    settings: OrganizationSettings = Field(
        default_factory=OrganizationSettings, description="Organization settings"
    )

    class Config:
        use_enum_values = True
        validate_assignment = True


class PaginatedResponse(BaseModel):
    """Base class for paginated API responses"""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")

    @validator('page')
    def validate_page(cls, v):
        """Validate page number"""
        if v < 1:
            raise ValueError('Page number must be >= 1')
        return v

    @validator('size')
    def validate_size(cls, v):
        """Validate page size"""
        if not (1 <= v <= 100):
            raise ValueError('Page size must be between 1 and 100')
        return v

    class Config:
        use_enum_values = True
        validate_assignment = True


class UsersResponse(PaginatedResponse):
    """Paginated users response"""
    items: List[UserResponse] = Field(..., description="List of users")


class AgentRunsResponse(PaginatedResponse):
    """Paginated agent runs response"""
    items: List[AgentRunResponse] = Field(..., description="List of agent runs")


class OrganizationsResponse(PaginatedResponse):
    """Paginated organizations response"""
    items: List[OrganizationResponse] = Field(..., description="List of organizations")


class AgentRunWithLogsResponse(BaseModel):
    """Agent run with associated logs"""
    id: int = Field(..., description="Agent run ID")
    organization_id: int = Field(..., description="Organization ID")
    logs: List[AgentRunLogResponse] = Field(..., description="Associated log entries")
    status: Optional[AgentRunStatus] = Field(None, description="Current run status")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    web_url: Optional[str] = Field(None, description="Web interface URL")
    result: Optional[str] = Field(None, description="Run result")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    total_logs: Optional[int] = Field(None, description="Total number of logs")
    page: Optional[int] = Field(None, description="Current page of logs")
    size: Optional[int] = Field(None, description="Logs per page")
    pages: Optional[int] = Field(None, description="Total pages of logs")

    class Config:
        use_enum_values = True
        validate_assignment = True


# Request Models
class CreateAgentRunRequest(BaseModel):
    """Request model for creating agent runs"""
    prompt: str = Field(..., min_length=1, max_length=10000, description="Agent prompt")
    images: Optional[List[str]] = Field(None, max_items=10, description="Base64 encoded images")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('images')
    def validate_images(cls, v):
        """Validate image data URIs"""
        if v:
            for img in v:
                if not img.startswith('data:image/'):
                    raise ValueError('Images must be base64 data URIs starting with "data:image/"')
        return v

    @validator('prompt')
    def validate_prompt(cls, v):
        """Validate prompt content"""
        if not v.strip():
            raise ValueError('Prompt cannot be empty or whitespace only')
        return v.strip()

    class Config:
        use_enum_values = True
        validate_assignment = True


class ResumeAgentRunRequest(BaseModel):
    """Request model for resuming agent runs"""
    agent_run_id: int = Field(..., description="ID of the agent run to resume")
    prompt: str = Field(..., min_length=1, max_length=10000, description="Resume prompt")
    images: Optional[List[str]] = Field(None, max_items=10, description="Base64 encoded images")

    @validator('images')
    def validate_images(cls, v):
        """Validate image data URIs"""
        if v:
            for img in v:
                if not img.startswith('data:image/'):
                    raise ValueError('Images must be base64 data URIs starting with "data:image/"')
        return v

    @validator('prompt')
    def validate_prompt(cls, v):
        """Validate prompt content"""
        if not v.strip():
            raise ValueError('Prompt cannot be empty or whitespace only')
        return v.strip()

    class Config:
        use_enum_values = True
        validate_assignment = True


class ListAgentRunsRequest(BaseModel):
    """Request model for listing agent runs"""
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    source_type: Optional[SourceType] = Field(None, description="Filter by source type")
    status: Optional[AgentRunStatus] = Field(None, description="Filter by status")
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(100, ge=1, le=100, description="Number of items to return")

    class Config:
        use_enum_values = True
        validate_assignment = True


class WebhookEvent(BaseModel):
    """Webhook event payload"""
    event_type: str = Field(..., description="Type of webhook event")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data payload")
    signature: Optional[str] = Field(None, description="Webhook signature for verification")

    class Config:
        use_enum_values = True
        validate_assignment = True


# Utility functions for model conversion
def convert_dict_to_model(data: Dict[str, Any], model_class: BaseModel) -> BaseModel:
    """Convert dictionary to Pydantic model with validation"""
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"Failed to convert data to {model_class.__name__}: {str(e)}")


def convert_model_to_dict(model: BaseModel, exclude_none: bool = True) -> Dict[str, Any]:
    """Convert Pydantic model to dictionary"""
    return model.dict(exclude_none=exclude_none)

