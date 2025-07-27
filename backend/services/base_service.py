"""
Base service class for CodegenCICD Dashboard services
"""
import structlog
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class BaseService(ABC):
    """Base class for all services with common functionality"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logger.bind(service=service_name)
        self._initialized = False
        self._config = {}
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the service with configuration"""
        try:
            self._config = config or {}
            await self._initialize_service()
            self._initialized = True
            self.logger.info("Service initialized successfully")
        except Exception as e:
            self.logger.error("Service initialization failed", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close the service and cleanup resources"""
        try:
            if self._initialized:
                await self._close_service()
                self._initialized = False
                self.logger.info("Service closed successfully")
        except Exception as e:
            self.logger.error("Service close failed", error=str(e))
            raise
    
    @abstractmethod
    async def _initialize_service(self) -> None:
        """Service-specific initialization logic"""
        pass
    
    @abstractmethod
    async def _close_service(self) -> None:
        """Service-specific cleanup logic"""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for this service"""
        return {
            "service": self.service_name,
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "config_keys": list(self._config.keys()) if self._config else []
        }

