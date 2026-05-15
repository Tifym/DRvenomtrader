"""
Dr. Venom Trader - DELTA Signal: Bollinger Bands
Price touches/stays above upper BB → RED (bearish)
Price drops below lower BB → GREEN (bullish)
"""

import numpy as np
import structlog
from typing import List, Optional
from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()
BB_PERIOD = 20
BB_STD_DEV = 2.0


def compute_bollinger_bands(closes: np.ndarray, period: int = BB_PERIOD, std_dev: float = BB_STD_DEV):
    """Calculate Bollinger Bands. Returns (sma, upper, lower, pct_b)."""
    if len(closes) < period:
        return None, None, None, None
    sma = np.full_like(closes, np.nan)
    upper = np.full_like(closes, np.nan)
    lower = np.full_like(closes, np.nan)
    pct_b = np.full_like(closes, np.nan)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1: i + 1]
        mean = np.mean(window)
        std = np.std(window, ddof=1)
        sma[i] = mean
        upper[i] = mean + (std_dev * std)
        lower[i] = mean - (std_dev * std)
        bw = upper[i] - lower[i]
        pct_b[i] = (closes[i] - lower[i]) / bw if bw > 0 else 0.5
    return sma, upper, lower, pct_b


class DeltaSignal(BaseSignal):
    """DELTA Signal — Bollinger Bands touch/breakout detection."""
    SIGNAL_TYPE = "DELTA"
    TIMEFRAMES = ["1H", "24m", "12m", "6m", "3m", "1m"]

    async def compute(self, symbol: str, timeframe: str, candles: List[dict]) -> Optional[SignalResult]:
        if len(candles) < BB_PERIOD + 5:
            return None
        closes = np.array([c["close"] for c in candles], dtype=float)
        highs = np.array([c["high"] for c in candles], dtype=float)
        lows = np.array([c["low"] for c in candles], dtype=float)
        sma, upper, lower, pct_b = compute_bollinger_bands(closes)
        if sma is None or np.isnan(upper[-1]):
            return SignalResult(self.SIGNAL_TYPE, symbol, timeframe, SignalDirection.NEUTRAL, 0.0, {}, "NO DATA")

        cur = closes[-1]
        if cur >= upper[-1] or highs[-1] >= upper[-1]:
            direction, strength, label = SignalDirection.SHORT, min(float(pct_b[-1]) / 1.5, 1.0), "UPPER BB"
        elif cur <= lower[-1] or lows[-1] <= lower[-1]:
            direction, strength, label = SignalDirection.LONG, min((1.0 - float(pct_b[-1])) / 1.5, 1.0), "LOWER BB"
        else:
            direction, strength, label = SignalDirection.NEUTRAL, 0.0, "MID BB"

        return SignalResult(
            signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
            direction=direction, strength=round(max(0, min(strength, 1.0)), 3), label=label,
            details={"upper": round(float(upper[-1]), 2), "lower": round(float(lower[-1]), 2),
                     "sma": round(float(sma[-1]), 2), "price": round(float(cur), 2),
                     "pct_b": round(float(pct_b[-1]), 4)},
        )
