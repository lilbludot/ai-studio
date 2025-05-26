"""
Configuration Manager for AI Studio
Handles all configuration loading, validation, and environment management
Created: 2025-05-23
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

# Set up logging
logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    type: str = "sqlite"
    path: str = "data/ai_studio.db"
    echo: bool = False
    # Future Firestore settings
    firestore_project: Optional[str] = None
    firestore_credentials: Optional[str] = None


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider"""
    api_key: str
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 60
    enabled: bool = True


@dataclass
class UIConfig:
    """UI-related configuration"""
    host: str = "127.0.0.1"
    port: int = 7860
    share: bool = False
    theme: str = "default"
    chat_panel_ratio: float = 0.7  # 70% for chat
    document_panel_ratio: float = 0.3  # 30% for document


@dataclass
class MemoryConfig:
    """Memory system configuration (Phase 2)"""
    max_context_tokens: int = 100000
    max_history_messages: int = 50
    include_system_prompt: bool = True
    system_prompt_tokens: int = 1000
    relevance_threshold: float = 0.7
    recency_weight: float = 0.3


class ConfigManager:
    """
    Manages application configuration across different environments.
    
    Configuration precedence (highest to lowest):
    1. Environment variables
    2. Environment-specific config file
    3. Default config file
    4. Hardcoded defaults
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize ConfigManager
        
        Args:
            config_dir: Directory containing config files. 
                       Defaults to 'config' in project root.
        """
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = Path(config_dir) if config_dir else self.project_root / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Determine current environment
        self.environment = self._get_environment()
        logger.info(f"ConfigManager initialized for environment: {self.environment.value}")
        
        # Load configuration
        self._config: Dict[str, Any] = {}
        self._load_config()
        
    def _get_environment(self) -> Environment:
        """Get current environment from ENV variable or default to development"""
        env_value = os.getenv("APP_ENVIRONMENT", "development").lower()
        try:
            return Environment(env_value)
        except ValueError:
            logger.warning(f"Invalid environment '{env_value}', defaulting to development")
            return Environment.DEVELOPMENT
    
    def _load_config(self) -> None:
        """Load configuration from files and environment"""
        # 1. Load default configuration
        default_config = self._load_default_config()
        
        # 2. Load environment-specific configuration
        env_config = self._load_env_config()
        
        # 3. Merge configurations (env overrides default)
        self._config = self._deep_merge(default_config, env_config)
        
        # 4. Override with environment variables
        self._apply_env_variables()
        
        # 5. Create necessary directories
        self._create_directories()
        
        logger.debug("Configuration loaded successfully")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        default_config = {
            "app_name": "AI Studio",
            "version": "0.1.0",
            "debug": self.environment == Environment.DEVELOPMENT,
            
            "database": {
                "type": "sqlite",
                "path": "data/ai_studio.db",
                "echo": False
            },
            
            "ui": {
                "host": "127.0.0.1",
                "port": 7860,
                "share": False,
                "theme": "default",
                "chat_panel_ratio": 0.7,
                "document_panel_ratio": 0.3
            },
            
            "providers": {
                "claude": {
                    "api_key": "",
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "timeout": 60,
                    "enabled": True
                },
                "openai": {
                    "api_key": "",
                    "model": "gpt-4-turbo-preview",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "timeout": 60,
                    "enabled": False
                },
                "gemini": {
                    "api_key": "",
                    "model": "gemini-pro",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "timeout": 60,
                    "enabled": False
                }
            },
            
            "memory": {
                "max_context_tokens": 100000,
                "max_history_messages": 50,
                "include_system_prompt": True,
                "system_prompt_tokens": 1000,
                "relevance_threshold": 0.7,
                "recency_weight": 0.3
            },
            
            "storage": {
                "projects_path": str(Path.home() / "iCloud Drive" / "ClaudeProjects"),
                "templates_dir": "_templates",
                "auto_save_interval": 30,  # seconds
                "max_file_size_mb": 10
            },
            
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/ai_studio.log",
                "max_bytes": 10485760,  # 10MB
                "backup_count": 5
            }
        }
        
        return default_config
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load environment-specific configuration"""
        env_config_path = self.config_dir / f"{self.environment.value}.yaml"
        
        if env_config_path.exists():
            try:
                with open(env_config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading {env_config_path}: {e}")
                return {}
        
        # Try JSON format
        env_config_path = self.config_dir / f"{self.environment.value}.json"
        if env_config_path.exists():
            try:
                with open(env_config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {env_config_path}: {e}")
                return {}
        
        return {}
    
    def _apply_env_variables(self) -> None:
        """Override config with environment variables"""
        # LLM Provider API Keys
        if api_key := os.getenv("CLAUDE_API_KEY"):
            self._config["providers"]["claude"]["api_key"] = api_key
            
        if api_key := os.getenv("OPENAI_API_KEY"):
            self._config["providers"]["openai"]["api_key"] = api_key
            
        if api_key := os.getenv("GEMINI_API_KEY"):
            self._config["providers"]["gemini"]["api_key"] = api_key
        
        # Database settings
        if db_path := os.getenv("DATABASE_PATH"):
            self._config["database"]["path"] = db_path
            
        # UI settings
        if port := os.getenv("UI_PORT"):
            self._config["ui"]["port"] = int(port)
            
        if host := os.getenv("UI_HOST"):
            self._config["ui"]["host"] = host
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def _create_directories(self) -> None:
        """Create necessary directories"""
        # Data directory
        data_dir = self.project_root / Path(self._config["database"]["path"]).parent
        data_dir.mkdir(exist_ok=True, parents=True)
        
        # Logs directory
        log_file = self._config["logging"]["file"]
        log_dir = self.project_root / Path(log_file).parent
        log_dir.mkdir(exist_ok=True, parents=True)
        
        # External storage
        projects_path = Path(self._config["storage"]["projects_path"])
        projects_path.mkdir(exist_ok=True, parents=True)
        
        templates_path = projects_path / self._config["storage"]["templates_dir"]
        templates_path.mkdir(exist_ok=True, parents=True)
    
    # Public methods for accessing configuration
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key
        
        Args:
            key: Configuration key (e.g., 'database.path', 'providers.claude.api_key')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set configuration value at runtime
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        # Set the value
        config[keys[-1]] = value
        return True
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration as a dataclass"""
        db_config = self._config.get("database", {})
        return DatabaseConfig(**db_config)
    
    def get_provider_config(self, provider_name: str) -> Optional[LLMProviderConfig]:
        """Get LLM provider configuration"""
        if provider_name not in self._config.get("providers", {}):
            return None
            
        provider_config = self._config["providers"][provider_name]
        return LLMProviderConfig(**provider_config)
    
    def get_ui_config(self) -> UIConfig:
        """Get UI configuration"""
        ui_config = self._config.get("ui", {})
        return UIConfig(**ui_config)
    
    def get_memory_config(self) -> MemoryConfig:
        """Get memory system configuration"""
        memory_config = self._config.get("memory", {})
        return MemoryConfig(**memory_config)
    
    def validate_config(self) -> Dict[str, Union[bool, str]]:
        """
        Validate current configuration
        
        Returns:
            Dictionary with 'valid' boolean and 'errors' list
        """
        errors = []
        
        # Check required API keys for enabled providers
        for provider, config in self._config.get("providers", {}).items():
            if config.get("enabled", False) and not config.get("api_key"):
                errors.append(f"{provider} is enabled but API key is missing")
        
        # Validate database path
        db_path = Path(self._config["database"]["path"])
        if not db_path.parent.exists():
            errors.append(f"Database directory {db_path.parent} does not exist")
        
        # Validate storage path
        storage_path = Path(self._config["storage"]["projects_path"])
        if not storage_path.exists():
            errors.append(f"Storage path {storage_path} does not exist")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def save_config(self, config_dict: Dict[str, Any], filename: Optional[str] = None) -> bool:
        """Save configuration to file"""
        if filename is None:
            filename = f"{self.environment.value}.yaml"
            
        config_path = self.config_dir / filename
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
            return False
    
    def export_config(self, path: str) -> bool:
        """Export current configuration (with sensitive data removed)"""
        export_config = self._deep_merge({}, self._config)
        
        # Remove sensitive data
        for provider in export_config.get("providers", {}).values():
            if "api_key" in provider:
                provider["api_key"] = "***REDACTED***"
                
        try:
            with open(path, 'w') as f:
                yaml.dump(export_config, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            logger.error(f"Error exporting config: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        self._config = self._load_default_config()
        self._apply_env_variables()
        return True