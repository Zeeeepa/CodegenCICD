"""
Webhook event models for tracking GitHub and other webhook events
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any
from enum import Enum as PyEnum
from datetime import datetime


class WebhookEventType(PyEnum):
    """Webhook event type enumeration"""
    GITHUB_PUSH = "github_push"
    GITHUB_PR_OPENED = "github_pr_opened"
    GITHUB_PR_UPDATED = "github_pr_updated"
    GITHUB_PR_CLOSED = "github_pr_closed"
    GITHUB_PR_MERGED = "github_pr_merged"
    GITHUB_ISSUE_OPENED = "github_issue_opened"
    GITHUB_ISSUE_UPDATED = "github_issue_updated"
    GITHUB_ISSUE_CLOSED = "github_issue_closed"
    CLOUDFLARE_WEBHOOK = "cloudflare_webhook"
    CUSTOM_WEBHOOK = "custom_webhook"


class WebhookEventStatus(PyEnum):
    """Webhook event processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    IGNORED = "ignored"


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project (optional, some webhooks might not be project-specific)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    
    # Event details
    event_type = Column(Enum(WebhookEventType), nullable=False, index=True)
    event_id = Column(String(255), nullable=True, index=True)  # External event ID (e.g., GitHub delivery ID)
    source = Column(String(100), nullable=False, index=True)  # e.g., "github", "cloudflare"
    
    # Processing status
    status = Column(Enum(WebhookEventStatus), default=WebhookEventStatus.PENDING, index=True)
    
    # Event data
    headers = Column(JSON, nullable=True)  # HTTP headers
    payload = Column(JSON, nullable=False)  # Event payload
    signature = Column(String(255), nullable=True)  # Webhook signature for verification
    
    # Processing details
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_duration = Column(Integer, nullable=True)  # Duration in milliseconds
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Related entities
    pr_number = Column(Integer, nullable=True)
    issue_number = Column(Integer, nullable=True)
    commit_sha = Column(String(40), nullable=True)
    branch_name = Column(String(255), nullable=True)
    
    # Actions triggered
    triggered_agent_run = Column(Boolean, default=False)
    triggered_validation = Column(Boolean, default=False)
    triggered_merge = Column(Boolean, default=False)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="webhook_events")
    
    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, type='{self.event_type.value}', status='{self.status.value}')>"
    
    @property
    def is_processed(self) -> bool:
        """Check if webhook event has been processed"""
        return self.status in [WebhookEventStatus.COMPLETED, WebhookEventStatus.FAILED, WebhookEventStatus.IGNORED]
    
    @property
    def is_github_event(self) -> bool:
        """Check if this is a GitHub webhook event"""
        return self.event_type.value.startswith("github_")
    
    @property
    def is_pr_event(self) -> bool:
        """Check if this is a PR-related event"""
        return "pr_" in self.event_type.value
    
    def start_processing(self):
        """Mark event as being processed"""
        self.status = WebhookEventStatus.PROCESSING
        self.processed_at = func.now()
        self.updated_at = func.now()
    
    def complete_processing(self, success: bool = True, error_message: str = None):
        """Mark event processing as completed"""
        self.status = WebhookEventStatus.COMPLETED if success else WebhookEventStatus.FAILED
        
        if error_message:
            self.error_message = error_message
        
        # Calculate processing duration
        if self.processed_at:
            duration = (datetime.utcnow() - self.processed_at).total_seconds() * 1000
            self.processing_duration = int(duration)
        
        self.updated_at = func.now()
    
    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1
        self.status = WebhookEventStatus.PENDING
        self.updated_at = func.now()
    
    def ignore_event(self, reason: str = None):
        """Mark event as ignored"""
        self.status = WebhookEventStatus.IGNORED
        if reason:
            self.error_message = f"Ignored: {reason}"
        self.updated_at = func.now()
    
    def extract_github_info(self) -> Dict[str, Any]:
        """Extract GitHub-specific information from payload"""
        if not self.is_github_event or not self.payload:
            return {}
        
        info = {}
        payload = self.payload
        
        # Extract PR information
        if "pull_request" in payload:
            pr = payload["pull_request"]
            info.update({
                "pr_number": pr.get("number"),
                "pr_title": pr.get("title"),
                "pr_url": pr.get("html_url"),
                "pr_branch": pr.get("head", {}).get("ref"),
                "pr_base_branch": pr.get("base", {}).get("ref"),
                "pr_state": pr.get("state"),
                "pr_merged": pr.get("merged", False)
            })
        
        # Extract repository information
        if "repository" in payload:
            repo = payload["repository"]
            info.update({
                "repo_name": repo.get("name"),
                "repo_full_name": repo.get("full_name"),
                "repo_url": repo.get("html_url"),
                "repo_default_branch": repo.get("default_branch")
            })
        
        # Extract commit information
        if "head_commit" in payload:
            commit = payload["head_commit"]
            info.update({
                "commit_sha": commit.get("id"),
                "commit_message": commit.get("message"),
                "commit_url": commit.get("url")
            })
        
        # Extract branch information
        if "ref" in payload:
            ref = payload["ref"]
            if ref.startswith("refs/heads/"):
                info["branch_name"] = ref.replace("refs/heads/", "")
        
        return info
    
    def to_dict(self, include_payload: bool = False) -> Dict[str, Any]:
        """Convert webhook event to dictionary for API responses"""
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "source": self.source,
            "status": self.status.value,
            "signature": self.signature,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_duration": self.processing_duration,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "pr_number": self.pr_number,
            "issue_number": self.issue_number,
            "commit_sha": self.commit_sha,
            "branch_name": self.branch_name,
            "triggered_agent_run": self.triggered_agent_run,
            "triggered_validation": self.triggered_validation,
            "triggered_merge": self.triggered_merge,
            "is_processed": self.is_processed,
            "is_github_event": self.is_github_event,
            "is_pr_event": self.is_pr_event,
            "metadata": self.metadata,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_payload:
            result.update({
                "headers": self.headers,
                "payload": self.payload
            })
        
        return result
    
    @classmethod
    def create_from_github(cls, project_id: int, event_type: WebhookEventType,
                          headers: Dict[str, str], payload: Dict[str, Any],
                          signature: str = None, event_id: str = None) -> "WebhookEvent":
        """Create webhook event from GitHub webhook"""
        event = cls(
            project_id=project_id,
            event_type=event_type,
            event_id=event_id,
            source="github",
            headers=headers,
            payload=payload,
            signature=signature
        )
        
        # Extract GitHub-specific information
        github_info = event.extract_github_info()
        event.pr_number = github_info.get("pr_number")
        event.commit_sha = github_info.get("commit_sha")
        event.branch_name = github_info.get("branch_name")
        
        return event

