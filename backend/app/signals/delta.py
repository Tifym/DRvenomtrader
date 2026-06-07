"""
Dr. Venom Trader - DELTA Signal: Bollinger Bands
Price touches/stays above upper BB → RED (bearish)
Price drops below lower BB → GREEN (bullish)
Upgraded with pandas-ta and dynamic settings.
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
import structlog
from typing import List, Optional
from app.signals.base import BaseSignal, SignalResult, SignalDirection

logger = structlog.get_logger()

class DeltaSignal(BaseSignal):
    """DELTA Signal — Bollinger Bands touch/breakout detection."""
    SIGNAL_TYPE = "DELTA"
    TIMEFRAMES = ["4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]

    def __init__(self):
        self.settings = {}

    def update_settings(self, new_settings: dict):
        self.settings = new_settings

    async def compute(self, symbol: str, timeframe: str, candles: List[dict]) -> Optional[SignalResult]:
        tf_settings = self.settings.get(timeframe, {})
        global_settings = self.settings.get("GLOBAL", {})
        
        bb_length = tf_settings.get("bb_length", global_settings.get("bb_length", 20))
        bb_std = tf_settings.get("bb_std", global_settings.get("bb_std", 2.0))

        if len(candles) < bb_length + 5:
            return None

        df = pd.DataFrame(candles)
        df.ta.bbands(length=bb_length, std=bb_std, append=True)

        # Get latest row
        latest = df.iloc[-1]
        
        # Columns added by pandas-ta e.g., BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBP_20_2.0
        bbl_col = f"BBL_{bb_length}_{bb_std}"
        bbm_col = f"BBM_{bb_length}_{bb_std}"
        bbu_col = f"BBU_{bb_length}_{bb_std}"
        bbp_col = f"BBP_{bb_length}_{bb_std}"

        if bbl_col not in df.columns or pd.isna(latest[bbl_col]):
            return SignalResult(
                signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
                direction=SignalDirection.NEUTRAL, strength=0.0, label="NO DATA", details={}
            )

        cur = latest["close"]
        high = latest["high"]
        low = latest["low"]
        upper = latest[bbu_col]
        lower = latest[bbl_col]
        sma = latest[bbm_col]
        pct_b = latest[bbp_col]

        if cur >= upper or high >= upper:
            direction, strength, label = SignalDirection.SHORT, min(float(pct_b) / 1.5, 1.0) if pct_b > 0 else 1.0, "UPPER BB"
        elif cur <= lower or low <= lower:
            direction, strength, label = SignalDirection.LONG, min((1.0 - float(pct_b)) / 1.5, 1.0) if pct_b < 1 else 1.0, "LOWER BB"
        else:
            direction, strength, label = SignalDirection.NEUTRAL, 0.0, "MID BB"

        return SignalResult(
            signal_type=self.SIGNAL_TYPE, symbol=symbol, timeframe=timeframe,
            direction=direction, strength=round(max(0, min(strength, 1.0)), 3), label=label,
            details={"upper": round(float(upper), 2), "lower": round(float(lower), 2),
                     "sma": round(float(sma), 2), "price": round(float(cur), 2),
                     "pct_b": round(float(pct_b), 4)},
        )
