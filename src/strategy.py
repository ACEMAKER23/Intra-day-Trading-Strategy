"""
QQQ ORB Backtester

Author: Haochen Tang
Description:
    Modular backtesting system supporting multiple trading strategies.
    Currently supports Opening Range Breakout (ORB) strategy.

Future features:
    - More strategy implementations
    - Options simulator
    - Position sizing
    - Walk-forward testing
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from strategies import ORBStrategy

# ==========================================
# CONFIGURATION
# ==========================================

# Strategy name for folder organization
# Used to organize data and results by strategy variant
# Example: "orb_15min", "orb_20min", "orb_long_only"
STRATEGY_NAME = "default"

# Strategy selection: choose which strategy to use
# Available strategies: "ORB" (Opening Range Breakout)
STRATEGY_TYPE = "ORB"

# Strategy configuration parameters (passed to selected strategy)
STRATEGY_CONFIG = {
    'orb_minutes': 15,
    'allow_longs': True,
    'allow_shorts': True,
    'signal_cutoff_hour': 12
}

# Path to the parquet file containing QQQ 1-minute OHLCV data
# This file should have columns: open, high, low, close, volume
DATA_PATH = Path("data/processed/QQQ_clean_backtest.parquet")

# Starting capital for the backtest simulation in dollars
# This is the initial equity value before any trades are executed
INITIAL_CAPITAL = 10000

# Risk-to-reward ratio for take profit calculation
# For every $1 of risk (distance to stop loss), target $R of profit
# Example: 2.0 means target is 2x the risk distance
# Higher values require larger moves but may reduce win rate
RISK_REWARD = 2.0

# Method for determining stop loss placement
# "orb_low_high": Stop at ORB low for longs, ORB high for shorts (default)
# "fixed_pct": Fixed percentage stop (not yet implemented)
# "atr": Average True Range based stop (not yet implemented)
STOP_MODE = "orb_low_high"

# Whether to limit to one trade per day
# When True: only the first valid signal per day is executed
# When False: multiple signals can be executed in same day (not recommended for ORB)
ONE_TRADE_PER_DAY = True

# Commission cost per trade in dollars
# Applied to both entry and exit (total cost = COMMISSION * 2)
# Set to 0.00 for commission-free backtesting
# Example: 1.00 means $1 commission per trade leg ($2 total per round-trip)
COMMISSION = 0.00

# Slippage as a decimal fraction (0.01 = 1%)
# Simulates price movement between signal and execution
# For longs: entry_price = actual_price * (1 + SLIPPAGE)
# For shorts: entry_price = actual_price * (1 - SLIPPAGE)
# Set to 0.00 for no slippage (ideal execution)
# Example: 0.001 means 0.1% slippage
SLIPPAGE = 0.001

# Whether to export trade log to CSV file
# When True: trades are saved to TRADES_OUTPUT path
# When False: no CSV file is created
EXPORT_TRADES = True

# File path for CSV export of trade log
# Contains columns: entry_time, exit_time, direction, entry_price, exit_price, pnl, pnl_pct, exit_reason
# Only created if EXPORT_TRADES is True
TRADES_OUTPUT = Path(f"../data/processed/{STRATEGY_NAME}/trades.csv")

# Percentage of equity to risk per trade (as decimal)
# Position size is calculated to ensure maximum loss = equity * RISK_PER_EQUITY
# Example: 0.01 means 1% of equity risked per trade
RISK_PER_EQUITY = 0.01

# ==========================================
# TRADE DATA CLASS
# ==========================================

@dataclass
class Trade:
    date: str
    direction: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    stop_price: float
    position_size: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    mfe: float  # Maximum Favorable Excursion (best price during trade)
    mae: float  # Maximum Adverse Excursion (worst price during trade)
    profit_R: float  # Profit in R multiples (pnl / risk_per_share)
    orb_width: float  # ORB width in absolute price terms
    orb_width_pct: float  # ORB width as percentage of entry price

# ==========================================
# LOAD DATA
# ==========================================

def load_data(path: Path) -> pd.DataFrame:
    """
    PURPOSE: Load OHLCV data from parquet file and clean it for backtesting.

    INPUTS:
        path (Path): Path to the parquet file containing OHLCV data

    OUTPUTS:
        pd.DataFrame: Cleaned DataFrame with OHLCV columns, no NaN values

    CHANGES:
        - Reads parquet file from disk
        - Drops rows with NaN values in any column
        - Prints count of dropped rows if any

    SIDE EFFECTS:
        - Prints message about dropped NaN rows
    """

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_parquet(path)

    # Drop rows with NaN values
    initial_len = len(df)
    df = df.dropna()
    dropped = initial_len - len(df)

    if dropped > 0:
        print(f"Dropped {dropped} rows with NaN values.")

    return df


# ==========================================
# DATA VALIDATOR
# ==========================================

def validate_data(df: pd.DataFrame) -> None:
    """
    PURPOSE: Validate that the loaded data meets all requirements for backtesting.

    INPUTS:
        df (pd.DataFrame): DataFrame to validate

    OUTPUTS:
        None: Function raises ValueError if validation fails

    CHANGES:
        - No data modifications
        - Only performs validation checks

    VALIDATION CHECKS:
        - DatetimeIndex exists and is timezone-aware
        - No duplicate timestamps
        - Index is sorted chronologically
        - Required columns exist (open, high, low, close, volume)
        - No NaN values in OHLCV columns
        - OHLC relationships are valid (high >= max(open,close), low <= min(open,close))

    SIDE EFFECTS:
        - Prints "Data validation passed" if successful
        - Raises ValueError with specific message if validation fails
    """
    # Check for DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Data must have DatetimeIndex")

    # Check for duplicates
    if df.index.duplicated().any():
        raise ValueError("Data contains duplicate timestamps")

    # Check if sorted
    if not df.index.is_monotonic_increasing:
        raise ValueError("Data index is not sorted")

    # Check required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Check for NaNs in OHLCV
    ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
    if df[ohlcv_cols].isna().any().any():
        raise ValueError("OHLCV columns contain NaN values")

    # Check OHLC correctness
    invalid_high = df['high'] < df[['open', 'close']].max(axis=1)
    invalid_low = df['low'] > df[['open', 'close']].min(axis=1)
    invalid_hl = df['high'] < df['low']

    if invalid_high.any():
        raise ValueError("High < max(open, close) in some rows")
    if invalid_low.any():
        raise ValueError("Low > min(open, close) in some rows")
    if invalid_hl.any():
        raise ValueError("High < Low in some rows")

    print("Data validation passed.")


# ==========================================
# SESSION BUILDER
# ==========================================

def build_sessions(df: pd.DataFrame) -> dict:
    """
    PURPOSE: Split continuous OHLCV data into daily trading sessions.

    INPUTS:
        df (pd.DataFrame): Continuous OHLCV data with DatetimeIndex

    OUTPUTS:
        dict: Dictionary mapping date (datetime.date) to DataFrame of that day's session

    CHANGES:
        - Converts timezone to US/Eastern if not set
        - Filters data to only include 09:30-16:00 trading hours
        - Groups data by date into separate DataFrames

    SIDE EFFECTS:
        - Prints count of built sessions
    """
    sessions = {}

    # Ensure timezone is set
    if df.index.tz is None:
        df = df.tz_localize('US/Eastern')
    else:
        df = df.tz_convert('US/Eastern')

    # Filter to trading hours
    df = df.between_time('09:30', '16:00')

    # Group by date
    for date, group in df.groupby(df.index.date):
        sessions[date] = group

    print(f"Built {len(sessions)} trading sessions.")
    return sessions


# ==========================================
# ORB ENGINE
# ==========================================
# TRADE EXECUTION ENGINE
# ==========================================

def execute_trade(session_df: pd.DataFrame, signal: dict, current_equity: float) -> Optional[Trade]:
    """
    PURPOSE: Simulate realistic trade execution with stop loss, take profit, and EOD exit.

    INPUTS:
        session_df (pd.DataFrame): DataFrame containing one day's OHLCV data
        signal (dict): Signal dictionary from generate_signals()
        current_equity (float): Current portfolio equity for position sizing

    OUTPUTS:
        Optional[Trade]: Trade object with complete trade details, or None if execution fails

    CHANGES:
        - No data modifications to session_df
        - Creates new Trade object with simulated execution results

    EXECUTION LOGIC:
        - Entry: Next bar open price after signal
        - Slippage: Applied to entry price based on direction
        - Stop Loss: ORB low for longs, ORB high for shorts
        - Take Profit: Entry + (risk * RISK_REWARD)
        - Position Sizing: Based on RISK_PER_EQUITY (1% of equity risked per trade)
        - Exit Conditions: Stop hit, target hit, or EOD (15:55-16:00)
        - OHLC Ambiguity: If both stop and target hit in same bar, stop assumed first
        - Commission: Applied to PnL calculation

    SIDE EFFECTS:
        - None
    """
    signal_time = signal['signal_time']
    direction = signal['direction']
    orb_high = signal['orb_high']
    orb_low = signal['orb_low']

    # Entry at next bar open
    signal_idx = session_df.index.get_loc(signal_time)
    if signal_idx + 1 >= len(session_df):
        return None

    entry_bar = session_df.iloc[signal_idx + 1]
    entry_time = entry_bar.name
    entry_price = entry_bar['open']

    # Apply slippage
    if direction == 'long':
        entry_price = entry_price * (1 + SLIPPAGE)
    else:
        entry_price = entry_price * (1 - SLIPPAGE)

    # Set stop loss at ORB boundary
    if direction == 'long':
        stop_price = orb_low
    else:
        stop_price = orb_high

    # Calculate risk per share for position sizing
    if direction == 'long':
        risk_per_share = entry_price - stop_price
    else:
        risk_per_share = stop_price - entry_price

    # Calculate position size based on risk per trade (1% of equity)
    # position_size = (equity * risk_percent) / risk_per_share
    risk_amount = current_equity * RISK_PER_EQUITY
    position_size = risk_amount / risk_per_share

    # Calculate ORB width
    orb_width = orb_high - orb_low
    orb_width_pct = orb_width / entry_price

    # Simulate trade execution
    exit_price = None
    exit_reason = None
    mfe = 0.0  # Maximum Favorable Excursion
    mae = 0.0  # Maximum Adverse Excursion

    # Start checking from entry bar onwards
    for idx in range(signal_idx + 1, len(session_df)):
        bar = session_df.iloc[idx]
        bar_time = bar.name

        # Track MFE and MAE
        if direction == 'long':
            favorable = bar['high'] - entry_price
            adverse = entry_price - bar['low']
        else:
            favorable = entry_price - bar['low']
            adverse = bar['high'] - entry_price

        mfe = max(mfe, favorable)
        mae = max(mae, adverse)

        # EOD exit (15:55-16:00) - only exit condition
        if bar_time.hour == 15 and bar_time.minute >= 55:
            exit_price = bar['close']
            exit_reason = 'eod'
            break

        # Check stop loss
        stop_hit = False

        if direction == 'long':
            if bar['low'] <= stop_price:
                stop_hit = True
        else:
            if bar['high'] >= stop_price:
                stop_hit = True

        if stop_hit:
            exit_price = stop_price
            exit_reason = 'stop'
            break

    # If no exit triggered (shouldn't happen with EOD exit)
    if exit_price is None:
        last_bar = session_df.iloc[-1]
        exit_price = last_bar['close']
        exit_reason = 'eod'

    # Calculate PnL (multiplied by position size)
    if direction == 'long':
        pnl_per_share = exit_price - entry_price
        pnl = pnl_per_share * position_size
        pnl_pct = (exit_price - entry_price) / entry_price
    else:
        pnl_per_share = entry_price - exit_price
        pnl = pnl_per_share * position_size
        pnl_pct = (entry_price - exit_price) / entry_price

    # Apply commission (per share)
    total_commission = COMMISSION * 2 * position_size  # Entry and exit
    pnl -= total_commission

    # Calculate profit in R multiples (before commission)
    profit_R = pnl_per_share / risk_per_share

    # Create Trade object
    trade = Trade(
        date=str(session_df.index[0].date()),
        direction=direction,
        entry_time=entry_time,
        exit_time=bar_time,
        entry_price=entry_price,
        exit_price=exit_price,
        stop_price=stop_price,
        position_size=position_size,
        pnl=pnl,
        pnl_pct=pnl_pct,
        exit_reason=exit_reason,
        mfe=mfe,
        mae=mae,
        profit_R=profit_R,
        orb_width=orb_width,
        orb_width_pct=orb_width_pct
    )

    return trade


# ==========================================
# PORTFOLIO ENGINE
# ==========================================

def simulate_portfolio(trades: List[Trade]) -> dict:
    """
    PURPOSE: Calculate portfolio equity curve and drawdowns from executed trades.

    INPUTS:
        trades (List[Trade]): List of executed Trade objects

    OUTPUTS:
        dict: Dictionary containing:
            - equity_curve (pd.Series): Portfolio value after each trade
            - drawdowns (pd.Series): Percentage drawdown at each point
            - max_drawdown (float): Maximum drawdown percentage

    CHANGES:
        - No modifications to input trades
        - Creates new equity and drawdown series

    CALCULATION:
        - Equity starts at INITIAL_CAPITAL
        - Each trade's PnL is added cumulatively
        - Drawdowns calculated as (equity - running_max) / running_max

    SIDE EFFECTS:
        - None
    """
    equity = [INITIAL_CAPITAL]
    equity_curve = pd.Series(equity, index=[pd.Timestamp.now()])

    cumulative_pnl = 0
    drawdowns = []

    for trade in trades:
        cumulative_pnl += trade.pnl
        new_equity = INITIAL_CAPITAL + cumulative_pnl
        equity.append(new_equity)

    equity_series = pd.Series(equity)

    # Calculate drawdowns
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = drawdown.min()

    return {
        'equity_curve': equity_series,
        'drawdowns': drawdown,
        'max_drawdown': max_drawdown
    }


# ==========================================
# METRICS ENGINE
# ==========================================

def compute_metrics(trades: List[Trade], portfolio: dict) -> dict:
    """
    PURPOSE: Calculate comprehensive performance metrics for the backtest.

    INPUTS:
        trades (List[Trade]): List of executed Trade objects
        portfolio (dict): Portfolio dictionary from simulate_portfolio()

    OUTPUTS:
        dict: Dictionary containing:
            - total_return (float): Total return as percentage of initial capital
            - win_rate (float): Percentage of winning trades
            - average_win (float): Average profit from winning trades
            - average_loss (float): Average loss from losing trades
            - expectancy (float): Expected PnL per trade
            - max_drawdown (float): Maximum drawdown percentage
            - profit_factor (float): Ratio of total wins to total losses
            - num_trades (int): Total number of trades
            - avg_duration (float): Average trade duration in minutes
            - long_trades (dict): Separate metrics for long trades
            - short_trades (dict): Separate metrics for short trades

    CHANGES:
        - No modifications to input data
        - Only computes and returns metrics

    SIDE EFFECTS:
        - None
    """
    if not trades:
        return {
            'total_return': 0,
            'win_rate': 0,
            'average_win': 0,
            'average_loss': 0,
            'expectancy': 0,
            'max_drawdown': 0,
            'profit_factor': 0,
            'num_trades': 0,
            'avg_duration': 0,
            'long_trades': {},
            'short_trades': {}
        }

    # Separate long and short trades
    long_trades = [t for t in trades if t.direction == 'long']
    short_trades = [t for t in trades if t.direction == 'short']

    # Helper function to calculate metrics for a subset of trades
    def calc_subset_metrics(subset_trades):
        if not subset_trades:
            return {
                'num_trades': 0,
                'win_rate': 0,
                'average_win': 0,
                'average_loss': 0,
                'expectancy': 0,
                'profit_factor': 0,
                'avg_profit_R': 0,
                'avg_mfe': 0,
                'avg_mae': 0
            }

        num = len(subset_trades)
        wins = [t for t in subset_trades if t.pnl > 0]
        losses = [t for t in subset_trades if t.pnl < 0]

        win_rate = len(wins) / num if num > 0 else 0
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        total_wins = sum(t.pnl for t in wins) if wins else 0
        total_losses = abs(sum(t.pnl for t in losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        avg_profit_R = np.mean([t.profit_R for t in subset_trades])
        avg_mfe = np.mean([t.mfe for t in subset_trades])
        avg_mae = np.mean([t.mae for t in subset_trades])

        return {
            'num_trades': num,
            'win_rate': win_rate,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'expectancy': expectancy,
            'profit_factor': profit_factor,
            'avg_profit_R': avg_profit_R,
            'avg_mfe': avg_mfe,
            'avg_mae': avg_mae
        }

    # Basic stats
    num_trades = len(trades)
    total_pnl = sum(t.pnl for t in trades)
    total_return = total_pnl / INITIAL_CAPITAL

    # Win/loss stats
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]

    win_rate = len(wins) / num_trades if num_trades > 0 else 0

    avg_win = np.mean([t.pnl for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl for t in losses]) if losses else 0

    # Expectancy
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    # Profit factor
    total_wins = sum(t.pnl for t in wins) if wins else 0
    total_losses = abs(sum(t.pnl for t in losses)) if losses else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

    # Average trade duration
    durations = [(t.exit_time - t.entry_time).total_seconds() / 60 for t in trades]
    avg_duration = np.mean(durations) if durations else 0

    # Max drawdown from portfolio
    max_drawdown = portfolio['max_drawdown']

    # Calculate long and short metrics
    long_metrics = calc_subset_metrics(long_trades)
    short_metrics = calc_subset_metrics(short_trades)

    return {
        'total_return': total_return,
        'win_rate': win_rate,
        'average_win': avg_win,
        'average_loss': avg_loss,
        'expectancy': expectancy,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'num_trades': num_trades,
        'avg_duration': avg_duration,
        'long_trades': long_metrics,
        'short_trades': short_metrics
    }


# ==========================================
# VISUALIZATION
# ==========================================

def plot_results(portfolio: dict, trades: List[Trade], output_path: Path):
    """
    PURPOSE: Generate visualization plots for backtest results.

    INPUTS:
        portfolio (dict): Portfolio dictionary from simulate_portfolio()
        trades (List[Trade]): List of executed Trade objects
        output_path (Path): Path where plot will be saved

    OUTPUTS:
        None: Function saves plot to file

    CHANGES:
        - No modifications to input data
        - Creates and saves PNG file to disk

    PLOTS GENERATED:
        - Equity Curve: Portfolio value over time with initial capital reference
        - Drawdowns: Percentage drawdowns filled in red
        - Trade PnL Distribution: Histogram of trade PnL values

    SIDE EFFECTS:
        - Saves plot to specified output path
        - Prints confirmation message
    """
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # Equity curve
    axes[0].plot(portfolio['equity_curve'], label='Equity')
    axes[0].axhline(y=INITIAL_CAPITAL, color='r', linestyle='--', label='Initial Capital')
    axes[0].set_title('Equity Curve')
    axes[0].set_ylabel('Equity ($)')
    axes[0].legend()
    axes[0].grid(True)

    # Drawdowns
    axes[1].fill_between(range(len(portfolio['drawdowns'])), portfolio['drawdowns'], 0, alpha=0.3, color='red')
    axes[1].plot(portfolio['drawdowns'], color='red')
    axes[1].set_title('Drawdowns')
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].grid(True)

    # Trade distribution
    pnls = [t.pnl for t in trades]
    axes[2].hist(pnls, bins=30, edgecolor='black')
    axes[2].axvline(x=0, color='r', linestyle='--')
    axes[2].set_title('Trade PnL Distribution')
    axes[2].set_xlabel('PnL ($)')
    axes[2].set_ylabel('Frequency')
    axes[2].grid(True)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    print(f"Plot saved to {output_path}")


# ==========================================
# CSV EXPORT
# ==========================================

def export_trades(trades: List[Trade], path: Path):
    """
    PURPOSE: Export executed trades to CSV file for external analysis.

    INPUTS:
        trades (List[Trade]): List of executed Trade objects
        path (Path): File path where CSV will be saved

    OUTPUTS:
        None: Function saves CSV file to disk

    CHANGES:
        - No modifications to input trades
        - Creates new CSV file at specified path

    CSV COLUMNS:
        - entry_time: Timestamp of trade entry
        - exit_time: Timestamp of trade exit
        - direction: 'long' or 'short'
        - entry_price: Entry execution price
        - exit_price: Exit execution price
        - pnl: Profit/loss in dollars
        - pnl_pct: Profit/loss as percentage
        - exit_reason: 'stop', 'target', or 'eod'

    SIDE EFFECTS:
        - Creates/overwrites CSV file at path
        - Prints confirmation message
    """
    if not trades:
        print("No trades to export.")
        return

    trades_dict = []
    for t in trades:
        trades_dict.append({
            'entry_time': t.entry_time,
            'exit_time': t.exit_time,
            'direction': t.direction,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'stop_price': t.stop_price,
            'position_size': t.position_size,
            'pnl': t.pnl,
            'pnl_pct': t.pnl_pct,
            'exit_reason': t.exit_reason,
            'mfe': t.mfe,
            'mae': t.mae,
            'profit_R': t.profit_R,
            'orb_width': t.orb_width,
            'orb_width_pct': t.orb_width_pct
        })

    df = pd.DataFrame(trades_dict)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Trades exported to {path}")


# ==========================================
# MAIN
# ==========================================

def main():
    """
    PURPOSE: Orchestrate the complete ORB backtesting pipeline from data load to results export.

    INPUTS:
        None: Uses configuration constants defined at module level

    OUTPUTS:
        None: Prints results to console and saves output files

    CHANGES:
        - No persistent state changes
        - Creates output files (trades.csv, backtest_results.png)

    EXECUTION FLOW:
        1. Load OHLCV data from parquet file
        2. Validate data structure and integrity
        3. Build daily trading sessions (09:30-16:00)
        4. For each session:
           a. Compute ORB high and low
           b. Generate breakout signals
           c. Execute trades with realistic simulation
        5. Simulate portfolio equity curve
        6. Compute performance metrics
        7. Print results summary to console
        8. Generate visualization plots
        9. Export trades to CSV (if enabled)

    SIDE EFFECTS:
        - Prints progress and results to console
        - Saves trades.csv file
        - Saves backtest_results.png file
    """
    print("=" * 60)
    print("QQQ BACKTESTER")
    print("=" * 60)
    print()

    # Initialize strategy
    print(f"Initializing {STRATEGY_TYPE} strategy...")
    if STRATEGY_TYPE == "ORB":
        strategy = ORBStrategy(STRATEGY_CONFIG)
        if not strategy.validate_config():
            print("ERROR: Invalid strategy configuration")
            return
        print(f"Strategy config: {strategy.get_config()}")
    else:
        print(f"ERROR: Unknown strategy type '{STRATEGY_TYPE}'")
        return
    print()

    # Load data
    print("Loading data...")
    df = load_data(DATA_PATH)
    print(f"Loaded {len(df)} rows.")
    print()

    # Validate data
    print("Validating data...")
    validate_data(df)
    print()

    # Build sessions
    print("Building sessions...")
    sessions = build_sessions(df)
    print()

    # Run backtest
    print("Running backtest...")
    trades = []
    current_equity = INITIAL_CAPITAL

    for date, session_df in sessions.items():
        # Generate signals using strategy
        signals = strategy.generate_signals(session_df)

        if not signals:
            continue

        # Execute trades (take first signal for ORB strategy)
        signal = signals[0]

        # Convert Signal object to dict for execute_trade
        signal_dict = {
            'direction': signal.direction,
            'signal_time': signal.timestamp,
            'signal_price': signal.entry_price,
            'orb_high': signal.orb_high,
            'orb_low': signal.orb_low
        }

        # Execute trade with current equity for position sizing
        trade = execute_trade(session_df, signal_dict, current_equity)

        if trade is not None:
            trades.append(trade)
            # Update equity for next trade
            current_equity += trade.pnl

    print(f"Generated {len(trades)} trades.")
    print()

    # Simulate portfolio
    print("Simulating portfolio...")
    portfolio = simulate_portfolio(trades)
    print(f"Final equity: ${portfolio['equity_curve'].iloc[-1]:.2f}")
    print()

    # Compute metrics
    print("Computing metrics...")
    metrics = compute_metrics(trades, portfolio)
    print()

    # Print results
    print("=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Total Return:      {metrics['total_return']:.2%}")
    print(f"Win Rate:          {metrics['win_rate']:.2%}")
    print(f"Average Win:       ${metrics['average_win']:.2f}")
    print(f"Average Loss:      ${metrics['average_loss']:.2f}")
    print(f"Expectancy:        ${metrics['expectancy']:.2f}")
    print(f"Profit Factor:     {metrics['profit_factor']:.2f}")
    print(f"Max Drawdown:      {metrics['max_drawdown']:.2%}")
    print(f"Number of Trades:  {metrics['num_trades']}")
    print(f"Avg Duration:      {metrics['avg_duration']:.1f} minutes")
    print("=" * 60)
    print()

    # Print long/short diagnostics
    print("=" * 60)
    print("LONG TRADES DIAGNOSTICS")
    print("=" * 60)
    long_m = metrics['long_trades']
    print(f"Number of Trades:  {long_m['num_trades']}")
    print(f"Win Rate:          {long_m['win_rate']:.2%}")
    print(f"Average Win:       ${long_m['average_win']:.2f}")
    print(f"Average Loss:      ${long_m['average_loss']:.2f}")
    print(f"Expectancy:        ${long_m['expectancy']:.2f}")
    print(f"Profit Factor:     {long_m['profit_factor']:.2f}")
    print(f"Avg Profit R:      {long_m['avg_profit_R']:.2f}R")
    print(f"Avg MFE:           ${long_m['avg_mfe']:.2f}")
    print(f"Avg MAE:           ${long_m['avg_mae']:.2f}")
    print("=" * 60)
    print()

    print("=" * 60)
    print("SHORT TRADES DIAGNOSTICS")
    print("=" * 60)
    short_m = metrics['short_trades']
    print(f"Number of Trades:  {short_m['num_trades']}")
    print(f"Win Rate:          {short_m['win_rate']:.2%}")
    print(f"Average Win:       ${short_m['average_win']:.2f}")
    print(f"Average Loss:      ${short_m['average_loss']:.2f}")
    print(f"Expectancy:        ${short_m['expectancy']:.2f}")
    print(f"Profit Factor:     {short_m['profit_factor']:.2f}")
    print(f"Avg Profit R:      {short_m['avg_profit_R']:.2f}R")
    print(f"Avg MFE:           ${short_m['avg_mfe']:.2f}")
    print(f"Avg MAE:           ${short_m['avg_mae']:.2f}")
    print("=" * 60)
    print()

    # Plot results
    print("Generating plots...")
    plot_results(portfolio, trades, Path(f"../results/{STRATEGY_NAME}/backtest_results.png"))
    print()

    # Export trades
    if EXPORT_TRADES:
        export_trades(trades, TRADES_OUTPUT)

    print("Backtest complete!")


if __name__ == "__main__":
    main()