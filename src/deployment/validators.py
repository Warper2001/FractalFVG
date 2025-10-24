"""
Input Validation Framework for QuantConnect Deployment Pipeline.

Provides comprehensive validation for all input types including files,
parameters, API responses, and configuration data.
"""

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
import requests

from .config import DeploymentConfig, Credentials, EnvironmentConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """Validation error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Validation error categories."""
    FILE_VALIDATION = "file_validation"
    PARAMETER_VALIDATION = "parameter_validation"
    API_VALIDATION = "api_validation"
    CONFIGURATION_VALIDATION = "configuration_validation"
    SECURITY_VALIDATION = "security_validation"
    FORMAT_VALIDATION = "format_validation"


@dataclass
class ValidationError:
    """Structured validation error information."""
    category: ValidationCategory
    severity: ValidationSeverity
    field: str
    message: str
    value: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"[{self.category.value}] {self.field}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has any errors."""
        return len(self.errors or []) > 0
    
    @property
    def has_critical_errors(self) -> bool:
        """Check if validation has critical errors."""
        return any(error.severity == ValidationSeverity.CRITICAL for error in self.errors or [])
    
    @property
    def error_count(self) -> int:
        """Get total error count."""
        return len(self.errors or [])
    
    @property
    def critical_error_count(self) -> int:
        """Get critical error count."""
        return sum(1 for error in self.errors or [] if error.severity == ValidationSeverity.CRITICAL)
    
    def add_error(self, error: ValidationError):
        """Add a validation error."""
        if self.errors is None:
            self.errors = []
        self.errors.append(error)
        if error.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False
    
    def get_errors_by_category(self, category: ValidationCategory) -> List[ValidationError]:
        """Get errors by category."""
        return [error for error in self.errors or [] if error.category == category]
    
    def get_errors_by_severity(self, severity: ValidationSeverity) -> List[ValidationError]:
        """Get errors by severity."""
        return [error for error in self.errors or [] if error.severity == severity]


class BaseValidator:
    """Base validator class with common functionality."""
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: Whether to enforce strict validation rules
        """
        self.strict_mode = strict_mode
    
    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """
        Validate a value.
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            
        Returns:
            ValidationResult with validation details
        """
        raise NotImplementedError("Subclasses must implement validate method")
    
    def _create_error(self, category: ValidationCategory, severity: ValidationSeverity,
                     field: str, message: str, value: Any = None, 
                     context: Optional[Dict[str, Any]] = None) -> ValidationError:
        """Create a validation error."""
        return ValidationError(
            category=category,
            severity=severity,
            field=field,
            message=message,
            value=value,
            context=context
        )


class FileValidator(BaseValidator):
    """Validator for file paths and file contents."""
    
    def __init__(self, strict_mode: bool = False, 
                 allowed_extensions: Optional[List[str]] = None,
                 max_file_size: Optional[int] = None):
        """
        Initialize file validator.
        
        Args:
            strict_mode: Whether to enforce strict validation rules
            allowed_extensions: List of allowed file extensions
            max_file_size: Maximum file size in bytes
        """
        super().__init__(strict_mode)
        self.allowed_extensions = allowed_extensions
        self.max_file_size = max_file_size
    
    def validate(self, value: Any, field_name: str = "file_path") -> ValidationResult:
        """
        Validate file path and file properties.
        
        Args:
            value: Path to file to validate
            field_name: Name of the field being validated
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Convert to Path object
        try:
            path = Path(value)
        except Exception as e:
            result.add_error(self._create_error(
                ValidationCategory.FILE_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                f"Invalid file path: {str(e)}",
                value
            ))
            return result
        
        # Check if path exists
        if not path.exists():
            result.add_error(self._create_error(
                ValidationCategory.FILE_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                "File does not exist",
                str(path)
            ))
            return result
        
        # Check if it's a file
        if not path.is_file():
            result.add_error(self._create_error(
                ValidationCategory.FILE_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                "Path is not a file",
                str(path)
            ))
            return result
        
        # Check file extension
        if self.allowed_extensions:
            extension = path.suffix.lower()
            if extension not in self.allowed_extensions:
                result.add_error(self._create_error(
                    ValidationCategory.FILE_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    f"File extension '{extension}' not allowed. Allowed: {self.allowed_extensions}",
                    str(path)
                ))
        
        # Check file size
        if self.max_file_size:
            try:
                file_size = path.stat().st_size
                if file_size > self.max_file_size:
                    result.add_error(self._create_error(
                        ValidationCategory.FILE_VALIDATION,
                        ValidationSeverity.WARNING,
                        field_name,
                        f"File size ({file_size} bytes) exceeds recommended limit ({self.max_file_size} bytes)",
                        str(path)
                    ))
            except Exception as e:
                result.add_error(self._create_error(
                    ValidationCategory.FILE_VALIDATION,
                    ValidationSeverity.WARNING,
                    field_name,
                    f"Could not check file size: {str(e)}",
                    str(path)
                ))
        
        # Check file readability
        try:
            with open(path, 'r', encoding='utf-8') as f:
                f.read(1)  # Try to read first character
        except UnicodeDecodeError:
            result.add_error(self._create_error(
                ValidationCategory.FILE_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                "File is not valid UTF-8 text",
                str(path)
            ))
        except Exception as e:
            result.add_error(self._create_error(
                ValidationCategory.FILE_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                f"File is not readable: {str(e)}",
                str(path)
            ))
        
        return result


class ParameterValidator(BaseValidator):
    """Validator for parameters and configuration values."""
    
    def __init__(self, strict_mode: bool = False):
        """Initialize parameter validator."""
        super().__init__(strict_mode)
    
    def validate_string(self, value: Any, field_name: str, 
                       min_length: int = 0, max_length: Optional[int] = None,
                       pattern: Optional[str] = None, required: bool = True) -> ValidationResult:
        """
        Validate string parameter.
        
        Args:
            value: Value to validate
            field_name: Name of the field
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regex pattern to match
            required: Whether the field is required
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Check if value is provided
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                result.add_error(self._create_error(
                    ValidationCategory.PARAMETER_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    "Required field is missing or empty"
                ))
            return result
        
        # Convert to string if needed
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception:
                result.add_error(self._create_error(
                    ValidationCategory.PARAMETER_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    "Value cannot be converted to string"
                ))
                return result
        
        # Check length
        if len(value) < min_length:
            result.add_error(self._create_error(
                ValidationCategory.PARAMETER_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                f"String length ({len(value)}) is less than minimum ({min_length})"
            ))
        
        if max_length and len(value) > max_length:
            result.add_error(self._create_error(
                ValidationCategory.PARAMETER_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                f"String length ({len(value)}) exceeds maximum ({max_length})"
            ))
        
        # Check pattern
        if pattern:
            if not re.match(pattern, value):
                result.add_error(self._create_error(
                    ValidationCategory.PARAMETER_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    f"String does not match required pattern: {pattern}"
                ))
        
        return result
    
    def validate_numeric(self, value: Any, field_name: str,
                        min_value: Optional[Union[int, float]] = None,
                        max_value: Optional[Union[int, float]] = None,
                        required: bool = True) -> ValidationResult:
        """
        Validate numeric parameter.
        
        Args:
            value: Value to validate
            field_name: Name of the field
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            required: Whether the field is required
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Check if value is provided
        if value is None:
            if required:
                result.add_error(self._create_error(
                    ValidationCategory.PARAMETER_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    "Required field is missing"
                ))
            return result
        
        # Check if value is numeric
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                result.add_error(self._create_error(
                    ValidationCategory.PARAMETER_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    "Value must be numeric"
                ))
                return result
        
        # Check range
        if min_value is not None and value < min_value:
            result.add_error(self._create_error(
                ValidationCategory.PARAMETER_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                f"Value ({value}) is less than minimum ({min_value})"
            ))
        
        if max_value is not None and value > max_value:
            result.add_error(self._create_error(
                ValidationCategory.PARAMETER_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                f"Value ({value}) exceeds maximum ({max_value})"
            ))
        
        return result
    
    def validate_json(self, value: Any, field_name: str, required: bool = True) -> ValidationResult:
        """
        Validate JSON parameter.
        
        Args:
            value: Value to validate
            field_name: Name of the field
            required: Whether the field is required
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Check if value is provided
        if value is None:
            if required:
                result.add_error(self._create_error(
                    ValidationCategory.PARAMETER_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    "Required field is missing"
                ))
            return result
        
        # If it's already a dict, it's valid JSON
        if isinstance(value, dict):
            return result
        
        # Try to parse JSON string
        if isinstance(value, str):
            try:
                json.loads(value)
            except json.JSONDecodeError as e:
                result.add_error(self._create_error(
                    ValidationCategory.PARAMETER_VALIDATION,
                    ValidationSeverity.ERROR,
                    field_name,
                    f"Invalid JSON: {str(e)}"
                ))
        else:
            result.add_error(self._create_error(
                ValidationCategory.PARAMETER_VALIDATION,
                ValidationSeverity.ERROR,
                field_name,
                "Value must be a JSON string or dictionary"
            ))
        
        return result


class APIValidator(BaseValidator):
    """Validator for API responses and requests."""
    
    def __init__(self, strict_mode: bool = False):
        """Initialize API validator."""
        super().__init__(strict_mode)
    
    def validate_response(self, response: requests.Response, 
                         expected_status_codes: Optional[List[int]] = None) -> ValidationResult:
        """
        Validate HTTP response.
        
        Args:
            response: HTTP response object
            expected_status_codes: List of expected status codes
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        if expected_status_codes is None:
            expected_status_codes = [200]
        
        # Check status code
        if response.status_code not in expected_status_codes:
            severity = ValidationSeverity.ERROR if response.status_code >= 400 else ValidationSeverity.WARNING
            result.add_error(self._create_error(
                ValidationCategory.API_VALIDATION,
                severity,
                "status_code",
                f"Unexpected status code: {response.status_code}. Expected: {expected_status_codes}",
                response.status_code
            ))
        
        # Check response content type
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            # Try to parse JSON
            try:
                response.json()
            except ValueError as e:
                result.add_error(self._create_error(
                    ValidationCategory.API_VALIDATION,
                    ValidationSeverity.ERROR,
                    "response_body",
                    f"Invalid JSON response: {str(e)}"
                ))
        
        # Check response size
        content_length = response.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                if size > 10 * 1024 * 1024:  # 10MB
                    result.add_error(self._create_error(
                        ValidationCategory.API_VALIDATION,
                        ValidationSeverity.WARNING,
                        "response_size",
                        f"Large response size: {size} bytes"
                    ))
            except ValueError:
                pass
        
        return result


class ConfigurationValidator(BaseValidator):
    """Validator for configuration objects."""
    
    def __init__(self, strict_mode: bool = False):
        """Initialize configuration validator."""
        super().__init__(strict_mode)
        self.file_validator = FileValidator(strict_mode)
        self.param_validator = ParameterValidator(strict_mode)
    
    def validate_deployment_config(self, config: DeploymentConfig) -> ValidationResult:
        """
        Validate deployment configuration.
        
        Args:
            config: Deployment configuration to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Validate algorithm file
        file_result = self.file_validator.validate(config.algorithm_file_path, "algorithm_file_path")
        result.errors.extend(file_result.errors)
        if not file_result.is_valid:
            result.is_valid = False
        
        # Validate project name
        if config.project_name:
            name_result = self.param_validator.validate_string(
                config.project_name, "project_name",
                min_length=1, max_length=100,
                pattern=r'^[a-zA-Z0-9_\-\s]+$'
            )
            result.errors.extend(name_result.errors)
            if not name_result.is_valid:
                result.is_valid = False
        
        # Validate backtest name
        backtest_result = self.param_validator.validate_string(
            config.backtest_name, "backtest_name",
            min_length=1, max_length=100
        )
        result.errors.extend(backtest_result.errors)
        if not backtest_result.is_valid:
            result.is_valid = False
        
        # Validate backtest parameters
        params_result = self.param_validator.validate_json(
            config.backtest_parameters, "backtest_parameters"
        )
        result.errors.extend(params_result.errors)
        if not params_result.is_valid:
            result.is_valid = False
        
        return result
    
    def validate_credentials(self, credentials: Credentials) -> ValidationResult:
        """
        Validate credentials.
        
        Args:
            credentials: Credentials to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Validate user ID
        user_id_result = self.param_validator.validate_string(
            credentials.user_id, "user_id",
            min_length=1, max_length=50,
            pattern=r'^\d+$'  # Must be numeric
        )
        result.errors.extend(user_id_result.errors)
        if not user_id_result.is_valid:
            result.is_valid = False
        
        # Validate API token
        token_result = self.param_validator.validate_string(
            credentials.api_token, "api_token",
            min_length=10, max_length=500
        )
        result.errors.extend(token_result.errors)
        if not token_result.is_valid:
            result.is_valid = False
        
        # Validate organization ID (if provided)
        if credentials.organization_id:
            org_result = self.param_validator.validate_string(
                credentials.organization_id, "organization_id",
                min_length=1, max_length=50
            )
            result.errors.extend(org_result.errors)
            if not org_result.is_valid:
                result.is_valid = False
        
        return result


class ValidationEngine:
    """Main validation engine that coordinates all validators."""
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validation engine.
        
        Args:
            strict_mode: Whether to enforce strict validation rules
        """
        self.strict_mode = strict_mode
        self.file_validator = FileValidator(strict_mode)
        self.param_validator = ParameterValidator(strict_mode)
        self.api_validator = APIValidator(strict_mode)
        self.config_validator = ConfigurationValidator(strict_mode)
    
    def validate_all(self, config: DeploymentConfig, 
                    credentials: Credentials) -> ValidationResult:
        """
        Validate all configuration and credentials.
        
        Args:
            config: Deployment configuration
            credentials: API credentials
            
        Returns:
            ValidationResult with all validation details
        """
        result = ValidationResult(is_valid=True)
        
        # Validate configuration
        config_result = self.config_validator.validate_deployment_config(config)
        result.errors.extend(config_result.errors)
        
        # Validate credentials
        cred_result = self.config_validator.validate_credentials(credentials)
        result.errors.extend(cred_result.errors)
        
        # Update overall validity
        result.is_valid = config_result.is_valid and cred_result.is_valid
        
        # Log validation results
        if result.is_valid:
            logger.info("All validation checks passed")
        else:
            logger.warning(f"Validation failed with {result.error_count} errors")
            for error in result.errors:
                if error.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
                    logger.error(f"Validation error: {error}")
        
        return result
    
    def validate_file(self, file_path: Union[str, Path], 
                     field_name: str = "file_path") -> ValidationResult:
        """Validate a single file."""
        return self.file_validator.validate(file_path, field_name)
    
    def validate_api_response(self, response: requests.Response,
                             expected_status_codes: Optional[List[int]] = None) -> ValidationResult:
        """Validate API response."""
        return self.api_validator.validate_response(response, expected_status_codes)


# Global validation engine instance
_default_validator: Optional[ValidationEngine] = None


def get_validator(strict_mode: bool = False) -> ValidationEngine:
    """Get or create default validation engine."""
    global _default_validator
    if _default_validator is None:
        _default_validator = ValidationEngine(strict_mode)
    return _default_validator


def validate_deployment_inputs(config: DeploymentConfig, 
                              credentials: Credentials,
                              strict_mode: bool = False) -> ValidationResult:
    """
    Convenience function to validate all deployment inputs.
    
    Args:
        config: Deployment configuration
        credentials: API credentials
        strict_mode: Whether to enforce strict validation
        
    Returns:
        ValidationResult with validation details
    """
    validator = get_validator(strict_mode)
    return validator.validate_all(config, credentials)