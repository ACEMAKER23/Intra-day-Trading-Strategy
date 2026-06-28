# QQQ ORB Backtesting System - User Manual

## Quick Start

This system backtests Opening Range Breakout (ORB) strategies on QQQ 1-minute data and provides comprehensive analysis of results. Results are organized by strategy variant for easy comparison.

## Workflow Overview

```
1. Configure Strategy → 2. Run Backtest → 3. Run Analysis → 4. Review Results
```

---

## Step 1: Configure Strategy

### Strategy Selection
Edit `src/strategy.py` to select your strategy:

```python
# Strategy selection: choose which strategy to use
# Available strategies: "ORB" (Opening Range Breakout), "StrictBreakout"
STRATEGY_TYPE = "ORB"

# Strategy configuration parameters (passed to selected strategy)
STRATEGY_CONFIG = {
    'orb_minutes': 15,
    'allow_longs': True,
    'allow_shorts': True,
    'signal_cutoff_hour': 12
}
```

**Available Strategies:**

**ORB (Opening Range Breakout):**
- Basic breakout strategy with minimal constraints
- Triggers when price breaks OR high/low
- Configuration: `orb_minutes`, `allow_longs`, `allow_shorts`, `signal_cutoff_hour`

**StrictBreakout:**
- Enhanced breakout strategy with quality filters
- Requires candle body size >= 0.6 (abs(close-open)/(high-low))
- Requires close location in top/bottom 20% of candle
- Requires breakout threshold of 0.05% beyond OR level
- Configuration: `orb_minutes`, `allow_longs`, `allow_shorts`, `signal_cutoff_hour`, `min_body_ratio`, `min_close_location`, `breakout_threshold`

**StrictBreakout Example Configuration:**
```python
STRATEGY_TYPE = "StrictBreakout"
STRATEGY_CONFIG = {
    'orb_minutes': 15,
    'allow_longs': True,
    'allow_shorts': True,
    'signal_cutoff_hour': 12,
    'min_body_ratio': 0.6,
    'min_close_location': 0.8,
    'breakout_threshold': 0.05
}
```

**Why?** The modular strategy system allows you to easily switch between different trading strategies by changing the `STRATEGY_TYPE` and adjusting the `STRATEGY_CONFIG` parameters.

### Strategy Name (for folder organization)
Edit `src/strategy.py` line 29 to set your strategy name:

```python
STRATEGY_NAME = "orb_15min"  # Example: orb_15min, orb_20min, orb_long_only
```

**Why?** This organizes all data and results by strategy variant for comparison.

### Other Configuration
Edit `src/strategy.py` to change:
- `STRATEGY_CONFIG`: Strategy-specific parameters (varies by strategy)
- `RISK_REWARD`: Risk-to-reward ratio for take profit (default: 2.0)
- `INITIAL_CAPITAL`: Starting capital (default: $10,000)
- `COMMISSION`: Commission per trade (default: $0.00)

---

## Step 2: Run the Backtest

### Command
```bash
python src/strategy.py
```

### What It Does
- Loads QQQ data from `data/processed/QQQ_clean_backtest.parquet`
- Runs ORB strategy backtest
- Generates performance metrics in console
- Saves equity curve plot to `results/{STRATEGY_NAME}/backtest_results.png`
- Exports trade details to `data/processed/{STRATEGY_NAME}/trades.csv`

### Console Output
You'll see:
- Data loading and validation status
- Number of trading sessions built
- Number of trades generated
- Overall metrics (total return, win rate, profit factor, etc.)
- Long vs Short trade diagnostics
- Confirmation that trades were exported

---

## Step 3: Run the Analysis

### Command
```bash
python src/analyze_trades.py --strategy {STRATEGY_NAME}
```

**Example:**
```bash
python src/analyze_trades.py --strategy orb_15min
```

### What It Does
- Loads trades from `data/processed/{STRATEGY_NAME}/trades.csv`
- Computes comprehensive performance metrics
- Generates 13 visualization plots
- Creates summary report in `results/{STRATEGY_NAME}/analysis/summary.md`
- Creates AI-friendly summary in `results/{STRATEGY_NAME}/analysis/summary.json`

### Output Location
All analysis outputs go to `results/{STRATEGY_NAME}/analysis/`:
- `summary.md` - Detailed markdown report
- `summary.json` - Aggregated statistics
- `figures/` - 13 visualization PNG files

### Command-Line Options
- `--strategy`: Strategy name (required for folder organization)
- `--trades-csv`: Override default trades CSV path
- `--output-dir`: Override default output directory

---

## Step 4: Review Results

### 4.1 Check Overall Metrics

Open `results/{STRATEGY_NAME}/analysis/summary.md` and review:

**Overall Performance:**
- **Total Return**: Is it positive or negative?
- **Win Rate**: Above 50% is good
- **Profit Factor**: Above 1.0 means profitable
- **Max Drawdown**: How much did equity decline at worst?

**Key Questions:**
- Is the strategy profitable overall?
- Is the drawdown acceptable?
- Are wins larger than losses?

### 3.2 Compare Long vs Short

In the same file, find the "Long vs Short" section:

**Look for:**
- Which side has higher win rate?
- Which side has better profit factor?
- Is one side dragging down performance?

**Action:**
- If shorts perform poorly, consider setting `ALLOW_SHORTS = False`
- If longs perform poorly, consider setting `ALLOW_LONGS = False`

### 3.3 Analyze Exit Reasons

Find the "Exit Reason Summary" section:

**Exit Types:**
- **stop**: Trade hit stop loss (losing trade)
- **eod**: Trade held until end of day

**Key Insight:**
- High stop hit rate = stops are being triggered frequently
- High EOD rate = trades are surviving to day's end

### 3.4 Check Entry Timing

Find the "Entry Time Analysis" section:

**Time Windows:**
- 09:45-10:00: Early entries
- 10:00-10:30: Mid-morning
- 10:30-11:00: Late morning
- 11:00-12:00: Pre-noon

**Key Insight:**
- Which time window has best win rate?
- Which time window has best average R?
- Consider filtering to best-performing windows

### 3.5 Review OR Width Impact

Find the "OR Width Analysis" section:

**ORB Buckets:**
- 0.0-0.2%: Narrow opening ranges
- 0.2-0.4%: Small opening ranges
- 0.4-0.6%: Medium opening ranges
- 0.6-0.8%: Wide opening ranges
- >0.8%: Very wide opening ranges

**Key Insight:**
- Do narrow ranges perform better?
- Do wide ranges perform better?
- Consider filtering OR width based on results

### 4.6 Examine Visualizations

Open `results/{STRATEGY_NAME}/analysis/figures/` folder:

**1. equity_curve.png**
- Look at overall trend
- Check for major drawdowns
- Is growth consistent or volatile?

**2. pnl_histogram.png**
- Distribution of dollar PnL
- Are winners larger than losers?
- Is distribution skewed positive or negative?

**3. profit_R_histogram.png**
- Distribution of profit in R multiples
- Center around 0R = breakeven
- Right skew = more large winners
- Left skew = more large losers

**4. mfe_histogram.png**
- Maximum favorable excursion (best price)
- High MFE = trades had big unrealized gains
- Did you capture these gains or lose them?

**5. mae_histogram.png**
- Maximum adverse excursion (worst price)
- High MAE = trades went against you significantly
- Are stops too loose (allowing large MAE)?

**6. mfe_vs_profitR.png** (CRITICAL)
- Scatter plot: MFE (x-axis) vs Final Profit (y-axis)
- **Red zone**: High MFE + Negative Profit = Missed opportunities
- **Green zone**: High MFE + Positive Profit = Captured gains
- **Insight**: If many trades in red zone, exit management needs improvement

**7. mae_vs_profitR.png**
- Scatter plot: MAE (x-axis) vs Final Profit (y-axis)
- High MAE + Negative Profit = Stop too loose
- Low MAE + Negative Profit = Stop too tight
- **Insight**: Optimize stop placement based on MAE distribution

**8. orb_width_vs_profitR.png**
- Scatter plot: OR width (x-axis) vs Profit (y-axis)
- Red line shows trend
- **Insight**: Does OR width predict profitability?

**9. entry_time_boxplot.png**
- Box plots of profit by entry time window
- Median line = typical profit
- Box width = profit variability
- **Insight**: Which entry times are most reliable?

**10. monthly_returns.png**
- Bar chart of monthly PnL
- **Insight**: Is performance consistent across months?
- Are there seasonal patterns?

**11. exit_reason_bar.png**
- Bar chart of exit reason frequency
- **Insight**: How do trades typically end?
- Are stops being hit too often?

**12. long_short_bar.png**
- Grouped bar chart comparing long vs short
- Compares win rate, avg R, profit factor
- **Insight**: Which direction performs better?

---

## Decision Framework

### After Reviewing Results, Ask:

**Is the strategy profitable?**
- Yes → Proceed to optimization
- No → Consider parameter changes or different strategy

**Is drawdown acceptable?**
- Yes → Good risk management
- No → Reduce RISK_PER_EQUITY or tighten stops

**Are longs or shorts better?**
- Longs better → Set ALLOW_SHORTS = False
- Shorts better → Set ALLOW_LONGS = False
- Both similar → Keep both

**What's the best entry time?**
- Identify best window in summary.md
- Consider adding time filter to strategy

**Is OR width predictive?**
- Narrow ranges better → Filter for small OR width
- Wide ranges better → Filter for large OR width

**Are exits optimal?**
- Check mfe_vs_profitR.png
- Many missed opportunities (high MFE, negative profit) → Need better exit management

---

## Iteration Process

### 1. Change Parameters
Edit `src/strategy.py`:
```python
# Example changes
ORB_MINUTES = 20  # Try different ORB duration
RISK_PER_EQUITY = 0.005  # Reduce risk
ALLOW_SHORTS = False  # Only trade longs
```

### 2. Re-run Backtest
```bash
python src/strategy.py
```

### 3. Re-run Analysis
```bash
python src/analyze_trades.py
```

### 4. Compare Results
- Did performance improve?
- Did drawdown decrease?
- Is win rate higher?

### 5. Repeat Until Satisfied
- Iterate on parameters
- Test different configurations
- Document what works

---

## Common Analysis Patterns

### Pattern 1: High Win Rate, Low Profit Factor
- **Issue**: Many small wins, few large losses
- **Solution**: Reduce position size or tighten stops

### Pattern 2: Low Win Rate, High Profit Factor
- **Issue**: Few large wins, many small losses
- **Solution**: Acceptable if expectancy is positive

### Pattern 3: Consistent Monthly Losses
- **Issue**: Strategy not working in current market
- **Solution**: Pause trading or change strategy

### Pattern 4: Large MAE on Winning Trades
- **Issue**: Trades recover from big drawdowns
- **Solution**: Consider tighter stops to reduce pain

### Pattern 5: High MFE, Negative Final Profit
- **Issue**: Missing profitable moves
- **Solution**: Add take profit targets or trailing stops

---

## File Locations Reference

**Source Code:**
- `src/strategy.py` - Backtest engine
- `src/analyze_trades.py` - Analysis module

**Data Files:**
- `data/processed/QQQ_clean_backtest.parquet` - Input data (shared across strategies)
- `data/processed/{STRATEGY_NAME}/trades.csv` - Trade results (strategy-specific)

**Results (per strategy):**
- `results/{STRATEGY_NAME}/analysis/summary.md` - Analysis report
- `results/{STRATEGY_NAME}/analysis/summary.json` - AI summary
- `results/{STRATEGY_NAME}/analysis/figures/` - All plots
- `results/{STRATEGY_NAME}/backtest_results.png` - Equity curve

**Documentation:**
- `docs/strategy.md` - Strategy details
- `docs/analyze.md` - Analysis specs
- `docs/user_manual.md` - This file

---

## Adding New Strategies

The modular strategy system makes it easy to add new trading strategies:

### 1. Create Strategy Class
Create a new file in `src/strategies/` (e.g., `my_strategy.py`):

```python
from .base_strategy import BaseStrategy, Signal
import pandas as pd
from typing import List

class MyStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize strategy-specific parameters
        self.param1 = config.get('param1', default_value)
    
    def generate_signals(self, session_df: pd.DataFrame) -> List[Signal]:
        # Implement your signal generation logic
        signals = []
        # ... your logic here ...
        return signals
    
    def get_config(self) -> dict:
        return {'name': 'MyStrategy', 'param1': self.param1}
    
    def validate_config(self) -> bool:
        # Validate your configuration
        return True
```

### 2. Register Strategy
Add your strategy to `src/strategies/__init__.py`:

```python
from .my_strategy import MyStrategy
__all__ = ['BaseStrategy', 'ORBStrategy', 'MyStrategy']
```

### 3. Import and Use
Import your strategy in `src/strategy.py`:

```python
from strategies import ORBStrategy, MyStrategy
```

### 4. Select Strategy
Update the strategy selection in `src/strategy.py`:

```python
STRATEGY_TYPE = "MyStrategy"  # Change to your strategy name
STRATEGY_CONFIG = {
    'param1': value,
    # ... other parameters ...
}
```

### 5. Update Strategy Factory
Add your strategy to the strategy selection logic in `main()`:

```python
if STRATEGY_TYPE == "ORB":
    strategy = ORBStrategy(STRATEGY_CONFIG)
elif STRATEGY_TYPE == "MyStrategy":
    strategy = MyStrategy(STRATEGY_CONFIG)
else:
    print(f"ERROR: Unknown strategy type '{STRATEGY_TYPE}'")
    return
```
