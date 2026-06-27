# QQQ Opening Range Breakout (ORB) Strategy

## Strategy Overview

The Opening Range Breakout (ORB) strategy is a momentum-based trading strategy that capitalizes on the initial price movement after market open. The strategy identifies the high and low price range during the first N minutes of trading, then enters trades when price breaks out of this range.

**Underlying Logic:** The opening range represents the initial balance between buyers and sellers. A breakout above this range indicates bullish momentum, while a breakout below indicates bearish momentum.

---

## Entry Conditions

### Signal Generation

The strategy generates signals after the ORB window completes (09:30 + ORB_MINUTES).

**Long Entry Signal:**
- Condition: `close_price > ORB_high`
- Timing: Confirmed on bar close
- Requirement: `ALLOW_LONGS = True`

**Short Entry Signal:**
- Condition: `close_price < ORB_low`
- Timing: Confirmed on bar close
- Requirement: `ALLOW_SHORTS = True`

### Entry Execution

**Entry Price:** Next bar's open price after signal confirmation

**Slippage Adjustment:**
- Long: `entry_price = actual_open * (1 + SLIPPAGE)`
- Short: `entry_price = actual_open * (1 - SLIPPAGE)`

**Current Slippage:** 0.1% (0.001)

**Trade Limit:** Only first valid signal per day when `ONE_TRADE_PER_DAY = True`

---

## Exit Conditions

The strategy uses three exit triggers with the following priority:

### 1. Stop Loss (Highest Priority)

**Stop Placement:**
- Long trades: Stop at ORB low
- Short trades: Stop at ORB high

**Stop Hit Detection:**
- Long: Bar's low ≤ stop_price
- Short: Bar's high ≥ stop_price

**Rationale:** The opposite ORB boundary represents the invalidation point for the breakout thesis.

### 2. Take Profit

**Target Calculation:**
- Risk = `entry_price - stop_price` (long) or `stop_price - entry_price` (short)
- Target = `entry_price + (risk * RISK_REWARD)` (long) or `entry_price - (risk * RISK_REWARD)` (short)

**Current Risk-Reward Ratio:** 2.0 (target is 2x the risk)

**Target Hit Detection:**
- Long: Bar's high ≥ target_price
- Short: Bar's low ≤ target_price

### 3. End of Day (EOD) Exit

**Exit Window:** 15:55 - 16:00 (last 5 minutes of trading)

**Exit Price:** Bar's close price

**Rationale:** Prevents overnight risk and ensures all positions are flat before market close.

### OHLC Ambiguity Rule

If both stop loss and take profit are hit within the same bar:
- **Assumption:** Stop hit first (conservative)
- **Exit Price:** Stop price
- **Exit Reason:** 'stop'

This rule prevents optimistic assumptions about order fill priority.

---

## Risk Management

### Position Sizing

**Current Implementation:** Fixed position size (1 contract/share per signal)

**Future Enhancements:** 
- Risk-based sizing (e.g., 1% of equity per trade)
- Volatility-adjusted sizing

### Costs

**Commission:** $0.00 per trade leg (currently disabled)
**Slippage:** 0.1% applied to entry price

**Total Cost per Round-Trip:** `2 * COMMISSION + SLIPPAGE`

---

## Configuration Parameters

| Parameter | Current Value | Description |
|-----------|---------------|-------------|
| `ORB_MINUTES` | 15 | Duration of opening range window (minutes) |
| `RISK_REWARD` | 2.0 | Risk-to-reward ratio for take profit |
| `STOP_MODE` | "orb_low_high" | Stop loss placement method |
| `ALLOW_LONGS` | True | Enable long trades |
| `ALLOW_SHORTS` | True | Enable short trades |
| `ONE_TRADE_PER_DAY` | True | Limit to one signal per day |
| `COMMISSION` | 0.00 | Commission per trade leg ($USD) |
| `SLIPPAGE` | 0.001 | Slippage as decimal (0.1%) |

### Common ORB Window Values

- **5 minutes:** Very aggressive, more signals, higher noise
- **10 minutes:** Moderate balance
- **15 minutes:** Standard (current)
- **30 minutes:** Conservative, fewer signals, higher quality

---

## Code Implementation

### Key Functions

**1. ORB Calculation** (`compute_orb()`)
- Location: Lines 262-291
- Purpose: Calculate ORB high and low from first N minutes
- Returns: `(orb_high, orb_low)` tuple

**2. Signal Generation** (`generate_signals()`)
- Location: Lines 294-359
- Purpose: Detect breakouts after ORB window
- Returns: Signal dictionary or None

**3. Trade Execution** (`execute_trade()`)
- Location: Lines 366-510
- Purpose: Simulate realistic trade execution
- Returns: Trade object or None

**4. Main Loop** (`main()`)
- Location: Lines 729-871
- Purpose: Orchestrate complete backtest pipeline

---

## Strategy Characteristics

### Advantages

1. **Momentum Capture:** Identifies and rides intraday momentum
2. **Clear Rules:** Objective entry and exit criteria
3. **Risk Defined:** Stop loss known at entry
4. **Time-Based:** No overnight exposure
5. **Backtestable:** Fully deterministic implementation

### Disadvantages

1. **Whipsaws:** False breakouts in choppy markets
2. **Late Entries:** Entry at next bar open may miss initial move
3. **Fixed Stops:** ORB-based stops may be too tight/tight for volatility
4. **No Trend Filter:** Takes signals regardless of market regime
5. **Single Timeframe:** Only uses 1-minute data

### Best Market Conditions

- **Trending Days:** Strong directional moves after open
- **High Volatility:** Larger ORB ranges lead to clearer breakouts
- **Clear News Drivers:** Earnings, economic data, Fed announcements

### Worst Market Conditions

- **Choppy/Ranging:** Multiple false breakouts
- **Low Volatility:** Small ORB ranges, unclear signals
- **Gap Opens:** Large gaps may invalidate ORB concept

---

## Performance Metrics

The backtest computes the following metrics:

- **Total Return:** Percentage gain/loss on initial capital
- **Win Rate:** Percentage of profitable trades
- **Average Win:** Mean profit from winning trades
- **Average Loss:** Mean loss from losing trades
- **Expectancy:** Expected PnL per trade
- **Profit Factor:** Ratio of total wins to total losses
- **Max Drawdown:** Maximum peak-to-trough decline
- **Number of Trades:** Total trades executed
- **Average Duration:** Mean trade length in minutes

---

## Example Trade

**Scenario:**
- ORB window (09:30-09:45): High = $514.92, Low = $510.02
- 09:54: Close = $515.13 (breaks above ORB high)
- 09:55: Entry at open = $515.00 (with 0.1% slippage = $515.52)
- Stop = $510.02 (ORB low)
- Risk = $515.52 - $510.02 = $5.50
- Target = $515.52 + ($5.50 × 2.0) = $526.52

**Possible Outcomes:**
1. Price hits $510.02 → Stop loss, loss = $5.50
2. Price hits $526.52 → Take profit, gain = $11.00
3. 15:55+ with no stop/target → EOD exit at close

---

## Future Enhancements

### Planned Features

1. **Additional Stop Modes:**
   - Fixed percentage stops
   - ATR-based stops
   - Trailing stops

2. **Position Sizing:**
   - Risk-based sizing (fixed % of equity)
   - Volatility-adjusted sizing
   - Kelly criterion

3. **Filters:**
   - Trend filter (e.g., above/below 200 SMA)
   - Volume filter
   - Gap filter

4. **Multi-Timeframe:**
   - Higher timeframe confirmation
   - Support/resistance levels

5. **Optimization:**
   - Parameter optimization
   - Walk-forward testing
   - Monte Carlo simulation

---

## References

- **Specification:** `orb_backtester_full_spec.md`
- **Implementation:** `strategy.py`
- **Data:** `QQQ_clean_backtest.parquet` (1-minute OHLCV)

---

*Last Updated: June 26, 2026*
