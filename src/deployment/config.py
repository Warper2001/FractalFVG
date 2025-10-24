"""
Configuration management for unified deployment script.

Handles deployment configuration, credential management, and environment setup.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from dotenv import load_dotenv
from enum import Enum


class Environment(Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""
    
    environment: Environment
    api_base_url: str
    timeout: int = 30
    max_retries: int = 3
    log_level: LogLevel = LogLevel.INFO
    enable_metrics: bool = True
    debug_mode: bool = False
    
    def __post_init__(self):
        """Validate environment configuration."""
        self._validate_api_base_url()
        self._validate_timeout()
        self._validate_max_retries()
    
    def _validate_api_base_url(self):
        """Validate API base URL."""
        if not self.api_base_url or not self.api_base_url.strip():
            raise ValueError("API base URL cannot be empty")
        
        if not self.api_base_url.startswith(('http://', 'https://')):
            raise ValueError("API base URL must start with http:// or https://")
    
    def _validate_timeout(self):
        """Validate timeout value."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
    
    def _validate_max_retries(self):
        """Validate max retries value."""
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")


@dataclass
class DeploymentConfig:
    """Configuration for the deployment pipeline."""
    
    algorithm_file_path: str
    project_name: Optional[str] = None
    backtest_name: str = "Automated Backtest"
    backtest_parameters: Dict[str, Any] = field(default_factory=dict)
    cleanup_test_projects: bool = True
    verbose_logging: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_algorithm_file()
        self._validate_backtest_parameters()
    
    def _validate_algorithm_file(self):
        """Validate that algorithm file exists and is readable."""
        if not Path(self.algorithm_file_path).exists():
            raise FileNotFoundError(f"Algorithm file not found: {self.algorithm_file_path}")
        
        if not Path(self.algorithm_file_path).is_file():
            raise ValueError(f"Algorithm path is not a file: {self.algorithm_file_path}")
    
    def _validate_backtest_parameters(self):
        """Validate that backtest parameters are serializable to JSON."""
        try:
            json.dumps(self.backtest_parameters)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Backtest parameters must be JSON serializable: {e}")


@dataclass
class Credentials:
    """QuantConnect API authentication credentials."""
    
    user_id: str
    api_token: str
    organization_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate credentials after initialization."""
        self._validate_user_id()
        self._validate_api_token()
    
    def _validate_user_id(self):
        """Validate user ID format."""
        if not self.user_id or not self.user_id.strip():
            raise ValueError("QUANTCONNECT_USER_ID cannot be empty")
        
        if not self.user_id.isdigit():
            raise ValueError("QUANTCONNECT_USER_ID must be numeric")
    
    def _validate_api_token(self):
        """Validate API token format."""
        if not self.api_token or not self.api_token.strip():
            raise ValueError("QUANTCONNECT_API_TOKEN cannot be empty")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }


def load_credentials() -> Credentials:
    """
    Load QuantConnect credentials from environment variables.
    
    Returns:
        Credentials: Loaded and validated credentials
        
    Raises:
        ValueError: If required credentials are missing or invalid
    """
    # Load environment variables from .env file
    load_dotenv()
    
    user_id = os.getenv('QUANTCONNECT_USER_ID')
    api_token = os.getenv('QUANTCONNECT_API_TOKEN')
    organization_id = os.getenv('QUANTCONNECT_ORGANIZATION_ID')
    
    if not user_id:
        raise ValueError("Missing QUANTCONNECT_USER_ID in environment variables")
    
    if not api_token:
        raise ValueError("Missing QUANTCONNECT_API_TOKEN in environment variables")
    
    return Credentials(
        user_id=user_id,
        api_token=api_token,
        organization_id=organization_id
    )


def create_deployment_config(
    algorithm_file_path: str,
    project_name: Optional[str] = None,
    backtest_name: str = "Automated Backtest",
    backtest_parameters: Optional[str] = None,
    cleanup_test_projects: bool = True,
    verbose_logging: bool = False
) -> DeploymentConfig:
    """
    Create and validate deployment configuration.
    
    Args:
        algorithm_file_path: Path to the algorithm file to deploy
        project_name: Custom name for the project
        backtest_name: Custom name for the backtest
        backtest_parameters: JSON string of backtest parameters
        cleanup_test_projects: Whether to clean up test projects after deployment
        verbose_logging: Enable detailed logging output
        
    Returns:
        DeploymentConfig: Validated configuration object
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Parse backtest parameters if provided
    params = {}
    if backtest_parameters:
        try:
            params = json.loads(backtest_parameters)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in backtest parameters: {e}")
    
    return DeploymentConfig(
        algorithm_file_path=algorithm_file_path,
        project_name=project_name,
        backtest_name=backtest_name,
        backtest_parameters=params,
        cleanup_test_projects=cleanup_test_projects,
        verbose_logging=verbose_logging
    )


def load_environment_config() -> EnvironmentConfig:
    """
    Load environment configuration from environment variables.
    
    Returns:
        EnvironmentConfig: Loaded and validated environment configuration
        
    Raises:
        ValueError: If environment configuration is invalid
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get environment type
    env_str = os.getenv('DEPLOYMENT_ENV', 'development').lower()
    try:
        environment = Environment(env_str)
    except ValueError:
        raise ValueError(f"Invalid DEPLOYMENT_ENV: {env_str}. Must be one of: {[e.value for e in Environment]}")
    
    # Get API base URL
    api_base_url = os.getenv('QUANTCONNECT_API_URL', 'https://www.quantconnect.com/api/v2')
    
    # Get other configuration values
    timeout = int(os.getenv('API_TIMEOUT', '30'))
    max_retries = int(os.getenv('API_MAX_RETRIES', '3'))
    
    # Get log level
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    try:
        log_level = LogLevel(log_level_str)
    except ValueError:
        raise ValueError(f"Invalid LOG_LEVEL: {log_level_str}. Must be one of: {[l.value for l in LogLevel]}")
    
    enable_metrics = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    return EnvironmentConfig(
        environment=environment,
        api_base_url=api_base_url,
        timeout=timeout,
        max_retries=max_retries,
        log_level=log_level,
        enable_metrics=enable_metrics,
        debug_mode=debug_mode
    )


def get_config_file_path(config_name: str = "deployment") -> Path:
    """
    Get path to configuration file.
    
    Args:
        config_name: Name of the configuration file (without extension)
        
    Returns:
        Path: Path to configuration file
    """
    # Check for config in current directory first
    config_path = Path(f"{config_name}.json")
    if config_path.exists():
        return config_path
    
    # Check in config directory
    config_path = Path("config") / f"{config_name}.json"
    if config_path.exists():
        return config_path
    
    # Check in user's home directory
    config_path = Path.home() / ".fractalfvg" / f"{config_name}.json"
    if config_path.exists():
        return config_path
    
    # Return default path (may not exist)
    return Path(f"{config_name}.json")


def load_config_from_file(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to configuration file. If None, uses default path.
        
    Returns:
        Dict[str, Any]: Configuration data
        
    Raises:
        FileNotFoundError: If configuration file is not found
        json.JSONDecodeError: If configuration file is invalid JSON
    """
    if config_path is None:
        config_path = get_config_file_path()
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)


def save_config_to_file(config_data: Dict[str, Any], 
                       config_path: Optional[Union[str, Path]] = None) -> Path:
    """
    Save configuration to JSON file.
    
    Args:
        config_data: Configuration data to save
        config_path: Path to save configuration. If None, uses default path.
        
    Returns:
        Path: Path where configuration was saved
        
    Raises:
        OSError: If file cannot be written
    """
    if config_path is None:
        config_path = get_config_file_path()
    
    config_path = Path(config_path)
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=2, default=str)
    
    return config_path


def merge_config_with_env(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge configuration data with environment variables.
    
    Environment variables take precedence over file configuration.
    
    Args:
        config_data: Configuration data from file
        
    Returns:
        Dict[str, Any]: Merged configuration data
    """
    # Load environment variables
    load_dotenv()
    
    # Define environment variable mappings
    env_mappings = {
        'QUANTCONNECT_API_URL': 'api_base_url',
        'API_TIMEOUT': 'timeout',
        'API_MAX_RETRIES': 'max_retries',
        'LOG_LEVEL': 'log_level',
        'ENABLE_METRICS': 'enable_metrics',
        'DEBUG_MODE': 'debug_mode',
        'DEPLOYMENT_ENV': 'environment'
    }
    
    # Create a copy of config data
    merged_config = config_data.copy()
    
    # Override with environment variables
    for env_var, config_key in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Convert string values to appropriate types
            if config_key in ['timeout', 'max_retries']:
                merged_config[config_key] = int(env_value)
            elif config_key in ['enable_metrics', 'debug_mode']:
                merged_config[config_key] = env_value.lower() == 'true'
            else:
                merged_config[config_key] = env_value
    
    return merged_config


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        bool: True if environment is valid
        
    Raises:
        ValueError: If required environment variables are missing
    """
    load_dotenv()
    
    required_vars = [
        'QUANTCONNECT_USER_ID',
        'QUANTCONNECT_API_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True


def get_environment_info() -> Dict[str, Any]:
    """
    Get information about the current environment.
    
    Returns:
        Dict[str, Any]: Environment information
    """
    load_dotenv()
    
    return {
        'deployment_env': os.getenv('DEPLOYMENT_ENV', 'development'),
        'api_url': os.getenv('QUANTCONNECT_API_URL', 'https://www.quantconnect.com/api/v2'),
        'api_timeout': os.getenv('API_TIMEOUT', '30'),
        'max_retries': os.getenv('API_MAX_RETRIES', '3'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'enable_metrics': os.getenv('ENABLE_METRICS', 'true'),
        'debug_mode': os.getenv('DEBUG_MODE', 'false'),
        'working_directory': str(Path.cwd()),
        'python_path': os.getenv('PYTHONPATH', ''),
        'path_separator': os.pathsep
    }