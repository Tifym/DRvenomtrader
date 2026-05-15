"use client";

import type { SignalData, SignalDirection } from "@/types/signals";
import { useState } from "react";

/**
 * Individual signal timeframe box with color-coded state and hover tooltip.
 */
interface SignalBoxProps {
  timeframe: string;
  signal?: SignalData;
}

const COLORS: Record<SignalDirection, { bg: string; border: string; glow: string; text: string }> = {
  LONG: {
    bg: "rgba(0, 230, 118, 0.12)",
    border: "rgba(0, 230, 118, 0.6)",
    glow: "0 0 12px rgba(0, 230, 118, 0.3)",
    text: "#00e676",
  },
  SHORT: {
    bg: "rgba(255, 23, 68, 0.12)",
    border: "rgba(255, 23, 68, 0.6)",
    glow: "0 0 12px rgba(255, 23, 68, 0.3)",
    text: "#ff1744",
  },
  NEUTRAL: {
    bg: "rgba(97, 110, 135, 0.1)",
    border: "rgba(97, 110, 135, 0.3)",
    glow: "none",
    text: "#64748b",
  },
};

export default function SignalBox({ timeframe, signal }: SignalBoxProps) {
  const [hovered, setHovered] = useState(false);
  const dir: SignalDirection = signal?.direction || "NEUTRAL";
  const c = COLORS[dir];
  const strength = signal?.strength ?? 0;

  return (
    <div
      style={{ position: "relative" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "10px 6px",
          borderRadius: "8px",
          background: c.bg,
          border: `1px solid ${c.border}`,
          boxShadow: c.glow,
          cursor: "pointer",
          transition: "all 0.25s ease",
          transform: hovered ? "scale(1.08)" : "scale(1)",
          minWidth: "52px",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            fontWeight: 700,
            color: c.text,
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {timeframe}
        </span>
        <span style={{ fontSize: "9px", color: c.text, marginTop: "3px", fontWeight: 600 }}>
          {signal?.label || "---"}
        </span>
        {strength > 0 && (
          <div
            style={{
              width: "100%",
              height: "2px",
              background: "rgba(255,255,255,0.1)",
              borderRadius: "1px",
              marginTop: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${strength * 100}%`,
                height: "100%",
                background: c.text,
                borderRadius: "1px",
                transition: "width 0.5s ease",
              }}
            />
          </div>
        )}
      </div>

      {/* Tooltip */}
      {hovered && signal && signal.direction !== "NEUTRAL" && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(15, 20, 35, 0.95)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(45, 55, 72, 0.6)",
            borderRadius: "10px",
            padding: "12px 16px",
            zIndex: 50,
            minWidth: "200px",
            fontSize: "12px",
            boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
          }}
        >
          <div style={{ fontWeight: 700, color: c.text, marginBottom: "6px" }}>
            {signal.signal_type} — {timeframe}
          </div>
          <div style={{ color: "#94a3b8", lineHeight: 1.6 }}>
            <div>Direction: <strong style={{ color: c.text }}>{dir}</strong></div>
            <div>Strength: {(strength * 100).toFixed(0)}%</div>
            {signal.details && Object.entries(signal.details).slice(0, 5).map(([k, v]) => (
              <div key={k}>
                {k}: <span style={{ color: "#e2e8f0" }}>{typeof v === "number" ? (v as number).toFixed(2) : String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
