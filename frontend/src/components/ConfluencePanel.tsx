"use client";

import type { AllSignals } from "@/types/signals";

const TF_WEIGHTS: Record<string, number> = {
  "1D": 4.0, "4H": 3.0, "2H": 2.0, "1H": 2.0,
  "30m": 1.5, "15m": 1.0, "5m": 0.75, "3m": 0.5, "1m": 0.25
};

const SIG_WEIGHTS: Record<string, number> = {
  "ALFA": 1.0,
  "BETA": 1.0,
  "GAMMA": 0.9,
  "DELTA": 0.8
};

interface ConfluencePanelProps {
  signals: AllSignals;
  symbol: string;
}

export default function ConfluencePanel({ signals, symbol }: ConfluencePanelProps) {
  const allActive: Array<{ type: string; tf: string; dir: string; strength: number }> = [];
  for (const [sigType, tfs] of Object.entries(signals)) {
    for (const [tf, sig] of Object.entries(tfs)) {
      const s = sig as any;
      if (s && typeof s === 'object' && 'direction' in s && s.direction !== "NEUTRAL" && (s.strength ?? 0) >= 0.25) {
        allActive.push({ type: sigType, tf, dir: s.direction, strength: s.strength ?? 0 });
      }
    }
  }

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
    score: number;
    tier: string;
  }> = [];

  const calcScore = (signalsArr: typeof allActive) => {
    let score = 0;
    signalsArr.forEach(s => {
      score += (TF_WEIGHTS[s.tf] || 1.0) * (SIG_WEIGHTS[s.type] || 1.0) * s.strength;
    });
    return score;
  };

  const getTier = (score: number) => {
    if (score >= 8.0) return "ULTRA";
    if (score >= 6.0) return "STRONG";
    return "VALID";
  };

  for (const [tf, sigs] of Object.entries(tfGroups)) {
    const longs = sigs.filter((s) => s.dir === "LONG");
    const shorts = sigs.filter((s) => s.dir === "SHORT");
    
    if (longs.length >= 2) {
      const score = calcScore(longs);
      confluences.push({
        timeframe: tf, direction: "LONG", count: longs.length,
        signals: longs.map((s) => s.type), score, tier: getTier(score)
      });
    }
    if (shorts.length >= 2) {
      const score = calcScore(shorts);
      confluences.push({
        timeframe: tf, direction: "SHORT", count: shorts.length,
        signals: shorts.map((s) => s.type), score, tier: getTier(score)
      });
    }
  }

  confluences.sort((a, b) => b.score - a.score);

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
          {symbol} · 2+ aligned
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
          No confluence detected — waiting for signals to align
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {confluences.map((c, i) => {
            const isLong = c.direction === "LONG";
            const color = isLong ? "#00e676" : "#ff1744";
            const bg = isLong ? "rgba(0,230,118,0.08)" : "rgba(255,23,68,0.08)";
            
            let tierColor = "#64748b";
            let tierShadow = "none";
            if (c.tier === "ULTRA") {
              tierColor = "#fbbf24"; // Gold
              tierShadow = "0 0 10px rgba(251, 191, 36, 0.6)";
            } else if (c.tier === "STRONG") {
              tierColor = "#38bdf8"; // Light Blue
              tierShadow = "0 0 8px rgba(56, 189, 248, 0.4)";
            }

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
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
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
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 800,
                          color: tierColor,
                          background: "rgba(15, 23, 42, 0.5)",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          border: `1px solid ${tierColor}40`,
                          boxShadow: tierShadow,
                          textShadow: tierShadow,
                        }}
                      >
                        [{c.tier}]
                      </span>
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>
                      {c.signals.join(" + ")}
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontWeight: 700, color, fontSize: "14px" }}>{c.count}/4</div>
                  <div style={{ fontSize: "10px", color: "#64748b" }}>
                    Score: {c.score.toFixed(1)}
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
