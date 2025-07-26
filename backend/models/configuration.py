"""
Configuration models for project settings and secrets
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import os
import base64

class ProjectConfiguration(Base):
    __tablename__ = "project_configurations"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Configuration key and value
    config_key = Column(String(255), nullable=False, index=True)
    config_value = Column(Text, nullable=True)
    
    # Configuration metadata
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="configurations")
    
    def __repr__(self):
        return f"<ProjectConfiguration(id={self.id}, project_id={self.project_id}, key='{self.config_key}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "config_key": self.config_key,
            "config_value": self.config_value,
            "description": self.description,
            "is_encrypted": self.is_encrypted,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class ProjectSecret(Base):
    __tablename__ = "project_secrets"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Secret information
    secret_name = Column(String(255), nullable=False, index=True)
    encrypted_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    
    # Secret metadata
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="secrets")
    
    def __repr__(self):
        return f"<ProjectSecret(id={self.id}, project_id={self.project_id}, name='{self.secret_name}')>"
    
    @staticmethod
    def _get_encryption_key() -> bytes:
        """Get or create encryption key for secrets"""
        key_env = os.getenv("SECRET_ENCRYPTION_KEY")
        if key_env:
            return base64.urlsafe_b64decode(key_env.encode())
        else:
            # Generate a new key (in production, this should be stored securely)
            key = Fernet.generate_key()
            print(f"⚠️  Generated new encryption key. Set SECRET_ENCRYPTION_KEY={key.decode()} in your environment")
            return key
    
    def set_value(self, value: str) -> None:
        """Encrypt and store secret value"""
        if not value:
            self.encrypted_value = ""
            return
            
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_bytes = fernet.encrypt(value.encode())
            self.encrypted_value = base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            raise ValueError(f"Failed to encrypt secret: {e}")
    
    def get_value(self) -> str:
        """Decrypt and return secret value"""
        if not self.encrypted_value:
            return ""
            
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_bytes = base64.urlsafe_b64decode(self.encrypted_value.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt secret: {e}")
    
    def to_dict(self, include_value: bool = False) -> Dict[str, Any]:
        """Convert secret to dictionary for API responses"""
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "secret_name": self.secret_name,
            "description": self.description,
            "is_active": self.is_active,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_value:
            try:
                result["value"] = self.get_value()
            except Exception:
                result["value"] = "[DECRYPTION_ERROR]"
        else:
            result["value"] = "[HIDDEN]"
            
        return result
    
    def to_env_format(self) -> str:
        """Convert secret to environment variable format"""
        try:
            value = self.get_value()
            return f"{self.secret_name}={value}"
        except Exception:
            return f"{self.secret_name}=[DECRYPTION_ERROR]"
