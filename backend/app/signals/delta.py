"""
Dr. Venom Trader - DELTA Signal v2: Professional Bollinger Bands System
=======================================================================
Upgrades from v1:
  - Squeeze detection (BB Bandwidth 50-period 20th percentile) to filter noise.
  - Keltner Channel (KC) overlay to grade breakout strength.
  - "BB Walk" detection (3+ closes outside BB = strong trend).
  - ADX filter (must be trending for BB breakouts).
  - Volume confirmation for breakouts.
  - 4-component strength score: Base (%B) + KC + Walk + Vol/ADX bonuses.
"""

import numpy as np
import pandas as pd
import pandas_ta_classic as ta
import structlog
from typing import List, Optional

from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()

class DeltaSignal(BaseSignal):
    """
    DELTA Signal v2 — Bollinger Bands System with Squeeze & Keltner Channels.
    """

    SIGNAL_TYPE = "DELTA"
    TIMEFRAMES = ["4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    def __init__(self):
        self.settings: dict = {}

    def update_settings(self, new_settings: dict):
        self.settings = new_settings

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:

        if len(candles) < 100:  # Need 100 for proper squeeze lookback + BB
            return None

        # ── Settings ─────────────────────────────────────────────────────────
        tf_s = self.settings.get(timeframe, {})
        gl_s = self.settings.get("GLOBAL", {})
        def g(k, d):
            return tf_s.get(k, gl_s.get(k, d))

        bb_len           = g("bb_length",        20)
        bb_std           = g("bb_std",           2.0)
        kc_mult          = g("kc_mult",          1.5)
        use_kc_filter    = g("use_kc_filter",    True)
        use_adx_filter   = g("use_adx_filter",   True)
        adx_min          = g("adx_min",          20)
        walk_bars        = g("walk_bars",        3)
        sqz_lookback     = g("squeeze_lookback", 50)
        vol_confirm      = g("vol_confirm",      True)

        # ── Data and Indicators ──────────────────────────────────────────────
        df = pd.DataFrame(candles)
        
        # BB
        df.ta.bbands(length=bb_len, std=bb_std, append=True)
        bbl_col = f"BBL_{bb_len}_{float(bb_std)}"
        bbm_col = f"BBM_{bb_len}_{float(bb_std)}"
        bbu_col = f"BBU_{bb_len}_{float(bb_std)}"
        bbw_col = f"BBB_{bb_len}_{float(bb_std)}"
        bbp_col = f"BBP_{bb_len}_{float(bb_std)}"

        # Keltner Channels
        df.ta.kc(length=bb_len, scalar=kc_mult, append=True)
        # Check standard KC naming convention
        kcl_cols = [c for c in df.columns if c.startswith("KCL")]
        kcu_cols = [c for c in df.columns if c.startswith("KCU")]
        
        if not kcl_cols or not kcu_cols or bbl_col not in df.columns:
             return None
             
        kcl_col = kcl_cols[0]
        kcu_col = kcu_cols[0]

        # ADX
        if use_adx_filter:
            df.ta.adx(length=14, append=True)
            adx_col = "ADX_14"
        else:
            adx_col = None

        df = df.dropna(subset=[bbl_col])
        if len(df) < sqz_lookback + 5:
            return None

        # ── Extract Series ───────────────────────────────────────────────────
        closes  = df["close"].values
        highs   = df["high"].values
        lows    = df["low"].values
        vols    = df["volume"].values if "volume" in df.columns else np.ones(len(df))
        
        bb_u    = df[bbu_col].values
        bb_l    = df[bbl_col].values
        bb_w    = df[bbw_col].values
        bb_p    = df[bbp_col].values
        kc_u    = df[kcu_col].values
        kc_l    = df[kcl_col].values
        
        adx_val = df[adx_col].values[-1] if adx_col and adx_col in df.columns else (adx_min + 1)
        
        cur_c = closes[-1]
        cur_h = highs[-1]
        cur_l = lows[-1]
        cur_p = bb_p[-1]

        # ── Squeeze Detection ────────────────────────────────────────────────
        # If current BB bandwidth is in the bottom 20% of its history, it's squeezing.
        # Breakouts from a squeeze are powerful. Signals IN a squeeze are ignored.
        recent_bbw = bb_w[-sqz_lookback:]
        bbw_20th = np.percentile(recent_bbw, 20)
        is_squeeze = bb_w[-1] < bbw_20th

        # ── KC Filter ────────────────────────────────────────────────────────
        # Bollinger Bands inside Keltner Channel = Squeeze.
        # But we use KC here to confirm breakouts: if price clears BB *and* KC, it's strong.
        kc_break_up = cur_c > kc_u[-1] or cur_h > kc_u[-1]
        kc_break_dn = cur_c < kc_l[-1] or cur_l < kc_l[-1]

        # ── BB Walk Detection ────────────────────────────────────────────────
        # How many consecutive closes outside the band?
        walk_up_count = 0
        for i in range(1, len(closes)):
            if closes[-i] > bb_u[-i]:
                walk_up_count += 1
            else:
                break
                
        walk_dn_count = 0
        for i in range(1, len(closes)):
            if closes[-i] < bb_l[-i]:
                walk_dn_count += 1
            else:
                break

        is_walking_up = walk_up_count >= walk_bars
        is_walking_dn = walk_dn_count >= walk_bars

        # ── Volume & ADX Confirmation ────────────────────────────────────────
        avg_vol = np.mean(vols[-50:-1]) if len(vols) > 50 else 1.0
        vol_ok  = (not vol_confirm) or vols[-1] >= avg_vol * 1.2  # 20% above avg

        adx_ok  = (not use_adx_filter) or (not np.isnan(adx_val) and adx_val >= adx_min)

        # ── Signal Logic ─────────────────────────────────────────────────────
        if is_squeeze:
            direction = SignalDirection.NEUTRAL
            strength  = 0.0
            label     = "SQUEEZE"
        elif cur_c >= bb_u[-1] or cur_h >= bb_u[-1]:
            # Bearish reversal or Bullish continuation (Walk)?
            # Standard BB system treats touching upper band as overbought (SHORT).
            # But if it's "walking" the band, it's a strong LONG trend.
            if is_walking_up and adx_ok:
                 direction = SignalDirection.LONG
                 label = f"BB WALK UP ({walk_up_count})"
                 base_st = min(float(cur_p), 1.0) # Strength based on %B
            else:
                 direction = SignalDirection.SHORT
                 label = "UPPER BB"
                 base_st = min(float(cur_p) / 1.5, 1.0) if cur_p > 0 else 1.0
                 
            strength = base_st
            if use_kc_filter and kc_break_up: strength += 0.2
            if vol_ok: strength += 0.1
            if adx_ok: strength += 0.1

        elif cur_c <= bb_l[-1] or cur_l <= bb_l[-1]:
            # Bullish reversal or Bearish continuation (Walk)?
            if is_walking_dn and adx_ok:
                 direction = SignalDirection.SHORT
                 label = f"BB WALK DN ({walk_dn_count})"
                 base_st = min(1.0 - float(cur_p), 1.0)
            else:
                 direction = SignalDirection.LONG
                 label = "LOWER BB"
                 base_st = min((1.0 - float(cur_p)) / 1.5, 1.0) if cur_p < 1 else 1.0
                 
            strength = base_st
            if use_kc_filter and kc_break_dn: strength += 0.2
            if vol_ok: strength += 0.1
            if adx_ok: strength += 0.1
        else:
            direction = SignalDirection.NEUTRAL
            strength  = 0.0
            label     = "MID BB"

        return SignalResult(
            signal_type=self.SIGNAL_TYPE,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            strength=round(min(strength, 1.0), 3),
            label=label,
            details={
                "upper":          round(float(bb_u[-1]), 2),
                "lower":          round(float(bb_l[-1]), 2),
                "kc_upper":       round(float(kc_u[-1]), 2),
                "kc_lower":       round(float(kc_l[-1]), 2),
                "price":          round(float(cur_c), 2),
                "pct_b":          round(float(cur_p), 4),
                "bandwidth":      round(float(bb_w[-1]), 4),
                "is_squeeze":     bool(is_squeeze),
                "bbw_20th_pct":   round(float(bbw_20th), 4),
                "walk_up_count":  walk_up_count,
                "walk_dn_count":  walk_dn_count,
                "kc_break_up":    bool(kc_break_up),
                "kc_break_dn":    bool(kc_break_dn),
                "adx":            round(float(adx_val), 2),
                "adx_ok":         bool(adx_ok),
                "vol_ok":         bool(vol_ok),
            },
        )
