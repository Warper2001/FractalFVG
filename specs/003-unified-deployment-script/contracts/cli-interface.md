# CLI Interface Specification

## Command Structure

```bash
deploy_unified.py [OPTIONS] ALGORITHM_FILE
```

## Options

### Required Arguments

- `ALGORITHM_FILE`: Path to the algorithm file to deploy

### Optional Options

- `--project-name, -p TEXT`: Custom name for the project (auto-generated if not provided)
- `--backtest-name, -b TEXT`: Custom name for the backtest (defaults to "Automated Backtest")
- `--backtest-params, -x JSON`: Parameters for backtest execution (JSON string)
- `--no-cleanup`: Skip cleanup of test projects after deployment
- `--verbose, -v`: Enable detailed logging output
- `--help, -h`: Show help message

## Environment Variables

Required environment variables in `.env` file:

```bash
QUANTCONNECT_USER_ID=your_user_id
QUANTCONNECT_API_TOKEN=your_api_token
QUANTCONNECT_ORGANIZATION_ID=your_organization_id  # Optional
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Authentication error
- `4`: API error
- `5`: Pipeline error

## Output Formats

### Standard Output
```
[2025-10-23 10:30:00] INFO: Starting unified deployment...
[2025-10-23 10:30:01] INFO: Validating algorithm file...
[2025-10-23 10:30:02] INFO: Creating project...
[████████████████████████████████] 100% Complete
```

### JSON Output (with --verbose)
```json
{
  "deployment_id": "deploy_20251023_103000",
  "status": "completed",
  "duration_seconds": 180,
  "project_url": "https://www.quantconnect.com/project/123456",
  "backtest_url": "https://www.quantconnect.com/backtest/789012",
  "performance": {
    "total_return": 15.2,
    "sharpe_ratio": 1.8,
    "max_drawdown": -5.3,
    "win_rate": 62.5,
    "total_trades": 48
  }
}
```

## Progress Bar Format

```
Deploying Algorithm: [████████████████████████████████] 100% Complete
Step: Monitoring Backtest (4/8) | Time: 02:45 | ETA: 01:20
```

## Error Messages

### Configuration Errors
- `Error: Algorithm file not found: /path/to/file.py`
- `Error: Invalid backtest parameters: not valid JSON`

### Authentication Errors
- `Error: Missing QUANTCONNECT_USER_ID in .env file`
- `Error: Invalid QuantConnect credentials`

### API Errors
- `Error: QuantConnect API rate limit exceeded`
- `Error: Network connection failed`

### Pipeline Errors
- `Error: Compilation failed: Syntax error in algorithm`
- `Error: Backtest creation failed: Invalid parameters`