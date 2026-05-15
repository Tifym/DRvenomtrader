"""
Dr. Venom Trader - GAMMA Signal: Liquidations
Bigger Longs Liquidated → Stronger SELL (Red)
Bigger Shorts Liquidated → Stronger BUY (Green)
"""

import structlog
from typing import Dict, List, Optional
from app.signals.base import BaseSignal, SignalResult, SignalDirection
from app.services.candle_cache import CandleCache

logger = structlog.get_logger()


class GammaSignal(BaseSignal):
    """GAMMA Signal — Liquidation imbalance detection."""
    SIGNAL_TYPE = "GAMMA"
    TIMEFRAMES = ["1D", "4H", "1H", "15m", "5m", "3m", "1m"]

    async def compute(self, symbol: str, timeframe: str, candles: List[dict] = None) -> Optional[SignalResult]:
        """Compute GAMMA from aggregated liquidation data in Redis."""
        liq = await CandleCache.get_liquidation_agg(symbol, timeframe)
        long_usd = liq.get("long_usd", 0)
        short_usd = liq.get("short_usd", 0)
        total = long_usd + short_usd

        if total < 1000:  # Less than $1K total — not enough data
            return SignalResult(
                signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
                direction=SignalDirection.NEUTRAL, strength=0.0, label="LOW VOL",
                details={"long_usd": round(long_usd, 2), "short_usd": round(short_usd, 2)},
            )

        long_m = long_usd / 1_000_000
        short_m = short_usd / 1_000_000

        if long_usd > short_usd:
            ratio = long_usd / max(short_usd, 1)
            direction = SignalDirection.SHORT
            strength = min(ratio / 5.0, 1.0)
            label = f"L:{long_m:.1f}M"
        elif short_usd > long_usd:
            ratio = short_usd / max(long_usd, 1)
            direction = SignalDirection.LONG
            strength = min(ratio / 5.0, 1.0)
            label = f"S:{short_m:.1f}M"
        else:
            direction = SignalDirection.NEUTRAL
            strength = 0.0
            label = "EQUAL"
            ratio = 1.0

        return SignalResult(
            signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
            direction=direction, strength=round(strength, 3), label=label,
            details={"long_usd": round(long_usd, 2), "short_usd": round(short_usd, 2),
                     "long_m": round(long_m, 2), "short_m": round(short_m, 2),
                     "ratio": round(ratio, 2), "total_count": liq.get("total_count", 0)},
        )

    async def compute_all_timeframes(self, symbol: str, candles_by_tf: Dict[str, List[dict]] = None) -> List[SignalResult]:
        """Override: GAMMA doesn't need candles, uses Redis liquidation data."""
        results = []
        for tf in self.TIMEFRAMES:
            result = await self.compute(symbol, tf)
            if result:
                results.append(result)
        return results
