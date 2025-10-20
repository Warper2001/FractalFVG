# QuantConnect MNQ Futures Trading Constitution

## Core Principles

### I. Real Data Only (NON-NEGOTIABLE)
All testing must use real MNQ (Micro E-mini Nasdaq-100) futures market data; No simulated or synthetic data permitted; Historical data must be from official exchange sources; Tick-level data required for high-frequency strategies

### II. Environment Parity
Backtesting, paper trading, and live trading environments must be identical; Same data feeds, same execution logic, same risk management; Any divergence between environments is a critical bug; Paper trading must use real-time market data

### III. Risk-First Development
All strategies must implement comprehensive risk management before any profit logic; Position sizing, stop-losses, and drawdown limits mandatory; Maximum daily loss limits enforced; No strategy may risk more than 2% per trade

### IV. QuantConnect Framework Compliance
All code must follow QuantConnect API patterns and best practices; Use LEAN algorithm framework exclusively; Custom data handlers must extend QC base classes; No bypassing built-in risk or portfolio management

### V. Performance & Latency Requirements
Backtesting must complete within 10x real-time duration; Paper trading latency under 100ms; Live trading execution under 50ms; Memory usage optimized for tick data processing

## Infrastructure Requirements

### Data Management
- MNQ futures data from CME only
- Tick-level resolution for backtesting
- Real-time streaming for paper/live trading
- Data validation and quality checks mandatory
- Backup data sources for redundancy

### Execution Environment
- QuantConnect Cloud for backtesting
- Dedicated paper trading account with real broker
- Live trading only after 30+ days profitable paper trading
- Automated deployment pipelines
- Real-time monitoring and alerting

### Security & Compliance
- API keys encrypted and rotated monthly
- Two-factor authentication required
- Audit trails for all trades
- Compliance with CME regulations
- No hardcoded credentials in code

## Development Workflow

### Strategy Development
1. Research phase: Backtest with 2+ years of MNQ data
2. Validation: Forward testing on unseen data
3. Paper trading: Minimum 30 days with real-time data
4. Live deployment: Gradual position sizing increase
5. Monitoring: Continuous performance tracking

### Testing Requirements
- Unit tests for all strategy components
- Integration tests with QuantConnect API
- Regression tests on strategy parameters
- Performance benchmarks for latency
- Risk management stress tests

### Code Review Process
- All code changes require peer review
- Risk management logic review mandatory
- Performance impact assessment required
- Documentation updates enforced
- Compliance verification before deployment

## Governance

This constitution supersedes all other development practices. Amendments require:
- Written proposal with impact analysis
- Team consensus (75% approval)
- Migration plan for existing strategies
- Updated documentation and training

All PRs must verify compliance with this constitution. Complexity must be justified with performance or risk benefits. Use QuantConnect documentation for runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2025-10-20 | **Last Amended**: 2025-10-20
