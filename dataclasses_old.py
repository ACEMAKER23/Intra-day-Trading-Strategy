@dataclass
class Trade:
    date: pd.Timestamp
    direction: str  # "long" or "short"

    entry_time: pd.Timestamp
    exit_time: pd.Timestamp

    entry_price: float
    exit_price: float

    stop_price: float
    target_price: float

    pnl: float
    pnl_pct: float

    exit_reason: str  # "stop", "target", "eod"

@dataclass
class BacktestResult:
    trades: List[Trade]

    equity_curve: pd.Series

    total_return: float
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float

    num_trades: int