# FractalFVG Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-20

## Active Technologies
- Python 3.11 (QuantConnect LEAN compatible) + QuantConnect LEAN, NumPy, pandas, scikit-learn (001-fvg-confluence-research)
- Python 3.11 (QuantConnect LEAN compatible) + QuantConnect LEAN, NumPy, pandas, matplotlib (001-fvg-confluence-research)
- Files (CSV/Parquet for research results, Pickle for ML models) (001-fvg-confluence-research)
- Python 3.11 (QuantConnect LEAN compatible) + QuantConnect LEAN, requests, asyncio, pandas, numpy (002-automate-quantconnect-pipeline)
- Files (JSON/CSV for results, joblib for ML models) (002-automate-quantconnect-pipeline)
- Python 3.11 (QuantConnect LEAN compatible) + requests, click, python-dotenv, existing QuantConnect API client (003-unified-deployment-script)
- Local filesystem for algorithm files, .env for credentials (003-unified-deployment-script)
- Python 3.11 (QuantConnect LEAN compatible) + requests, click, python-dotenv, tqdm, existing QuantConnect API client (003-unified-deployment-script)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11 (QuantConnect LEAN compatible): Follow standard conventions

## Recent Changes
- 003-unified-deployment-script: Added Python 3.11 (QuantConnect LEAN compatible) + requests, click, python-dotenv, tqdm, existing QuantConnect API client
- 003-unified-deployment-script: Added Python 3.11 (QuantConnect LEAN compatible) + requests, click, python-dotenv, existing QuantConnect API client
- 002-automate-quantconnect-pipeline: Added Python 3.11 (QuantConnect LEAN compatible) + QuantConnect LEAN, requests, asyncio, pandas, numpy

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
