"""
Strategy modules for backtesting.

This package contains different trading strategy implementations that can be
easily switched between in the main backtest system.
"""

from .base_strategy import BaseStrategy
from .orb_strategy import ORBStrategy

__all__ = ['BaseStrategy', 'ORBStrategy']
