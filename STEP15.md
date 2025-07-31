# STEP15: Codegen API Client Implementation

## ROLE
You are a senior backend systems engineer with 10+ years of experience in API integration and distributed systems, specializing in AI agent orchestration and real-time communication protocols with extensive FastAPI and async Python expertise.

## TASK
Implement Codegen API Client for Agent Run Management

## YOUR QUEST
Create a single, isolated Codegen API client implementation that handles agent run creation, status monitoring, and response processing using the official Codegen API endpoints, with proper authentication, error handling, and async support for real-time agent communication.

## TECHNICAL CONTEXT

### EXISTING CODEBASE:

```python
# From backend/services/codegen_client.py (existing partial implementation)
class CodegenClient:
    def __init__(self, api_token: str, org_id: str):
        self.api_token = api_token
        self.org_id = org_id
        self.base_url = "https://api.codegen.com"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

# From backend/core/grainchain_config.py
class GrainchainConfigManager:
    def __init__(self):
        self.settings = self._load_settings()
        
# From backend/models/project.py
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    full_name = Column(String(500), nullable=False)
    planning_statement = Column(Text)
    auto_confirm_plans = Column(Boolean, default=False)
```

### IMPLEMENTATION REQUIREMENTS:

- Implement complete CodegenAPIClient class with all agent run operations
- Support agent run creation with project context and planning statements
- Implement real-time status monitoring with polling and webhook support
- Handle all response types: regular, plan, PR creation notifications
- Implement proper authentication with API token validation
- Add comprehensive error handling for API failures and timeouts
- Support async operations with proper connection pooling
- Implement retry logic with exponential backoff for transient failures
- Add request/response logging for debugging and monitoring
- Support rate limiting and request throttling
- Ensure thread-safety for concurrent agent runs
- Performance requirement: <2s response time for agent run creation

### INTEGRATION CONTEXT

#### UPSTREAM DEPENDENCIES:
- Environment variables: CODEGEN_ORG_ID, CODEGEN_API_TOKEN from backend/.env.example
- HTTP client: httpx for async HTTP operations
- Configuration: backend/core/grainchain_config.py for settings management
- Database models: backend/models/project.py for project context

#### DOWNSTREAM DEPENDENCIES:
- STEP16 - Agent Run Manager: Will consume this client for orchestrating agent runs
- STEP17 - Plan Confirmation Handler: Will use this client for plan confirmations
- STEP18 - Agent Run Status Tracker: Will use this client for status monitoring
- STEP36 - Agent Run API: Will use this client in API endpoints

## EXPECTED OUTCOME

### Files to Create/Modify:
- **backend/services/codegen_api_client.py** - Complete Codegen API client implementation
- **backend/models/agent_run.py** - Enhanced agent run models with new fields
- **backend/tests/test_codegen_api_client.py** - Comprehensive unit tests

### Required Interface:
```python
class CodegenAPIClient:
    async def create_agent_run(
        self, 
        project_context: str, 
        user_prompt: str, 
        planning_statement: Optional[str] = None
    ) -> AgentRunResponse
    
    async def get_agent_run_status(self, run_id: str) -> AgentRunStatus
    
    async def confirm_plan(self, run_id: str, confirmation: str = "Proceed") -> AgentRunResponse
    
    async def continue_agent_run(self, run_id: str, continuation_prompt: str) -> AgentRunResponse
    
    async def cancel_agent_run(self, run_id: str) -> bool
    
    async def get_agent_run_logs(self, run_id: str) -> List[AgentRunLog]
```

## ACCEPTANCE CRITERIA
- [ ] CodegenAPIClient successfully creates agent runs with project context
- [ ] Client handles all response types (regular, plan, PR) correctly
- [ ] Status monitoring works with real-time updates
- [ ] Plan confirmation and continuation flows work properly
- [ ] Error handling covers all API failure scenarios
- [ ] All unit tests pass with >90% code coverage
- [ ] Performance test shows <2s response time for agent run creation
- [ ] Authentication and rate limiting work correctly
- [ ] Async operations handle concurrent requests properly
- [ ] Logging captures all API interactions for debugging

## IMPLEMENTATION CONSTRAINTS
- This task represents a SINGLE atomic unit of functionality
- Must be independently implementable (except for listed dependencies)
- Implementation must include comprehensive automated tests
- Code must conform to project coding standards with proper documentation
- Must not modify existing interfaces without backward compatibility
- All API interactions must be properly authenticated and secured

