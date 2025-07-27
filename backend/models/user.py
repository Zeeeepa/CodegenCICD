"""
User and authentication related database models
"""
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    # Basic user information
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    
    # Authentication
    hashed_password = Column(String(255))  # Optional for OAuth-only users
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # OAuth integration
    github_username = Column(String(255), unique=True, index=True)
    github_user_id = Column(String(50), unique=True, index=True)
    github_access_token = Column(Text)  # Encrypted
    
    # User preferences
    preferences = Column(JSON, default=dict)
    
    # API access
    api_key_hash = Column(String(255), unique=True, index=True)  # Hashed API key
    api_key_active = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(username={self.username}, email={self.email})>"
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.is_active
    
    def has_github_integration(self) -> bool:
        """Check if user has GitHub integration configured"""
        return bool(self.github_username and self.github_access_token)


class UserSession(BaseModel):
    """User session model for tracking active sessions"""
    __tablename__ = "user_sessions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Session information
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, index=True)
    
    # Session metadata
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(String(50), nullable=False)  # ISO timestamp as string
    last_activity_at = Column(String(50))  # ISO timestamp as string
    
    # Session data
    session_data = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self) -> str:
        return f"<UserSession(user_id={self.user_id}, active={self.is_active})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        from datetime import datetime
        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.utcnow() > expires_at
        except (ValueError, AttributeError):
            return True

