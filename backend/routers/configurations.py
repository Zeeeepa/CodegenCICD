"""
Configuration router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
import uuid

from backend.database import AsyncSessionLocal
from backend.models import Project, ProjectConfiguration, ProjectSecret
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()


# Dependency to get database session
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Pydantic models for request/response
from pydantic import BaseModel, Field


class ConfigurationCreate(BaseModel):
    config_type: str = Field(..., description="Configuration type (repository_rules, setup_commands, planning_statement)")
    content: str = Field(..., description="Configuration content")
    is_active: bool = Field(default=True, description="Whether configuration is active")


class ConfigurationUpdate(BaseModel):
    content: Optional[str] = Field(None, description="Configuration content")
    is_active: Optional[bool] = Field(None, description="Whether configuration is active")


class ConfigurationResponse(BaseModel):
    id: str
    project_id: str
    config_type: str
    content: str
    is_active: bool
    version: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class SecretCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Secret name")
    value: str = Field(..., min_length=1, description="Secret value (will be encrypted)")
    description: Optional[str] = Field(None, description="Secret description")


class SecretUpdate(BaseModel):
    value: Optional[str] = Field(None, description="New secret value")
    description: Optional[str] = Field(None, description="Secret description")
    is_active: Optional[bool] = Field(None, description="Whether secret is active")


class SecretResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str]
    is_active: bool
    last_used_at: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


# Configuration endpoints
@router.get("/{project_id}/configurations", response_model=List[ConfigurationResponse])
async def list_configurations(
    project_id: str,
    config_type: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
) -> List[ConfigurationResponse]:
    """List configurations for a project"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Check if project exists
        project_query = select(Project).where(Project.id == project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build query
        query = select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
        
        if config_type:
            query = query.where(ProjectConfiguration.config_type == config_type)
        
        if active_only:
            query = query.where(ProjectConfiguration.is_active == True)
        
        query = query.order_by(ProjectConfiguration.config_type, ProjectConfiguration.version.desc())
        
        # Execute query
        result = await db.execute(query)
        configurations = result.scalars().all()
        
        logger.info("Listed configurations", 
                   project_id=project_id,
                   count=len(configurations),
                   config_type=config_type)
        
        return [ConfigurationResponse.from_orm(config) for config in configurations]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list configurations", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve configurations")


@router.post("/{project_id}/configurations", response_model=ConfigurationResponse, status_code=201)
async def create_configuration(
    project_id: str,
    config_data: ConfigurationCreate,
    db: AsyncSession = Depends(get_db)
) -> ConfigurationResponse:
    """Create a new configuration"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Check if project exists
        project_query = select(Project).where(Project.id == project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if configuration type already exists and is active
        existing_query = select(ProjectConfiguration).where(
            and_(
                ProjectConfiguration.project_id == project_id,
                ProjectConfiguration.config_type == config_data.config_type,
                ProjectConfiguration.is_active == True
            )
        )
        result = await db.execute(existing_query)
        existing_config = result.scalar_one_or_none()
        
        if existing_config:
            # Deactivate existing configuration
            existing_config.is_active = False
        
        # Get next version number
        version_query = select(ProjectConfiguration).where(
            and_(
                ProjectConfiguration.project_id == project_id,
                ProjectConfiguration.config_type == config_data.config_type
            )
        ).order_by(ProjectConfiguration.version.desc()).limit(1)
        
        result = await db.execute(version_query)
        latest_config = result.scalar_one_or_none()
        next_version = (latest_config.version + 1) if latest_config else 1
        
        # Create new configuration
        configuration = ProjectConfiguration(
            project_id=project_id,
            config_type=config_data.config_type,
            content=config_data.content,
            is_active=config_data.is_active,
            version=next_version
        )
        
        db.add(configuration)
        await db.commit()
        await db.refresh(configuration)
        
        logger.info("Created configuration", 
                   project_id=project_id,
                   config_type=config_data.config_type,
                   version=next_version)
        
        return ConfigurationResponse.from_orm(configuration)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create configuration", project_id=project_id, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create configuration")


@router.get("/{project_id}/configurations/{config_id}", response_model=ConfigurationResponse)
async def get_configuration(
    project_id: str,
    config_id: str,
    db: AsyncSession = Depends(get_db)
) -> ConfigurationResponse:
    """Get a specific configuration"""
    try:
        # Validate UUIDs
        try:
            uuid.UUID(project_id)
            uuid.UUID(config_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Get configuration
        query = select(ProjectConfiguration).where(
            and_(
                ProjectConfiguration.id == config_id,
                ProjectConfiguration.project_id == project_id
            )
        )
        result = await db.execute(query)
        configuration = result.scalar_one_or_none()
        
        if not configuration:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return ConfigurationResponse.from_orm(configuration)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get configuration", 
                    project_id=project_id, 
                    config_id=config_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


@router.put("/{project_id}/configurations/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(
    project_id: str,
    config_id: str,
    config_data: ConfigurationUpdate,
    db: AsyncSession = Depends(get_db)
) -> ConfigurationResponse:
    """Update a configuration"""
    try:
        # Validate UUIDs
        try:
            uuid.UUID(project_id)
            uuid.UUID(config_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Get configuration
        query = select(ProjectConfiguration).where(
            and_(
                ProjectConfiguration.id == config_id,
                ProjectConfiguration.project_id == project_id
            )
        )
        result = await db.execute(query)
        configuration = result.scalar_one_or_none()
        
        if not configuration:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Update fields
        update_data = config_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(configuration, field, value)
        
        await db.commit()
        await db.refresh(configuration)
        
        logger.info("Updated configuration", 
                   project_id=project_id,
                   config_id=config_id,
                   updated_fields=list(update_data.keys()))
        
        return ConfigurationResponse.from_orm(configuration)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update configuration", 
                    project_id=project_id, 
                    config_id=config_id, 
                    error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.delete("/{project_id}/configurations/{config_id}", status_code=204)
async def delete_configuration(
    project_id: str,
    config_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a configuration (soft delete by setting is_active=False)"""
    try:
        # Validate UUIDs
        try:
            uuid.UUID(project_id)
            uuid.UUID(config_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Get configuration
        query = select(ProjectConfiguration).where(
            and_(
                ProjectConfiguration.id == config_id,
                ProjectConfiguration.project_id == project_id
            )
        )
        result = await db.execute(query)
        configuration = result.scalar_one_or_none()
        
        if not configuration:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Soft delete
        configuration.is_active = False
        await db.commit()
        
        logger.info("Deleted configuration", 
                   project_id=project_id,
                   config_id=config_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete configuration", 
                    project_id=project_id, 
                    config_id=config_id, 
                    error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete configuration")


# Secret endpoints (placeholder implementations - encryption not yet implemented)
@router.get("/{project_id}/secrets", response_model=List[SecretResponse])
async def list_secrets(
    project_id: str,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
) -> List[SecretResponse]:
    """List secrets for a project (values not included for security)"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Check if project exists
        project_query = select(Project).where(Project.id == project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build query
        query = select(ProjectSecret).where(ProjectSecret.project_id == project_id)
        
        if active_only:
            query = query.where(ProjectSecret.is_active == True)
        
        query = query.order_by(ProjectSecret.name)
        
        # Execute query
        result = await db.execute(query)
        secrets = result.scalars().all()
        
        logger.info("Listed secrets", 
                   project_id=project_id,
                   count=len(secrets))
        
        return [SecretResponse.from_orm(secret) for secret in secrets]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list secrets", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve secrets")


@router.post("/{project_id}/secrets", response_model=SecretResponse, status_code=201)
async def create_secret(
    project_id: str,
    secret_data: SecretCreate,
    db: AsyncSession = Depends(get_db)
) -> SecretResponse:
    """Create a new secret"""
    try:
        # Validate UUID
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        
        # Check if project exists
        project_query = select(Project).where(Project.id == project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if secret name already exists
        existing_query = select(ProjectSecret).where(
            and_(
                ProjectSecret.project_id == project_id,
                ProjectSecret.name == secret_data.name,
                ProjectSecret.is_active == True
            )
        )
        result = await db.execute(existing_query)
        existing_secret = result.scalar_one_or_none()
        
        if existing_secret:
            raise HTTPException(status_code=400, detail=f"Secret '{secret_data.name}' already exists")
        
        # TODO: Implement proper encryption
        # For now, we'll store a placeholder encrypted value
        encrypted_value = f"ENCRYPTED:{secret_data.value}"  # Placeholder
        
        # Create secret
        secret = ProjectSecret(
            project_id=project_id,
            name=secret_data.name,
            encrypted_value=encrypted_value,
            description=secret_data.description
        )
        
        db.add(secret)
        await db.commit()
        await db.refresh(secret)
        
        logger.info("Created secret", 
                   project_id=project_id,
                   secret_name=secret_data.name)
        
        return SecretResponse.from_orm(secret)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create secret", project_id=project_id, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create secret")


@router.delete("/{project_id}/secrets/{secret_id}", status_code=204)
async def delete_secret(
    project_id: str,
    secret_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a secret (soft delete by setting is_active=False)"""
    try:
        # Validate UUIDs
        try:
            uuid.UUID(project_id)
            uuid.UUID(secret_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Get secret
        query = select(ProjectSecret).where(
            and_(
                ProjectSecret.id == secret_id,
                ProjectSecret.project_id == project_id
            )
        )
        result = await db.execute(query)
        secret = result.scalar_one_or_none()
        
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")
        
        # Soft delete
        secret.is_active = False
        await db.commit()
        
        logger.info("Deleted secret", 
                   project_id=project_id,
                   secret_id=secret_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete secret", 
                    project_id=project_id, 
                    secret_id=secret_id, 
                    error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete secret")

