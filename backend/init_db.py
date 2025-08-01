#!/usr/bin/env python3
"""
Database initialization script
Creates all tables defined in the models
"""
import asyncio
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import engine
from backend.models.base import Base
from backend.models.project import Project
from backend.models.agent_run import AgentRun
from backend.models.user import User
from backend.models.validation import ValidationRun, ValidationStep


async def init_database():
    """Initialize the database by creating all tables"""
    print("Creating database tables...")
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database tables created successfully!")


async def main():
    """Main function"""
    try:
        await init_database()
        print("Database initialization completed successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
