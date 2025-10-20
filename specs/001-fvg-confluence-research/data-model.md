# Data Model: FVG Confluence Trading Strategy

**Date**: 2025-10-20  
**Feature**: FVG Confluence Trading Strategy Research

## Core Entities

### FairValueGap
Represents a price imbalance created by three-candle patterns.

**Fields**:
- `id`: string - Unique identifier (timestamp_timeframe_type)
- `type`: enum - "bullish" | "bearish"
- `timeframe`: integer - Timeframe in minutes (1-60)
- `timestamp`: datetime - Formation time
- `high_price`: decimal - Upper boundary of gap
- `low_price`: decimal - Lower boundary of gap
- `gap_size`: decimal - Size of price gap
- `is_filled`: boolean - Whether gap has been filled
- `fill_time`: datetime - When gap was filled (null if not filled)
- `volume_at_formation`: decimal - Volume when gap formed
- `volume_anomaly_score`: decimal - Volume deviation from average (0-1)

**Validation Rules**:
- `timeframe` must be between 1 and 60
- `gap_size` must be > 0
- `high_price` must be > `low_price`
- `volume_anomaly_score` between 0 and 1

### ConfluenceScore
Represents the strength of FVG alignment across multiple timeframes.

**Fields**:
- `id`: string - Unique identifier
- `price_level`: decimal - Price level where confluence occurs
- `timestamp`: datetime - Calculation time
- `timeframe_count`: integer - Number of timeframes with FVG at this level (1-60)
- `weighted_score`: decimal - Confluence strength (0-100)
- `volume_confirmation`: boolean - Volume anomaly present
- `volume_weight`: decimal - Volume contribution to score
- `timeframe_weights`: object - Individual timeframe contributions (1-60 minutes)
- `ml_importance_score`: decimal - ML-calculated timeframe importance (0-1)

**Validation Rules**:
- `timeframe_count` between 1 and 60
- `weighted_score` between 0 and 100
- `volume_weight` between 0 and 1
- `ml_importance_score` between 0 and 1

### TradeSetup
Represents a complete trading opportunity with all required parameters.

**Fields**:
- `id`: string - Unique identifier
- `confluence_id`: string - Reference to confluence score
- `timestamp`: datetime - Setup identification time
- `entry_price`: decimal - Suggested entry price
- `stop_loss_price`: decimal - ML-calculated dynamic stop loss level
- `target_price`: decimal - ML-calculated dynamic profit target
- `direction`: enum - "long" | "short"
- `risk_amount`: decimal - Risk in dollars
- `potential_reward`: decimal - Potential profit in dollars
- `risk_reward_ratio`: decimal - Risk/reward ratio
- `confidence_score`: decimal - Overall setup confidence (0-1)
- `timeframe_signals`: array - Contributing timeframes (1-60 minutes)
- `volume_profile_poc`: decimal - Volume Profile Point of Control
- `ml_stop_loss_factors`: object - ML factors influencing stop loss calculation
- `ml_target_factors`: object - ML factors influencing target calculation

**Validation Rules**:
- `risk_amount` > 0
- `potential_reward` > 0
- `risk_reward_ratio` > 0
- `confidence_score` between 0 and 1

### PerformanceMetrics
Represents strategy performance statistics.

**Fields**:
- `id`: string - Unique identifier
- `period_start`: datetime - Analysis period start
- `period_end`: datetime - Analysis period end
- `total_trades`: integer - Number of trades executed
- `winning_trades`: integer - Number of profitable trades
- `losing_trades`: integer - Number of losing trades
- `win_rate`: decimal - Percentage of winning trades
- `profit_factor`: decimal - Total profit / total loss
- `max_drawdown`: decimal - Maximum peak-to-trough decline
- `sharpe_ratio`: decimal - Risk-adjusted return metric
- `average_trade_duration`: decimal - Average time in trade (hours)
- `total_return`: decimal - Percentage return over period
- `volatility`: decimal - Standard deviation of returns

**Validation Rules**:
- `total_trades` = `winning_trades` + `losing_trades`
- `win_rate` between 0 and 1
- `max_drawdown` >= 0

## Entity Relationships

```
FairValueGap (1) -----> (1) ConfluenceScore
    |                          |
    |                          |
    +-----> (1) TradeSetup <----+
              |
              |
              v
        PerformanceMetrics
```

**Relationship Rules**:
- Multiple `FairValueGap` entities (across 1-60 timeframes) can contribute to one `ConfluenceScore`
- Each `TradeSetup` is derived from one `ConfluenceScore` with ML-enhanced calculations
- `PerformanceMetrics` aggregates results from multiple `TradeSetup` entities
- ML models provide dynamic factors for entry/exit calculations

## State Transitions

### FairValueGap Lifecycle
```
DETECTED → ACTIVE → FILLED → EXPIRED
    ↓         ↓        ↓        ↓
  New      Monitoring Completed  Archived
```

**Transition Rules**:
- `DETECTED` → `ACTIVE`: Gap confirmed with volume analysis
- `ACTIVE` → `FILLED`: Price trades through gap boundaries
- `FILLED` → `EXPIRED`: Gap filled and no longer relevant
- `ACTIVE` → `EXPIRED`: Gap not filled within time limit (e.g., 24 hours)

### TradeSetup Lifecycle
```
IDENTIFIED → EVALUATED → EXECUTED → CLOSED
     ↓           ↓          ↓        ↓
   New       Analysis   Active   Completed
```

**Transition Rules**:
- `IDENTIFIED` → `EVALUATED`: Risk parameters calculated
- `EVALUATED` → `EXECUTED`: Trade meets all criteria and is executed
- `EXECUTED` → `CLOSED`: Trade reaches target or stop loss

## Data Constraints

### Performance Requirements
- Process 1 day of tick data in <5 minutes
- Real-time processing latency <1 second
- Support 2 years of historical data
- Handle 60 concurrent timeframe analyses

### Data Quality Rules
- Price data must be chronologically ordered
- Volume data must be non-negative
- Gaps smaller than 0.25 points are filtered out
- Volume anomalies require minimum 1000 contracts

### Business Rules
- Maximum 20 trades per day
- Maximum 2% risk per trade
- Minimum risk/reward ratio of 1:1.5
- FVGs older than 24 hours are excluded

## Indexing Strategy

### Primary Indices
- `FairValueGap.timestamp` (time-series queries)
- `FairValueGap.timeframe` (timeframe filtering)
- `ConfluenceScore.weighted_score` (ranking)
- `TradeSetup.timestamp` (trade history)

### Composite Indices
- `(FairValueGap.timestamp, FairValueGap.timeframe)` (multi-timeframe analysis)
- `(TradeSetup.confidence_score, TradeSetup.timestamp)` (setup selection)
- `(PerformanceMetrics.period_start, PerformanceMetrics.period_end)` (period analysis)

## Data Retention Policy

### Hot Data (Active Access)
- Current day FVGs and trade setups
- Last 30 days of performance metrics
- Real-time market data

### Warm Data (Occasional Access)
- 1-12 months of historical FVGs
- Quarterly performance aggregations
- Backtesting results

### Cold Data (Archive)
- 1+ years of historical data
- Completed research projects
- Deprecated strategy versions

### Retention Periods
- Tick data: 2 years (as per requirements)
- FVG data: 2 years
- Trade data: 5 years (regulatory compliance)
- Performance metrics: 10 years