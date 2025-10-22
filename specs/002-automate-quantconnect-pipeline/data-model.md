# Data Model: Automated QuantConnect Pipeline

**Date**: 2025-10-22  
**Feature**: Automated QuantConnect Pipeline  
**Phase**: 1 - Design & Contracts

## Entity Overview

The automated pipeline manages five core entities: Algorithm, Backtest, Performance Metrics, Pipeline Execution, and Result Report. These entities support the end-to-end workflow from algorithm upload through results analysis.

## Core Entities

### 1. Algorithm

Represents a trading strategy with code, metadata, and configuration parameters.

**Fields**:
```python
class Algorithm:
    id: str                    # Unique algorithm identifier
    name: str                  # Human-readable name
    description: str           # Algorithm description
    language: str              # "CSharp" or "Python"
    files: List[AlgorithmFile] # Source code files
    metadata: AlgorithmMetadata # Configuration and settings
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
    project_id: int           # QuantConnect project ID
    status: AlgorithmStatus   # Current status
```

**Supporting Types**:
```python
class AlgorithmFile:
    name: str                 # File name (e.g., "Main.cs")
    content: str              # File content
    size: int                 # File size in bytes
    checksum: str             # MD5 hash for integrity

class AlgorithmMetadata:
    initial_cash: float       # Starting capital
    start_date: date         # Backtest start date
    end_date: date           # Backtest end date
    resolution: str          # Data resolution (tick/second/minute/hour/daily)
    parameters: Dict[str, Any] # Custom parameters
    risk_management: RiskSettings # Risk management configuration

class RiskSettings:
    max_drawdown: float       # Maximum drawdown percentage
    max_position_size: float  # Maximum position size
    stop_loss_ticks: int      # Stop loss in ticks
    take_profit_ticks: int    # Take profit in ticks
    max_daily_loss: float     # Maximum daily loss

enum AlgorithmStatus:
    DRAFT = "draft"
    VALIDATING = "validating"
    UPLOADED = "uploaded"
    COMPILATION_FAILED = "compilation_failed"
    READY = "ready"
    ARCHIVED = "archived"
```

**Validation Rules**:
- Algorithm name must be unique within project
- Files must have valid extensions (.cs, .py, .json)
- Total project size must be < 100MB
- Risk settings must comply with constitution (max 2% risk per trade)
- Dates must be within available data range

**State Transitions**:
```
DRAFT → VALIDATING → UPLOADED → READY
                    ↓ (validation failed)
                COMPILATION_FAILED
```

### 2. Backtest

Represents a specific execution of an algorithm with defined parameters and results.

**Fields**:
```python
class Backtest:
    id: str                   # Unique backtest identifier
    algorithm_id: str         # Reference to algorithm
    project_id: int          # QuantConnect project ID
    compile_id: str          # Compilation identifier
    name: str                # Backtest name
    parameters: BacktestParameters # Execution parameters
    status: BacktestStatus   # Current status
    created_at: datetime     # Creation timestamp
    started_at: datetime     # Execution start time
    completed_at: datetime   # Completion time
    duration_seconds: float  # Total execution time
    results: Optional[BacktestResults] # Performance results
    error_message: Optional[str] # Error details if failed
```

**Supporting Types**:
```python
class BacktestParameters:
    start_date: date         # Backtest start date
    end_date: date           # Backtest end date
    initial_cash: float      # Starting capital
    resolution: str          # Data resolution
    language: str           # Algorithm language
    custom_parameters: Dict[str, Any] # Algorithm-specific parameters

enum BacktestStatus:
    PENDING = "pending"
    COMPILING = "compiling"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
```

**Validation Rules**:
- Start date must be before end date
- Initial cash must be positive
- Resolution must be supported by data provider
- Algorithm must be in READY status
- Cannot exceed maximum backtest duration (24 hours)

**State Transitions**:
```
PENDING → COMPILING → RUNNING → COMPLETED
          ↓ (compile failed)    ↓ (execution failed)
        FAILED                FAILED
                              ↓ (timeout)
                            TIMEOUT
```

### 3. Performance Metrics

Quantitative measures of strategy performance extracted from backtest results.

**Fields**:
```python
class PerformanceMetrics:
    backtest_id: str         # Reference to backtest
    total_return: float      # Total portfolio return
    annual_return: float     # Annualized return
    sharpe_ratio: float      # Risk-adjusted return metric
    sortino_ratio: float     # Downside risk-adjusted return
    max_drawdown: float      # Maximum portfolio decline
    max_drawdown_duration: int # Maximum drawdown duration in days
    win_rate: float          # Percentage of winning trades
    profit_factor: float     # Gross profit / gross loss
    total_trades: int        # Number of completed trades
    average_win: float       # Average winning trade amount
    average_loss: float      # Average losing trade amount
    commission: float        # Total commission paid
    ending_portfolio_value: float # Final portfolio value
    beta: float              # Market correlation
    alpha: float             # Excess return over market
    information_ratio: float # Excess return per unit of risk
    tracking_error: float    # Deviation from benchmark
    var_95: float           # Value at risk (95% confidence)
    cvar_95: float          # Conditional value at risk (95% confidence)
    calmar_ratio: float     # Return / max drawdown
    recovery_factor: float  # Net profit / max drawdown
    volume_analysis: VolumeAnalysisMetrics # Volume-related metrics
```

**Supporting Types**:
```python
class VolumeAnalysisMetrics:
    volume_confirmation_rate: float # Percentage of trades with volume confirmation
    average_volume_multiplier: float # Average volume anomaly multiplier
    high_volume_trades: int         # Trades with HIGH volume confirmation
    session_distribution: Dict[str, float] # US/overnight/pre-market distribution
    volume_efficiency: float        # Return per unit of volume anomaly
```

**Validation Rules**:
- All ratios must be finite numbers
- Percentages must be between 0 and 1 (or 0-100 for win_rate)
- Trade counts must be non-negative integers
- Monetary values must be positive (except losses)
- Volume metrics must comply with constitution requirements

### 4. Pipeline Execution

Represents a complete run of upload-backtest-analysis workflow with state tracking.

**Fields**:
```python
class PipelineExecution:
    id: str                   # Unique pipeline execution identifier
    algorithm_id: str         # Reference to algorithm
    backtest_id: Optional[str] # Reference to backtest (if created)
    status: PipelineStatus    # Current pipeline status
    current_stage: PipelineStage # Current execution stage
    progress: float           # Progress percentage (0-100)
    created_at: datetime      # Creation timestamp
    started_at: datetime      # Execution start time
    completed_at: datetime    # Completion time
    duration_seconds: float   # Total execution time
    stages_completed: List[PipelineStage] # Completed stages
    error_history: List[PipelineError] # Error log
    metadata: PipelineMetadata # Execution metadata
```

**Supporting Types**:
```python
enum PipelineStatus:
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

enum PipelineStage:
    VALIDATION = "validation"
    UPLOAD = "upload"
    COMPILATION = "compilation"
    BACKTEST = "backtest"
    ANALYSIS = "analysis"
    REPORTING = "reporting"

class PipelineError:
    timestamp: datetime       # Error occurrence time
    stage: PipelineStage      # Stage where error occurred
    error_type: str          # Error classification
    message: str             # Error message
    severity: ErrorSeverity  # Error severity level
    retry_count: int         # Number of retry attempts
    resolved: bool           # Whether error was resolved

enum ErrorSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PipelineMetadata:
    algorithm_count: int      # Number of algorithms processed
    backtest_count: int       # Number of backtests executed
    total_api_calls: int      # Total API calls made
    api_quota_used: float     # Percentage of API quota used
    retry_count: int          # Total retry attempts
    performance_metrics: Dict[str, float] # Pipeline performance metrics
```

**Validation Rules**:
- Progress must be between 0 and 100
- Stages must be completed in order
- Error history must be chronological
- Total duration must be reasonable (< 10 minutes for standard algorithms)

**State Transitions**:
```
PENDING → RUNNING → COMPLETED
          ↓ (paused)    ↓ (failed)
        PAUSED        FAILED
                      ↓ (cancelled)
                    CANCELLED
```

### 5. Result Report

Structured output containing analysis, comparisons, and recommendations.

**Fields**:
```python
class ResultReport:
    id: str                   # Unique report identifier
    pipeline_execution_id: str # Reference to pipeline execution
    backtest_id: str         # Reference to backtest
    report_type: ReportType  # Type of report
    generated_at: datetime   # Generation timestamp
    format: ReportFormat     # Output format
    content: ReportContent   # Report content
    file_path: str          # File storage path
    size_bytes: int         # Report file size
    checksum: str           # File integrity checksum
```

**Supporting Types**:
```python
enum ReportType:
    PERFORMANCE = "performance"
    COMPARISON = "comparison"
    ANALYSIS = "analysis"
    SUMMARY = "summary"

enum ReportFormat:
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"

class ReportContent:
    executive_summary: str    # High-level summary
    performance_analysis: PerformanceAnalysis # Detailed performance
    risk_analysis: RiskAnalysis # Risk assessment
    volume_analysis: VolumeAnalysis # Volume analysis results
    recommendations: List[str] # Actionable recommendations
    comparisons: Optional[ComparisonAnalysis] # Comparative analysis
    charts: List[ChartSpec] # Chart specifications
    appendices: Dict[str, Any] # Additional data

class PerformanceAnalysis:
    strengths: List[str]     # Performance strengths
    weaknesses: List[str]    # Performance weaknesses
    key_metrics: Dict[str, float] # Important metrics
    trends: Dict[str, str]   # Performance trends
    benchmarks: Dict[str, float] # Benchmark comparisons

class RiskAnalysis:
    risk_level: str          # Overall risk assessment
    risk_factors: List[str]  # Identified risk factors
    drawdown_analysis: Dict[str, Any] # Drawdown details
    var_analysis: Dict[str, float] # Value at risk analysis
    recommendations: List[str] # Risk mitigation recommendations

class VolumeAnalysis:
    confirmation_effectiveness: float # Volume confirmation success rate
    session_performance: Dict[str, float] # Performance by session
    volume_anomalies: List[VolumeAnomaly] # Significant volume events
    optimization_suggestions: List[str] # Volume optimization suggestions

class ComparisonAnalysis:
    baseline_metrics: Dict[str, float] # Baseline performance
    comparison_metrics: Dict[str, float] # Comparison performance
    improvements: List[str] # Areas of improvement
    regressions: List[str]  # Areas of regression
    statistical_significance: Dict[str, float] # Statistical test results

class ChartSpec:
    chart_type: str          # Chart type (line, bar, scatter, etc.)
    title: str              # Chart title
    data_source: str        # Data source reference
    x_axis: str             # X-axis label
    y_axis: str             # Y-axis label
    configuration: Dict[str, Any] # Chart-specific configuration
```

**Validation Rules**:
- Report content must be non-empty
- File path must be accessible
- Checksum must match file content
- Charts must have valid data sources
- Recommendations must be actionable

## Relationships

### Entity Relationships
```
Algorithm 1───→ N Backtest
Algorithm 1───→ N PipelineExecution
Backtest 1───→ 1 PerformanceMetrics
PipelineExecution 1───→ 1 ResultReport
Backtest 1───→ 1 ResultReport
```

### Data Flow
```
Algorithm → PipelineExecution → Backtest → PerformanceMetrics → ResultReport
```

## Data Storage

### Primary Storage
- **Pipeline State**: JSON files in `data/pipeline_state/`
- **Results**: JSON/CSV files in `data/results/`
- **Reports**: Multiple formats in `data/reports/`
- **Logs**: Structured JSON logs in `data/logs/`

### Backup Strategy
- **Daily Backups**: Automated backup of all pipeline data
- **Version Control**: Git for configuration and code changes
- **Cloud Storage**: Optional cloud backup for critical results
- **Retention Policy**: 90 days for detailed logs, 1 year for results

## Performance Considerations

### Indexing Strategy
- **Algorithm ID**: Primary index for algorithm lookups
- **Backtest ID**: Primary index for backtest results
- **Pipeline ID**: Primary index for execution tracking
- **Timestamp**: Secondary index for time-based queries

### Query Optimization
- **Batch Operations**: Bulk inserts for performance metrics
- **Lazy Loading**: Load large result sets on demand
- **Caching**: Cache frequently accessed metadata
- **Compression**: Compress historical data to save space

## Security Considerations

### Data Protection
- **Encryption**: Sensitive data encrypted at rest
- **Access Control**: Role-based access to pipeline data
- **Audit Trail**: Complete audit log of all data operations
- **Data Retention**: Automatic cleanup of old data

### Privacy Compliance
- **PII Removal**: No personal information in pipeline data
- **Data Minimization**: Store only necessary data
- **Consent Management**: User consent for data usage
- **Regulatory Compliance**: Follow financial data regulations

## Integration Points

### QuantConnect API Integration
- **Algorithm Upload**: Use project and file creation endpoints
- **Backtest Execution**: Use compilation and backtest endpoints
- **Results Retrieval**: Use backtest read endpoint for metrics
- **Error Handling**: Map API errors to pipeline error types

### Volume Analysis Integration
- **Pre-Validation**: Validate volume analysis before upload
- **Runtime Monitoring**: Track volume analysis performance
- **Post-Analysis**: Include volume metrics in results
- **Compliance Checking**: Ensure constitution compliance

### Notification Integration
- **Progress Updates**: Real-time progress notifications
- **Completion Alerts**: Notification on pipeline completion
- **Error Alerts**: Immediate notification of critical errors
- **Report Delivery**: Automated report distribution

This data model provides a comprehensive foundation for implementing the automated QuantConnect pipeline with full support for the specified requirements and constitutional constraints.