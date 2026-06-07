"""
Dr. Venom Trader - ALFA Signal: Fibonacci Retracement
Detects when price enters the golden zone.
Upgraded with scipy peak detection and pandas-ta EMA filter.
"""

import structlog
import numpy as np
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks
from typing import Dict, List, Optional

from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()

# Default Fib levels to track
FIB_LEVELS = {
    "0": 0.0, "0.236": 0.236, "0.382": 0.382, "0.5": 0.5,
    "0.618": 0.618, "0.65": 0.65, "0.702": 0.702, "0.786": 0.786, "1": 1.0,
}

class AlfaSignal(BaseSignal):
    """ALFA Signal — Fibonacci Retracement golden zone detection."""
    SIGNAL_TYPE = "ALFA"
    TIMEFRAMES = ["1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    def __init__(self):
        # Default settings, will be overwritten by hot-reload
        self.settings = {}

    def update_settings(self, new_settings: dict):
        self.settings = new_settings

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:
        if len(candles) < 200: # Need enough for EMA 200
            return None

        # Fetch TF-specific settings or use global defaults
        tf_settings = self.settings.get(timeframe, {})
        global_settings = self.settings.get("GLOBAL", {})
        
        fib_zone_low = tf_settings.get("fib_zone_low", global_settings.get("fib_zone_low", 0.618))
        fib_zone_high = tf_settings.get("fib_zone_high", global_settings.get("fib_zone_high", 0.786))
        prominence_pct = tf_settings.get("prominence", global_settings.get("prominence", 0.005))
        distance = tf_settings.get("distance", global_settings.get("distance", 10))
        use_ema_filter = tf_settings.get("use_ema_filter", global_settings.get("use_ema_filter", True))

        df = pd.DataFrame(candles)
        df.ta.ema(length=200, append=True)
        ema_200 = df["EMA_200"].iloc[-1]
        current_price = df["close"].iloc[-1]
        
        highs = df["high"].values
        lows = df["low"].values
        
        # Prominence based on recent average price
        avg_price = df["close"].mean()
        prominence_abs = avg_price * prominence_pct
        
        # Find peaks (swing highs) and valleys (swing lows)
        peaks, _ = find_peaks(highs, prominence=prominence_abs, distance=distance)
        valleys, _ = find_peaks(-lows, prominence=prominence_abs, distance=distance)
        
        if len(peaks) == 0 or len(valleys) == 0:
            return self._neutral_result(symbol, timeframe)
            
        last_peak_idx = peaks[-1]
        last_valley_idx = valleys[-1]
        
        swing_high = highs[last_peak_idx]
        swing_low = lows[last_valley_idx]
        
        if swing_high == swing_low:
            return self._neutral_result(symbol, timeframe)
            
        price_range = swing_high - swing_low
        is_uptrend = last_valley_idx < last_peak_idx
        
        # EMA 200 Trend Filter
        if use_ema_filter:
            if is_uptrend and current_price < ema_200:
                is_uptrend = False # Counter-trend bounce, treat carefully
            elif not is_uptrend and current_price > ema_200:
                is_uptrend = True
        
        # Calculate Fib retracement levels
        if is_uptrend:
            fib_low = swing_high - (price_range * fib_zone_high)
            fib_high = swing_high - (price_range * fib_zone_low)
        else:
            fib_low = swing_low + (price_range * fib_zone_low)
            fib_high = swing_low + (price_range * fib_zone_high)
            
        zone_bottom = min(fib_low, fib_high)
        zone_top = max(fib_low, fib_high)
        
        fib_values = {}
        for name, level in FIB_LEVELS.items():
            if is_uptrend:
                fib_values[name] = swing_high - (price_range * level)
            else:
                fib_values[name] = swing_low + (price_range * level)
                
        in_zone = zone_bottom <= current_price <= zone_top
        
        if in_zone:
            direction = SignalDirection.LONG if is_uptrend else SignalDirection.SHORT
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
                "swing_high": round(float(swing_high), 2),
                "swing_low": round(float(swing_low), 2),
                "trend": "UP" if is_uptrend else "DOWN",
                "zone_top": round(float(zone_top), 2),
                "zone_bottom": round(float(zone_bottom), 2),
                "in_zone": in_zone,
                "current_price": round(float(current_price), 2),
                "ema_200": round(float(ema_200), 2) if not pd.isna(ema_200) else None,
                "fib_levels": {k: round(float(v), 2) for k, v in fib_values.items()},
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
