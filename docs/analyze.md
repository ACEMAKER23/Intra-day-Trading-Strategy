# Trade Analysis Module Specification

## Objective

The purpose of this module is **not** to backtest the strategy. The backtester has already produced `trades.csv`.

This module exists to answer:

> **Why did the strategy perform the way it did?**

The output should allow both a human and an AI agent to understand the strategy's behavior within a few minutes without manually inspecting hundreds of trades.

---

# Input

The module accepts a CSV similar to:

| Column | Description |
|----------|-------------|
| entry_time | Timestamp of entry |
| exit_time | Timestamp of exit |
| direction | Long / Short |
| entry_price | Entry price |
| exit_price | Exit price |
| stop_price | Initial stop |
| position_size | Shares |
| pnl | Dollar PnL |
| pnl_pct | Percent PnL |
| exit_reason | Stop / EndOfDay / Target / etc |
| mfe | Maximum Favorable Excursion |
| mae | Maximum Adverse Excursion |
| profit_R | Profit measured in R |
| orb_width | Opening Range width ($) |
| orb_width_pct | Opening Range width (%) |

---

# Output

Generate:

```
analysis/
    summary.json
    summary.md
    figures/
        equity_curve.png
        pnl_histogram.png
        profit_R_histogram.png
        mfe_histogram.png
        mae_histogram.png
        mfe_vs_profitR.png
        orb_width_vs_profitR.png
        entry_time_boxplot.png
        monthly_returns.png
        exit_reason_bar.png
        long_short_bar.png
```

---

# Libraries

Use:

- pandas
- numpy
- matplotlib

Do NOT use seaborn.

---

# Numeric Summary

Generate a markdown table.

## Overall

| Metric | Value |
|---------|------:|
| Number of Trades | |
| Total Return | |
| CAGR (if applicable) | |
| Win Rate | |
| Loss Rate | |
| Average Winner | |
| Average Loser | |
| Profit Factor | |
| Expectancy ($) | |
| Expectancy (R) | |
| Max Drawdown | |
| Average Holding Time | |
| Median Holding Time | |

---

## Long vs Short

| Metric | Long | Short |
|---------|------:|------:|
| Trades | | |
| Win Rate | | |
| Avg Win | | |
| Avg Loss | | |
| Profit Factor | | |
| Avg R | | |
| Total PnL | | |

Purpose:

Determine whether one side of the strategy is responsible for poor performance.

---

## Exit Reason Summary

| Exit Reason | Trades | Avg R | Win Rate |
|--------------|-------:|------:|----------:|

Purpose:

Understand how trades are ending.

Example:

- Stop Loss
- End Of Day
- Profit Target
- Trailing Stop

---

## OR Width Analysis

Create buckets.

Example:

```
0.0 - 0.2%
0.2 - 0.4%
0.4 - 0.6%
0.6 - 0.8%
>0.8%
```

Report

| OR Width Bucket | Trades | Avg R | Win Rate |
|-----------------|-------:|------:|----------:|

Purpose:

Determine whether large OR ranges reduce profitability.

---

## Entry Time Analysis

Group entries into windows.

Example

```
09:35-09:45
09:45-10:00
10:00-10:30
10:30-11:00
11:00-12:00
```

Report

| Entry Window | Trades | Avg R | Win Rate |
|---------------|-------:|------:|----------:|

Purpose:

Determine whether later entries perform worse.

---

## Holding Time Analysis

Compute

```
holding_time = exit_time - entry_time
```

Report

| Metric | Winners | Losers |
|----------|--------:|-------:|
| Mean | | |
| Median | | |
| Max | | |

Purpose:

Determine whether winners finish quickly while losers linger.

---

# Visualizations

---

## 1. Equity Curve

Line chart.

X-axis

Trading date

Y-axis

Portfolio equity

Purpose

Quickly evaluate

- growth
- stagnation
- drawdown

---

## 2. PnL Histogram

Histogram

X-axis

Dollar PnL

Y-axis

Trade count

Purpose

Understand profit distribution.

---

## 3. Profit in R Histogram

Histogram

X-axis

profit_R

Y-axis

Trade count

Purpose

Determine

- average trade
- skew
- fat tails
- frequency of large winners

---

## 4. MFE Histogram

Histogram

X-axis

MFE

Purpose

Measure how much unrealized profit trades typically achieve.

---

## 5. MAE Histogram

Histogram

X-axis

MAE

Purpose

Understand adverse movement before exit.

---

## 6. MFE vs Final Profit (Most Important)

Scatter plot.

X-axis

MFE

Y-axis

profit_R

Purpose

Determine whether profitable opportunities are being missed.

Interpretation:

If many losing trades have

```
MFE > 1R
```

but

```
Final Profit = -1R
```

then exit management is likely poor.

---

## 7. MAE vs Profit

Scatter plot.

X-axis

MAE

Y-axis

profit_R

Purpose

Determine whether stops are too tight or too loose.

---

## 8. OR Width vs Profit

Scatter plot.

X-axis

orb_width_pct

Y-axis

profit_R

Overlay a moving average or bin averages.

Purpose

Determine whether opening range size predicts profitability.

---

## 9. Box Plot of Entry Time

Convert entry time into minutes after market open.

Example

```
09:36 -> 6

09:45 -> 15

10:15 -> 45
```

Produce a box plot grouped by entry window.

Purpose

Understand how entry timing influences returns.

---

## 10. Monthly Returns

Bar chart.

X-axis

Month

Y-axis

Total Return

Purpose

Determine whether strategy performance is consistent over time.

---

## 11. Exit Reason Frequency

Bar chart.

X-axis

Exit reason

Y-axis

Trade count

Purpose

Quickly understand how trades terminate.

---

## 12. Long vs Short Performance

Grouped bar chart.

Compare

- Win Rate
- Avg R
- Profit Factor

Purpose

Determine whether long and short trades behave differently.

---

# AI-Friendly Summary

Generate `summary.json`.

Example

```json
{
  "total_return": -35.31,
  "profit_factor": 0.77,
  "expectancy_R": -0.12,
  "best_entry_window": "09:35-09:45",
  "worst_entry_window": "10:30-12:00",
  "best_or_width_bucket": "0.2%-0.4%",
  "worst_or_width_bucket": ">0.8%",
  "long_profit_factor": 1.08,
  "short_profit_factor": 0.56,
  "avg_mfe": 1.32,
  "avg_mae": 0.94,
  "largest_drawdown": -42.5
}
```

This file should contain only aggregated statistics that can be consumed by downstream AI agents without parsing raw trade data.

---

# Design Principles

1. Never inspect raw CSV rows manually.
2. Aggregate before interpreting.
3. Every visualization should answer a specific research question.
4. Every metric should help explain *why* the strategy succeeded or failed.
5. The report should be reproducible and generated automatically after every backtest.
6. All charts should include clear titles, axis labels, and grid lines.
7. Save every figure as a high-resolution PNG (e.g., 300 DPI) for inclusion in reports.

---

# Deliverables

The implementation should expose a single entry point:

```python
generate_analysis(
    trades_csv="results/trades.csv",
    output_dir="analysis/"
)
```

Running this function should automatically:

1. Load the trade CSV.
2. Compute all summary statistics.
3. Generate every table.
4. Generate every visualization.
5. Write `summary.md`.
6. Write `summary.json`.
7. Save all figures under `analysis/figures/`.

The analysis should be fully automated and require no manual intervention after each backtest.