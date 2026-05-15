"use client";

import type { SignalType, SignalsByType } from "@/types/signals";
import { SIGNAL_META, TIMEFRAMES_BY_SIGNAL } from "@/types/signals";
import SignalBox from "./SignalBox";

/**
 * Card displaying all timeframe boxes for a single signal type.
 */
interface SignalCardProps {
  signalType: SignalType;
  data: SignalsByType;
}

export default function SignalCard({ signalType, data }: SignalCardProps) {
  const meta = SIGNAL_META[signalType];
  const timeframes = TIMEFRAMES_BY_SIGNAL[signalType];

  // Count active directions
  const bullCount = Object.values(data).filter((s) => s?.direction === "LONG").length;
  const bearCount = Object.values(data).filter((s) => s?.direction === "SHORT").length;
  const total = timeframes.length;
  const activeCount = bullCount + bearCount;

  // Determine overall card accent
  let accentColor = "#64748b";
  let accentBg = "rgba(97, 110, 135, 0.08)";
  if (bullCount > bearCount && bullCount > 0) {
    accentColor = "#00e676";
    accentBg = "rgba(0, 230, 118, 0.05)";
  } else if (bearCount > bullCount && bearCount > 0) {
    accentColor = "#ff1744";
    accentBg = "rgba(255, 23, 68, 0.05)";
  }

  return (
    <div
      style={{
        background: accentBg,
        backdropFilter: "blur(16px)",
        borderRadius: "16px",
        border: `1px solid ${accentColor}33`,
        padding: "24px",
        transition: "all 0.3s ease",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "18px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "22px" }}>{meta.icon}</span>
          <div>
            <h2
              style={{
                fontSize: "18px",
                fontWeight: 800,
                color: "#e2e8f0",
                letterSpacing: "1.5px",
              }}
            >
              {meta.name}
            </h2>
            <p style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
              {meta.description}
            </p>
          </div>
        </div>

        {/* Direction summary badges */}
        <div style={{ display: "flex", gap: "6px" }}>
          {bullCount > 0 && (
            <span
              style={{
                padding: "4px 10px",
                background: "rgba(0,230,118,0.12)",
                border: "1px solid rgba(0,230,118,0.3)",
                borderRadius: "6px",
                fontSize: "10px",
                fontWeight: 700,
                color: "#00e676",
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              ▲ {bullCount}
            </span>
          )}
          {bearCount > 0 && (
            <span
              style={{
                padding: "4px 10px",
                background: "rgba(255,23,68,0.12)",
                border: "1px solid rgba(255,23,68,0.3)",
                borderRadius: "6px",
                fontSize: "10px",
                fontWeight: 700,
                color: "#ff1744",
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              ▼ {bearCount}
            </span>
          )}
          <span
            style={{
              padding: "4px 10px",
              background: "rgba(97,110,135,0.12)",
              border: "1px solid rgba(97,110,135,0.2)",
              borderRadius: "6px",
              fontSize: "10px",
              fontWeight: 600,
              color: "#94a3b8",
            }}
          >
            {activeCount}/{total}
          </span>
        </div>
      </div>

      {/* Timeframe Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${Math.min(timeframes.length, 5)}, 1fr)`,
          gap: "8px",
        }}
      >
        {timeframes.map((tf) => (
          <SignalBox key={tf} timeframe={tf} signal={data[tf]} />
        ))}
      </div>
    </div>
  );
}
