"""
Opening Range Breakout (ORB) strategy implementation.

This strategy looks for breakouts above/below the opening range
(first N minutes of trading) to generate trading signals.
"""

import pandas as pd
from typing import List, Optional
from .base_strategy import BaseStrategy, Signal


class ORBStrategy(BaseStrategy):
    """
    Opening Range Breakout strategy.
    
    This strategy identifies the opening range (first N minutes of trading)
    and generates signals when price breaks above (long) or below (short) this range.
    """
    
    def __init__(self, config: dict):
        """
        Initialize ORB strategy with configuration.
        
        Args:
            config: Dictionary with keys:
                - orb_minutes: Duration of opening range in minutes (default: 15)
                - allow_longs: Enable long trades (default: True)
                - allow_shorts: Enable short trades (default: True)
                - signal_cutoff_hour: Only generate signals before this hour (default: 12)
        """
        super().__init__(config)
        
        self.orb_minutes = config.get('orb_minutes', 15)
        self.allow_longs = config.get('allow_longs', True)
        self.allow_shorts = config.get('allow_shorts', True)
        self.signal_cutoff_hour = config.get('signal_cutoff_hour', 12)
    
    def generate_signals(self, session_df: pd.DataFrame) -> List[Signal]:
        """
        Generate ORB trading signals from a single trading session.
        
        Args:
            session_df: DataFrame with OHLCV data for one trading session
            
        Returns:
            List of Signal objects (typically 0 or 1 signal per session)
        """
        if len(session_df) < self.orb_minutes:
            return []
        
        # Calculate ORB from first N minutes
        orb_period = session_df.iloc[:self.orb_minutes]
        orb_high = orb_period['high'].max()
        orb_low = orb_period['low'].min()
        
        if orb_high is None or orb_low is None:
            return []
        
        # Calculate ORB width and percentage
        orb_width = orb_high - orb_low
        orb_width_pct = (orb_width / orb_low) * 100 if orb_low > 0 else 0
        
        # Start looking for signals after ORB window
        orb_end_time = session_df.index[0] + pd.Timedelta(minutes=self.orb_minutes)
        post_orb = session_df.loc[orb_end_time:]
        
        if post_orb.empty:
            return []
        
        signals = []
        
        for idx, row in post_orb.iterrows():
            # Time filter: only signals before cutoff hour
            if idx.hour >= self.signal_cutoff_hour:
                break
            
            # Check long signal
            if self.allow_longs and row['close'] > orb_high:
                signals.append(Signal(
                    timestamp=idx,
                    direction='long',
                    entry_price=row['close'],
                    stop_price=orb_low,
                    orb_high=orb_high,
                    orb_low=orb_low,
                    orb_width=orb_width,
                    orb_width_pct=orb_width_pct
                ))
                break  # Only first signal
            
            # Check short signal
            if self.allow_shorts and row['close'] < orb_low:
                signals.append(Signal(
                    timestamp=idx,
                    direction='short',
                    entry_price=row['close'],
                    stop_price=orb_high,
                    orb_high=orb_high,
                    orb_low=orb_low,
                    orb_width=orb_width,
                    orb_width_pct=orb_width_pct
                ))
                break  # Only first signal
        
        return signals
    
    def get_config(self) -> dict:
        """Return strategy configuration."""
        return {
            'name': 'ORB',
            'orb_minutes': self.orb_minutes,
            'allow_longs': self.allow_longs,
            'allow_shorts': self.allow_shorts,
            'signal_cutoff_hour': self.signal_cutoff_hour
        }
    
    def validate_config(self) -> bool:
        """Validate ORB strategy configuration."""
        if self.orb_minutes <= 0:
            return False
        if self.orb_minutes > 60:  # Reasonable limit
            return False
        if not self.allow_longs and not self.allow_shorts:
            return False
        if self.signal_cutoff_hour < 10 or self.signal_cutoff_hour > 16:
            return False
        return True
