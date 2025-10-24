"""
Unit tests for configuration management.

Tests DeploymentConfig, Credentials, and environment configuration.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.deployment.config import (
    DeploymentConfig, Credentials, EnvironmentConfig, Environment,
    load_credentials, create_deployment_config,
    load_environment_config, save_config_to_file,
    load_config_from_file, validate_environment
)


class TestCredentials:
    """Test Credentials class."""
    
    def test_valid_credentials(self):
        """Test creating valid credentials."""
        creds = Credentials(
            user_id="123456",
            api_token="test_token_123",
            organization_id="org_789"
        )
        
        assert creds.user_id == "123456"
        assert creds.api_token == "test_token_123"
        assert creds.organization_id == "org_789"
    
    def test_credentials_without_org(self):
        """Test creating credentials without organization ID."""
        creds = Credentials(
            user_id="123456",
            api_token="test_token_123"
        )
        
        assert creds.user_id == "123456"
        assert creds.api_token == "test_token_123"
        assert creds.organization_id is None
    
    def test_invalid_user_id_empty(self):
        """Test credentials with empty user ID."""
        with pytest.raises(ValueError, match="QUANTCONNECT_USER_ID cannot be empty"):
            Credentials(user_id="", api_token="test_token")
    
    def test_invalid_user_id_spaces(self):
        """Test credentials with whitespace-only user ID."""
        with pytest.raises(ValueError, match="QUANTCONNECT_USER_ID cannot be empty"):
            Credentials(user_id="   ", api_token="test_token")
    
    def test_invalid_user_id_non_numeric(self):
        """Test credentials with non-numeric user ID."""
        with pytest.raises(ValueError, match="QUANTCONNECT_USER_ID must be numeric"):
            Credentials(user_id="abc123", api_token="test_token")
    
    def test_invalid_api_token_empty(self):
        """Test credentials with empty API token."""
        with pytest.raises(ValueError, match="QUANTCONNECT_API_TOKEN cannot be empty"):
            Credentials(user_id="123456", api_token="")
    
    def test_invalid_api_token_spaces(self):
        """Test credentials with whitespace-only API token."""
        with pytest.raises(ValueError, match="QUANTCONNECT_API_TOKEN cannot be empty"):
            Credentials(user_id="123456", api_token="   ")
    
    def test_auth_headers(self):
        """Test authentication header generation."""
        creds = Credentials(
            user_id="123456",
            api_token="test_token_123"
        )
        
        headers = creds.get_auth_headers()
        
        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Content-Type"] == "application/json"
        assert "Timestamp" not in headers  # Not in basic auth headers


class TestDeploymentConfig:
    """Test DeploymentConfig class."""
    
    def test_valid_config(self, sample_algorithm_file):
        """Test creating valid deployment configuration."""
        config = DeploymentConfig(
            algorithm_file_path=str(sample_algorithm_file),
            project_name="Test Project",
            backtest_name="Test Backtest",
            backtest_parameters={"param1": "value1"},
            cleanup_test_projects=False,
            verbose_logging=True
        )
        
        assert config.algorithm_file_path == str(sample_algorithm_file)
        assert config.project_name == "Test Project"
        assert config.backtest_name == "Test Backtest"
        assert config.backtest_parameters == {"param1": "value1"}
        assert config.cleanup_test_projects is False
        assert config.verbose_logging is True
    
    def test_default_config(self, sample_algorithm_file):
        """Test creating deployment config with defaults."""
        config = DeploymentConfig(
            algorithm_file_path=str(sample_algorithm_file)
        )
        
        assert config.algorithm_file_path == str(sample_algorithm_file)
        assert config.project_name is None
        assert config.backtest_name == "Automated Backtest"
        assert config.backtest_parameters == {}
        assert config.cleanup_test_projects is True
        assert config.verbose_logging is False
    
    def test_invalid_algorithm_file_not_found(self):
        """Test config with non-existent algorithm file."""
        with pytest.raises(FileNotFoundError, match="Algorithm file not found"):
            DeploymentConfig(algorithm_file_path="/nonexistent/file.py")
    
    def test_invalid_algorithm_file_is_directory(self, temp_dir):
        """Test config with directory instead of file."""
        with pytest.raises(ValueError, match="Algorithm path is not a file"):
            DeploymentConfig(algorithm_file_path=str(temp_dir))
    
    def test_invalid_backtest_parameters(self, sample_algorithm_file):
        """Test config with non-serializable backtest parameters."""
        class UnserializableObject:
            pass
        
        with pytest.raises(ValueError, match="Backtest parameters must be JSON serializable"):
            DeploymentConfig(
                algorithm_file_path=str(sample_algorithm_file),
                backtest_parameters={"invalid": UnserializableObject()}
            )


class TestEnvironmentConfig:
    """Test EnvironmentConfig class."""
    
    def test_valid_config(self):
        """Test creating valid environment configuration."""
        config = EnvironmentConfig(
            environment=Environment.PRODUCTION,
            api_base_url="https://api.quantconnect.com/v2",
            timeout=60,
            max_retries=5,
            enable_metrics=False,
            debug_mode=False
        )
        
        assert config.environment == Environment.PRODUCTION
        assert config.api_base_url == "https://api.quantconnect.com/v2"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.enable_metrics is False
        assert config.debug_mode is False
    
    def test_default_config(self):
        """Test creating environment config with defaults."""
        config = EnvironmentConfig(
            environment=Environment.DEVELOPMENT,
            api_base_url="https://test.quantconnect.com/v2"
        )
        
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.enable_metrics is True
        assert config.debug_mode is False
    
    def test_invalid_api_base_url_empty(self):
        """Test config with empty API base URL."""
        with pytest.raises(ValueError, match="API base URL cannot be empty"):
            EnvironmentConfig(
                environment=Environment.DEVELOPMENT,
                api_base_url=""
            )
    
    def test_invalid_api_base_url_no_protocol(self):
        """Test config with API base URL missing protocol."""
        with pytest.raises(ValueError, match="API base URL must start with http:// or https://"):
            EnvironmentConfig(
                environment=Environment.DEVELOPMENT,
                api_base_url="api.quantconnect.com/v2"
            )
    
    def test_invalid_timeout(self):
        """Test config with invalid timeout."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            EnvironmentConfig(
                environment=Environment.DEVELOPMENT,
                api_base_url="https://test.quantconnect.com/v2",
                timeout=0
            )
    
    def test_invalid_max_retries(self):
        """Test config with invalid max retries."""
        with pytest.raises(ValueError, match="Max retries cannot be negative"):
            EnvironmentConfig(
                environment=Environment.DEVELOPMENT,
                api_base_url="https://test.quantconnect.com/v2",
                max_retries=-1
            )


class TestConfigFunctions:
    """Test configuration utility functions."""
    
    @patch.dict('os.environ', {
        'QUANTCONNECT_USER_ID': '123456',
        'QUANTCONNECT_API_TOKEN': 'test_token_123',
        'QUANTCONNECT_ORGANIZATION_ID': 'org_789'
    })
    def test_load_credentials_success(self):
        """Test successful credential loading."""
        creds = load_credentials()
        
        assert creds.user_id == "123456"
        assert creds.api_token == "test_token_123"
        assert creds.organization_id == "org_789"
    
    @patch('src.deployment.config.load_dotenv')
    @patch.dict('os.environ', {}, clear=True)
    def test_load_credentials_missing_user_id(self, mock_load_dotenv):
        """Test credential loading with missing user ID."""
        with pytest.raises(ValueError, match="Missing QUANTCONNECT_USER_ID in environment variables"):
            load_credentials()
    
    @patch('src.deployment.config.load_dotenv')
    @patch.dict('os.environ', {
        'QUANTCONNECT_USER_ID': '123456'
    }, clear=True)
    def test_load_credentials_missing_api_token(self, mock_load_dotenv):
        """Test credential loading with missing API token."""
        with pytest.raises(ValueError, match="Missing QUANTCONNECT_API_TOKEN in environment variables"):
            load_credentials()
    
    def test_create_deployment_config_success(self, sample_algorithm_file):
        """Test successful deployment config creation."""
        config = create_deployment_config(
            algorithm_file_path=str(sample_algorithm_file),
            project_name="Test Project",
            backtest_name="Custom Backtest",
            backtest_parameters='{"param1": "value1", "param2": 42}',
            cleanup_test_projects=False,
            verbose_logging=True
        )
        
        assert isinstance(config, DeploymentConfig)
        assert config.project_name == "Test Project"
        assert config.backtest_name == "Custom Backtest"
        assert config.backtest_parameters == {"param1": "value1", "param2": 42}
        assert config.cleanup_test_projects is False
        assert config.verbose_logging is True
    
    def test_create_deployment_config_invalid_json(self, sample_algorithm_file):
        """Test deployment config creation with invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON in backtest parameters"):
            create_deployment_config(
                algorithm_file_path=str(sample_algorithm_file),
                backtest_parameters='{"invalid": json}'
            )
    
    @patch.dict('os.environ', {
        'DEPLOYMENT_ENV': 'production',
        'QUANTCONNECT_API_URL': 'https://api.quantconnect.com/v2',
        'API_TIMEOUT': '60',
        'API_MAX_RETRIES': '5',
        'LOG_LEVEL': 'ERROR',
        'ENABLE_METRICS': 'false',
        'DEBUG_MODE': 'true'
    })
    def test_load_environment_config_success(self):
        """Test successful environment config loading."""
        config = load_environment_config()
        
        assert config.environment.value == "production"
        assert config.api_base_url == "https://api.quantconnect.com/v2"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.enable_metrics is False
        assert config.debug_mode is True
    
    @patch.dict('os.environ', {
        'DEPLOYMENT_ENV': 'invalid_env'
    })
    def test_load_environment_config_invalid_env(self):
        """Test environment config loading with invalid environment."""
        with pytest.raises(ValueError, match="Invalid DEPLOYMENT_ENV"):
            load_environment_config()
    
    def test_save_config_to_file(self, temp_dir):
        """Test saving configuration to file."""
        config_data = {
            "environment": "development",
            "api_base_url": "https://test.quantconnect.com/v2",
            "timeout": 30
        }
        
        config_file = temp_dir / "test_config.json"
        saved_path = save_config_to_file(config_data, config_file)
        
        assert saved_path == config_file
        assert config_file.exists()
        
        with open(config_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data == config_data
    
    def test_load_config_from_file(self, temp_dir):
        """Test loading configuration from file."""
        config_data = {
            "environment": "production",
            "api_base_url": "https://api.quantconnect.com/v2",
            "timeout": 60
        }
        
        config_file = temp_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        loaded_data = load_config_from_file(config_file)
        assert loaded_data == config_data
    
    def test_load_config_from_file_not_found(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/nonexistent/config.json")
    
    def test_load_config_from_file_invalid_json(self, temp_dir):
        """Test loading configuration from invalid JSON file."""
        config_file = temp_dir / "invalid.json"
        config_file.write_text("{ invalid json }")
        
        with pytest.raises(json.JSONDecodeError):
            load_config_from_file(config_file)
    
    @patch.dict('os.environ', {
        'QUANTCONNECT_USER_ID': '123456',
        'QUANTCONNECT_API_TOKEN': 'test_token'
    })
    def test_validate_environment_success(self):
        """Test successful environment validation."""
        assert validate_environment() is True
    
    @patch('src.deployment.config.load_dotenv')
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_environment_missing_vars(self, mock_load_dotenv):
        """Test environment validation with missing variables."""
        with pytest.raises(ValueError, match="Missing required environment variables: QUANTCONNECT_USER_ID, QUANTCONNECT_API_TOKEN"):
            validate_environment()


class TestConfigEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_credentials_with_none_values(self):
        """Test credentials with None values."""
        with pytest.raises(ValueError, match="QUANTCONNECT_USER_ID cannot be empty"):
            Credentials(user_id="", api_token="test_token")
        
        with pytest.raises(ValueError, match="QUANTCONNECT_API_TOKEN cannot be empty"):
            Credentials(user_id="123456", api_token="")
    
    def test_deployment_config_with_large_parameters(self, sample_algorithm_file):
        """Test deployment config with large parameter objects."""
        large_params = {
            "large_array": list(range(10000)),
            "nested_object": {
                "deep": {
                    "nested": {
                        "value": "test"
                    }
                }
            }
        }
        
        config = DeploymentConfig(
            algorithm_file_path=str(sample_algorithm_file),
            backtest_parameters=large_params
        )
        
        assert config.backtest_parameters == large_params
    
    def test_environment_config_with_url_parameters(self):
        """Test environment config with URL containing parameters."""
        config = EnvironmentConfig(
            environment=Environment.DEVELOPMENT,
            api_base_url="https://api.quantconnect.com/v2?version=2.0"
        )
        
        assert config.api_base_url == "https://api.quantconnect.com/v2?version=2.0"
    
    def test_config_file_creation_with_nested_dirs(self, temp_dir):
        """Test saving config file with nested directory creation."""
        nested_dir = temp_dir / "nested" / "config"
        config_file = nested_dir / "test.json"
        
        config_data = {"test": "data"}
        saved_path = save_config_to_file(config_data, config_file)
        
        assert saved_path == config_file
        assert config_file.exists()
        assert nested_dir.exists()