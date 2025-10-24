"""
Pipeline execution models for the Automated QuantConnect Pipeline.

This module contains data structures for pipeline workflow tracking:
- PipelineExecution: Main pipeline execution tracking
- PipelineStatus: Pipeline execution states
- PipelineStage: Individual pipeline stages
- PipelineError: Error tracking and handling
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class PipelineStage(Enum):
    """Individual pipeline stages."""
    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    UPLOAD = "upload"
    COMPILATION = "compilation"
    BACKTEST_SETUP = "backtest_setup"
    BACKTEST_EXECUTION = "backtest_execution"
    RESULTS_COLLECTION = "results_collection"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    CLEANUP = "cleanup"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PipelineError:
    """Error tracking and handling."""
    error_id: str
    stage: PipelineStage
    error_type: str
    message: str
    severity: ErrorSeverity
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    context: Dict[str, Any] = field(default_factory=dict)
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'error_id': self.error_id,
            'stage': self.stage.value,
            'error_type': self.error_type,
            'message': self.message,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'context': self.context,
            'resolution': self.resolution,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class PipelineMetadata:
    """Pipeline execution metadata."""
    pipeline_id: str
    algorithm_id: str
    triggered_by: str
    environment: str
    version: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'pipeline_id': self.pipeline_id,
            'algorithm_id': self.algorithm_id,
            'triggered_by': self.triggered_by,
            'environment': self.environment,
            'version': self.version,
            'parameters': self.parameters,
            'tags': self.tags
        }


@dataclass
class PipelineExecution:
    """Main pipeline execution tracking."""
    execution_id: str
    metadata: PipelineMetadata
    status: PipelineStatus
    current_stage: Optional[PipelineStage] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    stages_completed: List[PipelineStage] = field(default_factory=list)
    stages_failed: List[PipelineStage] = field(default_factory=list)
    errors: List[PipelineError] = field(default_factory=list)
    progress_percentage: float = 0.0
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def start(self) -> None:
        """Start pipeline execution."""
        self.status = PipelineStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.add_log(f"Pipeline execution started: {self.execution_id}")
    
    def complete(self) -> None:
        """Complete pipeline execution."""
        self.status = PipelineStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.progress_percentage = 100.0
        self.add_log(f"Pipeline execution completed in {self.duration_seconds:.2f} seconds")
    
    def fail(self, error: PipelineError) -> None:
        """Mark pipeline as failed."""
        self.status = PipelineStatus.FAILED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.errors.append(error)
        self.add_log(f"Pipeline execution failed: {error.message}")
    
    def advance_stage(self, stage: PipelineStage) -> None:
        """Advance to next pipeline stage."""
        if self.current_stage:
            self.stages_completed.append(self.current_stage)
        self.current_stage = stage
        self.add_log(f"Advanced to stage: {stage.value}")
        self._update_progress()
    
    def add_error(self, error: PipelineError) -> None:
        """Add error to pipeline execution."""
        self.errors.append(error)
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.stages_failed.append(error.stage)
        self.add_log(f"Error in {error.stage.value}: {error.message}")
    
    def add_log(self, message: str) -> None:
        """Add log entry."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
    
    def _update_progress(self) -> None:
        """Update progress percentage based on current stage."""
        all_stages = list(PipelineStage)
        if self.current_stage:
            current_index = all_stages.index(self.current_stage)
            self.progress_percentage = (current_index / len(all_stages)) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'execution_id': self.execution_id,
            'metadata': self.metadata.to_dict(),
            'status': self.status.value,
            'current_stage': self.current_stage.value if self.current_stage else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'stages_completed': [stage.value for stage in self.stages_completed],
            'stages_failed': [stage.value for stage in self.stages_failed],
            'errors': [error.to_dict() for error in self.errors],
            'progress_percentage': self.progress_percentage,
            'logs': self.logs,
            'metrics': self.metrics
        }