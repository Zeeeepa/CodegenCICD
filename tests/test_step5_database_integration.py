"""
Test suite for STEP5: Database Integration Layer
"""
import pytest
import pytest_asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend to path
import sys
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from database.connection_manager import DatabaseManager, ConnectionConfig
from repositories import (
    ProjectRepository, 
    ProjectSettingsRepository, 
    ProjectSecretsRepository,
    RepositoryFactory
)
from services.database_service import DatabaseService
from models import Project, ProjectSettings, ProjectSecret
from errors.exceptions import DatabaseError, ValidationError, SecurityError


class TestDatabaseIntegration:
    """Test database integration layer"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Create database manager with temp database
        config = ConnectionConfig(database_path=db_path)
        db_manager = DatabaseManager(config)
        
        # Initialize database schema
        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute schema creation
            for statement in schema_sql.split(';'):
                if statement.strip():
                    db_manager.execute_command(statement.strip())
        
        yield db_manager
        
        # Cleanup
        os.unlink(db_path)
    
    def test_project_repository_crud(self, temp_db):
        """Test project repository CRUD operations"""
        repo = ProjectRepository(temp_db)
        
        # Test create
        project_data = {
            'name': 'Test Project',
            'github_owner': 'testowner',
            'github_repo': 'testrepo',
            'webhook_url': 'https://example.com/webhook',
            'auto_merge_enabled': True,
            'auto_confirm_plans': False
        }
        
        project = repo.create(project_data)
        assert project.id is not None
        assert project.name == 'Test Project'
        assert project.github_owner == 'testowner'
        assert project.github_repo == 'testrepo'
        assert project.auto_merge_enabled is True
        
        # Test get by ID
        retrieved = repo.get_by_id(project.id)
        assert retrieved is not None
        assert retrieved.name == project.name
        
        # Test get by GitHub repo
        github_project = repo.get_by_github_repo('testowner', 'testrepo')
        assert github_project is not None
        assert github_project.id == project.id
        
        # Test update
        update_data = {'name': 'Updated Project', 'auto_merge_enabled': False}
        updated = repo.update(project.id, update_data)
        assert updated.name == 'Updated Project'
        assert updated.auto_merge_enabled is False
        
        # Test list active projects
        active_projects = repo.list_active_projects()
        assert len(active_projects) == 1
        assert active_projects[0].id == project.id
        
        # Test delete (soft delete)
        success = repo.delete(project.id)
        assert success is True
        
        # Verify project is marked as deleted
        deleted_project = repo.get_by_id(project.id)
        assert deleted_project.status == 'deleted'
    
    def test_project_settings_repository(self, temp_db):
        """Test project settings repository operations"""
        project_repo = ProjectRepository(temp_db)
        settings_repo = ProjectSettingsRepository(temp_db)
        
        # Create a project first
        project_data = {
            'name': 'Test Project',
            'github_owner': 'testowner',
            'github_repo': 'testrepo'
        }
        project = project_repo.create(project_data)
        
        # Test create settings
        settings_data = {
            'project_id': project.id,
            'planning_statement': 'Test planning statement',
            'repository_rules': 'Follow best practices',
            'setup_commands': 'npm install\nnpm start',
            'branch_name': 'develop'
        }
        
        settings = settings_repo.create(settings_data)
        assert settings.id is not None
        assert settings.project_id == project.id
        assert settings.planning_statement == 'Test planning statement'
        assert settings.branch_name == 'develop'
        
        # Test get by project ID
        retrieved = settings_repo.get_by_project_id(project.id)
        assert retrieved is not None
        assert retrieved.id == settings.id
        
        # Test update
        update_data = {
            'planning_statement': 'Updated planning statement',
            'setup_commands': 'yarn install\nyarn start'
        }
        updated = settings_repo.update(settings.id, update_data)
        assert updated.planning_statement == 'Updated planning statement'
        assert updated.setup_commands == 'yarn install\nyarn start'
        assert updated.branch_name == 'develop'  # Should remain unchanged
        
        # Test update by project ID
        project_update = {'repository_rules': 'Updated rules'}
        updated_by_project = settings_repo.update_by_project_id(project.id, project_update)
        assert updated_by_project.repository_rules == 'Updated rules'
    
    @patch.dict(os.environ, {'SECRETS_ENCRYPTION_KEY': 'test_key_for_encryption_testing_32b='})
    def test_project_secrets_repository(self, temp_db):
        """Test project secrets repository with encryption"""
        project_repo = ProjectRepository(temp_db)
        secrets_repo = ProjectSecretsRepository(temp_db)
        
        # Create a project first
        project_data = {
            'name': 'Test Project',
            'github_owner': 'testowner',
            'github_repo': 'testrepo'
        }
        project = project_repo.create(project_data)
        
        # Test create secret
        secret_data = {
            'project_id': project.id,
            'key_name': 'API_TOKEN',
            'value': 'secret_api_token_value'
        }
        
        secret = secrets_repo.create(secret_data)
        assert secret.id is not None
        assert secret.project_id == project.id
        assert secret.key_name == 'API_TOKEN'
        # Value should be encrypted
        assert secret.encrypted_value != 'secret_api_token_value'
        
        # Test get decrypted value
        decrypted_value = secrets_repo.get_decrypted_value(project.id, 'API_TOKEN')
        assert decrypted_value == 'secret_api_token_value'
        
        # Test get all decrypted secrets
        decrypted_secrets = secrets_repo.get_decrypted_secrets(project.id)
        assert 'API_TOKEN' in decrypted_secrets
        assert decrypted_secrets['API_TOKEN'] == 'secret_api_token_value'
        
        # Test update or create
        updated_secret = secrets_repo.update_or_create(
            project.id, 'API_TOKEN', 'updated_secret_value'
        )
        assert updated_secret.id == secret.id  # Should update existing
        
        new_secret = secrets_repo.update_or_create(
            project.id, 'NEW_TOKEN', 'new_secret_value'
        )
        assert new_secret.id != secret.id  # Should create new
        
        # Test bulk update
        bulk_secrets = {
            'TOKEN_1': 'value_1',
            'TOKEN_2': 'value_2',
            'TOKEN_3': 'value_3'
        }
        bulk_result = secrets_repo.bulk_update_secrets(project.id, bulk_secrets)
        assert len(bulk_result) == 3
        
        # Verify all secrets exist
        all_secrets = secrets_repo.get_decrypted_secrets(project.id)
        assert len(all_secrets) >= 5  # Original + updated + new + 3 bulk
        assert all_secrets['TOKEN_1'] == 'value_1'
        assert all_secrets['TOKEN_2'] == 'value_2'
        assert all_secrets['TOKEN_3'] == 'value_3'
    
    @pytest.mark.asyncio
    async def test_database_service_integration(self, temp_db):
        """Test database service layer coordination"""
        db_service = DatabaseService(temp_db)
        
        # Test create project with settings and secrets
        project_data = {
            'name': 'Integration Test Project',
            'github_owner': 'testowner',
            'github_repo': 'integration-test'
        }
        
        settings_data = {
            'planning_statement': 'Integration test planning',
            'repository_rules': 'Integration test rules',
            'setup_commands': 'echo "integration test"'
        }
        
        secrets_data = {
            'API_KEY': 'test_api_key',
            'SECRET_TOKEN': 'test_secret_token'
        }
        
        result = await db_service.create_project_with_settings(
            project_data, settings_data, secrets_data
        )
        
        project = result['project']
        settings = result['settings']
        secrets = result['secrets']
        
        assert project.name == 'Integration Test Project'
        assert settings.planning_statement == 'Integration test planning'
        assert len(secrets) == 2
        
        # Test get full configuration
        full_config = await db_service.get_project_full_config(project.id)
        assert full_config['project'].id == project.id
        assert full_config['settings'].id == settings.id
        assert full_config['secret_count'] == 2
        
        # Test update configuration
        update_result = await db_service.update_project_configuration(
            project_id=project.id,
            project_data={'auto_merge_enabled': True},
            settings_data={'branch_name': 'staging'},
            secrets_data={'NEW_SECRET': 'new_value'}
        )
        
        assert update_result['project'].auto_merge_enabled is True
        assert update_result['settings'].branch_name == 'staging'
        assert update_result['secrets_updated'] == 1
        
        # Test get planning context
        context = await db_service.get_project_planning_context(project.id)
        assert context['project_name'] == 'Integration Test Project'
        assert context['planning_statement'] == 'Integration test planning'
        assert context['branch_name'] == 'staging'
        assert 'API_KEY' in context['secrets']
        assert 'NEW_SECRET' in context['secrets']
        
        # Test delete complete
        success = await db_service.delete_project_complete(project.id)
        assert success is True
        
        # Verify project is deleted
        deleted_project = db_service.projects.get_by_id(project.id)
        assert deleted_project.status == 'deleted'
    
    def test_repository_factory(self, temp_db):
        """Test repository factory functionality"""
        factory = RepositoryFactory(temp_db)
        
        # Test repository creation
        project_repo = factory.project_repository
        settings_repo = factory.project_settings_repository
        secrets_repo = factory.project_secrets_repository
        
        assert isinstance(project_repo, ProjectRepository)
        assert isinstance(settings_repo, ProjectSettingsRepository)
        assert isinstance(secrets_repo, ProjectSecretsRepository)
        
        # Test singleton behavior
        assert factory.project_repository is project_repo
        assert factory.project_settings_repository is settings_repo
        assert factory.project_secrets_repository is secrets_repo
    
    def test_validation_errors(self, temp_db):
        """Test validation error handling"""
        repo = ProjectRepository(temp_db)
        
        # Test missing required fields
        with pytest.raises(ValidationError):
            repo.create({'name': 'Test'})  # Missing github_owner and github_repo
        
        # Test duplicate GitHub repo
        project_data = {
            'name': 'Test Project',
            'github_owner': 'testowner',
            'github_repo': 'testrepo'
        }
        repo.create(project_data)
        
        with pytest.raises(ValidationError):
            repo.create(project_data)  # Duplicate
    
    def test_error_handling(self, temp_db):
        """Test database error handling"""
        repo = ProjectRepository(temp_db)
        
        # Test get non-existent project
        result = repo.get_by_id(99999)
        assert result is None
        
        # Test update non-existent project
        result = repo.update(99999, {'name': 'Updated'})
        assert result is None
        
        # Test delete non-existent project
        result = repo.delete(99999)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
