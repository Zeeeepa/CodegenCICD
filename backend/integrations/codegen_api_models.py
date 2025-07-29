"""
Codegen API data models and enums
"""
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class SourceType(Enum):
    LOCAL = "LOCAL"
    SLACK = "SLACK"
    GITHUB = "GITHUB"
    GITHUB_CHECK_SUITE = "GITHUB_CHECK_SUITE"
    LINEAR = "LINEAR"
    API = "API"
    CHAT = "CHAT"
    JIRA = "JIRA"


class MessageType(Enum):
    # Plan Agent Types
    ACTION = "ACTION"
    PLAN_EVALUATION = "PLAN_EVALUATION"
    FINAL_ANSWER = "FINAL_ANSWER"
    ERROR = "ERROR"
    USER_MESSAGE = "USER_MESSAGE"
    USER_GITHUB_ISSUE_COMMENT = "USER_GITHUB_ISSUE_COMMENT"
    
    # PR Agent Types
    INITIAL_PR_GENERATION = "INITIAL_PR_GENERATION"
    DETECT_PR_ERRORS = "DETECT_PR_ERRORS"
    FIX_PR_ERRORS = "FIX_PR_ERRORS"
    PR_CREATION_FAILED = "PR_CREATION_FAILED"
    PR_EVALUATION = "PR_EVALUATION"
    
    # Commit Agent Types
    COMMIT_EVALUATION = "COMMIT_EVALUATION"
    
    # Link Types
    AGENT_RUN_LINK = "AGENT_RUN_LINK"


class AgentRunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class UserResponse:
    id: int
    email: Optional[str]
    github_user_id: str
    github_username: str
    avatar_url: Optional[str]
    full_name: Optional[str]


@dataclass
class GithubPullRequestResponse:
    id: int
    title: str
    url: str
    created_at: str


@dataclass
class AgentRunResponse:
    id: int
    organization_id: int
    status: Optional[str]
    created_at: Optional[str]
    web_url: Optional[str]
    result: Optional[str]
    source_type: Optional[SourceType]
    github_pull_requests: Optional[List[GithubPullRequestResponse]]
    metadata: Optional[Dict[str, Any]]


@dataclass
class AgentRunLogResponse:
    agent_run_id: int
    created_at: str
    message_type: str
    thought: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    observation: Optional[Union[Dict[str, Any], str]] = None


@dataclass
class OrganizationSettings:
    # Add specific settings fields as they become available
    pass


@dataclass
class OrganizationResponse:
    id: int
    name: str
    settings: OrganizationSettings


@dataclass
class PaginatedResponse:
    total: int
    page: int
    size: int
    pages: int


@dataclass
class UsersResponse(PaginatedResponse):
    items: List[UserResponse]


@dataclass
class AgentRunsResponse(PaginatedResponse):
    items: List[AgentRunResponse]


@dataclass
class OrganizationsResponse(PaginatedResponse):
    items: List[OrganizationResponse]


@dataclass
class AgentRunWithLogsResponse:
    id: int
    organization_id: int
    logs: List[AgentRunLogResponse]
    status: Optional[str]
    created_at: Optional[str]
    web_url: Optional[str]
    result: Optional[str]
    metadata: Optional[Dict[str, Any]]
    total_logs: Optional[int]
    page: Optional[int]
    size: Optional[int]
    pages: Optional[int]


@dataclass
class WebhookEvent:
    """Webhook event payload"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    signature: Optional[str] = None


@dataclass
class BulkOperationResult:
    """Result of a bulk operation"""
    total_items: int
    successful_items: int
    failed_items: int
    success_rate: float
    duration_seconds: float
    errors: List[Dict[str, Any]]
    results: List[Any]


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    method: str
    endpoint: str
    status_code: int
    duration_seconds: float
    timestamp: datetime
    request_id: str
    cached: bool = False


@dataclass
class ClientStats:
    """Comprehensive client statistics"""
    uptime_seconds: float
    total_requests: int
    total_errors: int
    error_rate: float
    requests_per_minute: float
    average_response_time: float
    cache_hit_rate: float
    status_code_distribution: Dict[int, int]
    recent_requests: List[RequestMetrics]

