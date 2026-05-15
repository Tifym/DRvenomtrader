"""
Dr. Venom Trader - Base Signal Module
Abstract base class for all signal types.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class SignalResult:
    """Standard output from any signal module."""
    signal_type: str       # ALFA, BETA, DELTA, GAMMA
    symbol: str
    timeframe: str
    direction: SignalDirection
    strength: float        # 0.0 to 1.0
    details: Dict          # Signal-specific metadata
    label: str = ""        # Human-readable label

    def to_dict(self) -> dict:
        return {
            "signal_type": self.signal_type,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "strength": self.strength,
            "details": self.details,
            "label": self.label,
        }


class BaseSignal(ABC):
    """
    Abstract base class for signal modules.
    All signals must implement the `compute` method.
    """

    # Override in subclass
    SIGNAL_TYPE: str = "BASE"
    TIMEFRAMES: List[str] = []

    @abstractmethod
    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:
        """
        Compute signal state for a given symbol and timeframe.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            timeframe: Timeframe string (e.g., 1H, 4H)
            candles: List of candle dicts, oldest first
            
        Returns:
            SignalResult or None if insufficient data
        """
        pass

    async def compute_all_timeframes(
        self, symbol: str, candles_by_tf: Dict[str, List[dict]]
    ) -> List[SignalResult]:
        """Compute signal across all configured timeframes."""
        results = []
        for tf in self.TIMEFRAMES:
            candles = candles_by_tf.get(tf, [])
            if len(candles) < 10:  # Minimum data requirement
                continue
            result = await self.compute(symbol, tf, candles)
            if result:
                results.append(result)
        return results
