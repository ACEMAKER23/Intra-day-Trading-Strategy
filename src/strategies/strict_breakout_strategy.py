"""
Strict Breakout strategy implementation.

This strategy is a variant of ORB with additional constraints on signal generation:
1. Candle body size is at least 0.6 (abs(close-open)/(high-low))
2. OR close location is in the top/bottom 20% of the candle for long/short
3. OR close breaks higher/lower by OR high/low +/- 0.05% of the price
"""

import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, Signal


class StrictBreakoutStrategy(BaseStrategy):
    """
    Strict Breakout strategy with additional signal quality filters.
    
    This strategy identifies the opening range (first N minutes of trading)
    and generates signals when price breaks above/below this range, but only
    if the breakout candle meets strict quality criteria.
    """
    
    def __init__(self, config: dict):
        """
        Initialize Strict Breakout strategy with configuration.

        Args:
            config: Dictionary with keys:
                - orb_minutes: Duration of opening range in minutes (default: 15)
                - allow_longs: Enable long trades (default: True)
                - allow_shorts: Enable short trades (default: True)
                - signal_cutoff_hour: Only generate signals before this hour (default: 12)
                - min_body_ratio: Minimum candle body ratio (default: 0.6)
                - min_close_location: Minimum close location in candle (default: 0.8)
                - breakout_threshold: Breakout threshold as percentage (default: 0.05)
                - use_conditions: List of conditions to check (default: ['body_ratio', 'close_location', 'breakout'])
                              Options: 'body_ratio', 'close_location', 'breakout'
        """
        super().__init__(config)

        self.orb_minutes = config.get('orb_minutes', 15)
        self.allow_longs = config.get('allow_longs', True)
        self.allow_shorts = config.get('allow_shorts', True)
        self.signal_cutoff_hour = config.get('signal_cutoff_hour', 12)
        self.min_body_ratio = config.get('min_body_ratio', 0.6)
        self.min_close_location = config.get('min_close_location', 0.8)
        self.breakout_threshold = config.get('breakout_threshold', 0.05)
        self.use_conditions = config.get('use_conditions', ['body_ratio', 'close_location', 'breakout'])
    
    def _check_candle_quality(self, row: pd.Series, direction: str) -> tuple[bool, list[str]]:
        """
        Check if candle meets quality criteria for signal generation.

        Args:
            row: Single row of OHLCV data
            direction: 'long' or 'short'

        Returns:
            Tuple of (passed, reasons) where passed is True if candle meets quality criteria,
            and reasons is a list of conditions that were met
        """
        high = row['high']
        low = row['low']
        close = row['close']
        open_price = row['open']

        # Calculate candle range
        candle_range = high - low
        if candle_range == 0:
            return False, []

        reasons = []

        # Check 1: Candle body size (abs(close-open) / (high-low) >= min_body_ratio)
        if 'body_ratio' in self.use_conditions:
            body_ratio = abs(close - open_price) / candle_range
            if body_ratio >= self.min_body_ratio:
                reasons.append(f"Body ratio {body_ratio:.2f} >= {self.min_body_ratio}")

        # Check 2: Close location in top/bottom 20% of candle
        if 'close_location' in self.use_conditions:
            if direction == 'long':
                # For long: close should be in top 20% (close-low)/(high-low) >= 0.8
                close_location = (close - low) / candle_range
                if close_location >= self.min_close_location:
                    reasons.append(f"Close location {close_location:.2f} >= {self.min_close_location} (top)")
            elif direction == 'short':
                # For short: close should be in bottom 20% (high-close)/(high-low) >= 0.8
                close_location = (high - close) / candle_range
                if close_location >= self.min_close_location:
                    reasons.append(f"Close location {close_location:.2f} >= {self.min_close_location} (bottom)")

        # Determine if passed based on which conditions are enabled
        enabled_conditions = [c for c in ['body_ratio', 'close_location'] if c in self.use_conditions]
        if len(enabled_conditions) == 0:
            return True, []  # No candle quality conditions enabled
        elif len(enabled_conditions) == 1:
            return len(reasons) >= 1, reasons  # At least one condition must pass
        else:
            return len(reasons) >= 1, reasons  # At least one condition must pass (OR logic)
    
    def _check_breakout_threshold(self, close: float, orb_level: float) -> tuple[bool, str]:
        """
        Check if close breaks OR level by threshold percentage.

        Args:
            close: Close price
            orb_level: OR high or low level

        Returns:
            Tuple of (passed, reason) where passed is True if close breaks OR level by threshold,
            and reason is a string describing the breakout strength
        """
        # If breakout condition is not enabled, always pass
        if 'breakout' not in self.use_conditions:
            return True, "Breakout condition disabled"

        # breakout_threshold is already a percentage (e.g., 0.5 means 0.5%)
        threshold = orb_level * (self.breakout_threshold / 100)
        threshold_pct = self.breakout_threshold

        if close > orb_level:
            # Check if close is above OR level + threshold
            if close >= (orb_level + threshold):
                breakout_pct = ((close - orb_level) / orb_level) * 100
                return True, f"Breakout {breakout_pct:.2f}% >= {threshold_pct}%"
        elif close < orb_level:
            # Check if close is below OR level - threshold
            if close <= (orb_level - threshold):
                breakout_pct = ((orb_level - close) / orb_level) * 100
                return True, f"Breakout {breakout_pct:.2f}% >= {threshold_pct}%"

        return False, ""
    
    def generate_signals(self, session_df: pd.DataFrame) -> List[Signal]:
        """
        Generate strict breakout trading signals from a single trading session.
        
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
                # Prerequisite: candle must open below OR high (within OR range)
                if row['open'] > orb_high:
                    continue  # Candle opens above OR high, not a valid breakout candle

                # Check if close breaks OR high by threshold (if enabled in use_conditions)
                breakout_passed, breakout_reason = self._check_breakout_threshold(row['close'], orb_high)
                if not breakout_passed:
                    continue

                # Check candle quality (if enabled)
                quality_passed, quality_reasons = self._check_candle_quality(row, 'long')
                if not quality_passed:
                    continue

                # Combine reasons
                all_reasons = quality_reasons
                if 'breakout' in self.use_conditions:
                    all_reasons.append(breakout_reason)
                reason_str = "; ".join(all_reasons) if all_reasons else "No conditions checked"

                signals.append(Signal(
                    timestamp=idx,
                    direction='long',
                    entry_price=row['close'],
                    stop_price=orb_low,
                    orb_high=orb_high,
                    orb_low=orb_low,
                    orb_width=orb_width,
                    orb_width_pct=orb_width_pct,
                    reason=reason_str,
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close']
                ))
                break  # Only first signal

            # Check short signal
            if self.allow_shorts and row['close'] < orb_low:
                # Prerequisite: candle must open above OR low (within OR range)
                if row['open'] < orb_low:
                    continue  # Candle opens below OR low, not a valid breakout candle

                # Check if close breaks OR low by threshold (if enabled in use_conditions)
                breakout_passed, breakout_reason = self._check_breakout_threshold(row['close'], orb_low)
                if not breakout_passed:
                    continue

                # Check candle quality (if enabled)
                quality_passed, quality_reasons = self._check_candle_quality(row, 'short')
                if not quality_passed:
                    continue

                # Combine reasons
                all_reasons = quality_reasons
                if 'breakout' in self.use_conditions:
                    all_reasons.append(breakout_reason)
                reason_str = "; ".join(all_reasons) if all_reasons else "No conditions checked"

                signals.append(Signal(
                    timestamp=idx,
                    direction='short',
                    entry_price=row['close'],
                    stop_price=orb_high,
                    orb_high=orb_high,
                    orb_low=orb_low,
                    orb_width=orb_width,
                    orb_width_pct=orb_width_pct,
                    reason=reason_str,
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close']
                ))
                break  # Only first signal
        
        return signals
    
    def get_config(self) -> dict:
        """Return strategy configuration."""
        return {
            'name': 'StrictBreakout',
            'orb_minutes': self.orb_minutes,
            'allow_longs': self.allow_longs,
            'allow_shorts': self.allow_shorts,
            'signal_cutoff_hour': self.signal_cutoff_hour,
            'min_body_ratio': self.min_body_ratio,
            'min_close_location': self.min_close_location,
            'breakout_threshold': self.breakout_threshold,
            'use_conditions': self.use_conditions
        }
    
    def validate_config(self) -> bool:
        """Validate Strict Breakout strategy configuration."""
        if self.orb_minutes <= 0:
            return False
        if self.orb_minutes > 60:
            return False
        if not self.allow_longs and not self.allow_shorts:
            return False
        if self.signal_cutoff_hour < 10 or self.signal_cutoff_hour > 16:
            return False
        if self.min_body_ratio <= 0 or self.min_body_ratio > 1:
            return False
        if self.min_close_location <= 0 or self.min_close_location > 1:
            return False
        if self.breakout_threshold < 0:
            return False
        return True
