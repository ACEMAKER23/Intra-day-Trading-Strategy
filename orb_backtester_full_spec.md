
# QQQ ORB Backtesting System — Full Project Specification

## 0. Objective

Build a complete, extensible intraday backtesting system for QQQ 1-minute OHLCV data.

The system must:
- Evaluate Opening Range Breakout (ORB) strategies
- Support long and short trades
- Simulate realistic execution (stop, target, EOD exit)
- Produce statistically valid performance metrics
- Be extensible to other strategies (VWAP, EMA, mean reversion, etc.)

---

## 1. Data Requirements

### Input Data Format (Parquet)

Required columns:

```
open, high, low, close
volume, vw, n
```

Index:
- Pandas `DatetimeIndex`
- Timezone-aware (US/Eastern preferred)
- 1-minute bars

---

## 2. Core Design Principles

### 2.1 Deterministic Simulation
Backtest must produce identical results for identical inputs.

### 2.2 No Lookahead Bias
No future data can be used in signal generation.

### 2.3 OHLC Ambiguity Handling
If both stop and target are touched in the same candle:
- Default: conservative assumption (stop hit first)

### 2.4 Session-Based Logic
All strategies operate per trading day:
- 09:30 → 16:00 only

---

## 3. System Architecture

Single-file modular architecture:

```
strategy.py
│
├── Configuration
├── Data Loader
├── Data Validator
├── Session Builder
├── Indicator Layer
├── Strategy Layer (ORB)
├── Execution Engine
├── Risk Management
├── Portfolio Simulation
├── Metrics Engine
├── Visualization
└── main()
```

---

## 4. Configuration Layer

Must support:

```python
DATA_PATH

INITIAL_CAPITAL

ORB_MINUTES

RISK_REWARD

STOP_MODE:
    - "orb_low_high"
    - "fixed_pct"
    - "atr"

ALLOW_LONGS
ALLOW_SHORTS

ONE_TRADE_PER_DAY

COMMISSION
SLIPPAGE
```

---

## 5. Data Loader

Responsibilities:
- Load parquet file
- Ensure correct dtypes
- Preserve timezone
- Sort index

---

## 6. Data Validator

Must validate:

### Structural
- DatetimeIndex exists
- No duplicate timestamps
- Sorted index

### Column integrity
- All required columns exist
- No NaNs in OHLCV

### OHLC correctness
For each row:

```
high >= max(open, close)
low <= min(open, close)
high >= low
```

---

## 7. Session Builder

Split data into daily sessions:

Output format:

```
Dict[
    date -> DataFrame
]
```

Rules:
- Only include 09:30–16:00 bars
- Drop incomplete sessions (optional toggle)

---

## 8. ORB Engine

For each session:

### Step 1: Compute ORB window

```
09:30 → 09:30 + ORB_MINUTES
```

Compute:

```
ORB_HIGH = max(high)
ORB_LOW  = min(low)
```

---

### Step 2: Generate signals

Long condition:

```
close > ORB_HIGH
```

Short condition:

```
close < ORB_LOW
```

Rules:
- First valid signal per day only (configurable)
- Signal confirmed on bar close
- We only initalize trade and find signal before noon.

---

## 9. Trade Execution Engine

### Entry
- Entry price = next bar open (default realistic)
- Apply slippage

---

### Stop Loss
Long:
```
stop = ORB_LOW (default)
```

Short:
```
stop = ORB_HIGH
```

---

### Take Profit
```
target = entry ± (risk * RISK_REWARD)
```

---

### Exit Rules

Exit if:
1. Stop hit
2. Target hit
3. End of day (15:55–16:00)

---

### OHLC Ambiguity Rule

If within same candle:
- stop and target both touched → assume stop first

---

## 10. Position Sizing

Default:

```
position_size = fixed contracts OR fixed dollar risk
```

Optional:

```
risk_per_trade = 1% of equity
```

---

## 11. Trade Object

```python
Trade:
    date
    direction

    entry_time
    exit_time

    entry_price
    exit_price

    stop_price
    target_price

    pnl
    pnl_pct

    exit_reason
```

---

## 12. Portfolio Engine

Tracks:

- equity curve
- realized PnL
- drawdowns

Formula:

```
equity[t] = equity[t-1] + pnl[t]
```

---

## 13. Metrics Engine

Must compute:

### Core metrics
- total return
- win rate
- average win
- average loss
- expectancy

### Risk metrics
- max drawdown
- Sharpe ratio (optional)
- profit factor

### Trade stats
- number of trades
- average trade duration

---

## 14. Visualization

Required plots:

- Equity curve
- Drawdown curve
- Trade distribution histogram

Optional:
- Daily PnL bar chart

---

## 15. Output

### Trade Log CSV

```
trades.csv
```

Columns:
- entry_time
- exit_time
- direction
- pnl
- reason

---

### Metrics Report

Printed summary:

```
Total Return:
Win Rate:
Expectancy:
Profit Factor:
Max Drawdown:
```

---

## 16. Extensibility Layer

Design must allow swapping:

### Entry logic
- ORB (current)
- EMA crossover
- VWAP reversion
- Breakout

### Exit logic
- fixed R:R
- trailing stop
- time-based exit

---

## 17. Future Extensions

System must later support:

- Options PnL mapping
- Multi-timeframe confirmation
- Walk-forward testing
- Monte Carlo simulation
- Parameter optimization

---

## 18. Success Criteria

A strategy is considered valid if:

- Tested on ≥ 100 trades
- Positive expectancy after costs
- Stable out-of-sample performance
- Reasonable drawdown (<20–30% for intraday systems)

---

## 19. Main Execution Flow

```
load data
validate data
build sessions

for each day:
    compute ORB
    generate signal
    simulate trade
    record result

compute metrics
plot results
export CSV
```

---

## END OF SPEC
