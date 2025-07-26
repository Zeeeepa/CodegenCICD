"""
Configurations API router
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
import asyncio
import subprocess

from backend.database import get_db
from backend.models.project import Project
from backend.models.configuration import ProjectConfiguration, ProjectSecret
from backend.services.encryption_service import encrypt_value, decrypt_value


router = APIRouter()


# Pydantic models for request/response
class ConfigurationUpdate(BaseModel):
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    planning_statement: Optional[str] = None


class SecretCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)


class SecretResponse(BaseModel):
    id: str
    project_id: str
    key: str
    created_at: Optional[str]
    value: Optional[str] = None  # Only included when explicitly requested


class SetupCommandsExecutionResult(BaseModel):
    success: bool
    logs: List[str]
    exit_code: Optional[int] = None
    duration: Optional[float] = None


@router.get("/{project_id}")
async def get_project_configuration(project_id: str, db: Session = Depends(get_db)):
    """Get project configuration"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if not project.configuration:
        # Create default configuration if it doesn't exist
        config = ProjectConfiguration(project_id=project.id)
        db.add(config)
        db.commit()
        db.refresh(config)
        db.refresh(project)
    
    return project.configuration.to_dict()


@router.put("/{project_id}")
async def update_project_configuration(
    project_id: str,
    config_data: ConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """Update project configuration"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get or create configuration
    config = project.configuration
    if not config:
        config = ProjectConfiguration(project_id=project.id)
        db.add(config)
        db.commit()
        db.refresh(config)
    
    # Update configuration fields
    update_data = config_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return config.to_dict()


@router.get("/{project_id}/secrets", response_model=List[SecretResponse])
async def get_project_secrets(
    project_id: str, 
    include_values: bool = False,
    db: Session = Depends(get_db)
):
    """Get project secrets"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if not project.configuration:
        return []
    
    secrets = project.configuration.secrets
    return [secret.to_dict(include_value=include_values) for secret in secrets]


@router.post("/{project_id}/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_project_secret(
    project_id: str,
    secret_data: SecretCreate,
    db: Session = Depends(get_db)
):
    """Create a new project secret"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get or create configuration
    config = project.configuration
    if not config:
        config = ProjectConfiguration(project_id=project.id)
        db.add(config)
        db.commit()
        db.refresh(config)
    
    # Check if secret with same key already exists
    existing_secret = db.query(ProjectSecret).filter(
        ProjectSecret.project_id == project_uuid,
        ProjectSecret.key == secret_data.key
    ).first()
    
    if existing_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Secret with this key already exists"
        )
    
    # Create encrypted secret
    secret = ProjectSecret(
        project_id=project.id,
        configuration_id=config.id,
        key=secret_data.key,
        encrypted_value=encrypt_value(secret_data.value)
    )
    
    db.add(secret)
    db.commit()
    db.refresh(secret)
    
    return secret.to_dict(include_value=True)


@router.delete("/{project_id}/secrets/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_secret(
    project_id: str,
    secret_id: str,
    db: Session = Depends(get_db)
):
    """Delete a project secret"""
    try:
        project_uuid = uuid.UUID(project_id)
        secret_uuid = uuid.UUID(secret_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )
    
    secret = db.query(ProjectSecret).filter(
        ProjectSecret.id == secret_uuid,
        ProjectSecret.project_id == project_uuid
    ).first()
    
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secret not found"
        )
    
    db.delete(secret)
    db.commit()


@router.post("/{project_id}/setup-commands/run")
async def run_setup_commands(
    project_id: str,
    branch: str = "main",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Run setup commands for a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if not project.configuration or not project.configuration.setup_commands:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No setup commands configured for this project"
        )
    
    # Execute setup commands
    commands = project.configuration.setup_commands.strip().split('\n')
    logs = []
    success = True
    exit_code = 0
    
    try:
        import time
        start_time = time.time()
        
        for command in commands:
            command = command.strip()
            if not command or command.startswith('#'):
                continue
            
            logs.append(f"$ {command}")
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.stdout:
                logs.extend(result.stdout.split('\n'))
            
            if result.stderr:
                logs.extend([f"ERROR: {line}" for line in result.stderr.split('\n')])
            
            if result.returncode != 0:
                success = False
                exit_code = result.returncode
                logs.append(f"Command failed with exit code {result.returncode}")
                break
            
            logs.append(f"Command completed successfully")
        
        duration = time.time() - start_time
        
        return SetupCommandsExecutionResult(
            success=success,
            logs=[log for log in logs if log.strip()],
            exit_code=exit_code,
            duration=duration
        )
        
    except subprocess.TimeoutExpired:
        return SetupCommandsExecutionResult(
            success=False,
            logs=logs + ["ERROR: Command execution timed out after 5 minutes"],
            exit_code=-1
        )
    except Exception as e:
        return SetupCommandsExecutionResult(
            success=False,
            logs=logs + [f"ERROR: {str(e)}"],
            exit_code=-1
        )
