"""
External service integrations for CodegenCICD Dashboard
"""
from .base_client import BaseClient, APIError, RateLimitError, AuthenticationError
from .codegen_client import CodegenClient
from .async_client import AsyncCodegenClient, create_development_client, create_production_client, create_client_from_env
from .github_client import GitHubClient
from .gemini_client import GeminiClient
from .grainchain_client import GrainchainClient
from .web_eval_client import WebEvalClient
from .web_eval_pr_client import WebEvalPRClient
from .graph_sitter_client import GraphSitterClient
from .config import ClientConfig, ConfigPresets

# Import key models and exceptions for convenience
from .models import (
    UserResponse, AgentRunResponse, OrganizationResponse,
    SourceType, MessageType, AgentRunStatus
)
from .exceptions import (
    CodegenAPIError, ValidationError, NotFoundError,
    ConflictError, ServerError, TimeoutError, NetworkError
)

__all__ = [
    # Base classes
    "BaseClient",
    "APIError",
    "RateLimitError", 
    "AuthenticationError",
    
    # Service clients
    "CodegenClient",
    "AsyncCodegenClient",  # Enhanced async client
    "GitHubClient",
    "GeminiClient",
    "GrainchainClient",
    "WebEvalClient",
    "WebEvalPRClient",
    "GraphSitterClient",
    
    # Enhanced client factories
    "create_development_client",
    "create_production_client",
    "create_client_from_env",
    
    # Configuration
    "ClientConfig",
    "ConfigPresets",
    
    # Key models
    "UserResponse",
    "AgentRunResponse",
    "OrganizationResponse",
    "SourceType",
    "MessageType", 
    "AgentRunStatus",
    
    # Enhanced exceptions
    "CodegenAPIError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ServerError",
    "TimeoutError",
    "NetworkError",
]
