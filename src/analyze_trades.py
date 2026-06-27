import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Tuple
import argparse


def generate_analysis(trades_csv: str = None, output_dir: str = None, strategy_name: str = "default"):
    """
    Generate comprehensive trade analysis from trades.csv.

    This function:
    1. Loads the trade CSV
    2. Computes all summary statistics
    3. Generates every table
    4. Generates every visualization
    5. Writes summary.md
    6. Writes summary.json
    7. Saves all figures under analysis/figures/

    Args:
        trades_csv: Path to the trades CSV file (if None, uses strategy-specific path)
        output_dir: Directory to save analysis outputs (if None, uses strategy-specific path)
        strategy_name: Name of the strategy for folder organization
    """
    # Set default paths based on strategy name
    if trades_csv is None:
        trades_csv = f"../data/processed/{strategy_name}/trades.csv"
    if output_dir is None:
        output_dir = f"../results/{strategy_name}/analysis/"
    # Create output directories
    output_path = Path(output_dir)
    figures_path = output_path / "figures"
    figures_path.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = load_trades(trades_csv)
    
    # Preprocess data
    df = preprocess_trades(df)
    
    # Compute all metrics
    metrics = compute_all_metrics(df)
    
    # Generate visualizations
    generate_all_visualizations(df, figures_path)
    
    # Write summary files
    write_summary_md(metrics, output_path)
    write_summary_json(metrics, output_path)
    
    print(f"Analysis complete. Results saved to {output_path}")


def load_trades(trades_csv: str) -> pd.DataFrame:
    """Load trades CSV file."""
    df = pd.read_csv(trades_csv)
    df['entry_time'] = pd.to_datetime(df['entry_time'], utc=True)
    df['exit_time'] = pd.to_datetime(df['exit_time'], utc=True)
    return df


def preprocess_trades(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess trade data for analysis."""
    # Compute holding time in minutes
    df['holding_time'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60
    
    # Convert UTC to Eastern time for entry time calculations
    df['entry_time_et'] = df['entry_time'].dt.tz_convert('America/New_York')
    
    # Extract entry time in minutes after market open (09:30 ET)
    df['entry_minutes_after_open'] = (
        df['entry_time_et'].dt.hour * 60 + df['entry_time_et'].dt.minute - 9 * 60 - 30
    )
    
    # Extract month for monthly returns
    df['month'] = df['entry_time_et'].dt.to_period('M')
    
    return df


def compute_all_metrics(df: pd.DataFrame) -> Dict:
    """Compute all analysis metrics."""
    metrics = {}
    
    # Overall metrics
    metrics['overall'] = compute_overall_metrics(df)
    
    # Long vs short
    metrics['long_short'] = compute_long_short_metrics(df)
    
    # Exit reason summary
    metrics['exit_reason'] = compute_exit_reason_metrics(df)
    
    # OR width buckets
    metrics['or_width'] = compute_or_width_metrics(df)
    
    # Entry time windows
    metrics['entry_time'] = compute_entry_time_metrics(df)
    
    # Holding time analysis
    metrics['holding_time'] = compute_holding_time_metrics(df)
    
    # Losing trades profit levels
    metrics['losing_profit_levels'] = compute_losing_trades_profit_levels(df)
    
    # Profit capture analysis
    metrics['profit_capture'] = compute_profit_capture(df)
    
    # AI-friendly summary stats
    metrics['summary'] = compute_ai_summary(df, metrics)
    
    return metrics


def compute_overall_metrics(df: pd.DataFrame) -> Dict:
    """Compute overall performance metrics."""
    total_trades = len(df)
    total_pnl = df['pnl'].sum()
    initial_capital = 10000  # From strategy.py
    total_return = total_pnl / initial_capital
    
    winners = df[df['pnl'] > 0]
    losers = df[df['pnl'] < 0]
    
    win_rate = len(winners) / total_trades if total_trades > 0 else 0
    loss_rate = len(losers) / total_trades if total_trades > 0 else 0
    
    avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0
    
    total_wins = winners['pnl'].sum() if len(winners) > 0 else 0
    total_losses = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    
    expectancy = df['pnl'].mean()
    expectancy_R = df['profit_R'].mean()
    
    # Compute equity curve and drawdown
    equity = [initial_capital]
    for pnl in df['pnl']:
        equity.append(equity[-1] + pnl)
    equity_series = pd.Series(equity)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = drawdown.min()
    
    avg_holding_time = df['holding_time'].mean()
    median_holding_time = df['holding_time'].median()
    
    return {
        'number_of_trades': total_trades,
        'total_return': total_return,
        'win_rate': win_rate,
        'loss_rate': loss_rate,
        'average_winner': avg_win,
        'average_loser': avg_loss,
        'profit_factor': profit_factor,
        'expectancy': expectancy,
        'expectancy_R': expectancy_R,
        'max_drawdown': max_drawdown,
        'average_holding_time': avg_holding_time,
        'median_holding_time': median_holding_time
    }


def compute_long_short_metrics(df: pd.DataFrame) -> Dict:
    """Compute long vs short performance metrics."""
    long_trades = df[df['direction'] == 'long']
    short_trades = df[df['direction'] == 'short']
    
    def calc_side_metrics(side_df):
        if len(side_df) == 0:
            return {
                'trades': 0, 'win_rate': 0, 'avg_win': 0, 'avg_loss': 0,
                'profit_factor': 0, 'avg_R': 0, 'total_pnl': 0
            }
        
        winners = side_df[side_df['pnl'] > 0]
        losers = side_df[side_df['pnl'] < 0]
        
        win_rate = len(winners) / len(side_df)
        avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0
        
        total_wins = winners['pnl'].sum() if len(winners) > 0 else 0
        total_losses = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return {
            'trades': len(side_df),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_R': side_df['profit_R'].mean(),
            'total_pnl': side_df['pnl'].sum()
        }
    
    return {
        'long': calc_side_metrics(long_trades),
        'short': calc_side_metrics(short_trades)
    }


def compute_exit_reason_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute exit reason summary."""
    # Calculate wins per exit reason
    df['is_win'] = df['pnl'] > 0
    grouped = df.groupby('exit_reason').agg({
        'pnl': 'count',
        'profit_R': 'mean',
        'is_win': 'mean'
    }).rename(columns={'pnl': 'trades', 'profit_R': 'avg_R', 'is_win': 'win_rate'})
    
    return grouped


def compute_or_width_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute OR width bucket analysis."""
    # Define buckets
    bins = [0, 0.002, 0.004, 0.006, 0.008, float('inf')]
    labels = ['0.0-0.2%', '0.2-0.4%', '0.4-0.6%', '0.6-0.8%', '>0.8%']
    
    df['or_bucket'] = pd.cut(df['orb_width_pct'], bins=bins, labels=labels)
    
    grouped = df.groupby('or_bucket').agg({
        'pnl': 'count',
        'profit_R': 'mean',
        'is_win': 'mean'
    }).rename(columns={'pnl': 'trades', 'profit_R': 'avg_R', 'is_win': 'win_rate'})
    
    return grouped


def compute_entry_time_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute entry time window analysis."""
    # Define windows (minutes after market open)
    bins = [5, 15, 30, 60, 90, 150]
    labels = ['09:35-09:45', '09:45-10:00', '10:00-10:30', '10:30-11:00', '11:00-12:00']
    
    df['entry_window'] = pd.cut(df['entry_minutes_after_open'], bins=bins, labels=labels)
    
    grouped = df.groupby('entry_window').agg({
        'pnl': 'count',
        'profit_R': 'mean',
        'is_win': 'mean'
    }).rename(columns={'pnl': 'trades', 'profit_R': 'avg_R', 'is_win': 'win_rate'})
    
    return grouped


def compute_holding_time_metrics(df: pd.DataFrame) -> Dict:
    """Compute holding time analysis for winners vs losers."""
    winners = df[df['pnl'] > 0]['holding_time']
    losers = df[df['pnl'] < 0]['holding_time']
    
    return {
        'winners': {
            'mean': winners.mean() if len(winners) > 0 else 0,
            'median': winners.median() if len(winners) > 0 else 0,
            'max': winners.max() if len(winners) > 0 else 0
        },
        'losers': {
            'mean': losers.mean() if len(losers) > 0 else 0,
            'median': losers.median() if len(losers) > 0 else 0,
            'max': losers.max() if len(losers) > 0 else 0
        }
    }


def compute_losing_trades_profit_levels(df: pd.DataFrame) -> Dict:
    """Analyze what profit levels losing trades reached before becoming losers."""
    losers = df[df['pnl'] < 0].copy()
    
    # Calculate the maximum profit reached during the trade (in R multiples)
    # For longs: (high - entry) / risk_per_share
    # For shorts: (entry - low) / risk_per_share
    # Since we don't have high/low data per trade, we'll use MFE as proxy for max profit
    
    # Convert MFE to R multiples using the same risk calculation as in strategy
    # risk_per_share ≈ stop distance
    losers['max_profit_R'] = losers['mfe'] / abs(losers['entry_price'] - losers['stop_price'])
    
    # Define profit level buckets in R multiples
    bins = [0, 0.5, 1.0, 1.5, 2.0, 3.0, float('inf')]
    labels = ['0-0.5R', '0.5-1R', '1-1.5R', '1.5-2R', '2-3R', '>3R']
    
    losers['profit_level'] = pd.cut(losers['max_profit_R'], bins=bins, labels=labels)
    
    # Count trades in each bucket
    level_counts = losers['profit_level'].value_counts().sort_index()
    
    # Calculate average final loss for trades that reached each profit level
    avg_loss_by_level = losers.groupby('profit_level')['profit_R'].mean()
    
    return {
        'total_losing_trades': len(losers),
        'level_counts': level_counts.to_dict(),
        'avg_loss_by_level': avg_loss_by_level.to_dict()
    }


def compute_profit_capture(df: pd.DataFrame) -> Dict:
    """Compute how much of available MFE was actually captured as final profit."""
    df = df.copy()
    
    # Only calculate profit capture for winning trades where it makes sense
    winners = df[df['pnl'] > 0].copy()
    
    if len(winners) == 0:
        return {
            'avg_capture_ratio': 0,
            'median_capture_ratio': 0,
            'total_winners': 0,
            'bucket_counts': {}
        }
    
    # Calculate MFE in R multiples (same as profit_R calculation)
    # MFE_R = MFE / risk_per_share
    # risk_per_share = abs(entry_price - stop_price)
    winners['mfe_R'] = winners['mfe'] / abs(winners['entry_price'] - winners['stop_price'])
    
    # Calculate profit capture ratio: Final Profit_R / MFE_R
    # This shows what percentage of the maximum favorable excursion (in R) was captured
    winners['profit_capture_ratio'] = winners['profit_R'] / winners['mfe_R']
    
    # Handle cases where MFE_R is 0 (avoid division by zero)
    winners.loc[winners['mfe_R'] == 0, 'profit_capture_ratio'] = 0
    
    # Calculate statistics
    avg_capture = winners['profit_capture_ratio'].mean()
    median_capture = winners['profit_capture_ratio'].median()
    
    # Bucket by capture ratio (only for meaningful ranges)
    bins = [0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, float('inf')]
    labels = ['0-25%', '25-50%', '50-75%', '75-100%', '100-150%', '150-200%', '>200%']
    
    winners['capture_bucket'] = pd.cut(winners['profit_capture_ratio'], bins=bins, labels=labels)
    bucket_counts = winners['capture_bucket'].value_counts().sort_index()
    
    return {
        'avg_capture_ratio': avg_capture,
        'median_capture_ratio': median_capture,
        'total_winners': len(winners),
        'bucket_counts': bucket_counts.to_dict()
    }


def compute_ai_summary(df: pd.DataFrame, metrics: Dict) -> Dict:
    """Compute AI-friendly summary statistics."""
    # Find best and worst entry windows
    entry_metrics = metrics['entry_time']
    best_entry = entry_metrics['avg_R'].idxmax() if len(entry_metrics) > 0 else None
    worst_entry = entry_metrics['avg_R'].idxmin() if len(entry_metrics) > 0 else None
    
    # Find best and worst OR width buckets
    or_metrics = metrics['or_width']
    best_or = or_metrics['avg_R'].idxmax() if len(or_metrics) > 0 else None
    worst_or = or_metrics['avg_R'].idxmin() if len(or_metrics) > 0 else None
    
    return {
        'total_return': metrics['overall']['total_return'],
        'profit_factor': metrics['overall']['profit_factor'],
        'expectancy_R': metrics['overall']['expectancy_R'],
        'best_entry_window': best_entry,
        'worst_entry_window': worst_entry,
        'best_or_width_bucket': best_or,
        'worst_or_width_bucket': worst_or,
        'long_profit_factor': metrics['long_short']['long']['profit_factor'],
        'short_profit_factor': metrics['long_short']['short']['profit_factor'],
        'avg_mfe': df['mfe'].mean(),
        'avg_mae': df['mae'].mean(),
        'largest_drawdown': metrics['overall']['max_drawdown']
    }


def generate_all_visualizations(df: pd.DataFrame, figures_path: Path):
    """Generate all visualization plots."""
    # Equity curve
    plot_equity_curve(df, figures_path)
    
    # Histograms
    plot_pnl_histogram(df, figures_path)
    plot_profit_r_histogram(df, figures_path)
    plot_mfe_histogram(df, figures_path)
    plot_mae_histogram(df, figures_path)
    
    # Scatter plots
    plot_mfe_vs_profit_r(df, figures_path)
    plot_mae_vs_profit_r(df, figures_path)
    plot_or_width_vs_profit_r(df, figures_path)
    
    # Bar charts and box plots
    plot_entry_time_boxplot(df, figures_path)
    plot_monthly_returns(df, figures_path)
    plot_exit_reason_bar(df, figures_path)
    plot_long_short_bar(df, figures_path)


def plot_equity_curve(df: pd.DataFrame, figures_path: Path):
    """Generate equity curve plot."""
    initial_capital = 10000
    equity = [initial_capital]
    for pnl in df['pnl']:
        equity.append(equity[-1] + pnl)
    
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(equity)), equity, linewidth=2)
    plt.xlabel('Trade Number')
    plt.ylabel('Portfolio Equity ($)')
    plt.title('Equity Curve')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'equity_curve.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_pnl_histogram(df: pd.DataFrame, figures_path: Path):
    """Generate PnL histogram."""
    plt.figure(figsize=(10, 6))
    plt.hist(df['pnl'], bins=50, edgecolor='black', alpha=0.7)
    plt.xlabel('Dollar PnL ($)')
    plt.ylabel('Trade Count')
    plt.title('PnL Distribution')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'pnl_histogram.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_profit_r_histogram(df: pd.DataFrame, figures_path: Path):
    """Generate profit in R histogram."""
    plt.figure(figsize=(10, 6))
    plt.hist(df['profit_R'], bins=50, edgecolor='black', alpha=0.7)
    plt.xlabel('Profit (R multiples)')
    plt.ylabel('Trade Count')
    plt.title('Profit in R Distribution')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'profit_R_histogram.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_mfe_histogram(df: pd.DataFrame, figures_path: Path):
    """Generate MFE histogram."""
    plt.figure(figsize=(10, 6))
    plt.hist(df['mfe'], bins=50, edgecolor='black', alpha=0.7)
    plt.xlabel('MFE ($)')
    plt.ylabel('Trade Count')
    plt.title('Maximum Favorable Excursion Distribution')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'mfe_histogram.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_mae_histogram(df: pd.DataFrame, figures_path: Path):
    """Generate MAE histogram."""
    plt.figure(figsize=(10, 6))
    plt.hist(df['mae'], bins=50, edgecolor='black', alpha=0.7)
    plt.xlabel('MAE ($)')
    plt.ylabel('Trade Count')
    plt.title('Maximum Adverse Excursion Distribution')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'mae_histogram.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_mfe_vs_profit_r(df: pd.DataFrame, figures_path: Path):
    """Generate MFE vs Profit R scatter plot."""
    plt.figure(figsize=(10, 6))
    plt.scatter(df['mfe'], df['profit_R'], alpha=0.6, s=20)
    plt.xlabel('MFE ($)')
    plt.ylabel('Profit (R multiples)')
    plt.title('MFE vs Final Profit (R)')
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='r', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'mfe_vs_profitR.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_mae_vs_profit_r(df: pd.DataFrame, figures_path: Path):
    """Generate MAE vs Profit R scatter plot."""
    plt.figure(figsize=(10, 6))
    plt.scatter(df['mae'], df['profit_R'], alpha=0.6, s=20)
    plt.xlabel('MAE ($)')
    plt.ylabel('Profit (R multiples)')
    plt.title('MAE vs Final Profit (R)')
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='r', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'mae_vs_profitR.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_or_width_vs_profit_r(df: pd.DataFrame, figures_path: Path):
    """Generate OR width vs Profit R scatter plot with bin averages."""
    plt.figure(figsize=(10, 6))
    plt.scatter(df['orb_width_pct'], df['profit_R'], alpha=0.6, s=20)
    
    # Add bin averages
    bins = np.linspace(df['orb_width_pct'].min(), df['orb_width_pct'].max(), 20)
    df['or_bin'] = pd.cut(df['orb_width_pct'], bins)
    bin_avg = df.groupby('or_bin')['profit_R'].mean()
    bin_centers = [(interval.left + interval.right) / 2 for interval in bin_avg.index]
    plt.plot(bin_centers, bin_avg.values, 'r-', linewidth=2, label='Bin Average')
    
    plt.xlabel('ORB Width (%)')
    plt.ylabel('Profit (R multiples)')
    plt.title('ORB Width vs Profit (R)')
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_path / 'orb_width_vs_profitR.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_entry_time_boxplot(df: pd.DataFrame, figures_path: Path):
    """Generate entry time box plot."""
    # Define windows
    bins = [5, 15, 30, 60, 90, 150]
    labels = ['09:35-09:45', '09:45-10:00', '10:00-10:30', '10:30-11:00', '11:00-12:00']
    
    df['entry_window'] = pd.cut(df['entry_minutes_after_open'], bins=bins, labels=labels)
    
    plt.figure(figsize=(12, 6))
    box_data = [df[df['entry_window'] == label]['profit_R'].values for label in labels]
    bp = plt.boxplot(box_data, tick_labels=labels)
    plt.xlabel('Entry Window')
    plt.ylabel('Profit (R multiples)')
    plt.title('Entry Time vs Profit (R)')
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(figures_path / 'entry_time_boxplot.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_monthly_returns(df: pd.DataFrame, figures_path: Path):
    """Generate monthly returns bar chart."""
    monthly_pnl = df.groupby('month')['pnl'].sum()
    
    plt.figure(figsize=(12, 6))
    monthly_pnl.plot(kind='bar', edgecolor='black')
    plt.xlabel('Month')
    plt.ylabel('Total PnL ($)')
    plt.title('Monthly Returns')
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(figures_path / 'monthly_returns.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_exit_reason_bar(df: pd.DataFrame, figures_path: Path):
    """Generate exit reason frequency bar chart."""
    exit_counts = df['exit_reason'].value_counts()
    
    plt.figure(figsize=(10, 6))
    exit_counts.plot(kind='bar', edgecolor='black')
    plt.xlabel('Exit Reason')
    plt.ylabel('Trade Count')
    plt.title('Exit Reason Frequency')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(figures_path / 'exit_reason_bar.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_long_short_bar(df: pd.DataFrame, figures_path: Path):
    """Generate long vs short performance grouped bar chart."""
    long_trades = df[df['direction'] == 'long']
    short_trades = df[df['direction'] == 'short']
    
    metrics = ['Win Rate', 'Avg R', 'Profit Factor']
    long_vals = [
        (long_trades['pnl'] > 0).mean(),
        long_trades['profit_R'].mean(),
        long_trades[long_trades['pnl'] > 0]['pnl'].sum() / abs(long_trades[long_trades['pnl'] < 0]['pnl'].sum()) if len(long_trades[long_trades['pnl'] < 0]) > 0 else 0
    ]
    short_vals = [
        (short_trades['pnl'] > 0).mean(),
        short_trades['profit_R'].mean(),
        short_trades[short_trades['pnl'] > 0]['pnl'].sum() / abs(short_trades[short_trades['pnl'] < 0]['pnl'].sum()) if len(short_trades[short_trades['pnl'] < 0]) > 0 else 0
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    plt.figure(figsize=(10, 6))
    plt.bar(x - width/2, long_vals, width, label='Long', edgecolor='black')
    plt.bar(x + width/2, short_vals, width, label='Short', edgecolor='black')
    plt.xlabel('Metric')
    plt.ylabel('Value')
    plt.title('Long vs Short Performance')
    plt.xticks(x, metrics)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(figures_path / 'long_short_bar.png', dpi=300, bbox_inches='tight')
    plt.close()


def write_summary_md(metrics: Dict, output_path: Path):
    """Write summary markdown file."""
    md_content = "# Trade Analysis Summary\n\n"
    
    # Overall metrics
    md_content += "## Overall Metrics\n\n"
    md_content += "| Metric | Value |\n"
    md_content += "|---------|------:|\n"
    o = metrics['overall']
    md_content += f"| Number of Trades | {o['number_of_trades']} |\n"
    md_content += f"| Total Return | {o['total_return']:.2%} |\n"
    md_content += f"| Win Rate | {o['win_rate']:.2%} |\n"
    md_content += f"| Loss Rate | {o['loss_rate']:.2%} |\n"
    md_content += f"| Average Winner | ${o['average_winner']:.2f} |\n"
    md_content += f"| Average Loser | ${o['average_loser']:.2f} |\n"
    md_content += f"| Profit Factor | {o['profit_factor']:.2f} |\n"
    md_content += f"| Expectancy ($) | ${o['expectancy']:.2f} |\n"
    md_content += f"| Expectancy (R) | {o['expectancy_R']:.2f}R |\n"
    md_content += f"| Max Drawdown | {o['max_drawdown']:.2%} |\n"
    md_content += f"| Average Holding Time | {o['average_holding_time']:.1f} min |\n"
    md_content += f"| Median Holding Time | {o['median_holding_time']:.1f} min |\n\n"
    
    # Long vs Short
    md_content += "## Long vs Short\n\n"
    md_content += "| Metric | Long | Short |\n"
    md_content += "|---------|------:|------:|\n"
    ls = metrics['long_short']
    md_content += f"| Trades | {ls['long']['trades']} | {ls['short']['trades']} |\n"
    md_content += f"| Win Rate | {ls['long']['win_rate']:.2%} | {ls['short']['win_rate']:.2%} |\n"
    md_content += f"| Avg Win | ${ls['long']['avg_win']:.2f} | ${ls['short']['avg_win']:.2f} |\n"
    md_content += f"| Avg Loss | ${ls['long']['avg_loss']:.2f} | ${ls['short']['avg_loss']:.2f} |\n"
    md_content += f"| Profit Factor | {ls['long']['profit_factor']:.2f} | {ls['short']['profit_factor']:.2f} |\n"
    md_content += f"| Avg R | {ls['long']['avg_R']:.2f}R | {ls['short']['avg_R']:.2f}R |\n"
    md_content += f"| Total PnL | ${ls['long']['total_pnl']:.2f} | ${ls['short']['total_pnl']:.2f} |\n\n"
    
    # Exit Reason
    md_content += "## Exit Reason Summary\n\n"
    md_content += "| Exit Reason | Trades | Avg R | Win Rate |\n"
    md_content += "|--------------|-------:|------:|----------:|\n"
    for reason, row in metrics['exit_reason'].iterrows():
        md_content += f"| {reason} | {int(row['trades'])} | {row['avg_R']:.2f}R | {row['win_rate']:.2%} |\n"
    md_content += "\n"
    
    # OR Width
    md_content += "## OR Width Analysis\n\n"
    md_content += "| OR Width Bucket | Trades | Avg R | Win Rate |\n"
    md_content += "|-----------------|-------:|------:|----------:|\n"
    for bucket, row in metrics['or_width'].iterrows():
        md_content += f"| {bucket} | {int(row['trades'])} | {row['avg_R']:.2f}R | {row['win_rate']:.2%} |\n"
    md_content += "\n"
    
    # Entry Time
    md_content += "## Entry Time Analysis\n\n"
    md_content += "| Entry Window | Trades | Avg R | Win Rate |\n"
    md_content += "|---------------|-------:|------:|----------:|\n"
    for window, row in metrics['entry_time'].iterrows():
        md_content += f"| {window} | {int(row['trades'])} | {row['avg_R']:.2f}R | {row['win_rate']:.2%} |\n"
    md_content += "\n"
    
    # Holding Time
    md_content += "## Holding Time Analysis\n\n"
    md_content += "| Metric | Winners | Losers |\n"
    md_content += "|----------|--------:|-------:|\n"
    ht = metrics['holding_time']
    md_content += f"| Mean | {ht['winners']['mean']:.1f} min | {ht['losers']['mean']:.1f} min |\n"
    md_content += f"| Median | {ht['winners']['median']:.1f} min | {ht['losers']['median']:.1f} min |\n"
    md_content += f"| Max | {ht['winners']['max']:.1f} min | {ht['losers']['max']:.1f} min |\n\n"
    
    # Losing Trades Profit Levels
    md_content += "## Losing Trades Profit Levels\n\n"
    md_content += "This analysis shows what profit levels losing trades reached before becoming losers.\n\n"
    lpl = metrics['losing_profit_levels']
    md_content += f"Total Losing Trades: {lpl['total_losing_trades']}\n\n"
    md_content += "| Profit Level Reached | Count | Avg Final Loss (R) |\n"
    md_content += "|---------------------|------:|------------------:|\n"
    for level in ['0-0.5R', '0.5-1R', '1-1.5R', '1.5-2R', '2-3R', '>3R']:
        count = lpl['level_counts'].get(level, 0)
        avg_loss = lpl['avg_loss_by_level'].get(level, 0)
        md_content += f"| {level} | {count} | {avg_loss:.2f}R |\n"
    md_content += "\n"
    
    # Profit Capture Analysis
    md_content += "## Profit Capture Analysis\n\n"
    md_content += "This measures how much of the available MFE (Maximum Favorable Excursion) was actually captured as final profit.\n"
    md_content += "Calculated only for winning trades where profit capture is meaningful.\n\n"
    pc = metrics['profit_capture']
    md_content += f"Total Winning Trades: {pc['total_winners']}\n"
    md_content += f"Average Capture Ratio: {pc['avg_capture_ratio']:.2%}\n"
    md_content += f"Median Capture Ratio: {pc['median_capture_ratio']:.2%}\n\n"
    md_content += "| Capture Range | Trade Count |\n"
    md_content += "|---------------|------------:|\n"
    for bucket in ['0-25%', '25-50%', '50-75%', '75-100%', '100-150%', '150-200%', '>200%']:
        count = pc['bucket_counts'].get(bucket, 0)
        md_content += f"| {bucket} | {count} |\n"
    md_content += "\n"
    
    with open(output_path / 'summary.md', 'w') as f:
        f.write(md_content)


def write_summary_json(metrics: Dict, output_path: Path):
    """Write AI-friendly summary JSON file."""
    summary = metrics['summary']
    
    # Convert numpy types to native Python types
    for key, value in summary.items():
        if isinstance(value, (np.integer, np.floating)):
            summary[key] = float(value)
        elif isinstance(value, str) and value is None:
            summary[key] = None
    
    with open(output_path / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze trade results from backtest")
    parser.add_argument(
        "--strategy",
        type=str,
        default="default",
        help="Strategy name for folder organization (default: default)"
    )
    parser.add_argument(
        "--trades-csv",
        type=str,
        default=None,
        help="Path to trades CSV file (overrides strategy-specific path)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (overrides strategy-specific path)"
    )
    
    args = parser.parse_args()
    
    generate_analysis(
        trades_csv=args.trades_csv,
        output_dir=args.output_dir,
        strategy_name=args.strategy
    )
