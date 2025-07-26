"""
Configurations API router for managing project settings and secrets
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.configuration import ProjectSecret

router = APIRouter()

# Pydantic models for request/response
class SecretCreate(BaseModel):
    project_id: int
    secret_name: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    description: Optional[str] = None

class SecretResponse(BaseModel):
    id: int
    project_id: int
    secret_name: str
    description: Optional[str]
    is_active: bool
    last_used: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    value: str  # Will be "[HIDDEN]" unless specifically requested

@router.get("/secrets", response_model=List[SecretResponse])
async def list_secrets(
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """List project secrets"""
    try:
        query = select(ProjectSecret)
        
        if project_id:
            query = query.where(ProjectSecret.project_id == project_id)
        
        query = query.where(ProjectSecret.is_active == True)
        
        result = await db.execute(query)
        secrets = result.scalars().all()
        
        return [SecretResponse(**secret.to_dict()) for secret in secrets]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list secrets: {str(e)}"
        )

@router.post("/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    secret_data: SecretCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project secret"""
    try:
        # Check if secret with same name already exists for this project
        existing_query = select(ProjectSecret).where(
            ProjectSecret.project_id == secret_data.project_id,
            ProjectSecret.secret_name == secret_data.secret_name,
            ProjectSecret.is_active == True
        )
        result = await db.execute(existing_query)
        existing_secret = result.scalar_one_or_none()
        
        if existing_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Secret '{secret_data.secret_name}' already exists for this project"
            )
        
        # Create new secret
        secret = ProjectSecret(
            project_id=secret_data.project_id,
            secret_name=secret_data.secret_name,
            description=secret_data.description
        )
        
        # Encrypt and store the value
        secret.set_value(secret_data.value)
        
        db.add(secret)
        await db.commit()
        await db.refresh(secret)
        
        return SecretResponse(**secret.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create secret: {str(e)}"
        )

@router.delete("/secrets/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(secret_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a project secret"""
    try:
        result = await db.execute(select(ProjectSecret).where(ProjectSecret.id == secret_id))
        secret = result.scalar_one_or_none()
        
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Secret with ID {secret_id} not found"
            )
        
        # Soft delete
        secret.is_active = False
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete secret: {str(e)}"
        )
