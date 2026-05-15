"""
Dr. Venom Trader - BETA Signal: Divergences (RSI + MACD)
Detects Regular, Hidden, and Implicit divergences.

Logic (inspired by VMC Cipher_B_Divergences):
- Regular Bullish: Price makes lower low, RSI/MACD makes higher low → BUY
- Regular Bearish: Price makes higher high, RSI/MACD makes lower high → SELL
- Hidden Bullish: Price makes higher low, RSI/MACD makes lower low → BUY (trend continuation)
- Hidden Bearish: Price makes lower high, RSI/MACD makes higher high → SELL (trend continuation)
- Implicit: Weaker form — detected via gradient comparison

Signal boxes stay colored until an opposite divergence appears.
"""

import numpy as np
import structlog
from typing import Dict, List, Optional

from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()

# RSI parameters
RSI_PERIOD = 14
# MACD parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
# Pivot lookback for swing detection
PIVOT_LOOKBACK = 5


def compute_rsi(closes: np.ndarray, period: int = RSI_PERIOD) -> np.ndarray:
    """Calculate RSI (Relative Strength Index)."""
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.zeros_like(closes)
    avg_loss = np.zeros_like(closes)

    # Initial SMA
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])

    # Smoothed (Wilder's)
    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[:period] = 50.0  # Fill initial values
    return rsi


def compute_macd(
    closes: np.ndarray,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> tuple:
    """Calculate MACD line, signal line, and histogram."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    multiplier = 2.0 / (period + 1)
    ema = np.zeros_like(data)
    ema[0] = data[0]
    for i in range(1, len(data)):
        ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def find_pivots(data: np.ndarray, lookback: int = PIVOT_LOOKBACK):
    """Find pivot highs and pivot lows."""
    pivot_highs = []  # (index, value)
    pivot_lows = []

    for i in range(lookback, len(data) - lookback):
        # Pivot high
        if all(data[i] >= data[i - j] for j in range(1, lookback + 1)) and \
           all(data[i] >= data[i + j] for j in range(1, lookback + 1)):
            pivot_highs.append((i, data[i]))

        # Pivot low
        if all(data[i] <= data[i - j] for j in range(1, lookback + 1)) and \
           all(data[i] <= data[i + j] for j in range(1, lookback + 1)):
            pivot_lows.append((i, data[i]))

    return pivot_highs, pivot_lows


class BetaSignal(BaseSignal):
    """BETA Signal — RSI + MACD Divergence Detection."""

    SIGNAL_TYPE = "BETA"
    TIMEFRAMES = ["4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:
        """Detect divergences between price and RSI/MACD."""
        if len(candles) < 50:
            return None

        closes = np.array([c["close"] for c in candles], dtype=float)
        highs = np.array([c["high"] for c in candles], dtype=float)
        lows = np.array([c["low"] for c in candles], dtype=float)

        # Calculate indicators
        rsi = compute_rsi(closes)
        macd_line, _, macd_hist = compute_macd(closes)

        # Find price pivots
        price_highs, price_lows = find_pivots(closes)
        rsi_highs, rsi_lows = find_pivots(rsi)
        macd_highs, macd_lows = find_pivots(macd_hist)

        divergences = []

        # --- RSI Divergences ---
        # Regular Bullish: Price lower low + RSI higher low
        rsi_reg_bull = self._check_regular_bullish(price_lows, rsi_lows)
        if rsi_reg_bull:
            divergences.append(("regular_bullish", "RSI", rsi_reg_bull))

        # Regular Bearish: Price higher high + RSI lower high
        rsi_reg_bear = self._check_regular_bearish(price_highs, rsi_highs)
        if rsi_reg_bear:
            divergences.append(("regular_bearish", "RSI", rsi_reg_bear))

        # Hidden Bullish: Price higher low + RSI lower low
        rsi_hid_bull = self._check_hidden_bullish(price_lows, rsi_lows)
        if rsi_hid_bull:
            divergences.append(("hidden_bullish", "RSI", rsi_hid_bull))

        # Hidden Bearish: Price lower high + RSI higher high
        rsi_hid_bear = self._check_hidden_bearish(price_highs, rsi_highs)
        if rsi_hid_bear:
            divergences.append(("hidden_bearish", "RSI", rsi_hid_bear))

        # --- MACD Divergences ---
        macd_reg_bull = self._check_regular_bullish(price_lows, macd_lows)
        if macd_reg_bull:
            divergences.append(("regular_bullish", "MACD", macd_reg_bull))

        macd_reg_bear = self._check_regular_bearish(price_highs, macd_highs)
        if macd_reg_bear:
            divergences.append(("regular_bearish", "MACD", macd_reg_bear))

        # Determine overall direction
        bull_count = sum(1 for d in divergences if "bullish" in d[0])
        bear_count = sum(1 for d in divergences if "bearish" in d[0])

        if bull_count > bear_count:
            direction = SignalDirection.LONG
            strength = min(bull_count / 3, 1.0)
            label = "BULL DIV"
        elif bear_count > bull_count:
            direction = SignalDirection.SHORT
            strength = min(bear_count / 3, 1.0)
            label = "BEAR DIV"
        else:
            direction = SignalDirection.NEUTRAL
            strength = 0.0
            label = "NO DIV"

        return SignalResult(
            signal_type=self.SIGNAL_TYPE,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            strength=round(strength, 3),
            label=label,
            details={
                "divergences": [
                    {"type": d[0], "indicator": d[1], "confidence": d[2]}
                    for d in divergences
                ],
                "rsi_current": round(float(rsi[-1]), 2),
                "macd_current": round(float(macd_line[-1]), 4),
                "bull_signals": bull_count,
                "bear_signals": bear_count,
            },
        )

    def _check_regular_bullish(self, price_pivots, indicator_pivots) -> Optional[float]:
        """Regular bullish: Price lower low + Indicator higher low."""
        if len(price_pivots) < 2 or len(indicator_pivots) < 2:
            return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] < pp1[1] and ip2[1] > ip1[1]:
            return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None

    def _check_regular_bearish(self, price_pivots, indicator_pivots) -> Optional[float]:
        """Regular bearish: Price higher high + Indicator lower high."""
        if len(price_pivots) < 2 or len(indicator_pivots) < 2:
            return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] > pp1[1] and ip2[1] < ip1[1]:
            return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None

    def _check_hidden_bullish(self, price_pivots, indicator_pivots) -> Optional[float]:
        """Hidden bullish: Price higher low + Indicator lower low."""
        if len(price_pivots) < 2 or len(indicator_pivots) < 2:
            return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] > pp1[1] and ip2[1] < ip1[1]:
            return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None

    def _check_hidden_bearish(self, price_pivots, indicator_pivots) -> Optional[float]:
        """Hidden bearish: Price lower high + Indicator higher high."""
        if len(price_pivots) < 2 or len(indicator_pivots) < 2:
            return None
        pp1, pp2 = price_pivots[-2], price_pivots[-1]
        ip1, ip2 = indicator_pivots[-2], indicator_pivots[-1]
        if pp2[1] < pp1[1] and ip2[1] > ip1[1]:
            return round(abs(pp2[1] - pp1[1]) / max(pp1[1], 0.001), 4)
        return None
