"""
Base strategy class for modular backtesting system.

All trading strategies should inherit from this class and implement
the required methods.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class Signal:
    """Trading signal data structure."""
    timestamp: pd.Timestamp
    direction: str  # 'long' or 'short'
    entry_price: float
    stop_price: float
    orb_high: float
    orb_low: float
    orb_width: float
    orb_width_pct: float


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    All strategies must implement:
    - generate_signals(): Generate trading signals from price data
    - get_config(): Return strategy configuration parameters
    """
    
    def __init__(self, config: Dict):
        """
        Initialize strategy with configuration.
        
        Args:
            config: Dictionary of strategy-specific parameters
        """
        self.config = config
        self.name = config.get('name', 'unnamed_strategy')
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """
        Generate trading signals from price data.
        
        Args:
            df: DataFrame with OHLCV data, indexed by timestamp
            
        Returns:
            List of Signal objects representing trading opportunities
        """
        pass
    
    @abstractmethod
    def get_config(self) -> Dict:
        """
        Return strategy configuration parameters.
        
        Returns:
            Dictionary of configuration parameters
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate strategy configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        return True
