"use client";

import React, { useEffect, useRef, useState } from "react";
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time, CrosshairMode } from "lightweight-charts";
import type { PriceData, AllSignals } from "@/types/signals";

interface SignalChartProps {
  symbol: string;
  price: PriceData | null;
  signals: AllSignals;
}

export default function SignalChart({ symbol, price, signals }: SignalChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  
  const [loading, setLoading] = useState(true);

  // Initialize chart and fetch historical data
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "rgba(45, 55, 72, 0.2)" },
        horzLines: { color: "rgba(45, 55, 72, 0.2)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(45, 55, 72, 0.4)" },
      timeScale: { borderColor: "rgba(45, 55, 72, 0.4)", timeVisible: true },
    });

    const series = chart.addCandlestickSeries({
      upColor: "#00e676",
      downColor: "#ff1744",
      borderVisible: false,
      wickUpColor: "#00e676",
      wickDownColor: "#ff1744",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    // Fetch initial historical candles (1m timeframe for rapid testing)
    const fetchCandles = async () => {
      try {
        setLoading(true);
        // Using Next.js rewrites or absolute URL.
        const getApiUrl = () => {
          if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
          if (typeof window === "undefined") return "http://localhost:8000/api";
          return `${window.location.protocol}//${window.location.host}/api`;
        };
        const apiUrl = getApiUrl();
        const res = await fetch(`${apiUrl}/candles/${symbol}/1m?limit=150`);
        if (res.ok) {
          const data = await res.json();
          const chartData = data.candles.map((c: any) => ({
            time: (c.open_time / 1000) as Time,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
          }));
          series.setData(chartData);
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
  }, [symbol]);

  // Update chart with real-time price and markers
  useEffect(() => {
    if (!seriesRef.current || !price) return;
    
    const timeSec = Math.floor(price.timestamp / 60000) * 60; // Snap to 1m resolution
    
    try {
      seriesRef.current.update({
        time: timeSec as Time,
        open: price.price, 
        high: price.price,
        low: price.price,
        close: price.price,
      });

      // Generate markers from signals
      const markers: any[] = [];
      
      // BETA - Divergences
      if (signals.BETA) {
        Object.values(signals.BETA).forEach((sig: any) => {
          if (sig.direction === "LONG") {
            markers.push({ time: timeSec as Time, position: 'belowBar', color: '#00e676', shape: 'arrowUp', text: `BULL DIV (${sig.timeframe})` });
          } else if (sig.direction === "SHORT") {
            markers.push({ time: timeSec as Time, position: 'aboveBar', color: '#ff1744', shape: 'arrowDown', text: `BEAR DIV (${sig.timeframe})` });
          }
        });
      }

      // GAMMA - Liquidations
      if (signals.GAMMA) {
        Object.values(signals.GAMMA).forEach((sig: any) => {
          if (sig.direction === "LONG") {
            markers.push({ time: timeSec as Time, position: 'belowBar', color: '#00bcd4', shape: 'circle', text: `LIQ LONG` });
          } else if (sig.direction === "SHORT") {
            markers.push({ time: timeSec as Time, position: 'aboveBar', color: '#e040fb', shape: 'circle', text: `LIQ SHORT` });
          }
        });
      }

      // DELTA - Bollinger Bands Breakout
      if (signals.DELTA) {
        Object.values(signals.DELTA).forEach((sig: any) => {
          if (sig.direction === "LONG") {
            markers.push({ time: timeSec as Time, position: 'belowBar', color: '#ffd600', shape: 'arrowUp', text: `BB BREAK LONG` });
          } else if (sig.direction === "SHORT") {
            markers.push({ time: timeSec as Time, position: 'aboveBar', color: '#ffd600', shape: 'arrowDown', text: `BB BREAK SHORT` });
          }
        });
      }

      // ALFA - Fibonacci
      if (signals.ALFA) {
        Object.values(signals.ALFA).forEach((sig: any) => {
          if (sig.direction === "LONG") {
            markers.push({ time: timeSec as Time, position: 'belowBar', color: '#ff9100', shape: 'arrowUp', text: `FIB 0.618 BUY` });
          } else if (sig.direction === "SHORT") {
            markers.push({ time: timeSec as Time, position: 'aboveBar', color: '#ff9100', shape: 'arrowDown', text: `FIB 0.618 SELL` });
          }
        });
      }

      if (markers.length > 0) {
        // Prevent overlapping too many markers on the same candle visually
        seriesRef.current.setMarkers(markers);
      }
    } catch (e) {
      // Ignore update errors
    }
  }, [price, signals]);

  return (
    <div style={{ position: "relative", height: "500px", width: "100%", borderRadius: "12px", overflow: "hidden", border: "1px solid rgba(45, 55, 72, 0.3)", background: "rgba(15, 23, 42, 0.6)" }}>
      {loading && (
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10, background: "rgba(15, 23, 42, 0.8)", color: "#00e676" }}>
          Loading Chart Data...
        </div>
      )}
      <div ref={chartContainerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
