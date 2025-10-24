# Automated QuantConnect Pipeline

Single script implementation of the 5-step automated workflow for QuantConnect.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install requests
```

### 2. Configure Credentials

**Option A: Environment Variables**
```bash
export QUANTCONNECT_USER_ID="your_user_id"
export QUANTCONNECT_API_TOKEN="your_api_token"
export QUANTCONNECT_ORGANIZATION_ID="your_org_id"  # Optional
```

**Option B: Config File**
```bash
cp quantconnect_config.json.example quantconnect_config.json
# Edit quantconnect_config.json with your credentials
```

### 3. Run the Pipeline

```bash
# Basic usage
python automated_quantconnect_pipeline.py your_algorithm.py

# With custom project name
python automated_quantconnect_pipeline.py your_algorithm.py MyProject

# With verbose logging
python automated_quantconnect_pipeline.py your_algorithm.py --verbose
```

## 📋 5-Step Workflow

1. **Stop Running Backtests** 🛑
   - Lists all running backtests
   - Stops each one automatically
   - Reports count of stopped backtests

2. **Create/Upload/Compile** 📁
   - Creates new QuantConnect project
   - Uploads your algorithm file
   - Compiles and verifies success

3. **Wait 10s + Create Backtest** ⏱️
   - Waits exactly 10 seconds (as required)
   - Creates new backtest with timestamp
   - Returns backtest ID

4. **Monitor with 30s Polling** 👀
   - Polls every 30 seconds for status
   - Tracks progress percentage
   - Waits for completion or error

5. **Output Results** 📊
   - Displays results to console
   - Saves detailed JSON report
   - Includes performance metrics

## 📊 Output Files

- `pipeline.log` - Detailed execution log
- `backtest_results_YYYYMMDD_HHMMSS.json` - Complete results with metrics
- Console output with key performance indicators

## 📈 JSON Results Format

```json
{
  "pipeline_execution": {
    "timestamp": "2025-01-23T10:30:00",
    "workflow_steps": {
      "step1": {"stopped": 2, "status": "success"},
      "step2": {"project_id": 12345, "status": "success"},
      "step3": {"backtest_id": "abc123", "status": "success"},
      "step4": {"status": "completed", "duration": 1800},
      "step5": {"json_file": "backtest_results_...", "status": "success"}
    }
  },
  "backtest_results": { ... },
  "performance_metrics": { ... },
  "statistics": { ... }
}
```

## 🔧 Algorithm File Requirements

Your algorithm file should be a valid QuantConnect Python algorithm:

```python
from AlgorithmImports import *

class MyAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)
    
    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)
```

## 🚨 Error Handling

The script includes comprehensive error handling:
- API request failures with retry logic
- Compilation error detection
- Backtest timeout handling
- Graceful failure reporting

## 📝 Logging

- **INFO**: Standard progress messages
- **WARNING**: Non-critical issues
- **ERROR**: Failures that stop execution
- **DEBUG**: Detailed API calls (use --verbose)

## 🔄 Example Output

```
2025-01-23 10:30:00 - INFO - 🚀 Starting Automated QuantConnect Pipeline
2025-01-23 10:30:01 - INFO - 🛑 Step 1: Stopping running backtests...
2025-01-23 10:30:02 - INFO - ✅ Step 1 complete: Stopped 2 running backtests
2025-01-23 10:30:03 - INFO - 📁 Step 2: Creating project and uploading algorithm...
2025-01-23 10:30:05 - INFO - ✅ Project created with ID: 12345
2025-01-23 10:30:08 - INFO - ✅ Compilation successful
2025-01-23 10:30:09 - INFO - ⏱️ Step 3: Waiting 10 seconds before creating backtest...
2025-01-23 10:30:19 - INFO - ✅ Backtest created with ID: abc123
2025-01-23 10:30:20 - INFO - 👀 Step 4: Monitoring backtest progress (30s polling)...
2025-01-23 10:33:20 - INFO - ✅ Backtest completed successfully
2025-01-23 10:33:21 - INFO - 📊 Step 5: Outputting results...
2025-01-23 10:33:22 - INFO - 🎯 BACKTEST RESULTS
2025-01-23 10:33:22 - INFO - Total Return: 15.2%
2025-01-23 10:33:22 - INFO - Sharpe Ratio: 1.23
2025-01-23 10:33:22 - INFO - ✅ Results saved to: backtest_results_20250123_103322.json
2025-01-23 10:33:23 - INFO - 🎉 PIPELINE COMPLETED SUCCESSFULLY!
```

## 🛠️ Troubleshooting

**Common Issues:**
1. **Authentication Error**: Check your credentials in config file or environment variables
2. **Compilation Error**: Verify your algorithm syntax and imports
3. **Timeout**: Increase max wait times in the script if needed
4. **File Not Found**: Ensure algorithm file path is correct

**Debug Mode:**
```bash
python automated_quantconnect_pipeline.py your_algorithm.py --verbose
```

## 📞 Support

For issues with:
- **QuantConnect API**: Check QuantConnect documentation
- **Script Logic**: Review the log file `pipeline.log`
- **Credentials**: Verify API token permissions