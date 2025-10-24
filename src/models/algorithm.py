"""
Algorithm models for the Automated QuantConnect Pipeline.

This module defines the data structures for representing trading algorithms,
their files, metadata, and configuration parameters.
"""

from datetime import datetime, date
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


class AlgorithmStatus(Enum):
    """Algorithm lifecycle status."""
    DRAFT = "draft"
    VALIDATING = "validating"
    UPLOADED = "uploaded"
    COMPILATION_FAILED = "compilation_failed"
    READY = "ready"
    ARCHIVED = "archived"


@dataclass
class RiskSettings:
    """Risk management configuration for algorithms."""
    max_drawdown: float = 0.15  # Maximum drawdown percentage
    max_position_size: float = 0.02  # Maximum position size (2% per constitution)
    stop_loss_ticks: int = 20  # Stop loss in ticks
    take_profit_ticks: int = 40  # Take profit in ticks
    max_daily_loss: float = 1000  # Maximum daily loss in dollars


@dataclass
class AlgorithmFile:
    """Represents a single algorithm source file."""
    name: str  # File name (e.g., "Main.cs")
    content: str  # File content
    size: int = field(init=False)  # File size in bytes
    checksum: str = field(init=False)  # MD5 hash for integrity
    
    def __post_init__(self):
        """Calculate file size and checksum after initialization."""
        self.size = len(self.content.encode('utf-8'))
        import hashlib
        self.checksum = hashlib.md5(self.content.encode('utf-8')).hexdigest()


@dataclass
class AlgorithmMetadata:
    """Algorithm configuration and metadata."""
    initial_cash: float = 100000  # Starting capital
    start_date: date = field(default_factory=lambda: date(2023, 1, 1))
    end_date: date = field(default_factory=lambda: date(2023, 12, 31))
    resolution: str = "minute"  # Data resolution (tick/second/minute/hour/daily)
    parameters: Dict[str, Any] = field(default_factory=dict)  # Custom parameters
    risk_management: RiskSettings = field(default_factory=RiskSettings)


@dataclass
class Algorithm:
    """Represents a trading strategy with code, metadata, and configuration."""
    id: str  # Unique algorithm identifier
    name: str  # Human-readable name
    description: str  # Algorithm description
    language: str  # "CSharp" or "Python"
    files: List[AlgorithmFile]  # Source code files
    metadata: AlgorithmMetadata  # Configuration and settings
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    project_id: Optional[int] = None  # QuantConnect project ID
    status: AlgorithmStatus = AlgorithmStatus.DRAFT
    
    def __post_init__(self):
        """Validate algorithm after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate algorithm configuration."""
        if not self.name or len(self.name) > 100:
            raise ValueError("Algorithm name must be 1-100 characters")
        
        if self.language not in ["CSharp", "Python"]:
            raise ValueError("Language must be 'CSharp' or 'Python'")
        
        if not self.files:
            raise ValueError("Algorithm must have at least one file")
        
        # Validate file extensions
        valid_extensions = {"CSharp": [".cs"], "Python": [".py"]}
        allowed_extensions = valid_extensions.get(self.language, [])
        
        for file in self.files:
            if not any(file.name.endswith(ext) for ext in allowed_extensions):
                raise ValueError(f"Invalid file extension for {self.language}: {file.name}")
        
        # Validate total project size
        total_size = sum(file.size for file in self.files)
        if total_size > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("Total project size must be less than 100MB")
        
        # Validate risk settings compliance with constitution
        if self.metadata.risk_management.max_position_size > 0.02:
            raise ValueError("Maximum position size cannot exceed 2% per constitution")
    
    def add_file(self, file: AlgorithmFile):
        """Add a file to the algorithm."""
        self.files.append(file)
        self.updated_at = datetime.utcnow()
        self._validate()
    
    def update_status(self, status: AlgorithmStatus):
        """Update algorithm status."""
        self.status = status
        self.updated_at = datetime.utcnow()