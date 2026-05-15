"""
Dr. Venom Trader - ALFA Signal: Fibonacci Retracement
Detects when price enters the golden zone (0.618 - 0.786 Fib retracement).

Logic:
- Auto-detect swing high and swing low over a lookback window
- Calculate Fibonacci levels from the swing
- If price is in the 0.618 - 0.786 zone:
    - In an uptrend (swing low → swing high, then retrace): GREEN (bullish)
    - In a downtrend (swing high → swing low, then bounce): RED (bearish)
"""

import structlog
from typing import Dict, List, Optional

from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()

# Default Fib levels to track
FIB_LEVELS = {
    "0": 0.0,
    "0.236": 0.236,
    "0.382": 0.382,
    "0.5": 0.5,
    "0.618": 0.618,
    "0.65": 0.65,
    "0.702": 0.702,
    "0.786": 0.786,
    "1": 1.0,
}

# Golden zone boundaries
GOLDEN_ZONE_LOW = 0.618
GOLDEN_ZONE_HIGH = 0.786

# Lookback periods per timeframe for swing detection
LOOKBACK = {
    "1D": 30, "4H": 50, "3H": 50, "2H": 60,
    "1H": 60, "24m": 60, "12m": 80, "6m": 100,
    "3m": 100, "1m": 120,
}


class AlfaSignal(BaseSignal):
    """ALFA Signal — Fibonacci Retracement golden zone detection."""

    SIGNAL_TYPE = "ALFA"
    TIMEFRAMES = ["1D", "4H", "3H", "2H", "1H", "24m", "12m", "6m", "3m", "1m"]

    def __init__(self, fib_zone_low: float = GOLDEN_ZONE_LOW, fib_zone_high: float = GOLDEN_ZONE_HIGH):
        self.fib_zone_low = fib_zone_low
        self.fib_zone_high = fib_zone_high

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:
        """Compute ALFA signal for given candles."""
        if len(candles) < 20:
            return None

        lookback = LOOKBACK.get(timeframe, 60)
        window = candles[-lookback:]

        # Find swing high and swing low
        highs = [c["high"] for c in window]
        lows = [c["low"] for c in window]

        swing_high = max(highs)
        swing_low = min(lows)
        swing_high_idx = highs.index(swing_high)
        swing_low_idx = lows.index(swing_low)

        if swing_high == swing_low:
            return self._neutral_result(symbol, timeframe)

        current_price = candles[-1]["close"]
        price_range = swing_high - swing_low

        # Determine trend direction based on which swing came first
        is_uptrend = swing_low_idx < swing_high_idx  # Low came first → uptrend

        # Calculate Fib retracement levels
        if is_uptrend:
            # Uptrend: retracement from high back down
            fib_618 = swing_high - (price_range * self.fib_zone_low)
            fib_786 = swing_high - (price_range * self.fib_zone_high)
            zone_top = fib_618
            zone_bottom = fib_786
        else:
            # Downtrend: retracement from low back up
            fib_618 = swing_low + (price_range * self.fib_zone_low)
            fib_786 = swing_low + (price_range * self.fib_zone_high)
            zone_bottom = fib_618
            zone_top = fib_786

        # Calculate all Fib levels for details
        fib_values = {}
        for name, level in FIB_LEVELS.items():
            if is_uptrend:
                fib_values[name] = swing_high - (price_range * level)
            else:
                fib_values[name] = swing_low + (price_range * level)

        # Check if price is in the golden zone
        in_zone = zone_bottom <= current_price <= zone_top

        if in_zone:
            direction = SignalDirection.LONG if is_uptrend else SignalDirection.SHORT
            # Strength based on how centered in the zone the price is
            zone_mid = (zone_top + zone_bottom) / 2
            distance_from_mid = abs(current_price - zone_mid)
            zone_half_width = (zone_top - zone_bottom) / 2
            strength = 1.0 - (distance_from_mid / zone_half_width) if zone_half_width > 0 else 0.5
        else:
            direction = SignalDirection.NEUTRAL
            strength = 0.0

        return SignalResult(
            signal_type=self.SIGNAL_TYPE,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            strength=round(strength, 3),
            label="FIB ZONE" if in_zone else "OUT",
            details={
                "swing_high": round(swing_high, 2),
                "swing_low": round(swing_low, 2),
                "trend": "UP" if is_uptrend else "DOWN",
                "zone_top": round(zone_top, 2),
                "zone_bottom": round(zone_bottom, 2),
                "in_zone": in_zone,
                "current_price": round(current_price, 2),
                "fib_levels": {k: round(v, 2) for k, v in fib_values.items()},
            },
        )

    def _neutral_result(self, symbol: str, timeframe: str) -> SignalResult:
        return SignalResult(
            signal_type=self.SIGNAL_TYPE,
            symbol=symbol,
            timeframe=timeframe,
            direction=SignalDirection.NEUTRAL,
            strength=0.0,
            label="NO DATA",
            details={},
        )
