"""
Pytest configuration and fixtures for unified deployment pipeline tests.

Provides common test fixtures, mock data, and test configuration.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, Optional
import os
import sys

# Add src directory to Python path for tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.deployment.config import DeploymentConfig, Credentials, EnvironmentConfig, Environment
from src.deployment.orchestrator import PipelineState, PipelineStep
from src.deployment.progress import ProgressUpdate
from src.utils.logger import get_logger


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_algorithm_file(temp_dir):
    """Create a sample algorithm file for testing."""
    algorithm_content = '''
# Sample Trading Algorithm
from AlgorithmImports import *

class SampleAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2021, 1, 1)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)
        
    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)
'''
    
    algorithm_file = temp_dir / "sample_algorithm.py"
    algorithm_file.write_text(algorithm_content.strip())
    return algorithm_file


@pytest.fixture
def sample_csharp_algorithm_file(temp_dir):
    """Create a sample C# algorithm file for testing."""
    algorithm_content = '''
using QuantConnect.Algorithm;
using QuantConnect.Data;

namespace QuantConnect.Algorithm.CSharp
{
    public class SampleAlgorithm : QCAlgorithm
    {
        public override void Initialize()
        {
            SetStartDate(2020, 1, 1);
            SetEndDate(2021, 1, 1);
            SetCash(100000);
            AddEquity("SPY", Resolution.Daily);
        }
        
        public override void OnData(Slice data)
        {
            if (!Portfolio.Invested)
            {
                SetHoldings("SPY", 1);
            }
        }
    }
}
'''
    
    algorithm_file = temp_dir / "SampleAlgorithm.cs"
    algorithm_file.write_text(algorithm_content.strip())
    return algorithm_file


@pytest.fixture
def test_credentials():
    """Create test credentials."""
    return Credentials(
        user_id="123456",
        api_token="test_api_token_12345",
        organization_id="test_org_789"
    )


@pytest.fixture
def test_environment_config():
    """Create test environment configuration."""
    return EnvironmentConfig(
        environment=Environment.DEVELOPMENT,
        api_base_url="https://test.quantconnect.com/api/v2",
        timeout=10,
        max_retries=2,
        enable_metrics=True,
        debug_mode=True
    )


@pytest.fixture
def test_deployment_config(sample_algorithm_file):
    """Create test deployment configuration."""
    return DeploymentConfig(
        algorithm_file_path=str(sample_algorithm_file),
        project_name="Test Project",
        backtest_name="Test Backtest",
        backtest_parameters={"ema_fast": 10, "ema_slow": 20},
        cleanup_test_projects=True,
        verbose_logging=True
    )


@pytest.fixture
def mock_quantconnect_responses():
    """Mock QuantConnect API responses."""
    return {
        "projects_create": {
            "projects": [{
                "id": 12345,
                "name": "Test Project",
                "language": "Python",
                "created": "2023-01-01T00:00:00Z"
            }]
        },
        "files_create": {
            "success": True,
            "file": {
                "name": "main.py",
                "size": 1024,
                "created": "2023-01-01T00:00:00Z"
            }
        },
        "compile_create": {
            "compileId": "test_compile_123",
            "state": "InQueue"
        },
        "compile_success": {
            "compileId": "test_compile_123",
            "state": "Build Success",
            "errors": []
        },
        "compile_error": {
            "compileId": "test_compile_123",
            "state": "Build Error",
            "errors": ["Test error message"]
        },
        "backtests_create": {
            "backtestId": "test_backtest_456",
            "name": "Test Backtest",
            "state": "InQueue"
        },
        "backtest_completed": {
            "backtestId": "test_backtest_456",
            "name": "Test Backtest",
            "state": "Completed",
            "progress": 100,
            "statistics": {
                "totalreturn": "15.5%",
                "sharperatio": "1.23",
                "maxdrawdown": "-5.2%",
                "winrate": "0.65",
                "totaltrades": 125
            }
        },
        "backtest_error": {
            "backtestId": "test_backtest_456",
            "name": "Test Backtest",
            "state": "Error",
            "error": "Test backtest error"
        },
        "projects_list": {
            "projects": [
                {
                    "id": 12345,
                    "name": "Test Project",
                    "language": "Python"
                }
            ]
        }
    }


@pytest.fixture
def mock_api_client():
    """Create a mock QuantConnect API client."""
    client = Mock()
    client.test_connection.return_value = True
    client.get_api_metrics.return_value = {
        "total_requests": 10,
        "successful_requests": 8,
        "failed_requests": 2,
        "success_rate": 0.8
    }
    return client


@pytest.fixture
def pipeline_state():
    """Create a test pipeline state."""
    return PipelineState(
        deployment_id="test-deployment-123",
        current_step=PipelineStep.INITIALIZING,
        progress_percentage=0
    )


@pytest.fixture
def progress_update():
    """Create a test progress update."""
    return ProgressUpdate(
        step="TEST_STEP",
        message="Test progress message",
        progress_percentage=50,
        details={"test": "data"}
    )


@pytest.fixture
def mock_env_file(temp_dir):
    """Create a mock .env file."""
    env_content = '''
QUANTCONNECT_USER_ID=123456
QUANTCONNECT_API_TOKEN=test_api_token_12345
QUANTCONNECT_ORGANIZATION_ID=test_org_789
DEPLOYMENT_ENV=development
API_TIMEOUT=30
API_MAX_RETRIES=3
LOG_LEVEL=INFO
ENABLE_METRICS=true
DEBUG_MODE=false
'''
    
    env_file = temp_dir / ".env"
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def invalid_algorithm_file(temp_dir):
    """Create an invalid algorithm file for testing error cases."""
    invalid_content = '''
# Invalid algorithm with syntax error
from AlgorithmImports import *

class InvalidAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        # Missing closing parenthesis - syntax error
        self.SetEndDate(2021, 1, 1
        
    def OnData(self, data):
        pass
'''
    
    algorithm_file = temp_dir / "invalid_algorithm.py"
    algorithm_file.write_text(invalid_content.strip())
    return algorithm_file


@pytest.fixture
def large_algorithm_file(temp_dir):
    """Create a large algorithm file for testing size limits."""
    large_content = "# Large algorithm file\n" * 10000  # ~200KB
    
    algorithm_file = temp_dir / "large_algorithm.py"
    algorithm_file.write_text(large_content)
    return algorithm_file


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment for all tests."""
    # Set test environment variables
    monkeypatch.setenv("DEPLOYMENT_ENV", "testing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENABLE_METRICS", "true")
    
    # Disable actual logging during tests
    logger = get_logger(__name__)
    logger.logger.handlers.clear()


@pytest.fixture
def mock_requests_session():
    """Create a mock requests session."""
    session = Mock()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"success": True}
    response.headers = {"content-type": "application/json"}
    session.request.return_value = response
    return session


class MockProgressMonitor:
    """Mock progress monitor for testing."""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.updates = []
    
    def update_progress(self, progress_update):
        """Mock progress update."""
        self.updates.append(progress_update)
        if self.callback:
            self.callback(progress_update)
    
    def get_updates(self):
        """Get all progress updates."""
        return self.updates


@pytest.fixture
def mock_progress_monitor():
    """Create a mock progress monitor."""
    return MockProgressMonitor()


# Test data generators
def generate_test_backtest_results():
    """Generate test backtest results."""
    return {
        "backtestId": "test_backtest_123",
        "name": "Test Backtest",
        "state": "Completed",
        "progress": 100,
        "statistics": {
            "totalreturn": "12.5%",
            "sharperatio": "1.15",
            "maxdrawdown": "-4.8%",
            "winrate": "0.62",
            "totaltrades": 98,
            "averagewin": "2.1%",
            "averageloss": "-1.3%",
            "profitfactor": "1.8",
            "sortino": "1.45"
        },
        "performance": {
            "equity": [100000, 102500, 105000, 112500],
            "drawdown": [0, -0.5, -1.2, -4.8],
            "dates": ["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01"]
        }
    }


def generate_test_compilation_errors():
    """Generate test compilation errors."""
    return [
        "error CS0103: The name 'UndefinedMethod' does not exist in the current context",
        "error CS0029: Cannot implicitly convert type 'string' to 'double'",
        "warning CS0168: The variable 'unused' is declared but never used"
    ]


# Custom pytest markers
pytest_plugins = []

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "cli: mark test as a CLI test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as requiring API access"
    )