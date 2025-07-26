"""
Configuration models for project settings and secrets
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any
from enum import Enum as PyEnum


class ConfigurationType(PyEnum):
    """Configuration type enumeration"""
    REPOSITORY_RULES = "repository_rules"
    SETUP_COMMANDS = "setup_commands"
    PLANNING_STATEMENT = "planning_statement"
    WEBHOOK_CONFIG = "webhook_config"
    VALIDATION_CONFIG = "validation_config"


class SecretType(PyEnum):
    """Secret type enumeration"""
    ENVIRONMENT_VARIABLE = "environment_variable"
    API_KEY = "api_key"
    TOKEN = "token"
    PASSWORD = "password"
    CERTIFICATE = "certificate"


class ProjectConfiguration(Base):
    __tablename__ = "project_configurations"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Configuration details
    config_type = Column(Enum(ConfigurationType), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration data
    config_data = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="configurations")
    
    def __repr__(self):
        return f"<ProjectConfiguration(id={self.id}, project_id={self.project_id}, type='{self.config_type.value}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "config_type": self.config_type.value,
            "name": self.name,
            "description": self.description,
            "config_data": self.config_data,
            "is_active": self.is_active,
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
    description = Column(Text, nullable=True)
    secret_type = Column(Enum(SecretType), default=SecretType.ENVIRONMENT_VARIABLE)
    
    # Encrypted secret value
    encrypted_value = Column(Text, nullable=False)
    
    # Secret metadata
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="secrets")
    
    def __repr__(self):
        return f"<ProjectSecret(id={self.id}, project_id={self.project_id}, name='{self.name}')>"
    
    def mark_used(self):
        """Mark secret as recently used"""
        self.last_used = func.now()
        self.updated_at = func.now()
    
    def to_dict(self, include_value: bool = False) -> Dict[str, Any]:
        """Convert secret to dictionary for API responses"""
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "secret_type": self.secret_type.value,
            "is_active": self.is_active,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Only include encrypted value if explicitly requested (for internal use)
        if include_value:
            result["encrypted_value"] = self.encrypted_value
        
        return result

