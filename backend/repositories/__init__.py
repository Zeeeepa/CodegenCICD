"""
Repository layer initialization and dependency injection
"""
from typing import Optional
from database.connection_manager import DatabaseManager, get_database_manager
from .project_repository import ProjectRepository
from .project_settings_repository import ProjectSettingsRepository
from .project_secrets_repository import ProjectSecretsRepository


class RepositoryFactory:
    """Factory for creating repository instances with shared database manager"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        self._project_repo = None
        self._settings_repo = None
        self._secrets_repo = None
    
    @property
    def project_repository(self) -> ProjectRepository:
        """Get or create project repository instance"""
        if self._project_repo is None:
            self._project_repo = ProjectRepository(self.db_manager)
        return self._project_repo
    
    @property
    def project_settings_repository(self) -> ProjectSettingsRepository:
        """Get or create project settings repository instance"""
        if self._settings_repo is None:
            self._settings_repo = ProjectSettingsRepository(self.db_manager)
        return self._settings_repo
    
    @property
    def project_secrets_repository(self) -> ProjectSecretsRepository:
        """Get or create project secrets repository instance"""
        if self._secrets_repo is None:
            self._secrets_repo = ProjectSecretsRepository(self.db_manager)
        return self._secrets_repo


# Global repository factory instance
_repository_factory: Optional[RepositoryFactory] = None


def get_repository_factory() -> RepositoryFactory:
    """Get the global repository factory instance"""
    global _repository_factory
    if _repository_factory is None:
        _repository_factory = RepositoryFactory()
    return _repository_factory


def initialize_repositories(db_manager: Optional[DatabaseManager] = None) -> RepositoryFactory:
    """Initialize repositories with custom database manager"""
    global _repository_factory
    _repository_factory = RepositoryFactory(db_manager)
    return _repository_factory


__all__ = [
    'RepositoryFactory',
    'ProjectRepository',
    'ProjectSettingsRepository', 
    'ProjectSecretsRepository',
    'get_repository_factory',
    'initialize_repositories'
]

