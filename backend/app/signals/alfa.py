"""
Dr. Venom Trader - ALFA Signal v2: Professional Fibonacci Retracement
=======================================================================
Upgrades from v1:
  - ZigZag multi-swing detection (ATR-filtered, non-repainting)
  - Multi-Fib cluster zones from up to 3 recent swing pairs (recency-weighted)
  - EMA 200 + EMA 50 dual trend alignment filter
  - ADX(14) trending-market gate
  - Volume confirmation at zone entry
  - Fib extension levels for trade targets
  - 4-component strength score (zone proximity + trend + ADX + volume)
"""

import structlog
import numpy as np
import pandas as pd
import pandas_ta_classic as ta
from typing import Dict, List, Optional, Tuple

from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()

# Standard Fibonacci retracement ratios
FIB_RETRACEMENT = {
    "0":     0.0,
    "0.236": 0.236,
    "0.382": 0.382,
    "0.5":   0.5,
    "0.618": 0.618,
    "0.65":  0.65,
    "0.702": 0.702,
    "0.786": 0.786,
    "1":     1.0,
}

# Fibonacci extension ratios (for targets beyond the swing)
FIB_EXTENSION = {
    "1.272": 1.272,
    "1.414": 1.414,
    "1.618": 1.618,
    "2.0":   2.0,
}


def compute_zigzag_swings(
    highs: np.ndarray,
    lows: np.ndarray,
    atr: np.ndarray,
    atr_mult: float = 1.5,
    min_bars: int = 5,
) -> List[Tuple[int, float, str]]:
    """
    ATR-filtered ZigZag swing detection.

    A new swing point is confirmed only when price reverses by at least
    atr_mult * ATR from the last extreme. min_bars ensures pivots are
    separated by enough candles for significance.

    The last candle is intentionally excluded to avoid repainting —
    only confirmed (closed) candles are evaluated.

    Returns:
        List of (bar_index, price, type) where type is 'H' (high pivot)
        or 'L' (low pivot), ordered chronologically.
    """
    swings: List[Tuple[int, float, str]] = []
    n = len(highs) - 1  # Exclude last unconfirmed candle

    if n < min_bars * 2:
        return swings

    direction = None           # Current ZigZag direction: 'UP' or 'DOWN'
    extreme_idx = 0
    extreme_price = (highs[0] + lows[0]) / 2

    for i in range(1, n):
        # Use ATR for minimum move, fall back to small fixed value
        curr_atr = float(atr[i]) if not np.isnan(atr[i]) else float(np.nanmean(atr[:i+1]))
        min_move = atr_mult * max(curr_atr, 1e-9)

        if direction is None:
            # Bootstrap direction from first significant move
            if highs[i] - lows[0] >= min_move:
                direction = 'UP'
                extreme_idx = 0
                extreme_price = lows[0]
            elif highs[0] - lows[i] >= min_move:
                direction = 'DOWN'
                extreme_idx = 0
                extreme_price = highs[0]
            continue

        if direction == 'UP':
            if highs[i] > extreme_price:
                # Continue the up move — update the running high
                extreme_price = highs[i]
                extreme_idx = i
            elif (extreme_price - lows[i]) >= min_move and (i - extreme_idx) >= min_bars:
                # Reversal confirmed: record the swing HIGH
                swings.append((extreme_idx, extreme_price, 'H'))
                direction = 'DOWN'
                extreme_price = lows[i]
                extreme_idx = i
        else:  # direction == 'DOWN'
            if lows[i] < extreme_price:
                # Continue the down move — update the running low
                extreme_price = lows[i]
                extreme_idx = i
            elif (highs[i] - extreme_price) >= min_move and (i - extreme_idx) >= min_bars:
                # Reversal confirmed: record the swing LOW
                swings.append((extreme_idx, extreme_price, 'L'))
                direction = 'UP'
                extreme_price = highs[i]
                extreme_idx = i

    return swings


def calc_fib_levels(
    swing_high: float, swing_low: float, is_uptrend: bool
) -> Dict[str, float]:
    """Calculate retracement Fib levels for a given swing pair."""
    rng = swing_high - swing_low
    return {
        name: (swing_high - rng * ratio) if is_uptrend else (swing_low + rng * ratio)
        for name, ratio in FIB_RETRACEMENT.items()
    }


def calc_fib_extensions(
    swing_high: float, swing_low: float, is_uptrend: bool
) -> Dict[str, float]:
    """Calculate extension Fib levels for trade targets."""
    rng = swing_high - swing_low
    return {
        name: (swing_low + rng * ratio) if is_uptrend else (swing_high - rng * ratio)
        for name, ratio in FIB_EXTENSION.items()
    }


class AlfaSignal(BaseSignal):
    """
    ALFA Signal v2 — Professional Fibonacci Retracement.

    Signal fires when price enters the 0.618–0.786 golden zone
    (or user-configured zone) of a significant ZigZag swing, confirmed
    by trend alignment (EMA 200, EMA 50) and optional ADX/volume filters.

    Strength is a composite of:
      - Zone proximity  (0–0.40): distance from zone midpoint
      - Trend alignment (0–0.30): EMA 200 + EMA 50 aligned
      - ADX score       (0–0.15): stronger trend = higher score
      - Volume confirm  (0–0.15): volume at or above 80% of 50-bar avg
    """

    SIGNAL_TYPE = "ALFA"
    TIMEFRAMES = ["1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    def __init__(self):
        self.settings: dict = {}

    def update_settings(self, new_settings: dict):
        self.settings = new_settings

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:

        if len(candles) < 100:
            return None

        # ── Settings ──────────────────────────────────────────────────────────
        tf_s = self.settings.get(timeframe, {})
        gl_s = self.settings.get("GLOBAL", {})
        def g(k, d):
            return tf_s.get(k, gl_s.get(k, d))

        fib_zone_low    = g("fib_zone_low",    0.618)
        fib_zone_high   = g("fib_zone_high",   0.786)
        atr_mult        = g("atr_mult",         1.5)
        min_bars        = g("min_bars",          5)
        use_ema_filter  = g("use_ema_filter",   True)
        use_adx_filter  = g("use_adx_filter",   True)
        adx_min         = g("adx_min",          20)
        vol_confirm     = g("vol_confirm",      True)
        max_swings      = g("max_swings",        3)

        # ── Build DataFrame and indicators ────────────────────────────────────
        df = pd.DataFrame(candles)
        if "close" not in df.columns:
            return None

        df.ta.ema(length=200, append=True)
        df.ta.ema(length=50,  append=True)
        df.ta.atr(length=14,  append=True)
        if use_adx_filter:
            df.ta.adx(length=14, append=True)

        highs   = df["high"].values.astype(float)
        lows    = df["low"].values.astype(float)
        closes  = df["close"].values.astype(float)
        volumes = df["volume"].values.astype(float) if "volume" in df.columns else np.ones(len(df))

        ema_200 = float(df["EMA_200"].iloc[-1]) if "EMA_200" in df.columns else np.nan
        ema_50  = float(df["EMA_50"].iloc[-1])  if "EMA_50"  in df.columns else np.nan

        # Locate ATR column (pandas-ta naming varies by version)
        atr_col = next((c for c in df.columns if c.startswith("ATRr") or c.startswith("ATR_")), None)
        atr_arr = df[atr_col].values.astype(float) if atr_col else np.full(len(df), np.nanstd(closes) * 0.01)

        adx_col = "ADX_14"
        adx_val = float(df[adx_col].iloc[-1]) if (use_adx_filter and adx_col in df.columns) else adx_min + 1

        current_price = closes[-1]

        # ── ZigZag swing detection ────────────────────────────────────────────
        swings = compute_zigzag_swings(highs, lows, atr_arr, atr_mult, min_bars)

        if len(swings) < 4:
            return self._neutral(symbol, timeframe, "INSUFFICIENT SWINGS")

        # ── Collect up to max_swings valid swing pairs ─────────────────────
        swing_pairs = []
        for i in range(len(swings) - 1, 0, -1):
            s2, s1 = swings[i], swings[i - 1]
            if s2[2] == 'H' and s1[2] == 'L':
                swing_pairs.append({
                    "high": s2[1], "low": s1[1],
                    "high_idx": s2[0], "low_idx": s1[0],
                    "is_uptrend": True,
                })
            elif s2[2] == 'L' and s1[2] == 'H':
                swing_pairs.append({
                    "high": s1[1], "low": s2[1],
                    "high_idx": s1[0], "low_idx": s2[0],
                    "is_uptrend": False,
                })
            if len(swing_pairs) >= max_swings:
                break

        if not swing_pairs:
            return self._neutral(symbol, timeframe, "NO SWING PAIRS")

        # ── Primary (most recent) swing ────────────────────────────────────
        primary    = swing_pairs[0]
        swing_high = primary["high"]
        swing_low  = primary["low"]
        is_uptrend = primary["is_uptrend"]

        # ── Multi-cluster Fib zone (recency-weighted average) ──────────────
        zone_bottoms, zone_tops, weights = [], [], []
        for idx, pair in enumerate(swing_pairs):
            rng = pair["high"] - pair["low"]
            lo = pair["high"] - rng * fib_zone_high if pair["is_uptrend"] else pair["low"] + rng * fib_zone_low
            hi = pair["high"] - rng * fib_zone_low  if pair["is_uptrend"] else pair["low"] + rng * fib_zone_high
            zone_bottoms.append(min(lo, hi))
            zone_tops.append(max(lo, hi))
            weights.append(1.0 / (idx + 1))   # Recency weight: 1, 0.5, 0.33 …

        total_w      = sum(weights)
        cluster_bot  = sum(b * w for b, w in zip(zone_bottoms, weights)) / total_w
        cluster_top  = sum(t * w for t, w in zip(zone_tops,    weights)) / total_w

        in_zone = cluster_bot <= current_price <= cluster_top

        # ── EMA Trend Filter ───────────────────────────────────────────────
        trend_bull = (not np.isnan(ema_200)) and current_price > ema_200 and (np.isnan(ema_50) or ema_50 > ema_200)
        trend_bear = (not np.isnan(ema_200)) and current_price < ema_200 and (np.isnan(ema_50) or ema_50 < ema_200)

        if use_ema_filter:
            ema_ok = (is_uptrend and trend_bull) or (not is_uptrend and trend_bear)
        else:
            ema_ok = True

        # ── ADX Filter ─────────────────────────────────────────────────────
        adx_ok = (not use_adx_filter) or (not np.isnan(adx_val) and adx_val >= adx_min)

        # ── Volume Confirmation ────────────────────────────────────────────
        avg_vol  = np.mean(volumes[max(0, len(volumes) - 51):-1]) if len(volumes) > 1 else 1.0
        curr_vol = volumes[-1]
        vol_ok   = (not vol_confirm) or curr_vol >= avg_vol * 0.8

        # ── Fib levels & extensions from primary swing ─────────────────────
        fib_levels = calc_fib_levels(swing_high, swing_low, is_uptrend)
        fib_ext    = calc_fib_extensions(swing_high, swing_low, is_uptrend)

        # ── Strength Calculation ───────────────────────────────────────────
        if in_zone:
            direction = SignalDirection.LONG if is_uptrend else SignalDirection.SHORT

            # 1) Zone proximity: how close to zone midpoint (0–0.40)
            zone_mid  = (cluster_top + cluster_bot) / 2
            zone_half = max((cluster_top - cluster_bot) / 2, 1e-9)
            prox      = max(0.0, 1.0 - abs(current_price - zone_mid) / zone_half) * 0.40

            # 2) Trend alignment (0–0.30)
            trend_sc  = 0.30 if ema_ok else 0.08

            # 3) ADX score (0–0.15)
            adx_sc    = (min(adx_val / 50.0, 1.0) * 0.15) if (adx_ok and not np.isnan(adx_val)) else 0.0

            # 4) Volume confirmation (0–0.15)
            vol_sc    = 0.15 if vol_ok else 0.05

            strength = round(min(prox + trend_sc + adx_sc + vol_sc, 1.0), 3)
            label    = "FIB ZONE" if ema_ok else "FIB ZONE (CT)"
        else:
            direction = SignalDirection.NEUTRAL
            strength  = 0.0
            label     = "OUT"

        return SignalResult(
            signal_type=self.SIGNAL_TYPE,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            strength=strength,
            label=label,
            details={
                "swing_high":       round(float(swing_high), 4),
                "swing_low":        round(float(swing_low), 4),
                "trend":            "UP" if is_uptrend else "DOWN",
                "cluster_top":      round(float(cluster_top), 4),
                "cluster_bottom":   round(float(cluster_bot), 4),
                "in_zone":          in_zone,
                "current_price":    round(float(current_price), 4),
                "ema_200":          round(ema_200, 4) if not np.isnan(ema_200) else None,
                "ema_50":           round(ema_50,  4) if not np.isnan(ema_50)  else None,
                "adx":              round(float(adx_val), 2) if not np.isnan(adx_val) else None,
                "ema_aligned":      ema_ok,
                "adx_ok":           adx_ok,
                "vol_ok":           vol_ok,
                "num_clusters":     len(swing_pairs),
                "fib_levels":       {k: round(float(v), 4) for k, v in fib_levels.items()},
                "fib_extensions":   {k: round(float(v), 4) for k, v in fib_ext.items()},
            },
        )

    def _neutral(self, symbol: str, timeframe: str, reason: str = "OUT") -> SignalResult:
        return SignalResult(
            signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
            direction=SignalDirection.NEUTRAL, strength=0.0, label=reason,
            details={"reason": reason},
        )
