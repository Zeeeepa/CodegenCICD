from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import base64
from cryptography.fernet import Fernet
import os

Base = declarative_base()

# Encryption key for sensitive data
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
if isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

class Settings(Base):
    """Global application settings."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EnvironmentVariable(Base):
    """Environment variables with encryption support."""
    __tablename__ = "environment_variables"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    encrypted_value = Column(LargeBinary)  # For sensitive data
    plain_value = Column(Text)  # For non-sensitive data
    category = Column(String(100), nullable=False)
    description = Column(Text)
    sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_value(self, value: str):
        """Set the value, encrypting if sensitive."""
        if self.sensitive:
            encrypted_value = cipher_suite.encrypt(value.encode())
            self.encrypted_value = encrypted_value
            self.plain_value = None
        else:
            self.plain_value = value
            self.encrypted_value = None
    
    def get_value(self) -> str:
        """Get the decrypted value."""
        if self.sensitive and self.encrypted_value:
            return cipher_suite.decrypt(self.encrypted_value).decode()
        return self.plain_value or ""
    
    def decrypt_value(self) -> str:
        """Alias for get_value for backward compatibility."""
        return self.get_value()

class ValidationRun(Base):
    """Validation pipeline runs."""
    __tablename__ = "validation_runs"
    
    id = Column(String(36), primary_key=True)  # UUID
    project_id = Column(Integer, nullable=False)
    pr_number = Column(Integer, nullable=False)
    pr_url = Column(String(500))
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    success = Column(Boolean, default=False)
    error_context = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class ValidationStep(Base):
    """Individual steps in validation pipeline."""
    __tablename__ = "validation_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    validation_id = Column(String(36), nullable=False)  # Foreign key to ValidationRun
    step_id = Column(String(100), nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    logs = Column(Text)  # JSON array of log messages
    error_message = Column(Text)
    result_data = Column(Text)  # JSON data from step execution
