# Data Model: Unified Deployment Script

**Date**: October 23, 2025  
**Feature**: Unified Deployment Script

---

## Core Entities

### DeploymentConfig

Configuration for the deployment pipeline.

**Fields**:
- `algorithm_file_path` (string, required): Path to the algorithm file to deploy
- `project_name` (string, optional): Custom name for the project (auto-generated if not provided)
- `backtest_name` (string, optional): Custom name for the backtest (defaults to "Automated Backtest")
- `backtest_parameters` (dict, optional): Parameters for backtest execution
- `cleanup_test_projects` (boolean, default: true): Whether to clean up test projects after deployment
- `verbose_logging` (boolean, default: false): Enable detailed logging output

**Validation Rules**:
- `algorithm_file_path` must exist and be readable
- `project_name` must be unique if provided
- `backtest_parameters` must be serializable to JSON

---

### PipelineState

Tracks the current state and progress of the deployment pipeline.

**Fields**:
- `deployment_id` (string, required): Unique identifier for this deployment
- `current_step` (enum, required): Current pipeline step
  - Values: `INITIALIZING`, `VALIDATING`, `CREATING_PROJECT`, `UPLOADING_FILES`, `COMPILING`, `CREATING_BACKTEST`, `MONITORING_BACKTEST`, `RETRIEVING_RESULTS`, `COMPLETED`, `FAILED`, `CLEANING_UP`
- `progress_percentage` (integer, 0-100): Overall progress indicator
- `started_at` (datetime): Deployment start timestamp
- `completed_at` (datetime, optional): Deployment completion timestamp
- `error_message` (string, optional): Error details if deployment failed

**Intermediate Results**:
- `project_id` (integer, optional): Created project ID
- `compile_id` (string, optional): Compilation ID
- `backtest_id` (string, optional): Backtest ID
- `backtest_results` (object, optional): Final backtest results

**State Transitions**:
```
INITIALIZING → VALIDATING → CREATATING_PROJECT → UPLOADING_FILES → COMPILING → CREATING_BACKTEST → MONITORING_BACKTEST → RETRIEVING_RESULTS → COMPLETED
                ↓               ↓                ↓              ↓           ↓              ↓                ↓
              FAILED          FAILED           FAILED         FAILED      FAILED          FAILED           CLEANING_UP
```

---

### Credentials

QuantConnect API authentication credentials.

**Fields**:
- `user_id` (string, required): QuantConnect user ID
- `api_token` (string, required): QuantConnect API token
- `organization_id` (string, optional): Organization ID for enterprise accounts

**Validation Rules**:
- `user_id` must be numeric string
- `api_token` must be non-empty string
- Credentials must be valid for QuantConnect API authentication

**Security Notes**:
- Loaded from .env file only
- Never logged or displayed
- Validated before API usage

---

### DeploymentResults

Final results and metrics from the deployment.

**Fields**:
- `deployment_id` (string, required): Reference to deployment
- `success` (boolean, required): Whether deployment completed successfully
- `duration_seconds` (integer): Total deployment time
- `backtest_performance` (object, optional): Backtest performance metrics
  - `total_return` (float): Total return percentage
  - `sharpe_ratio` (float): Sharpe ratio
  - `max_drawdown` (float): Maximum drawdown percentage
  - `win_rate` (float): Win rate percentage
  - `total_trades` (integer): Number of trades executed
- `project_url` (string, optional): URL to created project
- `backtest_url` (string, optional): URL to backtest results

---

### ProgressUpdate

Real-time progress information for user feedback.

**Fields**:
- `step_name` (string, required): Current step description
- `step_progress` (integer, 0-100): Progress within current step
- `overall_progress` (integer, 0-100): Overall deployment progress
- `message` (string, required): Status message for user
- `timestamp` (datetime): Update timestamp
- `details` (object, optional): Additional step-specific details

---

## Relationships

```
DeploymentConfig → PipelineState (1:1)
PipelineState → Credentials (1:1)
PipelineState → DeploymentResults (1:1)
PipelineState → ProgressUpdate (1:N)
```

---

## Data Flow

1. **Initialization**: Create `DeploymentConfig` from CLI arguments
2. **Credential Loading**: Load `Credentials` from .env file
3. **State Management**: Create `PipelineState` to track progress
4. **Progress Updates**: Generate `ProgressUpdate` for each step
5. **Results**: Create `DeploymentResults` upon completion

---

## Validation Summary

- **Input Validation**: Algorithm file exists, credentials present
- **State Validation**: Valid state transitions, required fields for each state
- **Output Validation**: Results contain required metrics and URLs
- **Security Validation**: Credentials never exposed in logs or output

---

## Error Handling

- **Configuration Errors**: Invalid file paths, missing required fields
- **Credential Errors**: Missing/invalid credentials, authentication failures
- **API Errors**: Network failures, rate limits, service unavailable
- **Pipeline Errors**: Step failures with rollback capability
- **Validation Errors**: Invalid data formats, out-of-range values