"""
Configurations router for managing project settings and secrets
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from backend.database import get_db
from backend.models.configuration import ProjectConfiguration, ProjectSecret
from backend.models.project import Project
from backend.utils.encryption import encrypt_value, decrypt_value
from backend.integrations.grainchain_client import GrainchainClient

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
from pydantic import BaseModel

class ProjectConfigurationResponse(BaseModel):
    id: int
    project_id: int
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    planning_statement: Optional[str] = None
    branch_name: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class ProjectConfigurationUpdate(BaseModel):
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    planning_statement: Optional[str] = None
    branch_name: Optional[str] = None

class ProjectSecretCreate(BaseModel):
    key: str
    value: str

class ProjectSecretResponse(BaseModel):
    id: int
    project_id: int
    key: str
    value: str  # This will be encrypted
    created_at: str

    class Config:
        from_attributes = True

class TestSetupCommandsRequest(BaseModel):
    commands: str
    branch: Optional[str] = "main"

@router.get("/{project_id}", response_model=ProjectConfigurationResponse)
async def get_project_configuration(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get project configuration"""
    try:
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get configuration
        result = await db.execute(
            select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            # Create default configuration
            config = ProjectConfiguration(
                project_id=project_id,
                repository_rules="",
                setup_commands="",
                planning_statement="",
                branch_name="main"
            )
            db.add(config)
            await db.commit()
            await db.refresh(config)
        
        return ProjectConfigurationResponse.model_validate(config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project configuration"
        )

@router.put("/{project_id}", response_model=ProjectConfigurationResponse)
async def update_project_configuration(
    project_id: int,
    config_data: ProjectConfigurationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update project configuration"""
    try:
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get or create configuration
        result = await db.execute(
            select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            config = ProjectConfiguration(
                project_id=project_id,
                repository_rules="",
                setup_commands="",
                planning_statement="",
                branch_name="main"
            )
            db.add(config)
        
        # Update fields
        update_data = config_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"Updated configuration for project {project_id}")
        return ProjectConfigurationResponse.model_validate(config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project configuration"
        )

@router.get("/{project_id}/secrets", response_model=List[ProjectSecretResponse])
async def get_project_secrets(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get project secrets (values will be encrypted)"""
    try:
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get secrets
        result = await db.execute(
            select(ProjectSecret).where(ProjectSecret.project_id == project_id)
        )
        secrets = result.scalars().all()
        
        # Decrypt values for response
        decrypted_secrets = []
        for secret in secrets:
            try:
                decrypted_value = decrypt_value(secret.value)
                decrypted_secrets.append(ProjectSecretResponse(
                    id=secret.id,
                    project_id=secret.project_id,
                    key=secret.key,
                    value=decrypted_value,
                    created_at=secret.created_at.isoformat()
                ))
            except Exception as e:
                logger.error(f"Failed to decrypt secret {secret.key}: {e}")
                # Skip corrupted secrets
                continue
        
        return decrypted_secrets
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project secrets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project secrets"
        )

@router.post("/{project_id}/secrets", response_model=ProjectSecretResponse)
async def create_project_secret(
    project_id: int,
    secret_data: ProjectSecretCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project secret"""
    try:
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if secret key already exists
        result = await db.execute(
            select(ProjectSecret).where(
                ProjectSecret.project_id == project_id,
                ProjectSecret.key == secret_data.key
            )
        )
        existing_secret = result.scalar_one_or_none()
        
        if existing_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Secret with this key already exists"
            )
        
        # Encrypt the value
        encrypted_value = encrypt_value(secret_data.value)
        
        # Create secret
        secret = ProjectSecret(
            project_id=project_id,
            key=secret_data.key,
            value=encrypted_value
        )
        
        db.add(secret)
        await db.commit()
        await db.refresh(secret)
        
        logger.info(f"Created secret {secret_data.key} for project {project_id}")
        
        # Return with decrypted value
        return ProjectSecretResponse(
            id=secret.id,
            project_id=secret.project_id,
            key=secret.key,
            value=secret_data.value,  # Return original value
            created_at=secret.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project secret: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project secret"
        )

@router.put("/{project_id}/secrets/{secret_id}", response_model=ProjectSecretResponse)
async def update_project_secret(
    project_id: int,
    secret_id: int,
    secret_data: ProjectSecretCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a project secret"""
    try:
        # Get secret
        result = await db.execute(
            select(ProjectSecret).where(
                ProjectSecret.id == secret_id,
                ProjectSecret.project_id == project_id
            )
        )
        secret = result.scalar_one_or_none()
        
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Secret not found"
            )
        
        # Encrypt the new value
        encrypted_value = encrypt_value(secret_data.value)
        
        # Update secret
        secret.key = secret_data.key
        secret.value = encrypted_value
        
        await db.commit()
        await db.refresh(secret)
        
        logger.info(f"Updated secret {secret_data.key} for project {project_id}")
        
        # Return with decrypted value
        return ProjectSecretResponse(
            id=secret.id,
            project_id=secret.project_id,
            key=secret.key,
            value=secret_data.value,  # Return original value
            created_at=secret.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project secret: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project secret"
        )

@router.delete("/{project_id}/secrets/{secret_id}")
async def delete_project_secret(
    project_id: int,
    secret_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project secret"""
    try:
        # Get secret
        result = await db.execute(
            select(ProjectSecret).where(
                ProjectSecret.id == secret_id,
                ProjectSecret.project_id == project_id
            )
        )
        secret = result.scalar_one_or_none()
        
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Secret not found"
            )
        
        await db.delete(secret)
        await db.commit()
        
        logger.info(f"Deleted secret {secret.key} for project {project_id}")
        return {"message": "Secret deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project secret: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project secret"
        )

@router.post("/{project_id}/test-setup")
async def test_setup_commands(
    project_id: int,
    test_data: TestSetupCommandsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test setup commands in a sandbox environment"""
    try:
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Create temporary snapshot for testing
        grainchain = GrainchainClient()
        
        # Get project secrets for environment
        result = await db.execute(
            select(ProjectSecret).where(ProjectSecret.project_id == project_id)
        )
        secrets = result.scalars().all()
        
        environment_vars = {}
        for secret in secrets:
            try:
                decrypted_value = decrypt_value(secret.value)
                environment_vars[secret.key] = decrypted_value
            except Exception as e:
                logger.warning(f"Failed to decrypt secret {secret.key}: {e}")
        
        # Create snapshot
        snapshot_config = {
            "tools": ["git", "node", "python"],
            "environment_variables": environment_vars
        }
        
        snapshot_id = await grainchain.create_snapshot(snapshot_config)
        
        try:
            # Clone repository
            repo_url = f"https://github.com/{project.github_owner}/{project.github_repo}.git"
            await grainchain.clone_repository(snapshot_id, repo_url, test_data.branch)
            
            # Execute setup commands
            commands = [cmd.strip() for cmd in test_data.commands.split('\n') if cmd.strip()]
            result = await grainchain.execute_commands(snapshot_id, commands)
            
            # Clean up snapshot
            await grainchain.delete_snapshot(snapshot_id)
            
            return {
                "success": result.get("exit_code", 1) == 0,
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "duration": result.get("duration", 0)
            }
            
        except Exception as e:
            # Clean up snapshot on error
            await grainchain.delete_snapshot(snapshot_id)
            raise e
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test setup commands: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test setup commands: {str(e)}"
        )

