"""
Dr. Venom Trader - BETA Signal: Divergences (RSI + MACD)
Detects Regular, Hidden, and Implicit divergences.
Upgraded with scipy peak detection and pandas-ta indicators.
"""

import numpy as np
import pandas as pd
import pandas_ta_classic as ta
from scipy.signal import find_peaks
import structlog
from typing import List, Optional

from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()

def find_scipy_pivots(data: np.ndarray, distance: int, prominence: float):
    """Find pivot highs and pivot lows using scipy."""
    peaks, _ = find_peaks(data, distance=distance, prominence=prominence)
    valleys, _ = find_peaks(-data, distance=distance, prominence=prominence)
    
    # Return as list of (index, value)
    return [(p, data[p]) for p in peaks], [(v, data[v]) for v in valleys]

class BetaSignal(BaseSignal):
    """BETA Signal — RSI + MACD Divergence Detection."""
    SIGNAL_TYPE = "BETA"
    TIMEFRAMES = ["4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    def __init__(self):
        self.settings = {}

    def update_settings(self, new_settings: dict):
        self.settings = new_settings

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:
        if len(candles) < 50:
            return None

        tf_settings = self.settings.get(timeframe, {})
        global_settings = self.settings.get("GLOBAL", {})
        
        rsi_period = tf_settings.get("rsi_period", global_settings.get("rsi_period", 14))
        macd_fast = tf_settings.get("macd_fast", global_settings.get("macd_fast", 12))
        macd_slow = tf_settings.get("macd_slow", global_settings.get("macd_slow", 26))
        macd_signal = tf_settings.get("macd_signal", global_settings.get("macd_signal", 9))
        pivot_dist = tf_settings.get("pivot_distance", global_settings.get("pivot_distance", 5))
        
        df = pd.DataFrame(candles)
        df.ta.rsi(length=rsi_period, append=True)
        df.ta.macd(fast=macd_fast, slow=macd_slow, signal=macd_signal, append=True)
        
        rsi_col = f"RSI_{rsi_period}"
        macd_hist_col = f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}"
        macd_line_col = f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"
        
        if rsi_col not in df.columns or macd_hist_col not in df.columns:
            return None
            
        closes = df["close"].values
        rsi = df[rsi_col].values
        macd_hist = df[macd_hist_col].fillna(0).values
        macd_line = df[macd_line_col].fillna(0).values

        # Prominence dynamically calculated based on std
        price_prom = np.std(closes[-50:]) * 0.1
        rsi_prom = np.std(rsi[~np.isnan(rsi)][-50:]) * 0.1 if len(rsi[~np.isnan(rsi)]) > 0 else 2.0
        macd_prom = np.std(macd_hist[-50:]) * 0.1 if len(macd_hist) > 0 else 0.1

        price_highs, price_lows = find_scipy_pivots(closes, pivot_dist, price_prom)
        rsi_highs, rsi_lows = find_scipy_pivots(rsi, pivot_dist, rsi_prom)
        macd_highs, macd_lows = find_scipy_pivots(macd_hist, pivot_dist, macd_prom)

        divergences = []

        rsi_reg_bull = self._check_regular_bullish(price_lows, rsi_lows)
        if rsi_reg_bull: divergences.append(("regular_bullish", "RSI", rsi_reg_bull))

        rsi_reg_bear = self._check_regular_bearish(price_highs, rsi_highs)
        if rsi_reg_bear: divergences.append(("regular_bearish", "RSI", rsi_reg_bear))

        rsi_hid_bull = self._check_hidden_bullish(price_lows, rsi_lows)
        if rsi_hid_bull: divergences.append(("hidden_bullish", "RSI", rsi_hid_bull))

        rsi_hid_bear = self._check_hidden_bearish(price_highs, rsi_highs)
        if rsi_hid_bear: divergences.append(("hidden_bearish", "RSI", rsi_hid_bear))

        macd_reg_bull = self._check_regular_bullish(price_lows, macd_lows)
        if macd_reg_bull: divergences.append(("regular_bullish", "MACD", macd_reg_bull))

        macd_reg_bear = self._check_regular_bearish(price_highs, macd_highs)
        if macd_reg_bear: divergences.append(("regular_bearish", "MACD", macd_reg_bear))

        bull_count = sum(1 for d in divergences if "bullish" in d[0])
        bear_count = sum(1 for d in divergences if "bearish" in d[0])

        if bull_count > bear_count:
            direction, strength, label = SignalDirection.LONG, min(bull_count / 3, 1.0), "BULL DIV"
        elif bear_count > bull_count:
            direction, strength, label = SignalDirection.SHORT, min(bear_count / 3, 1.0), "BEAR DIV"
        else:
            direction, strength, label = SignalDirection.NEUTRAL, 0.0, "NO DIV"

        return SignalResult(
            signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
            direction=direction, strength=round(strength, 3), label=label,
            details={
                "divergences": [{"type": d[0], "indicator": d[1], "confidence": d[2]} for d in divergences],
                "rsi_current": round(float(rsi[-1]) if not np.isnan(rsi[-1]) else 0, 2),
                "macd_current": round(float(macd_line[-1]) if not np.isnan(macd_line[-1]) else 0, 4),
                "bull_signals": bull_count,
                "bear_signals": bear_count,
            },
        )

    def _check_regular_bullish(self, price_pivots, indicator_pivots) -> Optional[float]:
        if len(price_pivots) < 2 or len(indicator_pivots) < 2: return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] < pp1[1] and ip2[1] > ip1[1]: return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None

    def _check_regular_bearish(self, price_pivots, indicator_pivots) -> Optional[float]:
        if len(price_pivots) < 2 or len(indicator_pivots) < 2: return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] > pp1[1] and ip2[1] < ip1[1]: return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None

    def _check_hidden_bullish(self, price_pivots, indicator_pivots) -> Optional[float]:
        if len(price_pivots) < 2 or len(indicator_pivots) < 2: return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] > pp1[1] and ip2[1] < ip1[1]: return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None

    def _check_hidden_bearish(self, price_pivots, indicator_pivots) -> Optional[float]:
        if len(price_pivots) < 2 or len(indicator_pivots) < 2: return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] < pp1[1] and ip2[1] > ip1[1]: return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None
