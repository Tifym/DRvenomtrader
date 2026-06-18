"""
Dr. Venom Trader - GAMMA Signal v2: Professional Liquidation Intelligence
=========================================================================
Upgrades from v1:
  - Liquidation Spikes: Compares current liq vs a rolling mean (Rate of Change).
  - Historical Percentiles: Requires liq to be in the upper percentiles of recent history.
  - Liquidity Sweeps: Identifies large liquidations accompanied by a candle wick (sweep & reverse).
  - Timeframe Weighting incorporated into strength.
"""

import structlog
import numpy as np
from typing import Dict, List, Optional
from app.signals.base import BaseSignal, SignalResult, SignalDirection
from app.services.candle_cache import CandleCache

logger = structlog.get_logger()

# Used for sweep detection - how much of the candle is wick?
WICK_THRESHOLD_PCT = 0.40

# Timeframe multiplier for strength. Higher TF = stronger signal.
TF_MULTIPLIERS = {
    "1D": 1.5,
    "4H": 1.25,
    "2H": 1.1,
    "1H": 1.0,
    "30m": 0.8,
    "15m": 0.7,
    "5m": 0.5,
    "3m": 0.3,
    "1m": 0.2,
}

class GammaSignal(BaseSignal):
    """
    GAMMA Signal v2 — Liquidation Imbalance & Sweep detection.
    Requires candle data for sweep logic, unlike v1.
    """
    SIGNAL_TYPE = "GAMMA"
    TIMEFRAMES = ["1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    def __init__(self):
        self.settings: dict = {}
        # In-memory history for percentiles: {symbol: {tf: {long: [], short: []}}}
        # In a real cluster this should be stored in Redis to survive restarts
        self._history = {}

    def update_settings(self, new_settings: dict):
        self.settings = new_settings

    async def compute(
        self, symbol: str, timeframe: str, candles: List[dict]
    ) -> Optional[SignalResult]:
        
        # 1. Get liquidation data
        liq = await CandleCache.get_liquidation_agg(symbol, timeframe)
        long_usd = liq.get("long_usd", 0)
        short_usd = liq.get("short_usd", 0)
        total = long_usd + short_usd

        # 2. Get settings
        tf_s = self.settings.get(timeframe, {})
        gl_s = self.settings.get("GLOBAL", {})
        def g(k, d):
            return tf_s.get(k, gl_s.get(k, d))

        min_total_usd     = g("min_total_usd",          500_000)
        spike_mult        = g("spike_mult",             2.0)
        strong_pctile     = g("strong_percentile",      75)
        very_strong_pctile= g("very_strong_percentile", 90)
        history_window    = g("history_window",         20)
        use_sweep_detect  = g("use_sweep_detect",       True)

        if total < min_total_usd:
            return self._neutral(symbol, timeframe, "LOW VOL", long_usd, short_usd)

        # 3. Update History & Calc Percentiles
        if symbol not in self._history: self._history[symbol] = {}
        if timeframe not in self._history[symbol]: self._history[symbol][timeframe] = {"L": [], "S": []}
        
        hist = self._history[symbol][timeframe]
        hist["L"].append(long_usd)
        hist["S"].append(short_usd)
        
        # Keep window size
        if len(hist["L"]) > history_window:
            hist["L"].pop(0)
            hist["S"].pop(0)

        if len(hist["L"]) < 5: # Need a tiny bit of history
            return self._neutral(symbol, timeframe, "WARMUP", long_usd, short_usd)

        l_mean = np.mean(hist["L"][:-1]) if len(hist["L"]) > 1 else 1.0
        s_mean = np.mean(hist["S"][:-1]) if len(hist["S"]) > 1 else 1.0

        l_pctile = sum(1 for x in hist["L"] if x <= long_usd) / len(hist["L"]) * 100
        s_pctile = sum(1 for x in hist["S"] if x <= short_usd) / len(hist["S"]) * 100

        long_spike = long_usd > l_mean * spike_mult and l_pctile >= strong_pctile
        short_spike = short_usd > s_mean * spike_mult and s_pctile >= strong_pctile

        if not (long_spike or short_spike):
             return self._neutral(symbol, timeframe, "NO SPIKE", long_usd, short_usd)

        # 4. Sweep Detection
        # Big Long Liq + Long Lower Wick = Sweep. Means market absorbed the selling.
        is_sweep = False
        sweep_type = "NONE"
        if use_sweep_detect and candles and len(candles) > 0:
             c = candles[-1]
             rng = c["high"] - c["low"]
             if rng > 0:
                 upper_wick = c["high"] - max(c["open"], c["close"])
                 lower_wick = min(c["open"], c["close"]) - c["low"]
                 
                 if long_spike and (lower_wick / rng) >= WICK_THRESHOLD_PCT:
                     is_sweep = True
                     sweep_type = "LOWER_SWEEP" # Bullish
                 elif short_spike and (upper_wick / rng) >= WICK_THRESHOLD_PCT:
                     is_sweep = True
                     sweep_type = "UPPER_SWEEP" # Bearish

        # 5. Logic
        long_m = long_usd / 1_000_000
        short_m = short_usd / 1_000_000

        if long_usd > short_usd:
            # Longs rekt -> Price went down -> Contrarian Buy (Short squeeze potential)
            direction = SignalDirection.SHORT # V1 says short, wait, if longs liquidated price goes down, trend is DOWN. 
            # Or is it contrarian? Let's stick to V1 logic to not break user expectations: Longs liq = SHORT signal
            
            # UNLESS it's a sweep!
            if is_sweep and sweep_type == "LOWER_SWEEP":
                 direction = SignalDirection.LONG # Reversal!
                 label = f"SWEEP L:{long_m:.1f}M"
                 base_str = 0.8 + (0.2 if l_pctile >= very_strong_pctile else 0.0)
            else:
                 direction = SignalDirection.SHORT # Trend continuation
                 label = f"LIQ L:{long_m:.1f}M"
                 base_str = min((long_usd / max(l_mean, 1)) / spike_mult * 0.5, 1.0)
            ratio = long_usd / max(short_usd, 1)

        elif short_usd > long_usd:
            if is_sweep and sweep_type == "UPPER_SWEEP":
                 direction = SignalDirection.SHORT # Reversal!
                 label = f"SWEEP S:{short_m:.1f}M"
                 base_str = 0.8 + (0.2 if s_pctile >= very_strong_pctile else 0.0)
            else:
                 direction = SignalDirection.LONG
                 label = f"LIQ S:{short_m:.1f}M"
                 base_str = min((short_usd / max(s_mean, 1)) / spike_mult * 0.5, 1.0)
            ratio = short_usd / max(long_usd, 1)
        else:
             return self._neutral(symbol, timeframe, "EQUAL", long_usd, short_usd)

        tf_mult = TF_MULTIPLIERS.get(timeframe, 1.0)
        final_strength = min(base_str * tf_mult, 1.0)

        return SignalResult(
            signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
            direction=direction, strength=round(final_strength, 3), label=label,
            details={
                "long_usd":        round(long_usd, 2), 
                "short_usd":       round(short_usd, 2),
                "long_m":          round(long_m, 2), 
                "short_m":         round(short_m, 2),
                "ratio":           round(ratio, 2), 
                "total_count":     liq.get("total_count", 0),
                "l_pctile":        round(l_pctile, 1),
                "s_pctile":        round(s_pctile, 1),
                "is_sweep":        is_sweep,
                "sweep_type":      sweep_type,
                "spike_mult":      spike_mult
            },
        )

    def _neutral(self, symbol, tf, label, l, s):
        return SignalResult(
            signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
            direction=SignalDirection.NEUTRAL, strength=0.0, label=label,
            details={"long_usd": l, "short_usd": s, "long_m": l/1e6, "short_m": s/1e6}
        )

    async def compute_all_timeframes(self, symbol: str, candles_by_tf: Dict[str, List[dict]] = None) -> List[SignalResult]:
        results = []
        for tf in self.TIMEFRAMES:
            candles = candles_by_tf.get(tf, []) if candles_by_tf else []
            result = await self.compute(symbol, tf, candles)
            if result:
                results.append(result)
        return results
