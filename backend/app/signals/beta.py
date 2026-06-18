"""
Dr. Venom Trader - BETA Signal v2: Professional Divergence Engine
=================================================================
Upgrades from v1:
  - Uses actual high/low arrays for price pivots (v1 incorrectly used closes)
  - Nearest-pivot time-matching between price and indicator pivots
  - 3-leg divergence support (stronger, higher-confidence signals)
  - RSI + MACD confluence gate (both must confirm for max strength)
  - MACD histogram slope as momentum confirmation
  - StochRSI extreme zones add 10% strength bonus
  - ATR-adaptive pivot prominence (scales with volatility)
  - Non-repainting: last 2 bars excluded from pivot search
"""

import numpy as np
import pandas as pd
import pandas_ta_classic as ta
from scipy.signal import find_peaks
import structlog
from typing import List, Optional, Tuple

from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()


# ── Pivot detection ────────────────────────────────────────────────────────────

def find_pivots(
    data: np.ndarray,
    distance: int,
    prominence: float,
    exclude_last: int = 2,
) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Find confirmed pivot highs and pivot lows using scipy.

    Args:
        data:         1-D array to search (e.g., price highs or RSI)
        distance:     Minimum bar separation between pivots
        prominence:   Minimum price/indicator move for a pivot to qualify
        exclude_last: Strip this many bars from the end to avoid repainting

    Returns:
        (peaks, valleys) — each as list of (bar_index, value)
    """
    safe_len = max(1, len(data) - exclude_last)
    safe = data[:safe_len]

    peaks,   _ = find_peaks( safe, distance=distance, prominence=prominence)
    valleys, _ = find_peaks(-safe, distance=distance, prominence=prominence)

    return (
        [(int(i), float(safe[i])) for i in peaks],
        [(int(i), float(safe[i])) for i in valleys],
    )


def nearest_pivot(
    pivots: List[Tuple[int, float]], target_idx: int
) -> Optional[Tuple[int, float]]:
    """Return the pivot closest in time to target_idx."""
    if not pivots:
        return None
    return min(pivots, key=lambda p: abs(p[0] - target_idx))


# ── 2-Leg divergence logic ─────────────────────────────────────────────────────

def check_2leg(
    price_pivots: List[Tuple[int, float]],
    ind_pivots:   List[Tuple[int, float]],
    div_type: str,
) -> Optional[float]:
    """
    2-leg divergence between the two most recent price pivots and their
    nearest indicator counterparts.

    Divergence types:
      reg_bull: Price lower low  + Indicator higher low  → reversal up
      reg_bear: Price higher high + Indicator lower high  → reversal down
      hid_bull: Price higher low  + Indicator lower low   → trend continuation up
      hid_bear: Price lower high  + Indicator higher high → trend continuation down

    Returns confidence score in [0, 1] or None if divergence not found.
    """
    if len(price_pivots) < 2 or not ind_pivots:
        return None

    pp1, pp2 = price_pivots[-2], price_pivots[-1]
    ip1 = nearest_pivot(ind_pivots, pp1[0])
    ip2 = nearest_pivot(ind_pivots, pp2[0])

    if ip1 is None or ip2 is None or ip1[0] == ip2[0]:
        return None

    p_diff = pp2[1] - pp1[1]   # positive = price higher
    i_diff = ip2[1] - ip1[1]   # positive = indicator higher

    # Require meaningful moves (avoid noise)
    EPS = 1e-6

    if div_type == "reg_bull" and p_diff < -EPS and i_diff > EPS:
        return round(min(abs(i_diff) / (abs(i_diff) + abs(p_diff) * 0.1 + EPS), 1.0), 4)
    if div_type == "reg_bear" and p_diff > EPS  and i_diff < -EPS:
        return round(min(abs(i_diff) / (abs(i_diff) + abs(p_diff) * 0.1 + EPS), 1.0), 4)
    if div_type == "hid_bull" and p_diff > EPS  and i_diff < -EPS:
        return round(min(abs(p_diff) / (abs(p_diff) + abs(i_diff) * 0.1 + EPS), 1.0), 4)
    if div_type == "hid_bear" and p_diff < -EPS and i_diff > EPS:
        return round(min(abs(p_diff) / (abs(p_diff) + abs(i_diff) * 0.1 + EPS), 1.0), 4)

    return None


def check_3leg(
    price_pivots: List[Tuple[int, float]],
    ind_pivots:   List[Tuple[int, float]],
    div_type: str,
) -> Optional[float]:
    """
    3-leg divergence: all three consecutive pivot pairs must maintain
    the divergence pattern. Returns 1.25× the average 2-leg score
    when confirmed — significantly stronger signal.
    """
    if len(price_pivots) < 3 or not ind_pivots:
        return None

    pp1, pp2, pp3 = price_pivots[-3], price_pivots[-2], price_pivots[-1]
    ip1 = nearest_pivot(ind_pivots, pp1[0])
    ip2 = nearest_pivot(ind_pivots, pp2[0])
    ip3 = nearest_pivot(ind_pivots, pp3[0])

    if ip1 is None or ip2 is None or ip3 is None:
        return None
    if len({ip1[0], ip2[0], ip3[0]}) < 3:   # Must be three distinct indicator pivots
        return None

    leg1 = check_2leg([pp1, pp2], [ip1, ip2], div_type)
    leg2 = check_2leg([pp2, pp3], [ip2, ip3], div_type)

    if leg1 and leg2:
        return round(min((leg1 + leg2) / 2 * 1.25, 1.0), 4)   # +25% bonus for 3-leg
    return None


# ── Signal class ───────────────────────────────────────────────────────────────

class BetaSignal(BaseSignal):
    """
    BETA Signal v2 — Professional Divergence Engine.

    Scans for Regular and Hidden divergences on RSI and MACD histogram,
    using 2-leg and 3-leg checks. RSI + MACD confluence is required for
    maximum strength; single-indicator divergences are downweighted.
    Momentum confirmation via MACD histogram slope and StochRSI extremes.
    """

    SIGNAL_TYPE = "BETA"
    TIMEFRAMES  = ["4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    def __init__(self):
        self.settings: dict = {}

    def update_settings(self, new_settings: dict):
        self.settings = new_settings

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:

        if len(candles) < 60:
            return None

        # ── Settings ─────────────────────────────────────────────────────────
        tf_s = self.settings.get(timeframe, {})
        gl_s = self.settings.get("GLOBAL", {})
        def g(k, d):
            return tf_s.get(k, gl_s.get(k, d))

        rsi_period         = g("rsi_period",                  14)
        macd_fast          = g("macd_fast",                   12)
        macd_slow          = g("macd_slow",                   26)
        macd_sig           = g("macd_signal",                  9)
        pivot_dist         = g("pivot_distance",               5)
        atr_mult_prom      = g("atr_mult_prominence",         0.5)
        require_confluence = g("require_rsi_macd_confluence", True)

        # ── Indicators ────────────────────────────────────────────────────────
        df = pd.DataFrame(candles)
        df.ta.rsi(length=rsi_period, append=True)
        df.ta.macd(fast=macd_fast, slow=macd_slow, signal=macd_sig, append=True)
        df.ta.atr(length=14,  append=True)
        df.ta.stochrsi(length=14, rsi_length=rsi_period, k=3, d=3, append=True)

        rsi_col    = f"RSI_{rsi_period}"
        macd_h_col = f"MACDh_{macd_fast}_{macd_slow}_{macd_sig}"
        macd_l_col = f"MACD_{macd_fast}_{macd_slow}_{macd_sig}"
        atr_col    = next((c for c in df.columns if c.startswith("ATRr") or c.startswith("ATR_")), None)
        srsi_k_col = next((c for c in df.columns if "STOCHRSIk" in c), None)

        if rsi_col not in df.columns or macd_h_col not in df.columns:
            return None

        highs  = df["high"].values.astype(float)
        lows   = df["low"].values.astype(float)
        rsi    = df[rsi_col].fillna(50).values.astype(float)
        macd_h = df[macd_h_col].fillna(0).values.astype(float)
        macd_l = df[macd_l_col].fillna(0).values.astype(float)
        srsi_k = df[srsi_k_col].fillna(50).values.astype(float) if srsi_k_col else np.full(len(df), 50.0)

        atr_v   = df[atr_col].values.astype(float) if atr_col else np.full(len(df), np.nanstd(df["close"].values) * 0.01)
        avg_atr = max(np.nanmean(atr_v[-50:]), 1e-9)

        # ── ATR-adaptive prominence ───────────────────────────────────────────
        price_prom = avg_atr * atr_mult_prom
        rsi_prom   = max(float(np.nanstd(rsi[-50:])) * 0.3,  0.5)
        macd_prom  = max(float(np.nanstd(macd_h[-50:])) * 0.3, 1e-6)

        # ── Find pivots on correct arrays ─────────────────────────────────────
        # For bullish divergences we check LOWS (price and indicator troughs)
        # For bearish divergences we check HIGHS (price and indicator peaks)
        price_peaks,   price_valleys  = find_pivots(highs, pivot_dist, price_prom)
        rsi_peaks,     rsi_valleys    = find_pivots(rsi,   pivot_dist, rsi_prom)
        macd_peaks,    macd_valleys   = find_pivots(macd_h, pivot_dist, macd_prom)

        # Use actual lows array for bullish pivot prices
        price_peaks_lo, price_valleys_lo = find_pivots(lows, pivot_dist, price_prom)

        # ── MACD histogram slope (momentum direction) ─────────────────────────
        macd_slope = float(macd_h[-1] - macd_h[max(-4, -len(macd_h))])

        # ── StochRSI extremes ─────────────────────────────────────────────────
        srsi_oversold   = float(srsi_k[-1]) < 20
        srsi_overbought = float(srsi_k[-1]) > 80

        # ── Divergence scanning ───────────────────────────────────────────────
        found = []   # (div_type, indicator, leg_count, confidence)

        scan = [
            ("reg_bull", price_valleys_lo, rsi_valleys,  macd_valleys),
            ("hid_bull", price_valleys_lo, rsi_valleys,  macd_valleys),
            ("reg_bear", price_peaks,      rsi_peaks,    macd_peaks),
            ("hid_bear", price_peaks,      rsi_peaks,    macd_peaks),
        ]

        for div_type, pp, rsi_p, macd_p in scan:
            # Try 3-leg first (stronger); fall back to 2-leg
            r3 = check_3leg(pp, rsi_p, div_type)
            if r3:
                found.append((div_type, "RSI", 3, r3))
            else:
                r2 = check_2leg(pp, rsi_p, div_type)
                if r2:
                    found.append((div_type, "RSI", 2, r2))

            m3 = check_3leg(pp, macd_p, div_type)
            if m3:
                found.append((div_type, "MACD", 3, m3))
            else:
                m2 = check_2leg(pp, macd_p, div_type)
                if m2:
                    found.append((div_type, "MACD", 2, m2))

        # ── Score bull / bear divergences ─────────────────────────────────────
        BULL_TYPES = {"reg_bull", "hid_bull"}
        BEAR_TYPES = {"reg_bear", "hid_bear"}

        bull_divs = [f for f in found if f[0] in BULL_TYPES]
        bear_divs = [f for f in found if f[0] in BEAR_TYPES]

        def score(divs: list) -> float:
            if not divs:
                return 0.0
            indicators  = {d[1] for d in divs}
            base_conf   = max(d[3] for d in divs)
            leg_bonus   = sum((d[2] - 2) * 0.25 for d in divs)          # +25% per extra leg
            conf_bonus  = 0.20 if len(indicators) > 1 else 0.0           # RSI+MACD alignment bonus
            return min(base_conf + leg_bonus + conf_bonus, 1.0)

        bull_score = score(bull_divs)
        bear_score = score(bear_divs)

        # ── RSI + MACD confluence gate ─────────────────────────────────────────
        if require_confluence:
            bull_inds = {d[1] for d in bull_divs}
            bear_inds = {d[1] for d in bear_divs}
            # Penalise if RSI not present (less reliable without RSI confirmation)
            if bull_score > 0 and "RSI" not in bull_inds:
                bull_score *= 0.5
            if bear_score > 0 and "RSI" not in bear_inds:
                bear_score *= 0.5

        # ── Momentum confirmation ──────────────────────────────────────────────
        if bull_score > bear_score:
            if macd_slope > 0:
                bull_score = min(bull_score * 1.10, 1.0)   # Histogram turning up
            if srsi_oversold:
                bull_score = min(bull_score * 1.10, 1.0)   # Oversold adds confidence
        elif bear_score > bull_score:
            if macd_slope < 0:
                bear_score = min(bear_score * 1.10, 1.0)
            if srsi_overbought:
                bear_score = min(bear_score * 1.10, 1.0)

        # ── Final direction ────────────────────────────────────────────────────
        MIN_SCORE = 0.15
        if bull_score >= MIN_SCORE and bull_score > bear_score:
            direction = SignalDirection.LONG
            strength  = round(bull_score, 3)
            label     = f"BULL DIV ({len(bull_divs)}×)"
        elif bear_score >= MIN_SCORE and bear_score > bull_score:
            direction = SignalDirection.SHORT
            strength  = round(bear_score, 3)
            label     = f"BEAR DIV ({len(bear_divs)}×)"
        else:
            direction = SignalDirection.NEUTRAL
            strength  = 0.0
            label     = "NO DIV"

        return SignalResult(
            signal_type=self.SIGNAL_TYPE,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            strength=strength,
            label=label,
            details={
                "divergences": [
                    {"type": d[0], "indicator": d[1], "legs": d[2], "confidence": d[3]}
                    for d in found
                ],
                "rsi_current":      round(float(rsi[-1]), 2),
                "macd_current":     round(float(macd_l[-1]), 6),
                "macd_histogram":   round(float(macd_h[-1]), 6),
                "macd_slope":       round(float(macd_slope), 6),
                "srsi_k":           round(float(srsi_k[-1]), 2),
                "srsi_oversold":    bool(srsi_oversold),
                "srsi_overbought":  bool(srsi_overbought),
                "bull_score":       round(float(bull_score), 3),
                "bear_score":       round(float(bear_score), 3),
                "bull_count":       len(bull_divs),
                "bear_count":       len(bear_divs),
            },
        )
