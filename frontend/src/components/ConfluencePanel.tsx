"use client";

import type { AllSignals } from "@/types/signals";

/**
 * Confluence panel: shows when 3+ signals align in the same direction.
 */
interface ConfluencePanelProps {
  signals: AllSignals;
  symbol: string;
}

export default function ConfluencePanel({ signals, symbol }: ConfluencePanelProps) {
  // Collect all active signals across all types/timeframes
  const allActive: Array<{ type: string; tf: string; dir: string; strength: number }> = [];
  for (const [sigType, tfs] of Object.entries(signals)) {
    for (const [tf, sig] of Object.entries(tfs)) {
      if (sig && sig.direction !== "NEUTRAL") {
        allActive.push({ type: sigType, tf, dir: sig.direction, strength: sig.strength ?? 0 });
      }
    }
  }

  // Group by timeframe → check if 3+ signals align
  const tfGroups: Record<string, typeof allActive> = {};
  for (const s of allActive) {
    if (!tfGroups[s.tf]) tfGroups[s.tf] = [];
    tfGroups[s.tf].push(s);
  }

  const confluences: Array<{
    timeframe: string;
    direction: string;
    count: number;
    signals: string[];
    avgStrength: number;
  }> = [];

  for (const [tf, sigs] of Object.entries(tfGroups)) {
    const longs = sigs.filter((s) => s.dir === "LONG");
    const shorts = sigs.filter((s) => s.dir === "SHORT");
    if (longs.length >= 3) {
      confluences.push({
        timeframe: tf,
        direction: "LONG",
        count: longs.length,
        signals: longs.map((s) => s.type),
        avgStrength: longs.reduce((a, b) => a + b.strength, 0) / longs.length,
      });
    }
    if (shorts.length >= 3) {
      confluences.push({
        timeframe: tf,
        direction: "SHORT",
        count: shorts.length,
        signals: shorts.map((s) => s.type),
        avgStrength: shorts.reduce((a, b) => a + b.strength, 0) / shorts.length,
      });
    }
  }

  confluences.sort((a, b) => b.count - a.count || b.avgStrength - a.avgStrength);

  return (
    <div
      style={{
        background: "rgba(26, 31, 46, 0.6)",
        backdropFilter: "blur(16px)",
        borderRadius: "16px",
        border: "1px solid rgba(45, 55, 72, 0.5)",
        padding: "20px 24px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
        <span style={{ fontSize: "18px" }}>🎯</span>
        <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#e2e8f0", letterSpacing: "1px" }}>
          CONFLUENCE
        </h2>
        <span
          style={{
            marginLeft: "auto",
            fontSize: "11px",
            color: "#64748b",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {symbol} · 3+ aligned
        </span>
      </div>

      {confluences.length === 0 ? (
        <div
          style={{
            padding: "24px",
            textAlign: "center",
            color: "#475569",
            fontSize: "13px",
            background: "rgba(97,110,135,0.05)",
            borderRadius: "10px",
            border: "1px dashed rgba(97,110,135,0.2)",
          }}
        >
          No confluence detected — waiting for 3+ signals to align
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {confluences.map((c, i) => {
            const isLong = c.direction === "LONG";
            const color = isLong ? "#00e676" : "#ff1744";
            const bg = isLong ? "rgba(0,230,118,0.08)" : "rgba(255,23,68,0.08)";
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  background: bg,
                  borderRadius: "10px",
                  border: `1px solid ${color}33`,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "16px" }}>{isLong ? "🟢" : "🔴"}</span>
                  <div>
                    <span
                      style={{
                        fontWeight: 700,
                        color,
                        fontSize: "13px",
                        fontFamily: "'JetBrains Mono', monospace",
                      }}
                    >
                      {c.direction} · {c.timeframe}
                    </span>
                    <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>
                      {c.signals.join(" + ")}
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontWeight: 700, color, fontSize: "14px" }}>{c.count}/4</div>
                  <div style={{ fontSize: "10px", color: "#64748b" }}>
                    {(c.avgStrength * 100).toFixed(0)}% avg
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
