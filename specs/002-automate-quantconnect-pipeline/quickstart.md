# Quick Start Guide: Automated QuantConnect Pipeline

**Date**: 2025-10-22  
**Feature**: Automated QuantConnect Pipeline  
**Purpose**: Get started with the automated pipeline in under 10 minutes

## Prerequisites

### System Requirements
- Python 3.11+ (QuantConnect LEAN compatible)
- 8GB+ RAM recommended for batch processing
- Stable internet connection for QuantConnect API access
- QuantConnect account with API access enabled

### Dependencies Installation
```bash
# Install core dependencies
pip install requests aiohttp asyncio tenacity pandas numpy

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov black flake8

# Install optional monitoring dependencies
pip install prometheus-client grafana-api
```

### Authentication Setup
```bash
# Set up QuantConnect credentials
export QUANTCONNECT_USER_ID="your_user_id"
export QUANTCONNECT_API_TOKEN="your_api_token"

# Or use encrypted credential file
python -m src.utils.credential_manager setup quantconnect
```

## Basic Usage

### 1. Single Algorithm Pipeline
```python
from src.pipeline.automated_pipeline import AutomatedPipeline

# Initialize pipeline
pipeline = AutomatedPipeline()

# Run complete pipeline for single algorithm
result = pipeline.run_algorithm(
    algorithm_path="path/to/algorithm.py",
    backtest_config={
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "initial_cash": 100000,
        "resolution": "minute"
    }
)

print(f"Pipeline completed: {result.status}")
print(f"Backtest ID: {result.backtest_id}")
print(f"Report: {result.report_path}")
```

### 2. Batch Processing
```python
# Process multiple algorithms
algorithms = [
    {"path": "strategies/momentum.py", "name": "Momentum Strategy"},
    {"path": "strategies/mean_reversion.py", "name": "Mean Reversion"},
    {"path": "strategies/volume_fvg.py", "name": "Volume FVG Strategy"}
]

batch_results = pipeline.run_batch(algorithms)
for result in batch_results:
    print(f"{result.algorithm_name}: {result.status}")
```

### 3. Pipeline Monitoring
```python
# Monitor pipeline progress
for update in pipeline.monitor_stream(pipeline_id="pipeline_123"):
    print(f"Stage: {update.stage} - Progress: {update.progress}%")
    if update.error:
        print(f"Error: {update.error.message}")
```

## Configuration

### Pipeline Configuration
```yaml
# config/pipeline.yaml
pipeline:
  max_concurrent_algorithms: 5
  timeout_minutes: 10
  retry_attempts: 3
  backoff_factor: 1.5

quantconnect:
  api_base_url: "https://www.quantconnect.com/api/v2"
  rate_limit_requests_per_minute: 60
  timeout_seconds: 300

storage:
  results_path: "data/results"
  reports_path: "data/reports"
  state_path: "data/pipeline_state"

monitoring:
  enable_metrics: true
  metrics_port: 8080
  log_level: "INFO"
```

### Algorithm Metadata
```python
# algorithms/momentum_strategy/metadata.json
{
    "name": "Momentum Strategy",
    "description": "Momentum-based trading strategy",
    "language": "Python",
    "initial_cash": 100000,
    "resolution": "minute",
    "parameters": {
        "lookback_period": 20,
        "momentum_threshold": 0.02
    },
    "risk_management": {
        "max_drawdown": 0.15,
        "max_position_size": 0.1,
        "stop_loss_ticks": 20,
        "take_profit_ticks": 40
    }
}
```

## Error Handling

### Common Error Scenarios
```python
try:
    result = pipeline.run_algorithm("algorithm.py")
except QuantConnectAPIError as e:
    print(f"API Error: {e.message}")
    print(f"Retry after: {e.retry_after} seconds")
except ValidationError as e:
    print(f"Validation failed: {e.errors}")
except PipelineTimeoutError as e:
    print(f"Pipeline timed out after {e.timeout} minutes")
except Exception as e:
    print(f"Unexpected error: {e}")
    pipeline.support.create_ticket(e)
```

### Recovery from Failures
```python
# Resume pipeline from last checkpoint
recovered_result = pipeline.resume_from_checkpoint(
    pipeline_id="failed_pipeline_123"
)

# Retry specific failed stage
retry_result = pipeline.retry_stage(
    pipeline_id="pipeline_123",
    stage="backtest"
)
```

## Monitoring and Debugging

### Real-time Monitoring
```bash
# Start monitoring dashboard
python -m src.monitoring.dashboard --port 8080

# View pipeline status
python -m src.cli.pipeline status --pipeline-id pipeline_123

# Stream logs
python -m src.cli.logs follow --pipeline-id pipeline_123
```

### Performance Metrics
```python
# Get pipeline performance metrics
metrics = pipeline.get_metrics(pipeline_id="pipeline_123")
print(f"Total duration: {metrics.duration_seconds}s")
print(f"API calls made: {metrics.api_calls}")
print(f"Success rate: {metrics.success_rate}%")
```

## Integration Examples

### CI/CD Integration
```yaml
# .github/workflows/pipeline.yml
name: Automated Pipeline
on: [push]

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run automated pipeline
        run: |
          python -m src.pipeline.automated_pipeline \
            --algorithm-path strategies/ \
            --config config/pipeline.yaml
        env:
          QUANTCONNECT_USER_ID: ${{ secrets.QUANTCONNECT_USER_ID }}
          QUANTCONNECT_API_TOKEN: ${{ secrets.QUANTCONNECT_API_TOKEN }}
```

### Jupyter Notebook Integration
```python
# In Jupyter notebook for research
%load_ext src.pipeline.jupyter_extension

# Run pipeline and display results
%%pipeline
algorithm: strategies/research_strategy.py
backtest:
  start_date: 2023-01-01
  end_date: 2023-06-30
  initial_cash: 100000

# Visualize results
import matplotlib.pyplot as plt
results = pipeline.get_last_results()
results.plot_equity_curve()
plt.show()
```

## Troubleshooting

### Common Issues
1. **Authentication Failures**: Verify API credentials and account status
2. **Rate Limiting**: Reduce concurrent operations or upgrade account tier
3. **Compilation Errors**: Validate algorithm syntax before upload
4. **Timeout Issues**: Increase timeout settings or optimize algorithm complexity
5. **Memory Issues**: Reduce batch size or enable streaming processing

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run pipeline with debug mode
pipeline.run_algorithm(
    "algorithm.py",
    debug=True,
    save_intermediate_results=True
)
```

### Support Resources
- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory  
- **API Reference**: `docs/api_reference.md`
- **Troubleshooting Guide**: `docs/troubleshooting.md`
- **Community Support**: GitHub Issues

## Next Steps

1. **Review Examples**: Check `examples/` directory for complete workflows
2. **Configure Monitoring**: Set up monitoring and alerting
3. **Customize Reports**: Modify report templates to your needs
4. **Scale Up**: Configure batch processing for high-volume usage
5. **Integrate**: Connect with your existing trading infrastructure

This quick start guide provides everything needed to get the automated QuantConnect pipeline running in minutes while supporting advanced use cases and enterprise requirements.
