# Quickstart Guide: Unified Deployment Script

## Overview

The unified deployment script consolidates all QuantConnect deployment functionality into a single end-to-end command-line tool. It handles project creation, file upload, compilation, backtesting, and results retrieval with real-time progress monitoring.

## Prerequisites

1. **Python 3.11+** with required dependencies:
   ```bash
   pip install requests click python-dotenv tqdm rich
   ```

2. **QuantConnect Account** with API access

3. **Algorithm File** ready for deployment

## Setup

### 1. Configure Credentials

Create a `.env` file in your project root:

```bash
# Required
QUANTCONNECT_USER_ID=your_user_id_here
QUANTCONNECT_API_TOKEN=your_api_token_here

# Optional (for enterprise accounts)
QUANTCONNECT_ORGANIZATION_ID=your_organization_id_here
```

**Get your credentials:**
- User ID: From your QuantConnect profile URL (`/u/123456`)
- API Token: Settings → API → Generate New Token

### 2. Prepare Algorithm File

Ensure your algorithm file is ready:
```python
# Example: my_algorithm.py
from AlgorithmImports import *

class MyAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Hour)
        
    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1.0)
```

## Basic Usage

### Simple Deployment

```bash
python deploy_unified.py my_algorithm.py
```

This will:
- Auto-generate project name
- Use default backtest settings
- Clean up test projects after completion
- Show basic progress output

### Advanced Usage

```bash
python deploy_unified.py my_algorithm.py \
  --project-name "My Trading Strategy" \
  --backtest-name "Q1 2024 Test" \
  --backtest-params '{"ema_fast": 10, "ema_slow": 20}' \
  --verbose
```

## Command Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--project-name` | `-p` | Custom project name | `"My Strategy"` |
| `--backtest-name` | `-b` | Custom backtest name | `"Test Run"` |
| `--backtest-params` | `-x` | Backtest parameters (JSON) | `'{"param": "value"}'` |
| `--no-cleanup` | | Keep test projects | |
| `--verbose` | `-v` | Detailed logging | |
| `--help` | `-h` | Show help | |

## Output Examples

### Standard Output
```
[2025-10-23 10:30:00] INFO: Starting unified deployment...
[2025-10-23 10:30:01] INFO: Validating algorithm file...
[2025-10-23 10:30:02] INFO: Creating project...
[2025-10-23 10:30:15] INFO: Uploading files...
[2025-10-23 10:30:20] INFO: Compiling project...
[2025-10-23 10:30:35] INFO: Creating backtest...
[2025-10-23 10:30:40] INFO: Monitoring backtest...
Deploying Algorithm: [████████████████████████████████] 100% Complete
[2025-10-23 10:32:15] INFO: Retrieving results...
[2025-10-23 10:32:20] INFO: Deployment completed successfully!

Results:
- Project: https://www.quantconnect.com/project/123456
- Backtest: https://www.quantconnect.com/backtest/789012
- Total Return: 15.2%
- Sharpe Ratio: 1.8
- Win Rate: 62.5%
```

### Verbose JSON Output
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

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   Error: Invalid QuantConnect credentials
   ```
   **Solution**: Verify your `.env` file contains correct `QUANTCONNECT_USER_ID` and `QUANTCONNECT_API_TOKEN`

2. **File Not Found**
   ```
   Error: Algorithm file not found: my_algorithm.py
   ```
   **Solution**: Check file path and ensure file exists

3. **Compilation Error**
   ```
   Error: Compilation failed: Syntax error in algorithm
   ```
   **Solution**: Check your algorithm code for syntax errors

4. **Rate Limit**
   ```
   Error: QuantConnect API rate limit exceeded
   ```
   **Solution**: Wait a few minutes and try again

### Debug Mode

Use `--verbose` flag for detailed error information:
```bash
python deploy_unified.py my_algorithm.py --verbose
```

## Best Practices

1. **Test Locally**: Validate your algorithm in QuantConnect IDE first
2. **Use Descriptive Names**: Provide meaningful project and backtest names
3. **Monitor Progress**: Use `--verbose` for long-running deployments
4. **Clean Up**: Default cleanup removes test projects to save quota
5. **Parameter Testing**: Use `--backtest-params` for parameter optimization

## Integration Examples

### CI/CD Pipeline
```bash
#!/bin/bash
# deploy.sh
set -e

echo "Deploying algorithm..."
python deploy_unified.py production_algorithm.py \
  --project-name "Production Strategy" \
  --backtest-name "Daily Validation" \
  --verbose

echo "Deployment completed successfully!"
```

### Batch Deployment
```bash
#!/bin/bash
# deploy_all.sh
for algorithm in algorithms/*.py; do
  echo "Deploying $algorithm..."
  python deploy_unified.py "$algorithm" \
    --project-name "$(basename "$algorithm" .py)" \
    --no-cleanup
done
```

## Next Steps

- **Parameter Optimization**: Use the script with different `--backtest-params`
- **Automated Workflows**: Integrate into your CI/CD pipeline
- **Monitoring**: Set up alerts based on backtest results
- **Scaling**: Deploy multiple algorithms with batch scripts

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the full specification in `spec.md`
3. Examine the API contracts in `contracts/`
4. Check existing test cases in `tests/`