"""
Grainchain configuration and setup for CodegenCICD.

This module handles the configuration and initialization of grainchain
for snapshot management and analysis pipeline integration.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from grainchain import Sandbox, SandboxConfig, Providers
from grainchain.core.config import get_config_manager


class SandboxProvider(str, Enum):
    """Available sandbox providers for grainchain."""
    LOCAL = "local"
    E2B = "e2b"
    DAYTONA = "daytona"
    MORPH = "morph"
    MODAL = "modal"


@dataclass
class GrainchainSettings:
    """Grainchain configuration settings."""
    default_provider: SandboxProvider = SandboxProvider.LOCAL
    timeout: int = 300  # 5 minutes default timeout
    max_concurrent_sandboxes: int = 5
    snapshot_storage_path: str = "/tmp/grainchain_snapshots"
    enable_snapshots: bool = True
    cleanup_on_exit: bool = True
    
    # Provider-specific settings
    e2b_api_key: Optional[str] = None
    daytona_api_key: Optional[str] = None
    morph_api_key: Optional[str] = None
    modal_api_key: Optional[str] = None


class GrainchainConfigManager:
    """Manages grainchain configuration and initialization."""
    
    def __init__(self):
        self.settings = self._load_settings()
        self._config_manager = None
    
    def _load_settings(self) -> GrainchainSettings:
        """Load grainchain settings from environment variables."""
        return GrainchainSettings(
            default_provider=SandboxProvider(
                os.getenv("GRAINCHAIN_DEFAULT_PROVIDER", "local")
            ),
            timeout=int(os.getenv("GRAINCHAIN_TIMEOUT", "300")),
            max_concurrent_sandboxes=int(
                os.getenv("GRAINCHAIN_MAX_CONCURRENT", "5")
            ),
            snapshot_storage_path=os.getenv(
                "GRAINCHAIN_SNAPSHOT_PATH", "/tmp/grainchain_snapshots"
            ),
            enable_snapshots=os.getenv("GRAINCHAIN_ENABLE_SNAPSHOTS", "true").lower() == "true",
            cleanup_on_exit=os.getenv("GRAINCHAIN_CLEANUP_ON_EXIT", "true").lower() == "true",
            
            # Provider API keys
            e2b_api_key=os.getenv("E2B_API_KEY"),
            daytona_api_key=os.getenv("DAYTONA_API_KEY"),
            morph_api_key=os.getenv("MORPH_API_KEY"),
            modal_api_key=os.getenv("MODAL_API_KEY"),
        )
    
    def get_config_manager(self):
        """Get grainchain config manager instance."""
        if self._config_manager is None:
            self._config_manager = get_config_manager()
        return self._config_manager
    
    def create_sandbox_config(self, **overrides) -> SandboxConfig:
        """Create a sandbox configuration with default settings."""
        config_data = {
            "timeout": self.settings.timeout,
            "cleanup_on_exit": self.settings.cleanup_on_exit,
            **overrides
        }
        return SandboxConfig(**config_data)
    
    def create_sandbox(
        self, 
        provider: Optional[str] = None,
        config: Optional[SandboxConfig] = None
    ) -> Sandbox:
        """Create a new sandbox instance."""
        provider = provider or self.settings.default_provider.value
        config = config or self.create_sandbox_config()
        
        return Sandbox(provider=provider, config=config)
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Get list of available and configured providers."""
        from grainchain import get_available_providers
        
        available = get_available_providers()
        configured = {}
        
        for provider in SandboxProvider:
            is_available = provider.value in available
            is_configured = self._is_provider_configured(provider)
            configured[provider.value] = is_available and is_configured
        
        return configured
    
    def _is_provider_configured(self, provider: SandboxProvider) -> bool:
        """Check if a provider is properly configured."""
        if provider == SandboxProvider.LOCAL:
            return True  # Local provider doesn't need API keys
        
        api_key_map = {
            SandboxProvider.E2B: self.settings.e2b_api_key,
            SandboxProvider.DAYTONA: self.settings.daytona_api_key,
            SandboxProvider.MORPH: self.settings.morph_api_key,
            SandboxProvider.MODAL: self.settings.modal_api_key,
        }
        
        return api_key_map.get(provider) is not None
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate grainchain configuration and return status."""
        status = {
            "configured": True,
            "default_provider": self.settings.default_provider.value,
            "providers": self.get_available_providers(),
            "settings": {
                "timeout": self.settings.timeout,
                "max_concurrent": self.settings.max_concurrent_sandboxes,
                "snapshots_enabled": self.settings.enable_snapshots,
                "snapshot_path": self.settings.snapshot_storage_path,
            },
            "errors": []
        }
        
        # Check if default provider is available
        available_providers = status["providers"]
        if not available_providers.get(self.settings.default_provider.value, False):
            status["errors"].append(
                f"Default provider '{self.settings.default_provider.value}' is not available or configured"
            )
            status["configured"] = False
        
        # Check snapshot storage path
        if self.settings.enable_snapshots:
            try:
                os.makedirs(self.settings.snapshot_storage_path, exist_ok=True)
            except Exception as e:
                status["errors"].append(f"Cannot create snapshot storage path: {e}")
                status["configured"] = False
        
        return status


# Global configuration instance
grainchain_config = GrainchainConfigManager()


def get_grainchain_config() -> GrainchainConfigManager:
    """Get the global grainchain configuration instance."""
    return grainchain_config


def create_default_sandbox() -> Sandbox:
    """Create a sandbox with default configuration."""
    return grainchain_config.create_sandbox()


async def test_grainchain_connection() -> Dict[str, Any]:
    """Test grainchain connection and return status."""
    try:
        async with create_default_sandbox() as sandbox:
            result = await sandbox.execute("echo 'Grainchain connection test'")
            return {
                "success": True,
                "provider": grainchain_config.settings.default_provider.value,
                "test_output": result.stdout.strip(),
                "execution_time": result.execution_time
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "provider": grainchain_config.settings.default_provider.value
        }
