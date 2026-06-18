"use client";

import React, { useEffect, useRef, useState } from "react";
import { createChart, IChartApi, ISeriesApi, Time, CrosshairMode } from "lightweight-charts";
import type { PriceData, AllSignals } from "@/types/signals";

interface SignalChartProps {
  symbol: string;
  price: PriceData | null;
  signals: AllSignals;
}

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1H", "2H", "4H", "1D"];

export default function SignalChart({ symbol, price, signals }: SignalChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  
  // Bollinger Bands Series
  const bbUpperSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbMiddleSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbLowerSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  
  // Liquidation Histogram Series
  const liqSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  
  // Price Lines for Fibonacci levels
  const fibLinesRef = useRef<any[]>([]);

  // State
  const [timeframe, setTimeframe] = useState("5m");
  const [loading, setLoading] = useState(true);
  const [historicalData, setHistoricalData] = useState<any[]>([]);

  // Helper: Snap timestamp to chosen timeframe resolution (in seconds)
  const getSnapResolution = (tf: string): number => {
    const unit = tf.slice(-1);
    const value = parseInt(tf);
    if (unit === "m") return value * 60;
    if (unit === "H") return value * 3600;
    if (unit === "D") return 86400;
    return 300; // default 5m
  };

  // Helper: Calculate Bollinger Bands historically
  const calculateBollingerBands = (data: any[], period = 20, multiplier = 2) => {
    const upper: any[] = [];
    const middle: any[] = [];
    const lower: any[] = [];

    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) continue;
      const slice = data.slice(i - period + 1, i + 1);
      const closes = slice.map((c) => c.close);
      const sum = closes.reduce((a, b) => a + b, 0);
      const mean = sum / period;
      
      const variance = closes.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / period;
      const stdDev = Math.sqrt(variance);

      upper.push({ time: data[i].time, value: mean + multiplier * stdDev });
      middle.push({ time: data[i].time, value: mean });
      lower.push({ time: data[i].time, value: mean - multiplier * stdDev });
    }
    return { upper, middle, lower };
  };

  // Initialize chart and fetch historical candles
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart with premium TradingView Dark style
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: "#08080c" },
        textColor: "#94a3b8",
        fontSize: 11,
        fontFamily: "'Inter', sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.03)" },
        horzLines: { color: "rgba(255, 255, 255, 0.03)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(148, 163, 184, 0.4)",
          width: 1,
          style: 2, // Dashed
          labelBackgroundColor: "#1e293b",
        },
        horzLine: {
          color: "rgba(148, 163, 184, 0.4)",
          width: 1,
          style: 2, // Dashed
          labelBackgroundColor: "#1e293b",
        },
      },
      rightPriceScale: { 
        borderColor: "rgba(255, 255, 255, 0.07)",
        autoScale: true,
      },
      timeScale: { 
        borderColor: "rgba(255, 255, 255, 0.07)", 
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Main Candlestick Series (TradingView colors and borders)
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderUpColor: "#26a69a",
      borderDownColor: "#ef5350",
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
      borderVisible: true,
    });

    // Bollinger Bands Series
    const bbUpper = chart.addLineSeries({
      color: "rgba(245, 158, 11, 0.6)", // Gold dashed
      lineWidth: 1,
      lineStyle: 1, // Dashed
      crosshairMarkerVisible: false,
    });
    const bbMiddle = chart.addLineSeries({
      color: "rgba(148, 163, 184, 0.3)", // Gray
      lineWidth: 1,
      crosshairMarkerVisible: false,
    });
    const bbLower = chart.addLineSeries({
      color: "rgba(245, 158, 11, 0.6)",
      lineWidth: 1,
      lineStyle: 1, // Dashed
      crosshairMarkerVisible: false,
    });

    // Liquidation Histogram Series (placed at bottom)
    const liqSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "liq-scale",
    });
    chart.priceScale("liq-scale").applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      visible: false,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    bbUpperSeriesRef.current = bbUpper;
    bbMiddleSeriesRef.current = bbMiddle;
    bbLowerSeriesRef.current = bbLower;
    liqSeriesRef.current = liqSeries;

    // Fetch initial candles for chosen timeframe
    const fetchCandles = async () => {
      try {
        setLoading(true);
        const getApiUrl = () => {
          if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
          if (typeof window === "undefined") return "http://localhost:8000/api";
          return `${window.location.protocol}//${window.location.host}/api`;
        };
        const apiUrl = getApiUrl();
        const res = await fetch(`${apiUrl}/candles/${symbol}/${timeframe}?limit=150`);
        if (res.ok) {
          const data = await res.json();
          const parsedCandles = data.candles.map((c: any) => ({
            time: (Number(c.open_time) / 1000) as Time,
            open: Number(c.open),
            high: Number(c.high),
            low: Number(c.low),
            close: Number(c.close),
          }));
          
          setHistoricalData(parsedCandles);
          candleSeries.setData(parsedCandles);

          // Calculate and set BB
          const bbData = calculateBollingerBands(parsedCandles);
          bbUpper.setData(bbData.upper);
          bbMiddle.setData(bbData.middle);
          bbLower.setData(bbData.lower);

          // Seed historical liquidations
          const dummyLiqs = parsedCandles.map((c: any) => ({
            time: c.time,
            value: 0,
            color: "rgba(0,0,0,0)",
          }));
          liqSeries.setData(dummyLiqs);
        }
      } catch (err) {
        console.error("Failed to fetch historical candles", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCandles();

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current?.clientWidth });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [symbol, timeframe]);

  // Handle real-time price & signals updates
  useEffect(() => {
    if (!candleSeriesRef.current || !price || historicalData.length === 0) return;

    const snapSec = getSnapResolution(timeframe);
    const timeSec = Math.floor(price.timestamp / 1000 / snapSec) * snapSec;

    try {
      // 1. Update main candlestick
      const lastCandle = historicalData[historicalData.length - 1];
      const updatedCandles = [...historicalData];
      
      const newPrice = Number(price.price);

      if (lastCandle && lastCandle.time === timeSec) {
        // Update current candle
        lastCandle.close = newPrice;
        if (newPrice > lastCandle.high) lastCandle.high = newPrice;
        if (newPrice < lastCandle.low) lastCandle.low = newPrice;
        candleSeriesRef.current.update(lastCandle);
      } else {
        // Start a new candle
        const newCandle = {
          time: timeSec as Time,
          open: newPrice,
          high: newPrice,
          low: newPrice,
          close: newPrice,
        };
        updatedCandles.push(newCandle);
        candleSeriesRef.current.update(newCandle);
        setHistoricalData(updatedCandles);
      }

      // 2. Recalculate and update Bollinger Bands real-time
      const bbData = calculateBollingerBands(updatedCandles);
      if (bbUpperSeriesRef.current && bbMiddleSeriesRef.current && bbLowerSeriesRef.current) {
        bbUpperSeriesRef.current.setData(bbData.upper);
        bbMiddleSeriesRef.current.setData(bbData.middle);
        bbLowerSeriesRef.current.setData(bbData.lower);
      }

      // 3. Draw Fibonacci retracement lines dynamically from ALFA
      const alfa = signals.ALFA?.[timeframe];
      if (alfa?.details?.fib_levels) {
        const levels = alfa.details.fib_levels as any;
        
        // Remove old lines
        fibLinesRef.current.forEach((line) => {
          try {
            candleSeriesRef.current?.removePriceLine(line);
          } catch (e) {}
        });
        fibLinesRef.current = [];

        // Add 0.618 zone line (emerald/green)
        if (levels["0.618"]) {
          const line618 = candleSeriesRef.current.createPriceLine({
            price: Number(levels["0.618"]),
            color: "#10b981",
            lineWidth: 2,
            lineStyle: 0, // Solid
            axisLabelVisible: true,
            title: "FIB 0.618 ZONE",
          });
          fibLinesRef.current.push(line618);
        }

        // Add 0.786 zone line (crimson/red)
        if (levels["0.786"]) {
          const line786 = candleSeriesRef.current.createPriceLine({
            price: Number(levels["0.786"]),
            color: "#ef4444",
            lineWidth: 2,
            lineStyle: 0, // Solid
            axisLabelVisible: true,
            title: "FIB 0.786 STOP",
          });
          fibLinesRef.current.push(line786);
        }
      }

      // 4. Update markers: Divergences (BETA) & Bollinger Breakouts (DELTA)
      const markers: any[] = [];

      // BETA - Divergences
      const beta = signals.BETA?.[timeframe];
      if (beta && beta.direction !== "NEUTRAL") {
        const label = beta.label || "DIV";
        const isBull = beta.direction === "LONG";
        markers.push({
          time: timeSec as Time,
          position: isBull ? "belowBar" : "aboveBar",
          color: isBull ? "#10b981" : "#ef4444",
          shape: isBull ? "arrowUp" : "arrowDown",
          text: `BETA: ${label}`,
        });
      }

      // DELTA - BB Breakouts
      const delta = signals.DELTA?.[timeframe];
      if (delta && delta.direction !== "NEUTRAL") {
        const label = delta.label || "BB Break";
        const isBull = delta.direction === "LONG";
        markers.push({
          time: timeSec as Time,
          position: isBull ? "belowBar" : "aboveBar",
          color: "#f59e0b",
          shape: isBull ? "arrowUp" : "arrowDown",
          text: `DELTA: ${label}`,
        });
      }

      if (markers.length > 0) {
        candleSeriesRef.current.setMarkers(markers);
      }

      // 5. Update Liquidations (GAMMA) as volume-style histogram at the bottom
      const gamma = signals.GAMMA?.[timeframe];
      if (gamma && liqSeriesRef.current) {
        const details = gamma.details || {};
        const longLiq = Number(details.long_usd || 0);
        const shortLiq = Number(details.short_usd || 0);

        if (longLiq > 0) {
          liqSeriesRef.current.update({
            time: timeSec as Time,
            value: longLiq,
            color: "rgba(239, 68, 68, 0.85)", // Red bar for long liq
          });
        } else if (shortLiq > 0) {
          liqSeriesRef.current.update({
            time: timeSec as Time,
            value: shortLiq,
            color: "rgba(16, 185, 129, 0.85)", // Green bar for short liq
          });
        }
      }
    } catch (e) {
      console.warn("Error updating real-time chart elements", e);
    }
  }, [price, signals, timeframe, historicalData]);

  // Extract signal values for dashboard display
  const activeAlfa = signals.ALFA?.[timeframe];
  const activeBeta = signals.BETA?.[timeframe];
  const activeDelta = signals.DELTA?.[timeframe];
  const activeGamma = signals.GAMMA?.[timeframe];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%" }}>
      {/* Top chart controls and Timeframe Selector */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(15, 23, 42, 0.4)", padding: "10px 16px", borderRadius: "12px", border: "1px solid rgba(45, 55, 72, 0.2)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "16px", fontWeight: 700, color: "#fff", letterSpacing: "0.5px" }}>
            📊 {symbol} LIVE TELEMETRY
          </span>
          <span style={{ fontSize: "12px", color: "#64748b", background: "rgba(100, 116, 139, 0.15)", padding: "2px 8px", borderRadius: "6px", fontFamily: "monospace" }}>
            {timeframe}
          </span>
        </div>

        {/* Timeframe Buttons */}
        <div style={{ display: "flex", gap: "4px" }}>
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              style={{
                padding: "6px 12px",
                borderRadius: "8px",
                border: "none",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                background: timeframe === tf ? "#10b981" : "rgba(30, 41, 59, 0.6)",
                color: timeframe === tf ? "#0f172a" : "#94a3b8",
                transition: "all 0.2s ease",
              }}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <div style={{ position: "relative", height: "550px", width: "100%", borderRadius: "16px", overflow: "hidden", border: "1px solid rgba(255, 255, 255, 0.08)", background: "#08080c" }}>
        {loading && (
          <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", gap: "10px", alignItems: "center", justifyContent: "center", zIndex: 10, background: "rgba(8, 8, 12, 0.95)", color: "#26a69a" }}>
            <div style={{ width: "30px", height: "30px", borderRadius: "50%", border: "3px solid rgba(38, 166, 154, 0.2)", borderTopColor: "#26a69a", animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: "13px", fontWeight: 600 }}>Syncing Historical Telemetry...</span>
            <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* Chart Viewport */}
        <div ref={chartContainerRef} style={{ width: "100%", height: "100%" }} />

        {/* Dynamic Glassmorphic Floating Legend Panels */}
        <div style={{ position: "absolute", top: "20px", left: "20px", zIndex: 5, display: "flex", flexDirection: "column", gap: "10px", pointerEvents: "none" }}>
          
          {/* Signal Confluence Overlay */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", background: "rgba(15, 23, 42, 0.8)", backdropFilter: "blur(12px)", border: "1px solid rgba(255, 255, 255, 0.08)", padding: "12px", borderRadius: "12px", width: "240px", boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.3)" }}>
            <span style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>INDICATOR OVERLAYS</span>
            
            {/* ALFA */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>🔹 ALFA (Fibonacci)</span>
              <span style={{ fontSize: "11px", fontWeight: 700, color: activeAlfa?.direction === "LONG" ? "#10b981" : activeAlfa?.direction === "SHORT" ? "#ef4444" : "#64748b" }}>
                {activeAlfa?.label || "OUT"}
              </span>
            </div>

            {/* BETA */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>🔸 BETA (Divergence)</span>
              <span style={{ fontSize: "11px", fontWeight: 700, color: activeBeta?.direction === "LONG" ? "#10b981" : activeBeta?.direction === "SHORT" ? "#ef4444" : "#64748b" }}>
                {activeBeta?.label || "NO DIV"}
              </span>
            </div>

            {/* DELTA */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>💛 DELTA (Bollinger)</span>
              <span style={{ fontSize: "11px", fontWeight: 700, color: activeDelta?.direction === "LONG" ? "#10b981" : activeDelta?.direction === "SHORT" ? "#ef4444" : "#64748b" }}>
                {activeDelta?.label || "MID BB"}
              </span>
            </div>

            {/* GAMMA */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>💥 GAMMA (Liquidations)</span>
              <span style={{ fontSize: "11px", fontWeight: 700, color: activeGamma?.direction === "LONG" ? "#10b981" : activeGamma?.direction === "SHORT" ? "#ef4444" : "#64748b" }}>
                {activeGamma?.label || "LOW VOL"}
              </span>
            </div>
          </div>

          {/* Color/Marker Legend explanation */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", background: "rgba(15, 23, 42, 0.8)", backdropFilter: "blur(12px)", border: "1px solid rgba(255, 255, 255, 0.08)", padding: "10px 12px", borderRadius: "12px", width: "240px", boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.3)" }}>
            <span style={{ fontSize: "9px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>MAP KEY</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", fontSize: "10px", color: "#94a3b8" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b" }} />
                <span>Bollinger</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "8px", height: "8px", background: "#10b981" }} />
                <span>Fib 0.618</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "8px", height: "8px", background: "#ef4444" }} />
                <span>Fib 0.786</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span style={{ color: "#10b981" }}>▲</span>
                <span>Bull Div</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span style={{ color: "#ef4444" }}>▼</span>
                <span>Bear Div</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "12px", height: "6px", background: "rgba(239, 68, 68, 0.5)" }} />
                <span>Long Liq</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "12px", height: "6px", background: "rgba(16, 185, 129, 0.5)" }} />
                <span>Short Liq</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
