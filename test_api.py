#!/usr/bin/env python3
"""
Test the pinned projects API directly
"""
import asyncio
import uuid
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/tmp/Zeeeepa/CodegenCICD')

from backend.services.project_service import ProjectService
from backend.database import AsyncSessionLocal

async def test_api():
    """Test the project service directly"""
    try:
        async with AsyncSessionLocal() as session:
            service = ProjectService(session)
            user_id = uuid.UUID('550e8400-e29b-41d4-a716-446655440000')
            
            # Test getting pinned projects
            print("Testing get_pinned_projects...")
            projects = await service.get_pinned_projects(user_id)
            print(f"Found {len(projects)} pinned projects")
            
            # Test pinning a project
            print("Testing pin_project...")
            project_data = {
                "github_repo_name": "test-repo",
                "github_repo_url": "https://github.com/test/test-repo",
                "github_owner": "test",
                "display_name": "Test Repository",
                "description": "A test repository"
            }
            
            result = await service.pin_project(user_id, project_data)
            print(f"Pinned project: {result}")
            
            # Test getting pinned projects again
            print("Testing get_pinned_projects after pinning...")
            projects = await service.get_pinned_projects(user_id)
            print(f"Found {len(projects)} pinned projects")
            for project in projects:
                print(f"  - {project['display_name']}: {project['github_repo_url']}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())

