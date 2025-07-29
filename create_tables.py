#!/usr/bin/env python3
"""
Create database tables for CodegenCICD Dashboard
"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Create base
Base = declarative_base()

# Define minimal models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    pinned_projects = relationship("PinnedProject", back_populates="user", cascade="all, delete-orphan")

class PinnedProject(Base):
    __tablename__ = "pinned_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    github_repo_name = Column(String(255), nullable=False, index=True)
    github_repo_url = Column(String(500), nullable=False)
    github_owner = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    pinned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    user = relationship("User", back_populates="pinned_projects")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'github_repo_name', name='unique_user_repo'),
    )

async def create_tables():
    # Create engine
    engine = create_async_engine("sqlite+aiosqlite:///./codegen_cicd.db")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Tables created successfully")
    
    # Create test user
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        test_user = User(
            id=uuid.UUID('550e8400-e29b-41d4-a716-446655440000'),
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            is_active=True
        )
        session.add(test_user)
        await session.commit()
        print("Test user created successfully")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())

