"""
Tests for Codegen API Client
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.services.codegen_api_client import (
    CodegenAPIClient,
    CodegenAPIError,
    AgentRunResponse,
    AgentRunResponseType,
    AgentRunLog
)


class TestCodegenAPIClient:
    """Test cases for CodegenAPIClient"""
    
    @pytest.fixture
    def client(self):
        """Create a test client instance"""
        with patch.dict('os.environ', {
            'CODEGEN_API_TOKEN': 'test-token',
            'CODEGEN_ORG_ID': '123'
        }):
            return CodegenAPIClient()
    
    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response"""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            'id': 'run-123',
            'status': 'running',
            'content': 'Test response content',
            'metadata': {'test': 'data'},
            'created_at': datetime.now().isoformat()
        }
        return response
    
    def test_client_initialization_success(self):
        """Test successful client initialization"""
        with patch.dict('os.environ', {
            'CODEGEN_API_TOKEN': 'test-token',
            'CODEGEN_ORG_ID': '123'
        }):
            client = CodegenAPIClient()
            assert client.api_token == 'test-token'
            assert client.org_id == '123'
            assert client.base_url == 'https://api.codegen.com/v1'
    
    def test_client_initialization_missing_credentials(self):
        """Test client initialization with missing credentials"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(CodegenAPIError, match="Missing CODEGEN_API_TOKEN or CODEGEN_ORG_ID"):
                CodegenAPIClient()
    
    @pytest.mark.asyncio
    async def test_create_agent_run_success(self, client, mock_response):
        """Test successful agent run creation"""
        with patch.object(client, '_make_request', return_value=mock_response.json.return_value) as mock_request:
            response = await client.create_agent_run(
                project_context="test-project",
                user_prompt="Create a test feature",
                planning_statement="Test planning statement"
            )
            
            # Verify request was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/agents/runs"
            
            # Verify request data
            request_data = call_args[1]['data']
            assert request_data['organization_id'] == '123'
            assert 'test-project' in request_data['prompt']
            assert 'Create a test feature' in request_data['prompt']
            assert 'Test planning statement' in request_data['prompt']
            
            # Verify response
            assert isinstance(response, AgentRunResponse)
            assert response.run_id == 'run-123'
            assert response.status == 'running'
    
    @pytest.mark.asyncio
    async def test_get_agent_run_status_success(self, client, mock_response):
        """Test successful agent run status retrieval"""
        with patch.object(client, '_make_request', return_value=mock_response.json.return_value) as mock_request:
            response = await client.get_agent_run_status("run-123")
            
            mock_request.assert_called_once_with("GET", "/agents/runs/run-123")
            assert isinstance(response, AgentRunResponse)
            assert response.run_id == 'run-123'
    
    @pytest.mark.asyncio
    async def test_confirm_plan_success(self, client, mock_response):
        """Test successful plan confirmation"""
        with patch.object(client, '_make_request', return_value=mock_response.json.return_value) as mock_request:
            response = await client.confirm_plan("run-123", "Proceed with plan")
            
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/agents/runs/run-123/continue"
            
            request_data = call_args[1]['data']
            assert request_data['message'] == "Proceed with plan"
            assert request_data['action'] == "confirm_plan"
    
    @pytest.mark.asyncio
    async def test_continue_agent_run_success(self, client, mock_response):
        """Test successful agent run continuation"""
        with patch.object(client, '_make_request', return_value=mock_response.json.return_value) as mock_request:
            response = await client.continue_agent_run("run-123", "Additional instructions")
            
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/agents/runs/run-123/continue"
            
            request_data = call_args[1]['data']
            assert request_data['message'] == "Additional instructions"
            assert request_data['action'] == "continue"
    
    @pytest.mark.asyncio
    async def test_cancel_agent_run_success(self, client):
        """Test successful agent run cancellation"""
        with patch.object(client, '_make_request', return_value={}) as mock_request:
            result = await client.cancel_agent_run("run-123")
            
            mock_request.assert_called_once_with("POST", "/agents/runs/run-123/cancel")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_cancel_agent_run_failure(self, client):
        """Test agent run cancellation failure"""
        with patch.object(client, '_make_request', side_effect=CodegenAPIError("API Error")) as mock_request:
            result = await client.cancel_agent_run("run-123")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_agent_run_logs_success(self, client):
        """Test successful agent run logs retrieval"""
        logs_data = {
            'logs': [
                {
                    'timestamp': datetime.now().isoformat(),
                    'level': 'INFO',
                    'message': 'Test log message',
                    'metadata': {'test': 'data'}
                }
            ]
        }
        
        with patch.object(client, '_make_request', return_value=logs_data) as mock_request:
            logs = await client.get_agent_run_logs("run-123")
            
            mock_request.assert_called_once_with("GET", "/agents/runs/run-123/logs")
            assert len(logs) == 1
            assert isinstance(logs[0], AgentRunLog)
            assert logs[0].level == 'INFO'
            assert logs[0].message == 'Test log message'
    
    @pytest.mark.asyncio
    async def test_list_agent_runs_success(self, client):
        """Test successful agent runs listing"""
        runs_data = {
            'runs': [
                {
                    'id': 'run-1',
                    'status': 'completed',
                    'content': 'First run',
                    'metadata': {},
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 'run-2',
                    'status': 'running',
                    'content': 'Second run',
                    'metadata': {},
                    'created_at': datetime.now().isoformat()
                }
            ]
        }
        
        with patch.object(client, '_make_request', return_value=runs_data) as mock_request:
            runs = await client.list_agent_runs(limit=10)
            
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "/agents/runs"
            assert call_args[1]['params']['limit'] == 10
            assert call_args[1]['params']['organization_id'] == '123'
            
            assert len(runs) == 2
            assert all(isinstance(run, AgentRunResponse) for run in runs)
    
    @pytest.mark.asyncio
    async def test_validate_connection_success(self, client):
        """Test successful connection validation"""
        with patch.object(client, '_make_request', return_value={}) as mock_request:
            result = await client.validate_connection()
            
            mock_request.assert_called_once_with("GET", "/organizations/current")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, client):
        """Test connection validation failure"""
        with patch.object(client, '_make_request', side_effect=CodegenAPIError("Connection failed")) as mock_request:
            result = await client.validate_connection()
            
            assert result is False


class TestAgentRunResponse:
    """Test cases for AgentRunResponse"""
    
    def test_from_api_response_regular(self):
        """Test creating AgentRunResponse from regular API response"""
        api_data = {
            'id': 'run-123',
            'status': 'completed',
            'content': 'Regular response content',
            'metadata': {'type': 'regular'},
            'created_at': datetime.now().isoformat()
        }
        
        response = AgentRunResponse.from_api_response(api_data)
        
        assert response.run_id == 'run-123'
        assert response.status == 'completed'
        assert response.response_type == AgentRunResponseType.REGULAR
        assert response.content == 'Regular response content'
    
    def test_from_api_response_plan(self):
        """Test creating AgentRunResponse from plan API response"""
        api_data = {
            'id': 'run-123',
            'status': 'waiting_for_input',
            'content': 'Here is the plan with multiple steps to implement',
            'metadata': {'type': 'plan'},
            'created_at': datetime.now().isoformat()
        }
        
        response = AgentRunResponse.from_api_response(api_data)
        
        assert response.response_type == AgentRunResponseType.PLAN
    
    def test_from_api_response_pr(self):
        """Test creating AgentRunResponse from PR API response"""
        api_data = {
            'id': 'run-123',
            'status': 'completed',
            'content': 'Pull request has been created successfully',
            'metadata': {'pr_url': 'https://github.com/test/repo/pull/1'},
            'created_at': datetime.now().isoformat()
        }
        
        response = AgentRunResponse.from_api_response(api_data)
        
        assert response.response_type == AgentRunResponseType.PR
    
    def test_from_api_response_error(self):
        """Test creating AgentRunResponse from error API response"""
        api_data = {
            'id': 'run-123',
            'status': 'error',
            'content': 'An error occurred during execution',
            'metadata': {'error_code': 'EXECUTION_FAILED'},
            'created_at': datetime.now().isoformat()
        }
        
        response = AgentRunResponse.from_api_response(api_data)
        
        assert response.response_type == AgentRunResponseType.ERROR


class TestCodegenAPIError:
    """Test cases for CodegenAPIError"""
    
    def test_error_creation_basic(self):
        """Test basic error creation"""
        error = CodegenAPIError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.status_code is None
        assert error.response_data is None
    
    def test_error_creation_with_details(self):
        """Test error creation with status code and response data"""
        response_data = {"error": "Invalid request", "code": "BAD_REQUEST"}
        error = CodegenAPIError("API request failed", status_code=400, response_data=response_data)
        
        assert error.message == "API request failed"
        assert error.status_code == 400
        assert error.response_data == response_data


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client as async context manager"""
    with patch.dict('os.environ', {
        'CODEGEN_API_TOKEN': 'test-token',
        'CODEGEN_ORG_ID': '123'
    }):
        async with CodegenAPIClient() as client:
            assert client.api_token == 'test-token'
            # Client should be properly initialized
            assert hasattr(client, 'client')
        
        # Client should be closed after context exit
        # Note: In real usage, the httpx client would be closed
