"""
Configuration models for project settings and secrets management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any
from datetime import datetime


class ProjectConfiguration(Base):
    __tablename__ = "project_configurations"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Configuration details
    key = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    # Configuration type and category
    config_type = Column(String(100), nullable=False, index=True)  # e.g., "validation", "deployment", "webhook"
    category = Column(String(100), nullable=True)  # e.g., "grainchain", "github", "general"
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_encrypted = Column(Boolean, default=False)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="configurations")
    
    def __repr__(self):
        return f"<ProjectConfiguration(id={self.id}, project_id={self.project_id}, key='{self.key}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "key": self.key,
            "value": self.value if not self.is_encrypted else "[ENCRYPTED]",
            "description": self.description,
            "config_type": self.config_type,
            "category": self.category,
            "is_active": self.is_active,
            "is_encrypted": self.is_encrypted,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectSecret(Base):
    __tablename__ = "project_secrets"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Secret details
    name = Column(String(255), nullable=False, index=True)
    encrypted_value = Column(Text, nullable=False)  # Always encrypted
    description = Column(Text, nullable=True)
    
    # Secret metadata
    secret_type = Column(String(100), nullable=False, index=True)  # e.g., "api_key", "token", "password"
    environment = Column(String(50), default="all")  # e.g., "development", "production", "all"
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="secrets")
    
    def __repr__(self):
        return f"<ProjectSecret(id={self.id}, project_id={self.project_id}, name='{self.name}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if secret is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def mark_used(self):
        """Mark secret as used (update usage tracking)"""
        self.last_used = func.now()
        self.usage_count += 1
        self.updated_at = func.now()
    
    def to_dict(self, include_value: bool = False) -> Dict[str, Any]:
        """Convert secret to dictionary for API responses"""
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "secret_type": self.secret_type,
            "environment": self.environment,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_value:
            result["encrypted_value"] = self.encrypted_value
        
        return result
    
    @classmethod
    def create_secret(cls, project_id: int, name: str, encrypted_value: str,
                     secret_type: str, description: str = None, 
                     environment: str = "all", expires_at: datetime = None,
                     metadata: Dict[str, Any] = None) -> "ProjectSecret":
        """Create a new project secret"""
        return cls(
            project_id=project_id,
            name=name,
            encrypted_value=encrypted_value,
            description=description,
            secret_type=secret_type,
            environment=environment,
            expires_at=expires_at,
            metadata=metadata
        )

