"""
Simple database configuration for pinned projects
Avoids conflicts with existing models
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import structlog

logger = structlog.get_logger(__name__)

# Create separate base for pinned projects
PinnedBase = declarative_base()

class SimpleUser(PinnedBase):
    __tablename__ = "simple_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    pinned_projects = relationship("SimplePinnedProject", back_populates="user", cascade="all, delete-orphan")

class SimplePinnedProject(PinnedBase):
    __tablename__ = "simple_pinned_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("simple_users.id"), nullable=False, index=True)
    github_repo_name = Column(String(255), nullable=False, index=True)
    github_repo_url = Column(String(500), nullable=False)
    github_owner = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    pinned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    user = relationship("SimpleUser", back_populates="pinned_projects")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'github_repo_name', name='unique_simple_user_repo'),
    )
    
    def to_dict(self):
        """Convert model instance to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "github_repo_name": self.github_repo_name,
            "github_repo_url": self.github_repo_url,
            "github_owner": self.github_owner,
            "display_name": self.display_name,
            "description": self.description,
            "pinned_at": self.pinned_at.isoformat() if self.pinned_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_active": self.is_active
        }

# Create engine for simple database
simple_engine = create_async_engine(
    "sqlite+aiosqlite:///./simple_pinned.db",
    echo=False,
    connect_args={"check_same_thread": False}
)

# Create session maker
SimpleAsyncSessionLocal = async_sessionmaker(
    simple_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_simple_db():
    """Initialize simple database"""
    async with simple_engine.begin() as conn:
        await conn.run_sync(PinnedBase.metadata.create_all)
    
    # Create test user
    async with SimpleAsyncSessionLocal() as session:
        # Check if test user exists
        from sqlalchemy import select
        stmt = select(SimpleUser).where(SimpleUser.id == uuid.UUID('550e8400-e29b-41d4-a716-446655440000'))
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            test_user = SimpleUser(
                id=uuid.UUID('550e8400-e29b-41d4-a716-446655440000'),
                username='testuser',
                email='test@example.com',
                full_name='Test User',
                is_active=True
            )
            session.add(test_user)
            await session.commit()
            logger.info("Test user created in simple database")

class SimplePinnedProjectService:
    """Service for managing pinned projects using simple database"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_pinned_projects(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all pinned projects for a user."""
        try:
            from sqlalchemy import select
            stmt = select(SimplePinnedProject).where(
                SimplePinnedProject.user_id == user_id,
                SimplePinnedProject.is_active == True
            ).order_by(SimplePinnedProject.pinned_at.desc())
            
            result = await self.db.execute(stmt)
            projects = result.scalars().all()
            
            return [project.to_dict() for project in projects]
            
        except Exception as e:
            logger.error(f"Error fetching pinned projects for user {user_id}: {e}")
            raise Exception("Failed to fetch pinned projects")
    
    async def pin_project(self, user_id: uuid.UUID, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Pin a project to user's dashboard."""
        try:
            # Check if project is already pinned
            from sqlalchemy import select
            stmt = select(SimplePinnedProject).where(
                SimplePinnedProject.user_id == user_id,
                SimplePinnedProject.github_repo_name == project_data["github_repo_name"],
                SimplePinnedProject.is_active == True
            )
            
            result = await self.db.execute(stmt)
            existing_project = result.scalar_one_or_none()
            
            if existing_project:
                raise Exception("Project is already pinned")
            
            # Create new pinned project
            new_project = SimplePinnedProject(
                user_id=user_id,
                github_repo_name=project_data["github_repo_name"],
                github_repo_url=project_data["github_repo_url"],
                github_owner=project_data["github_owner"],
                display_name=project_data.get("display_name"),
                description=project_data.get("description"),
                pinned_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                is_active=True
            )
            
            self.db.add(new_project)
            await self.db.commit()
            await self.db.refresh(new_project)
            
            return new_project.to_dict()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error pinning project for user {user_id}: {e}")
            raise Exception("Failed to pin project")
    
    async def unpin_project(self, user_id: uuid.UUID, project_id: int) -> bool:
        """Unpin a project from user's dashboard."""
        try:
            from sqlalchemy import select
            stmt = select(SimplePinnedProject).where(
                SimplePinnedProject.id == project_id,
                SimplePinnedProject.user_id == user_id,
                SimplePinnedProject.is_active == True
            )
            
            result = await self.db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise Exception("Project not found")
            
            project.is_active = False
            project.last_updated = datetime.utcnow()
            
            await self.db.commit()
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error unpinning project {project_id} for user {user_id}: {e}")
            raise Exception("Failed to unpin project")

async def get_simple_db() -> AsyncSession:
    """FastAPI dependency for simple database sessions"""
    async with SimpleAsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Simple database session error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()

if __name__ == "__main__":
    asyncio.run(init_simple_db())

