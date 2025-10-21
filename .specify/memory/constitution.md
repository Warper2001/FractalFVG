# QuantConnect MNQ Futures Trading Constitution

## Core Principles

### I. Real Data Only (NON-NEGOTIABLE)
All testing must use real MNQ (Micro E-mini Nasdaq-100) futures market data; No simulated or synthetic data permitted; Historical data must be from official exchange sources; Tick-level data required for high-frequency strategies

### II. Environment Parity
Backtesting, paper trading, and live trading environments must be identical; Same data feeds, same execution logic, same risk management; Any divergence between environments is a critical bug; Paper trading must use real-time market data

### III. Risk-First Development
All strategies must implement comprehensive risk management before any profit logic; Position sizing, stop-losses, and drawdown limits mandatory; Maximum daily loss limits enforced; No strategy may risk more than 2% per trade; **Futures-specific**: Risk management MUST be measured in ticks and dollars appropriate for contract specifications; Tick-based stop-losses and take-profits mandatory for futures algorithms

### IV. QuantConnect Framework Compliance
All code must follow QuantConnect API patterns and best practices; Use LEAN algorithm framework exclusively; Custom data handlers must extend QC base classes; No bypassing built-in risk or portfolio management; **Futures-specific**: Must use QuantConnect Futures API for contract management, symbol mapping, and margin requirements

### V. Performance & Latency Requirements
Backtesting must complete within 10x real-time duration; Paper trading latency under 100ms; Live trading execution under 50ms; Memory usage optimized for tick data processing; **Futures-specific**: Multi-timeframe analysis (1-60 minutes) must complete batch processing under 5 minutes; Real-time FVG detection under 1 second latency

## Infrastructure Requirements

### Data Management
- MNQ futures data from CME only
- Tick-level resolution for backtesting
- Real-time streaming for paper/live trading
- Data validation and quality checks mandatory
- Backup data sources for redundancy
- **Futures-specific**: Volume analysis with 20-period moving average baseline; 2x volume anomaly detection for confirmation; Session-based volume adjustments (US session 2.0x, overnight 0.3x)

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
1. Research phase: Backtest with 2+ years of MNQ data with tick-based risk management
2. Validation: Forward testing on unseen data with volume confirmation
3. Paper trading: Minimum 30 days with real-time data and futures-specific risk controls
4. Live deployment: Gradual position sizing increase with tick-level monitoring
5. Monitoring: Continuous performance tracking with futures metrics (tick P&L, volume analysis)
6. **Research Phase Exception**: Risk management implementation required but may be simplified for research validation; full production risk management required before live trading

### Testing Requirements
- Unit tests for all strategy components
- Integration tests with QuantConnect API
- Regression tests on strategy parameters
- Performance benchmarks for latency
- Risk management stress tests
- **Futures-specific**: Multi-timeframe FVG detection validation; Volume anomaly detection testing; Tick-based risk management validation; Confluence scoring accuracy tests

### Code Review Process
- All code changes require peer review
- Risk management logic review mandatory
- Performance impact assessment required
- Documentation updates enforced
- Compliance verification before deployment

## Futures Trading Addendum

### VI. Futures-Specific Requirements

**Risk Management**
- All stop-losses and take-profits MUST be specified in ticks (e.g., 20 ticks SL, 40 ticks TP)
- Position sizing MUST consider contract multiplier and tick value
- Daily loss limits enforced in dollars based on contract specifications
- Margin requirements monitored in real-time to prevent margin calls

**Volume Analysis**
- 20-period moving average baseline for volume anomaly detection
- 2x volume threshold for high-impact confirmation
- Session-based adjustments: US session 2.0x multiplier, overnight 0.3x multiplier
- Volume confirmation required before trade entry

**Multi-Timeframe Analysis**
- Complete timeframe coverage: 1-60 minutes in 1-minute intervals
- Confluence scoring: 70% timeframe alignment, 30% volume confirmation
- Batch processing must complete within 5 minutes for 1 day of data
- Real-time detection must process under 1 second latency

**Performance Validation**
- Sharpe ratio > 1.0 for strategy viability
- Maximum drawdown < $100 during backtesting
- Win rate > 45% with profit factor > 1.3
- Trade frequency: 5-20 trades per day maximum

**Data Requirements**
- MNQ (Micro E-mini Nasdaq-100) futures from CME only
- Tick-level data for backtesting and research
- Real-time streaming for paper/live trading
- Minimum 2 years historical data for validation

### VII. Research Phase Exception

**Scope**: Research-only features may implement simplified risk management for validation purposes, provided:
- Tick-based risk management principles are followed
- Volume analysis parameters are implemented
- Multi-timeframe requirements are met
- Full production risk management added before live trading

**Validation Requirements**:
- Backtesting on 2+ years of MNQ data
- Performance metrics meet minimum thresholds
- Edge case handling implemented (gaps, news, low volume)
- Constitution compliance verified before proceeding

## Governance

This constitution supersedes all other development practices. Amendments require:
- Written proposal with impact analysis
- Team consensus (75% approval)
- Migration plan for existing strategies
- Updated documentation and training

All PRs must verify compliance with this constitution. Complexity must be justified with performance or risk benefits. Use QuantConnect documentation for runtime development guidance.

**Version**: 1.1.1 | **Ratified**: 2025-10-20 | **Last Amended**: 2025-10-20

**Amendment 1.1.0 (2025-10-20)**: Added futures-specific requirements including tick-based risk management, volume analysis parameters, multi-timeframe performance requirements, and research phase risk management exception.

**Amendment 1.1.1 (2025-10-20)**: Updated maximum drawdown requirement from percentage-based (15%) to fixed dollar amount ($100) for futures trading risk management.
