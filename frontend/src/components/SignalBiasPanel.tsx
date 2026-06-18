"use client";

import React, { useState, useEffect, useRef } from "react";

interface SignalBiasPanelProps {
  totalBull: number;
  totalBear: number;
}

type BiasType = "STRONG_BULLISH" | "BULLISH" | "NEUTRAL" | "BEARISH" | "STRONG_BEARISH";

interface HistoryItem {
  bias: BiasType;
  duration: string;
  timestamp: number;
}

const BIAS_CONFIG = {
  STRONG_BULLISH: {
    label: "Strong Bullish",
    color: "#00e676",
    glow: "rgba(0, 230, 118, 0.75)",
    bg: "rgba(0, 230, 118, 0.1)",
    border: "rgba(0, 230, 118, 0.3)",
  },
  BULLISH: {
    label: "Bullish",
    color: "#00c853",
    glow: "rgba(0, 200, 83, 0.4)",
    bg: "rgba(0, 200, 83, 0.08)",
    border: "rgba(0, 200, 83, 0.2)",
  },
  NEUTRAL: {
    label: "Neutral",
    color: "#64748b",
    glow: "rgba(100, 116, 139, 0.1)",
    bg: "rgba(100, 116, 139, 0.05)",
    border: "rgba(100, 116, 139, 0.15)",
  },
  BEARISH: {
    label: "Bearish",
    color: "#ff1744",
    glow: "rgba(255, 23, 68, 0.4)",
    bg: "rgba(255, 23, 68, 0.08)",
    border: "rgba(255, 23, 68, 0.2)",
  },
  STRONG_BEARISH: {
    label: "Strong Bearish",
    color: "#d50000",
    glow: "rgba(213, 0, 0, 0.75)",
    bg: "rgba(213, 0, 0, 0.1)",
    border: "rgba(213, 0, 0, 0.3)",
  },
};

export default function SignalBiasPanel({ totalBull, totalBear }: SignalBiasPanelProps) {
  const [currentBias, setCurrentBias] = useState<BiasType>("NEUTRAL");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [pulse, setPulse] = useState(false);

  // Keep tracks of the previous bias to detect transitions
  const prevBiasRef = useRef<BiasType>("NEUTRAL");
  const biasStartRef = useRef<number>(Date.now());

  // Determine current bias based on net value
  const netBias = totalBull - totalBear;
  let computedBias: BiasType = "NEUTRAL";
  if (netBias >= 7) computedBias = "STRONG_BULLISH";
  else if (netBias >= 3) computedBias = "BULLISH";
  else if (netBias <= -7) computedBias = "STRONG_BEARISH";
  else if (netBias <= -3) computedBias = "BEARISH";

  // Load history from localStorage
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem("venom_bias_history");
      const savedStart = localStorage.getItem("venom_bias_start_time");
      const savedLastBias = localStorage.getItem("venom_bias_last");

      if (savedHistory) setHistory(JSON.parse(savedHistory));
      
      if (savedLastBias && savedLastBias === computedBias && savedStart) {
        biasStartRef.current = parseInt(savedStart);
        setElapsedSeconds(Math.floor((Date.now() - biasStartRef.current) / 1000));
      } else {
        biasStartRef.current = Date.now();
        localStorage.setItem("venom_bias_start_time", biasStartRef.current.toString());
        localStorage.setItem("venom_bias_last", computedBias);
      }
    } catch (e) {
      console.warn("Storage error", e);
    }
    setCurrentBias(computedBias);
    prevBiasRef.current = computedBias;
  }, []);

  // Format seconds to human-readable string
  const formatDuration = (sec: number): string => {
    if (sec < 60) return `${sec}s`;
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    if (mins < 60) return `${mins}m ${secs}s`;
    const hrs = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return `${hrs}h ${remainingMins}m`;
  };

  // Handle updates when computed bias changes
  useEffect(() => {
    if (computedBias === prevBiasRef.current) return;

    // Trigger visual flash/pulse on change
    setPulse(true);
    const timer = setTimeout(() => setPulse(false), 1200);

    // Archive the previous bias
    const durationSec = Math.floor((Date.now() - biasStartRef.current) / 1000);
    if (durationSec > 5) { // Only log if active for more than 5s
      const newHistoryItem: HistoryItem = {
        bias: prevBiasRef.current,
        duration: formatDuration(durationSec),
        timestamp: Date.now(),
      };
      
      setHistory(prev => {
        const updated = [newHistoryItem, ...prev].slice(0, 5); // Keep last 5
        localStorage.setItem("venom_bias_history", JSON.stringify(updated));
        return updated;
      });
    }

    // Reset current timer
    biasStartRef.current = Date.now();
    setElapsedSeconds(0);
    localStorage.setItem("venom_bias_start_time", biasStartRef.current.toString());
    localStorage.setItem("venom_bias_last", computedBias);

    setCurrentBias(computedBias);
    prevBiasRef.current = computedBias;

    return () => clearTimeout(timer);
  }, [computedBias]);

  // Keep timer ticking
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - biasStartRef.current) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const activeConfig = BIAS_CONFIG[currentBias];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        background: "rgba(15, 23, 42, 0.45)",
        backdropFilter: "blur(12px)",
        borderRadius: "16px",
        border: `1px solid ${pulse ? activeConfig.color : "rgba(255, 255, 255, 0.08)"}`,
        padding: "16px 20px",
        boxShadow: "0 4px 30px rgba(0, 0, 0, 0.25)",
        transition: "border-color 0.4s ease",
      }}
    >
      {/* Top Section: Glowing Bias HUD */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        
        {/* Left: Indicator Status */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {/* LED Circle */}
          <div
            style={{
              position: "relative",
              width: "20px",
              height: "20px",
              borderRadius: "50%",
              backgroundColor: activeConfig.color,
              boxShadow: `0 0 16px 4px ${activeConfig.glow}`,
              transition: "all 0.5s ease-in-out",
              animation: currentBias === "STRONG_BULLISH"
                ? "venomPulseBull 2s infinite ease-in-out" 
                : currentBias === "STRONG_BEARISH"
                ? "venomPulseBear 2s infinite ease-in-out"
                : undefined,
            }}
          />

          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>
              CONFLUENCE BIAS
            </span>
            <span
              style={{
                fontSize: "20px",
                fontWeight: 800,
                color: "#ffffff",
                letterSpacing: "-0.5px",
                textShadow: `0 2px 10px ${activeConfig.glow}40`,
              }}
            >
              {activeConfig.label}
            </span>
          </div>
        </div>

        {/* Center: Live Timer Badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: activeConfig.bg,
            border: `1px solid ${activeConfig.border}`,
            padding: "8px 16px",
            borderRadius: "30px",
            color: activeConfig.color,
            fontSize: "13px",
            fontFamily: "monospace",
            fontWeight: 700,
            transition: "all 0.5s ease",
          }}
        >
          ⏱️ Active for {formatDuration(elapsedSeconds)}
        </div>

        {/* Right: Net Signal Distribution */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
            <span style={{ fontSize: "10px", color: "#64748b", fontWeight: 600 }}>TELEMETRY SPLIT</span>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff", fontFamily: "monospace" }}>
              🟢 {totalBull} Bullish / 🔴 {totalBear} Bearish
            </span>
          </div>
          {/* Visual Bias Ratio Bar */}
          <div
            style={{
              width: "100px",
              height: "8px",
              borderRadius: "4px",
              background: "rgba(255,255,255,0.05)",
              overflow: "hidden",
              display: "flex",
              border: "1px solid rgba(255,255,255,0.05)"
            }}
          >
            {(totalBull + totalBear) > 0 ? (
              <>
                <div style={{ width: `${(totalBull / (totalBull + totalBear)) * 100}%`, background: "#00e676" }} />
                <div style={{ width: `${(totalBear / (totalBull + totalBear)) * 100}%`, background: "#ff1744" }} />
              </>
            ) : (
              <div style={{ width: "100%", background: "#475569" }} />
            )}
          </div>
        </div>
      </div>

      {/* Bottom Section: History List (Inline flow) */}
      {history.length > 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            borderTop: "1px solid rgba(255, 255, 255, 0.04)",
            paddingTop: "10px",
            fontSize: "11px",
            color: "#64748b",
            overflowX: "auto",
            whiteSpace: "nowrap"
          }}
        >
          <span style={{ fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>History:</span>
          {history.map((item, idx) => {
            const itemConf = BIAS_CONFIG[item.bias];
            return (
              <span
                key={idx}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  background: "rgba(30, 41, 59, 0.3)",
                  border: "1px solid rgba(255, 255, 255, 0.03)",
                  padding: "3px 8px",
                  borderRadius: "6px",
                  color: "#94a3b8"
                }}
              >
                <span style={{ color: itemConf.color }}>●</span>
                <span style={{ fontWeight: 600 }}>{itemConf.label}</span>
                <span style={{ color: "#475569" }}>({item.duration})</span>
              </span>
            );
          })}
        </div>
      )}

      {/* Global CSS for Glow Animations */}
      <style>{`
        @keyframes venomPulseBull {
          0% { box-shadow: 0 0 12px 3px rgba(0, 230, 118, 0.5); }
          50% { box-shadow: 0 0 24px 8px rgba(0, 230, 118, 0.9); }
          100% { box-shadow: 0 0 12px 3px rgba(0, 230, 118, 0.5); }
        }
        @keyframes venomPulseBear {
          0% { box-shadow: 0 0 12px 3px rgba(213, 0, 0, 0.5); }
          50% { box-shadow: 0 0 24px 8px rgba(213, 0, 0, 0.9); }
          100% { box-shadow: 0 0 12px 3px rgba(213, 0, 0, 0.5); }
        }
      `}</style>
    </div>
  );
}
