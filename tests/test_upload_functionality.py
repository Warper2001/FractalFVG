"""
Tests for algorithm upload functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.models.algorithm import Algorithm, AlgorithmFile, AlgorithmStatus
from src.automation.upload.validation import AlgorithmValidator, ValidationResult
from src.automation.upload.algorithm_uploader import AlgorithmUploader


class TestAlgorithmValidator:
    """Test algorithm validation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = AlgorithmValidator()
    
    def test_validate_basic_algorithm(self):
        """Test basic algorithm validation."""
        # Create a simple Python algorithm
        algorithm = Algorithm(
            name="Test Algorithm",
            description="Test algorithm for validation",
            language="Py",
            files=[
                AlgorithmFile(
                    name="main.py",
                    content="""
from AlgorithmImports import *

class TestAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2020, 12, 31)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)
    
    def OnData(self, data):
        pass
""",
                    size=200,
                    is_main=True
                )
            ],
            status=AlgorithmStatus.DRAFT
        )
        
        result = self.validator.validate_algorithm(algorithm)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert "algorithm_classes" in result.metadata
        assert result.metadata["algorithm_classes"] == 1
    
    def test_validate_missing_required_methods(self):
        """Test validation fails with missing required methods."""
        algorithm = Algorithm(
            name="Invalid Algorithm",
            description="Algorithm missing required methods",
            language="Py",
            files=[
                AlgorithmFile(
                    name="main.py",
                    content="""
from AlgorithmImports import *

class TestAlgorithm(QCAlgorithm):
    def Initialize(self):
        pass
# Missing OnData method
""",
                    size=100,
                    is_main=True
                )
            ],
            status=AlgorithmStatus.DRAFT
        )
        
        result = self.validator.validate_algorithm(algorithm)
        
        assert not result.is_valid
        assert any("Missing required method: OnData" in error for error in result.errors)
    
    def test_validate_no_qc_algorithm_class(self):
        """Test validation fails without QCAlgorithm class."""
        algorithm = Algorithm(
            name="No QC Algorithm",
            description="Algorithm without QCAlgorithm inheritance",
            language="Py",
            files=[
                AlgorithmFile(
                    name="main.py",
                    content="""
class RegularClass:
    def Initialize(self):
        pass
    
    def OnData(self, data):
        pass
""",
                    size=100,
                    is_main=True
                )
            ],
            status=AlgorithmStatus.DRAFT
        )
        
        result = self.validator.validate_algorithm(algorithm)
        
        assert not result.is_valid
        assert any("No QCAlgorithm class found" in error for error in result.errors)


class TestAlgorithmUploader:
    """Test algorithm uploader."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.uploader = AlgorithmUploader()
    
    @patch('src.automation.upload.algorithm_uploader.get_quantconnect_credential_manager')
    @patch('src.automation.upload.algorithm_uploader.QuantConnectAPIClient')
    def test_initialization_with_credentials(self, mock_api_client, mock_cred_manager):
        """Test uploader initialization with valid credentials."""
        # Mock credentials
        mock_cred_manager.return_value.get_quantconnect_credentials.return_value = (
            "test_user_id", "test_api_token", "test_org_id"
        )
        
        uploader = AlgorithmUploader()
        
        assert uploader.api_client is not None
        mock_api_client.assert_called_once_with(
            user_id="test_user_id",
            api_token="test_api_token",
            organization_id="test_org_id"
        )
    
    @patch('src.automation.upload.algorithm_uploader.get_quantconnect_credential_manager')
    def test_initialization_without_credentials(self, mock_cred_manager):
        """Test uploader initialization fails without credentials."""
        # Mock no credentials
        mock_cred_manager.return_value.get_quantconnect_credentials.return_value = (
            None, None, None
        )
        
        with pytest.raises(ValueError, match="QuantConnect credentials not found"):
            AlgorithmUploader()
    
    def test_upload_algorithm_without_api_client(self):
        """Test upload fails without API client."""
        uploader = AlgorithmUploader()
        uploader.api_client = None
        
        algorithm = Algorithm(
            name="Test",
            description="Test",
            language="Py",
            files=[],
            status=AlgorithmStatus.DRAFT
        )
        
        with pytest.raises(RuntimeError, match="API client not initialized"):
            uploader.upload_algorithm(algorithm)


class TestIntegration:
    """Integration tests for upload functionality."""
    
    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        validator = AlgorithmValidator()
        
        # Create valid algorithm
        algorithm = Algorithm(
            name="Integration Test Algorithm",
            description="Algorithm for integration testing",
            language="Py",
            files=[
                AlgorithmFile(
                    name="main.py",
                    content="""
from AlgorithmImports import *

class IntegrationTestAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2023, 12, 31)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)
        self.symbol = self.Symbol("SPY")
    
    def OnData(self, data):
        if self.symbol in data and data[self.symbol]:
            close_price = data[self.symbol].Close
            self.Debug(f"SPY Close: {close_price}")
""",
                    size=300,
                    is_main=True
                ),
                AlgorithmFile(
                    name="helpers.py",
                    content="""
# Helper functions for the algorithm
def calculate_sma(prices, period):
    return sum(prices[-period:]) / period if len(prices) >= period else None
""",
                    size=100,
                    is_main=False
                )
            ],
            status=AlgorithmStatus.DRAFT
        )
        
        result = validator.validate_algorithm(algorithm)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.metadata['total_files'] == 2
        assert result.metadata['main_files'] == 1
        assert 'SPY' in algorithm.files[0].content


if __name__ == "__main__":
    pytest.main([__file__])