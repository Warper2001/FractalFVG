# Unified Deployment Script Usage Guide

## Overview

The unified deployment script (`deploy_unified.py`) provides a single command-line interface for deploying trading algorithms to QuantConnect with automated backtesting and result analysis.

## Prerequisites

1. **Python 3.11+** with required dependencies:
   ```bash
   pip install click python-dotenv tqdm rich requests
   ```

2. **QuantConnect Credentials** configured in `.env` file:
   ```bash
   QUANTCONNECT_USER_ID=your_user_id
   QUANTCONNECT_API_TOKEN=your_api_token
   QUANTCONNECT_ORGANIZATION_ID=your_org_id  # Optional
   ```

## Quick Start

### 1. Configure Credentials

```bash
python deploy_unified.py configure
```

This will prompt for your credentials and save them to `.env` file.

### 2. Deploy Algorithm

```bash
# Basic deployment
python deploy_unified.py deploy -f your_algorithm.py

# With custom project name
python deploy_unified.py deploy -f your_algorithm.py -p "My Trading Strategy"

# With backtest parameters
python deploy_unified.py deploy -f your_algorithm.py -params '{"ema_fast": 10, "ema_slow": 20}'

# Verbose output with logging
python deploy_unified.py deploy -f your_algorithm.py -v --log-file deployment.log
```

### 3. Test Connection

```bash
python deploy_unified.py test-connection
```

## Command Reference

### deploy

Deploy a trading algorithm to QuantConnect and run a backtest.

**Options:**
- `-f, --algorithm-file PATH`: Path to algorithm file (required)
- `-p, --project-name TEXT`: Custom project name
- `-b, --backtest-name TEXT`: Custom backtest name (default: "Automated Backtest")
- `--params, --backtest-parameters TEXT`: JSON string of backtest parameters
- `--no-cleanup`: Don't clean up test projects after deployment
- `-v, --verbose`: Enable verbose logging
- `--log-file PATH`: Log file path
- `--output-format [json|table|summary]`: Results output format
- `-o, --output-file PATH`: Output file for results

### configure

Configure QuantConnect credentials.

**Options:**
- `--user-id TEXT`: QuantConnect user ID
- `--api-token TEXT`: API token
- `--organization-id TEXT`: Organization ID (optional)

### test-connection

Test connection to QuantConnect API.

## Pipeline Steps

The deployment script automates these steps:

1. **Validation**: Verify inputs, credentials, and API connection
2. **Project Creation**: Create QuantConnect project
3. **File Upload**: Upload algorithm file to project
4. **Compilation**: Compile the project
5. **Backtest Creation**: Create and start backtest
6. **Monitoring**: Monitor backtest execution
7. **Results Retrieval**: Get backtest results and performance metrics
8. **Cleanup**: Remove temporary resources (optional)

## Output Formats

### Summary (default)
```
🎉 DEPLOYMENT SUCCESSFUL!
⏱️  Completed in 45.23 seconds
🔗 View backtest: https://www.quantconnect.com/backtest/12345
📊 Performance Summary:
   • Total Return: 12.5%
   • Sharpe Ratio: 1.23
   • Max Drawdown: -5.2%
```

### Table
```
DEPLOYMENT RESULTS
==================================================
Deployment ID: abc123-def456
Success: ✅ Yes
Duration: 45.23 seconds
Project URL: https://www.quantconnect.com/project/789
Backtest URL: https://www.quantconnect.com/backtest/12345

PERFORMANCE METRICS
--------------------
Total Return: 12.5%
Sharpe Ratio: 1.23
Max Drawdown: -5.2%
Win Rate: 65.0%
Total Trades: 42
```

### JSON
```json
{
  "deployment_id": "abc123-def456",
  "success": true,
  "duration_seconds": 45.23,
  "project_url": "https://www.quantconnect.com/project/789",
  "backtest_url": "https://www.quantconnect.com/backtest/12345",
  "performance": {
    "total_return": "12.5%",
    "sharpe_ratio": 1.23,
    "max_drawdown": "-5.2%",
    "win_rate": 0.65,
    "total_trades": 42
  }
}
```

## Environment Variables

Optional environment variables for advanced configuration:

```bash
# API Configuration
QUANTCONNECT_API_URL=https://www.quantconnect.com/api/v2
API_TIMEOUT=30
API_MAX_RETRIES=3

# Logging
LOG_LEVEL=INFO
ENABLE_METRICS=true
DEBUG_MODE=false

# Deployment
DEPLOYMENT_ENV=development
```

## Error Handling

The script includes comprehensive error handling:

- **Authentication Errors**: Clear messages for invalid credentials
- **Rate Limiting**: Automatic retry with exponential backoff
- **Compilation Errors**: Detailed compilation error messages
- **Network Issues**: Retry logic for connection problems
- **Validation Errors**: Input validation before API calls

## Examples

### Example 1: Basic Deployment
```bash
python deploy_unified.py deploy -f strategy.py
```

### Example 2: Advanced Deployment with Parameters
```bash
python deploy_unified.py deploy \
  -f strategy.py \
  -p "EMA Crossover Strategy" \
  -b "EMA Test Run" \
  -params '{"ema_fast": 10, "ema_slow": 20, "risk_per_trade": 0.02}' \
  -v \
  --output-format json \
  -o results.json
```

### Example 3: Development Testing
```bash
python deploy_unified.py deploy \
  -f test_strategy.py \
  --no-cleanup \
  -v \
  --log-file debug.log
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify credentials in `.env` file
   - Check user ID is numeric
   - Ensure API token is correct

2. **Rate Limited**
   - Wait for rate limit to reset (typically 12-24 hours)
   - Use conservative deployment frequency

3. **Compilation Errors**
   - Check algorithm syntax
   - Verify required imports
   - Review compilation logs

4. **Network Issues**
   - Check internet connection
   - Verify firewall settings
   - Try again with increased timeout

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
DEBUG_MODE=true python deploy_unified.py deploy -f strategy.py -v
```

## Integration with CI/CD

The script is designed for CI/CD integration:

```yaml
# GitHub Actions example
- name: Deploy to QuantConnect
  run: |
    python deploy_unified.py deploy \
      -f strategy.py \
      --output-format json \
      -o results.json
  env:
    QUANTCONNECT_USER_ID: ${{ secrets.QUANTCONNECT_USER_ID }}
    QUANTCONNECT_API_TOKEN: ${{ secrets.QUANTCONNECT_API_TOKEN }}
```

## Support

For issues and questions:
1. Check the logs for detailed error messages
2. Verify credentials and network connectivity
3. Review algorithm file for syntax errors
4. Test with a simple algorithm first