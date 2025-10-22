"""
Backtest Parameter Manager

Manages backtest parameters, validation, and optimization.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """Parameter type enumeration."""
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    DATE = "date"
    LIST = "list"


@dataclass
class ParameterDefinition:
    """Definition of a backtest parameter."""
    name: str
    param_type: ParameterType
    default_value: Any
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""
    required: bool = True
    validation_regex: Optional[str] = None
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a parameter value against this definition.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check type
        if self.param_type == ParameterType.INTEGER:
            if not isinstance(value, int):
                try:
                    value = int(float(value))
                except (ValueError, TypeError):
                    return False, f"Parameter '{self.name}' must be an integer"
        elif self.param_type == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    return False, f"Parameter '{self.name}' must be a number"
        elif self.param_type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    try:
                        value = bool(value)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{self.name}' must be a boolean"
        elif self.param_type == ParameterType.STRING:
            if not isinstance(value, str):
                try:
                    value = str(value)
                except (ValueError, TypeError):
                    return False, f"Parameter '{self.name}' must be a string"
        elif self.param_type == ParameterType.DATE:
            if not isinstance(value, str):
                return False, f"Parameter '{self.name}' must be a date string"
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return False, f"Parameter '{self.name}' must be a valid ISO date"
        elif self.param_type == ParameterType.LIST:
            if not isinstance(value, list):
                return False, f"Parameter '{self.name}' must be a list"
        
        # Check min/max constraints
        if self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            if isinstance(value, (int, float)):
                if self.min_value is not None and value < self.min_value:
                    return False, f"Parameter '{self.name}' must be >= {self.min_value}"
                if self.max_value is not None and value > self.max_value:
                    return False, f"Parameter '{self.name}' must be <= {self.max_value}"
        
        # Check allowed values
        if self.allowed_values is not None and value not in self.allowed_values:
            return False, f"Parameter '{self.name}' must be one of {self.allowed_values}"
        
        # Check regex pattern
        if self.validation_regex and isinstance(value, str):
            import re
            if not re.match(self.validation_regex, value):
                return False, f"Parameter '{self.name}' does not match required pattern"
        
        return True, None


@dataclass
class ParameterSet:
    """A set of parameters for a backtest."""
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'parameters': self.parameters,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterSet':
        """Create from dictionary."""
        data = data.copy()
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class OptimizationRange:
    """Range definition for parameter optimization."""
    parameter_name: str
    start: Union[int, float]
    end: Union[int, float]
    step: Union[int, float]
    param_type: ParameterType = ParameterType.FLOAT
    
    def generate_values(self) -> List[Any]:
        """Generate all values in this range."""
        if self.param_type == ParameterType.INTEGER:
            return list(range(int(self.start), int(self.end) + 1, int(self.step)))
        else:
            values = []
            current = self.start
            while current <= self.end:
                values.append(round(current, 10))  # Avoid floating point precision issues
                current += self.step
            return values


class ParameterManager:
    """
    Manages backtest parameters, validation, and optimization.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize parameter manager.
        
        Args:
            config_file: Optional path to parameter configuration file
        """
        self.config_file = config_file or Path("parameter_config.json")
        self.parameter_definitions: Dict[str, ParameterDefinition] = {}
        self.parameter_sets: Dict[str, ParameterSet] = {}
        self.optimization_ranges: Dict[str, OptimizationRange] = {}
        
        # Load default parameter definitions
        self._load_default_definitions()
        
        # Load configuration if exists
        if self.config_file.exists():
            self.load_config()
    
    def _load_default_definitions(self):
        """Load default parameter definitions."""
        default_definitions = [
            ParameterDefinition(
                name="start_date",
                param_type=ParameterType.DATE,
                default_value="2024-01-01",
                description="Backtest start date (ISO format)",
                required=True
            ),
            ParameterDefinition(
                name="end_date",
                param_type=ParameterType.DATE,
                default_value="2024-12-31",
                description="Backtest end date (ISO format)",
                required=True
            ),
            ParameterDefinition(
                name="initial_cash",
                param_type=ParameterType.INTEGER,
                default_value=100000,
                min_value=1000,
                max_value=10000000,
                description="Initial cash amount",
                required=True
            ),
            ParameterDefinition(
                name="ema_fast",
                param_type=ParameterType.INTEGER,
                default_value=10,
                min_value=1,
                max_value=100,
                description="Fast EMA period",
                required=False
            ),
            ParameterDefinition(
                name="ema_slow",
                param_type=ParameterType.INTEGER,
                default_value=100,
                min_value=1,
                max_value=500,
                description="Slow EMA period",
                required=False
            ),
            ParameterDefinition(
                name="rsi_period",
                param_type=ParameterType.INTEGER,
                default_value=14,
                min_value=1,
                max_value=100,
                description="RSI period",
                required=False
            ),
            ParameterDefinition(
                name="rsi_overbought",
                param_type=ParameterType.FLOAT,
                default_value=70.0,
                min_value=50.0,
                max_value=100.0,
                description="RSI overbought threshold",
                required=False
            ),
            ParameterDefinition(
                name="rsi_oversold",
                param_type=ParameterType.FLOAT,
                default_value=30.0,
                min_value=0.0,
                max_value=50.0,
                description="RSI oversold threshold",
                required=False
            ),
            ParameterDefinition(
                name="volume_threshold",
                param_type=ParameterType.FLOAT,
                default_value=1.5,
                min_value=0.5,
                max_value=5.0,
                description="Volume confirmation threshold",
                required=False
            ),
            ParameterDefinition(
                name="min_fvg_size",
                param_type=ParameterType.FLOAT,
                default_value=0.5,
                min_value=0.1,
                max_value=10.0,
                description="Minimum FVG size in points",
                required=False
            ),
            ParameterDefinition(
                name="max_hold_time",
                param_type=ParameterType.INTEGER,
                default_value=60,
                min_value=1,
                max_value=1440,
                description="Maximum hold time in minutes",
                required=False
            ),
            ParameterDefinition(
                name="stop_loss",
                param_type=ParameterType.FLOAT,
                default_value=2.0,
                min_value=0.1,
                max_value=20.0,
                description="Stop loss in points",
                required=False
            ),
            ParameterDefinition(
                name="take_profit",
                param_type=ParameterType.FLOAT,
                default_value=4.0,
                min_value=0.1,
                max_value=50.0,
                description="Take profit in points",
                required=False
            ),
            ParameterDefinition(
                name="position_size",
                param_type=ParameterType.FLOAT,
                default_value=1.0,
                min_value=0.1,
                max_value=10.0,
                description="Position size multiplier",
                required=False
            ),
            ParameterDefinition(
                name="use_trailing_stop",
                param_type=ParameterType.BOOLEAN,
                default_value=False,
                description="Enable trailing stop loss",
                required=False
            ),
            ParameterDefinition(
                name="trailing_stop_distance",
                param_type=ParameterType.FLOAT,
                default_value=1.0,
                min_value=0.1,
                max_value=10.0,
                description="Trailing stop distance in points",
                required=False
            ),
            ParameterDefinition(
                name="confluence_threshold",
                param_type=ParameterType.FLOAT,
                default_value=0.7,
                min_value=0.0,
                max_value=1.0,
                description="Minimum confluence score threshold",
                required=False
            ),
            ParameterDefinition(
                name="risk_per_trade",
                param_type=ParameterType.FLOAT,
                default_value=0.02,
                min_value=0.001,
                max_value=0.1,
                description="Risk per trade as fraction of portfolio",
                required=False
            ),
            ParameterDefinition(
                name="max_positions",
                param_type=ParameterType.INTEGER,
                default_value=1,
                min_value=1,
                max_value=10,
                description="Maximum number of concurrent positions",
                required=False
            ),
            ParameterDefinition(
                name="enable_ml_filter",
                param_type=ParameterType.BOOLEAN,
                default_value=True,
                description="Enable ML-based filtering",
                required=False
            ),
            ParameterDefinition(
                name="ml_confidence_threshold",
                param_type=ParameterType.FLOAT,
                default_value=0.6,
                min_value=0.0,
                max_value=1.0,
                description="ML model confidence threshold",
                required=False
            )
        ]
        
        for definition in default_definitions:
            self.parameter_definitions[definition.name] = definition
    
    def add_parameter_definition(self, definition: ParameterDefinition):
        """Add a new parameter definition."""
        self.parameter_definitions[definition.name] = definition
        logger.info(f"Added parameter definition: {definition.name}")
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate a set of parameters.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = {}
        
        # Check required parameters
        for name, definition in self.parameter_definitions.items():
            if definition.required and name not in parameters:
                errors[name] = f"Required parameter '{name}' is missing"
        
        # Validate provided parameters
        for name, value in parameters.items():
            if name in self.parameter_definitions:
                is_valid, error = self.parameter_definitions[name].validate(value)
                if not is_valid:
                    errors[name] = error
            else:
                logger.warning(f"Unknown parameter: {name}")
        
        return len(errors) == 0, errors
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameter values."""
        return {
            name: definition.default_value 
            for name, definition in self.parameter_definitions.items()
        }
    
    def merge_parameters(self, base_params: Dict[str, Any], 
                        override_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge parameter dictionaries with validation.
        
        Args:
            base_params: Base parameters
            override_params: Parameters to override
            
        Returns:
            Merged and validated parameters
        """
        merged = base_params.copy()
        merged.update(override_params)
        
        # Validate merged parameters
        is_valid, errors = self.validate_parameters(merged)
        if not is_valid:
            raise ValueError(f"Invalid parameters: {errors}")
        
        return merged
    
    def create_parameter_set(self, name: str, parameters: Dict[str, Any],
                           description: str = "", tags: Optional[List[str]] = None) -> ParameterSet:
        """
        Create a new parameter set.
        
        Args:
            name: Parameter set name
            parameters: Parameter values
            description: Optional description
            tags: Optional tags
            
        Returns:
            Created parameter set
        """
        # Validate parameters
        is_valid, errors = self.validate_parameters(parameters)
        if not is_valid:
            raise ValueError(f"Invalid parameters: {errors}")
        
        parameter_set = ParameterSet(
            name=name,
            parameters=parameters,
            description=description,
            tags=tags or []
        )
        
        self.parameter_sets[name] = parameter_set
        logger.info(f"Created parameter set: {name}")
        
        return parameter_set
    
    def get_parameter_set(self, name: str) -> Optional[ParameterSet]:
        """Get a parameter set by name."""
        return self.parameter_sets.get(name)
    
    def list_parameter_sets(self, tags: Optional[List[str]] = None) -> List[ParameterSet]:
        """
        List parameter sets, optionally filtered by tags.
        
        Args:
            tags: Optional tags to filter by
            
        Returns:
            List of matching parameter sets
        """
        sets = list(self.parameter_sets.values())
        
        if tags:
            sets = [ps for ps in sets if any(tag in ps.tags for tag in tags)]
        
        return sorted(sets, key=lambda ps: ps.created_at, reverse=True)
    
    def delete_parameter_set(self, name: str) -> bool:
        """Delete a parameter set."""
        if name in self.parameter_sets:
            del self.parameter_sets[name]
            logger.info(f"Deleted parameter set: {name}")
            return True
        return False
    
    def add_optimization_range(self, range_def: OptimizationRange):
        """Add an optimization range."""
        self.optimization_ranges[range_def.parameter_name] = range_def
        logger.info(f"Added optimization range for: {range_def.parameter_name}")
    
    def generate_optimization_combinations(self, 
                                         base_parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations for optimization.
        
        Args:
            base_parameters: Base parameters to start from
            
        Returns:
            List of parameter combinations
        """
        if not self.optimization_ranges:
            return [base_parameters or self.get_default_parameters()]
        
        base = base_parameters or self.get_default_parameters()
        
        # Generate all combinations
        param_names = list(self.optimization_ranges.keys())
        param_values = [self.optimization_ranges[name].generate_values() 
                       for name in param_names]
        
        combinations = []
        
        # Cartesian product of all parameter values
        import itertools
        for combination in itertools.product(*param_values):
            params = base.copy()
            for name, value in zip(param_names, combination):
                params[name] = value
            combinations.append(params)
        
        logger.info(f"Generated {len(combinations)} parameter combinations")
        return combinations
    
    def save_config(self):
        """Save configuration to file."""
        config = {
            'parameter_definitions': {
                name: asdict(definition) 
                for name, definition in self.parameter_definitions.items()
            },
            'parameter_sets': {
                name: parameter_set.to_dict() 
                for name, parameter_set in self.parameter_sets.items()
            },
            'optimization_ranges': {
                name: asdict(range_def) 
                for name, range_def in self.optimization_ranges.items()
            }
        }
        
        # Convert enums to strings
        for def_dict in config['parameter_definitions'].values():
            def_dict['param_type'] = def_dict['param_type'].value
        
        for range_dict in config['optimization_ranges'].values():
            range_dict['param_type'] = range_dict['param_type'].value
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved parameter configuration to {self.config_file}")
    
    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Load parameter definitions
            if 'parameter_definitions' in config:
                self.parameter_definitions = {}
                for name, def_dict in config['parameter_definitions'].items():
                    def_dict['param_type'] = ParameterType(def_dict['param_type'])
                    self.parameter_definitions[name] = ParameterDefinition(**def_dict)
            
            # Load parameter sets
            if 'parameter_sets' in config:
                self.parameter_sets = {}
                for name, set_dict in config['parameter_sets'].items():
                    self.parameter_sets[name] = ParameterSet.from_dict(set_dict)
            
            # Load optimization ranges
            if 'optimization_ranges' in config:
                self.optimization_ranges = {}
                for name, range_dict in config['optimization_ranges'].items():
                    range_dict['param_type'] = ParameterType(range_dict['param_type'])
                    self.optimization_ranges[name] = OptimizationRange(**range_dict)
            
            logger.info(f"Loaded parameter configuration from {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load parameter configuration: {e}")
            raise
    
    def export_parameter_set(self, name: str, file_path: Path):
        """Export a parameter set to file."""
        parameter_set = self.get_parameter_set(name)
        if not parameter_set:
            raise ValueError(f"Parameter set '{name}' not found")
        
        with open(file_path, 'w') as f:
            json.dump(parameter_set.to_dict(), f, indent=2)
        
        logger.info(f"Exported parameter set '{name}' to {file_path}")
    
    def import_parameter_set(self, file_path: Path, overwrite: bool = False) -> str:
        """
        Import a parameter set from file.
        
        Args:
            file_path: Path to import file
            overwrite: Whether to overwrite existing set with same name
            
        Returns:
            Name of imported parameter set
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        parameter_set = ParameterSet.from_dict(data)
        
        if parameter_set.name in self.parameter_sets and not overwrite:
            raise ValueError(f"Parameter set '{parameter_set.name}' already exists")
        
        # Validate parameters
        is_valid, errors = self.validate_parameters(parameter_set.parameters)
        if not is_valid:
            raise ValueError(f"Invalid parameters in imported set: {errors}")
        
        self.parameter_sets[parameter_set.name] = parameter_set
        logger.info(f"Imported parameter set '{parameter_set.name}' from {file_path}")
        
        return parameter_set.name