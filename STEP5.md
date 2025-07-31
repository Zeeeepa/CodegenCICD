# STEP5: Database Integration Layer

## ROLE
You are a senior backend systems engineer with 10+ years of experience in database integration, specializing in SQLite optimization, connection pooling, and repository pattern implementation with extensive FastAPI and Pydantic expertise.

## TASK
Integrate Foundation Database Layer with FastAPI Application

## YOUR QUEST
Create a single, isolated database integration layer that connects the existing foundation database schema and connection management with the FastAPI application, providing repository pattern implementations and database service layer for all project-related operations.

## TECHNICAL CONTEXT

### EXISTING CODEBASE:

**Foundation Database Layer (COMPLETE):**
```python
# From database/schema.sql - 9 tables with relationships
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    github_owner TEXT NOT NULL,
    github_repo TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    webhook_url TEXT,
    auto_merge_enabled BOOLEAN DEFAULT FALSE,
    auto_confirm_plans BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    planning_statement TEXT,
    repository_rules TEXT,
    setup_commands TEXT,
    branch_name TEXT DEFAULT 'main',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE project_secrets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    key_name TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

# Additional tables: agent_runs, pipeline_states, webhooks, test_results, grainchain_snapshots, system_logs
```

**Foundation Connection Manager:**
```python
# From database/connection_manager.py
class DatabaseManager:
    def __init__(self, config: Optional[ConnectionConfig] = None):
        self.config = config or ConnectionConfig()
        self.sync_pool = ConnectionPool(self.config)
        self.async_pool = AsyncConnectionPool(self.config)
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        return self.sync_pool.execute_query(query, params)
    
    def execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        return self.sync_pool.execute_command(command, params)
    
    @contextmanager
    def transaction(self):
        with self.sync_pool.transaction() as conn:
            yield conn

# From database/base.py
class BaseRepository(Generic[T], ABC):
    def __init__(self, model_class: Type[T], table_name: str, db_manager: Optional[DatabaseManager] = None):
        self.model_class = model_class
        self.table_name = table_name
        self.db_manager = db_manager or get_database_manager()
    
    def create(self, data: Dict[str, Any]) -> T:
        # Implementation with transaction handling
    
    def get_by_id(self, record_id: int) -> Optional[T]:
        # Implementation with error handling
    
    def update(self, record_id: int, data: Dict[str, Any]) -> Optional[T]:
        # Implementation with validation
```

**Foundation Models:**
```python
# From models.py
class Project(BaseDBModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=255)
    github_owner: str = Field(..., min_length=1, max_length=100)
    github_repo: str = Field(..., min_length=1, max_length=100)
    status: str = Field(default="active")
    webhook_url: Optional[str] = None
    auto_merge_enabled: bool = Field(default=False)
    auto_confirm_plans: bool = Field(default=False)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ProjectSettings(BaseDBModel):
    id: Optional[int] = None
    project_id: int
    planning_statement: Optional[str] = None
    repository_rules: Optional[str] = None
    setup_commands: Optional[str] = None
    branch_name: str = Field(default="main")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ProjectSecret(BaseDBModel):
    id: Optional[int] = None
    project_id: int
    key_name: str = Field(..., min_length=1, max_length=100)
    encrypted_value: str = Field(..., min_length=1)
    created_at: Optional[datetime] = None
```

**Current FastAPI Mock Endpoints:**
```python
# From backend/main.py - NEEDS REPLACEMENT
@app.get("/api/projects")
async def get_projects():
    return {"projects": [mock_data]}  # REPLACE WITH REAL DATABASE

@app.post("/api/projects")
async def create_project(project_data: dict):
    return mock_project  # REPLACE WITH REAL DATABASE

@app.get("/api/projects/{project_id}/configuration")
async def get_project_configuration(project_id: int):
    return mock_config  # REPLACE WITH REAL DATABASE
```

### IMPLEMENTATION REQUIREMENTS:

1. **Repository Pattern Implementation**
   - Create concrete repository classes for Project, ProjectSettings, ProjectSecret
   - Implement all CRUD operations with proper error handling
   - Use existing BaseRepository from foundation layer
   - Include transaction support for complex operations

2. **Database Service Layer**
   - Create DatabaseService class that coordinates repository operations
   - Implement business logic for project management
   - Handle cross-table operations (project + settings + secrets)
   - Provide async/await support for FastAPI integration

3. **FastAPI Integration**
   - Create dependency injection for database services
   - Replace mock endpoints with real database operations
   - Implement proper error handling and HTTP status codes
   - Add request/response validation using Pydantic models

4. **Security and Encryption**
   - Implement encryption/decryption for project secrets
   - Use existing security settings from foundation configuration
   - Ensure sensitive data is never logged or exposed

5. **Performance Requirements**
   - Database operations must complete in <50ms at P95
   - Support concurrent requests with connection pooling
   - Implement proper indexing for query optimization
   - Use prepared statements for all database operations

## INTEGRATION CONTEXT

### UPSTREAM DEPENDENCIES:
- **Foundation Database Layer (COMPLETE)**: 
  - `database/connection_manager.py` - DatabaseManager class
  - `database/base.py` - BaseRepository class
  - `models.py` - Pydantic models for all entities
  - `config/settings.py` - Database configuration
- **Foundation Configuration (COMPLETE)**:
  - Environment variable management
  - Security settings for encryption
- **Foundation Logging (COMPLETE)**:
  - Structured logging with correlation IDs
  - Error handling framework

### DOWNSTREAM DEPENDENCIES:
- **STEP6 - GitHub Service Integration**: Will use project repositories
- **STEP7 - Project Management Service**: Will use database service layer
- **STEP8 - Agent Run Orchestration**: Will use agent run repository
- **STEP9 - Webhook Management**: Will use webhook repository

## EXPECTED OUTCOME

### Files to Create:
1. **`backend/repositories/project_repository.py`**
   - ProjectRepository class extending BaseRepository
   - All CRUD operations for projects table
   - Complex queries for project listing and filtering

2. **`backend/repositories/project_settings_repository.py`**
   - ProjectSettingsRepository class extending BaseRepository
   - Settings management with validation
   - Integration with project lifecycle

3. **`backend/repositories/project_secrets_repository.py`**
   - ProjectSecretsRepository class extending BaseRepository
   - Encryption/decryption of secret values
   - Secure secret management operations

4. **`backend/repositories/__init__.py`**
   - Repository factory and dependency injection
   - Database initialization and migration runner

5. **`backend/services/database_service.py`**
   - DatabaseService class coordinating all repositories
   - Business logic for complex operations
   - Transaction management for multi-table operations

6. **`backend/dependencies.py`**
   - FastAPI dependency injection for database services
   - Database session management
   - Error handling middleware

### Files to Modify:
1. **`backend/main.py`**
   - Replace mock endpoints with real database operations
   - Add dependency injection for database services
   - Implement proper error handling

2. **`backend/requirements.txt`**
   - Add any additional dependencies for encryption

### Required Method Signatures:
```python
class ProjectRepository(BaseRepository[Project]):
    def get_by_github_repo(self, owner: str, repo: str) -> Optional[Project]
    def list_active_projects(self) -> List[Project]
    def update_webhook_url(self, project_id: int, webhook_url: str) -> bool

class DatabaseService:
    async def create_project_with_settings(
        self, project_data: Dict[str, Any], settings_data: Dict[str, Any]
    ) -> Project
    async def get_project_full_config(self, project_id: int) -> Dict[str, Any]
    async def update_project_secrets(
        self, project_id: int, secrets: List[Dict[str, str]]
    ) -> bool
```

## ACCEPTANCE CRITERIA

1. **Database Integration**
   - [ ] All foundation database components successfully integrated with FastAPI
   - [ ] Repository pattern implemented for all project-related tables
   - [ ] Database service layer provides business logic coordination
   - [ ] All mock endpoints replaced with real database operations

2. **Security Implementation**
   - [ ] Project secrets are encrypted before storage
   - [ ] Decryption works correctly for secret retrieval
   - [ ] No sensitive data appears in logs or error messages
   - [ ] Encryption keys are managed securely via configuration

3. **Performance Requirements**
   - [ ] Database operations complete in <50ms at P95
   - [ ] Connection pooling handles concurrent requests efficiently
   - [ ] All queries use proper indexing and prepared statements
   - [ ] Memory usage remains stable under load

4. **API Functionality**
   - [ ] All project CRUD operations work through real database
   - [ ] Project settings and secrets management functional
   - [ ] Proper HTTP status codes and error responses
   - [ ] Request/response validation using Pydantic models

5. **Testing Requirements**
   - [ ] Unit tests for all repository classes (>90% coverage)
   - [ ] Integration tests for database service layer
   - [ ] API endpoint tests with real database operations
   - [ ] Performance tests validating latency requirements

## IMPLEMENTATION CONSTRAINTS

- This task represents a SINGLE atomic unit of functionality (database integration)
- Must be independently implementable using existing foundation layer
- Must include comprehensive tests and documentation
- Must conform to project coding standards and security requirements
- Must not modify any existing foundation layer interfaces
- All database operations must use the existing connection manager
- Must maintain backward compatibility with existing API contracts

