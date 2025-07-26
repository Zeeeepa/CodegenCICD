"""
Configuration models for CodegenCICD Dashboard
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class ProjectConfiguration(Base):
    __tablename__ = "project_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True)
    repository_rules = Column(Text, nullable=True)
    setup_commands = Column(Text, nullable=True)
    planning_statement = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="configuration")
    secrets = relationship("ProjectSecret", back_populates="configuration", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProjectConfiguration(id={self.id}, project_id={self.project_id})>"

    def to_dict(self):
        """Convert configuration to dictionary for API responses"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "repository_rules": self.repository_rules,
            "setup_commands": self.setup_commands,
            "planning_statement": self.planning_statement,
            "secrets": [secret.to_dict() for secret in self.secrets] if self.secrets else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectSecret(Base):
    __tablename__ = "project_secrets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    configuration_id = Column(UUID(as_uuid=True), ForeignKey("project_configurations.id"), nullable=False)
    key = Column(String(255), nullable=False)
    encrypted_value = Column(Text, nullable=False)  # This will store encrypted values
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    configuration = relationship("ProjectConfiguration", back_populates="secrets")

    def __repr__(self):
        return f"<ProjectSecret(id={self.id}, key='{self.key}', project_id={self.project_id})>"

    def to_dict(self, include_value=False):
        """Convert secret to dictionary for API responses"""
        result = {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "key": self.key,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        # Only include decrypted value if explicitly requested (for settings dialog)
        if include_value:
            # This would decrypt the value using your encryption service
            result["value"] = self.get_decrypted_value()
        
        return result

    def get_decrypted_value(self):
        """Decrypt and return the secret value"""
        # This would use your encryption service to decrypt the value
        # For now, returning a placeholder
        from backend.services.encryption_service import decrypt_value
        return decrypt_value(self.encrypted_value)

    def set_encrypted_value(self, plain_value):
        """Encrypt and store the secret value"""
        # This would use your encryption service to encrypt the value
        from backend.services.encryption_service import encrypt_value
        self.encrypted_value = encrypt_value(plain_value)
