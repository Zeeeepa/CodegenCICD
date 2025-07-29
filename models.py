"""
Database Models for CodegenCICD Dashboard

This module contains Pydantic models for all database entities with proper
field validation, type definitions, and relationship mappings.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class AgentRunStatus(str, Enum):
    """Agent run status enumeration"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class PipelineState(str, Enum):
    """Pipeline state enumeration"""
    CREATED = "created"
    WEBHOOK_SETUP = "webhook_setup"
    AGENT_RUNNING = "agent_running"
    PLAN_CONFIRMATION = "plan_confirmation"
    PR_CREATED = "pr_created"
    SNAPSHOT_CREATING = "snapshot_creating"
    DEPLOYMENT_RUNNING = "deployment_running"
    TESTING = "testing"
    VALIDATION_COMPLETE = "validation_complete"
    AUTO_MERGING = "auto_merging"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestStatus(str, Enum):
    """Test result status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class SnapshotStatus(str, Enum):
    """Grainchain snapshot status enumeration"""
    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DESTROYED = "destroyed"


class WebhookType(str, Enum):
    """Webhook type enumeration"""
    GITHUB_PR = "github_pr"
    GITHUB_PUSH = "github_push"
    CLOUDFLARE = "cloudflare"
    CUSTOM = "custom"


class LogLevel(str, Enum):
    """System log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ============================================================================
# BASE MODELS
# ============================================================================

class BaseDBModel(BaseModel):
    """Base model with common database fields"""
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# ============================================================================
# PROJECT MODELS
# ============================================================================

class ProjectBase(BaseModel):
    """Base project model"""
    name: str = Field(..., min_length=1, max_length=255)
    github_repo_url: str = Field(..., regex=r'^https://github\.com/[\w\-\.]+/[\w\-\.]+$')
    github_repo_name: str = Field(..., min_length=1, max_length=255)
    github_owner: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    default_branch: str = Field(default="main", max_length=255)
    webhook_url: Optional[str] = Field(None, regex=r'^https?://.+')
    webhook_secret: Optional[str] = None
    is_active: bool = Field(default=True)
    auto_merge_enabled: bool = Field(default=False)
    auto_confirm_plans: bool = Field(default=False)

    @validator('github_repo_url')
    def validate_github_url(cls, v):
        if not v.startswith('https://github.com/'):
            raise ValueError('GitHub URL must start with https://github.com/')
        return v


class ProjectCreate(ProjectBase):
    """Model for creating a new project"""
    pass


class ProjectUpdate(BaseModel):
    """Model for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    default_branch: Optional[str] = Field(None, max_length=255)
    webhook_url: Optional[str] = Field(None, regex=r'^https?://.+')
    webhook_secret: Optional[str] = None
    is_active: Optional[bool] = None
    auto_merge_enabled: Optional[bool] = None
    auto_confirm_plans: Optional[bool] = None


class Project(ProjectBase, BaseDBModel):
    """Complete project model"""
    pass


# ============================================================================
# PROJECT SETTINGS MODELS
# ============================================================================

class ProjectSettingsBase(BaseModel):
    """Base project settings model"""
    project_id: int
    planning_statement: Optional[str] = Field(None, max_length=5000)
    repository_rules: Optional[str] = Field(None, max_length=5000)
    setup_commands: Optional[str] = Field(None, max_length=10000)
    target_branch: str = Field(default="main", max_length=255)
    deployment_config: Optional[Dict[str, Any]] = None
    notification_config: Optional[Dict[str, Any]] = None


class ProjectSettingsCreate(ProjectSettingsBase):
    """Model for creating project settings"""
    pass


class ProjectSettingsUpdate(BaseModel):
    """Model for updating project settings"""
    planning_statement: Optional[str] = Field(None, max_length=5000)
    repository_rules: Optional[str] = Field(None, max_length=5000)
    setup_commands: Optional[str] = Field(None, max_length=10000)
    target_branch: Optional[str] = Field(None, max_length=255)
    deployment_config: Optional[Dict[str, Any]] = None
    notification_config: Optional[Dict[str, Any]] = None


class ProjectSettings(ProjectSettingsBase, BaseDBModel):
    """Complete project settings model"""
    pass


# ============================================================================
# PROJECT SECRETS MODELS
# ============================================================================

class ProjectSecretBase(BaseModel):
    """Base project secret model"""
    project_id: int
    key_name: str = Field(..., min_length=1, max_length=255, regex=r'^[A-Z][A-Z0-9_]*$')
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)

    @validator('key_name')
    def validate_key_name(cls, v):
        if not v.isupper():
            raise ValueError('Secret key names must be uppercase')
        return v


class ProjectSecretCreate(ProjectSecretBase):
    """Model for creating a project secret"""
    value: str = Field(..., min_length=1)


class ProjectSecretUpdate(BaseModel):
    """Model for updating a project secret"""
    value: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ProjectSecret(ProjectSecretBase, BaseDBModel):
    """Complete project secret model (without value)"""
    encrypted_value: str


class ProjectSecretWithValue(ProjectSecret):
    """Project secret model with decrypted value"""
    value: str


# ============================================================================
# AGENT RUN MODELS
# ============================================================================

class AgentRunBase(BaseModel):
    """Base agent run model"""
    project_id: int
    prompt: str = Field(..., min_length=1, max_length=50000)
    planning_statement: Optional[str] = Field(None, max_length=5000)
    status: AgentRunStatus = Field(default=AgentRunStatus.PENDING)
    metadata: Optional[Dict[str, Any]] = None


class AgentRunCreate(AgentRunBase):
    """Model for creating an agent run"""
    pass


class AgentRunUpdate(BaseModel):
    """Model for updating an agent run"""
    status: Optional[AgentRunStatus] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    web_url: Optional[str] = None
    github_pr_url: Optional[str] = None
    github_pr_number: Optional[int] = None
    completed_at: Optional[datetime] = None


class AgentRun(AgentRunBase, BaseDBModel):
    """Complete agent run model"""
    codegen_run_id: Optional[int] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    web_url: Optional[str] = None
    github_pr_url: Optional[str] = None
    github_pr_number: Optional[int] = None
    completed_at: Optional[datetime] = None


# ============================================================================
# PIPELINE STATE MODELS
# ============================================================================

class PipelineStateBase(BaseModel):
    """Base pipeline state model"""
    agent_run_id: int
    state: PipelineState
    previous_state: Optional[PipelineState] = None
    data: Optional[Dict[str, Any]] = None
    error_context: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)


class PipelineStateCreate(PipelineStateBase):
    """Model for creating a pipeline state"""
    pass


class PipelineStateUpdate(BaseModel):
    """Model for updating a pipeline state"""
    state: Optional[PipelineState] = None
    data: Optional[Dict[str, Any]] = None
    error_context: Optional[str] = None
    retry_count: Optional[int] = Field(None, ge=0)


class PipelineStateModel(PipelineStateBase, BaseDBModel):
    """Complete pipeline state model"""
    pass


# ============================================================================
# WEBHOOK MODELS
# ============================================================================

class WebhookBase(BaseModel):
    """Base webhook model"""
    project_id: int
    webhook_type: WebhookType
    webhook_url: str = Field(..., regex=r'^https?://.+')
    secret_token: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: bool = Field(default=True)


class WebhookCreate(WebhookBase):
    """Model for creating a webhook"""
    pass


class WebhookUpdate(BaseModel):
    """Model for updating a webhook"""
    webhook_url: Optional[str] = Field(None, regex=r'^https?://.+')
    secret_token: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class Webhook(WebhookBase, BaseDBModel):
    """Complete webhook model"""
    last_triggered_at: Optional[datetime] = None


# ============================================================================
# TEST RESULT MODELS
# ============================================================================

class TestResultBase(BaseModel):
    """Base test result model"""
    agent_run_id: int
    test_type: str = Field(..., min_length=1, max_length=100)
    test_name: str = Field(..., min_length=1, max_length=255)
    status: TestStatus
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    screenshot_path: Optional[str] = None
    log_path: Optional[str] = None


class TestResultCreate(TestResultBase):
    """Model for creating a test result"""
    pass


class TestResultUpdate(BaseModel):
    """Model for updating a test result"""
    status: Optional[TestStatus] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    screenshot_path: Optional[str] = None
    log_path: Optional[str] = None


class TestResult(TestResultBase, BaseDBModel):
    """Complete test result model"""
    pass


# ============================================================================
# GRAINCHAIN SNAPSHOT MODELS
# ============================================================================

class GrainchainSnapshotBase(BaseModel):
    """Base grainchain snapshot model"""
    agent_run_id: int
    snapshot_id: str = Field(..., min_length=1, max_length=255)
    status: SnapshotStatus = Field(default=SnapshotStatus.CREATING)
    config: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class GrainchainSnapshotCreate(GrainchainSnapshotBase):
    """Model for creating a grainchain snapshot"""
    pass


class GrainchainSnapshotUpdate(BaseModel):
    """Model for updating a grainchain snapshot"""
    status: Optional[SnapshotStatus] = None
    config: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    destroyed_at: Optional[datetime] = None


class GrainchainSnapshot(GrainchainSnapshotBase, BaseDBModel):
    """Complete grainchain snapshot model"""
    destroyed_at: Optional[datetime] = None


# ============================================================================
# SYSTEM LOG MODELS
# ============================================================================

class SystemLogBase(BaseModel):
    """Base system log model"""
    level: LogLevel
    message: str = Field(..., min_length=1, max_length=10000)
    component: Optional[str] = Field(None, max_length=255)
    context: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = Field(None, max_length=255)


class SystemLogCreate(SystemLogBase):
    """Model for creating a system log"""
    pass


class SystemLog(SystemLogBase, BaseDBModel):
    """Complete system log model"""
    pass


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ProjectWithSettings(Project):
    """Project model with settings included"""
    settings: Optional[ProjectSettings] = None
    secrets_count: int = 0
    active_runs_count: int = 0


class ProjectSummary(BaseModel):
    """Project summary model"""
    id: int
    name: str
    github_repo_name: str
    is_active: bool
    auto_merge_enabled: bool
    total_runs: int
    completed_runs: int
    failed_runs: int
    running_runs: int
    last_run_at: Optional[datetime] = None


class AgentRunWithProject(AgentRun):
    """Agent run model with project information"""
    project: Project


class PipelineStateWithRun(PipelineStateModel):
    """Pipeline state model with agent run information"""
    agent_run: AgentRun


# ============================================================================
# REQUEST MODELS
# ============================================================================

class BulkProjectCreate(BaseModel):
    """Model for bulk project creation"""
    projects: List[ProjectCreate]


class BulkSecretCreate(BaseModel):
    """Model for bulk secret creation"""
    project_id: int
    secrets: List[ProjectSecretCreate]


class WebhookEvent(BaseModel):
    """Model for webhook event payload"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    signature: Optional[str] = None


# ============================================================================
# PAGINATION MODELS
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool


class PaginatedProjects(BaseModel):
    """Paginated projects response"""
    items: List[Project]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool


class PaginatedAgentRuns(BaseModel):
    """Paginated agent runs response"""
    items: List[AgentRun]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool

