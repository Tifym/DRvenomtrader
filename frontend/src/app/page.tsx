"use client";

import { useState } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { SignalType } from "@/types/signals";
import Header from "@/components/Header";
import SignalCard from "@/components/SignalCard";
import ConfluencePanel from "@/components/ConfluencePanel";
import AlertFeed from "@/components/AlertFeed";

const SYMBOLS = ["BTCUSDT", "ETHUSDT"];
const SIGNAL_TYPES: SignalType[] = ["ALFA", "BETA", "DELTA", "GAMMA"];

export default function Dashboard() {
  const [symbol, setSymbol] = useState(SYMBOLS[0]);
  const { signals, price, connected, alerts } = useWebSocket(symbol);

  // Overall confluence summary
  const totalBull = Object.values(signals).reduce(
    (sum, tfs) => sum + Object.values(tfs).filter((s: any) => s?.direction === "LONG").length,
    0
  );
  const totalBear = Object.values(signals).reduce(
    (sum, tfs) => sum + Object.values(tfs).filter((s: any) => s?.direction === "SHORT").length,
    0
  );

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg, #0a0e17 0%, #0f1729 40%, #111827 100%)",
        padding: "20px",
      }}
    >
      <div style={{ maxWidth: "1440px", margin: "0 auto" }}>
        <Header
          price={price}
          connected={connected}
          symbol={symbol}
          symbols={SYMBOLS}
          onSymbolChange={setSymbol}
        />

        {/* Overall bias bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "20px",
            padding: "12px 20px",
            background: "rgba(26, 31, 46, 0.5)",
            borderRadius: "12px",
            border: "1px solid rgba(45, 55, 72, 0.3)",
          }}
        >
          <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>BIAS</span>
          <div
            style={{
              flex: 1,
              height: "6px",
              background: "rgba(97,110,135,0.2)",
              borderRadius: "3px",
              overflow: "hidden",
              display: "flex",
            }}
          >
            {(totalBull + totalBear) > 0 && (
              <>
                <div
                  style={{
                    width: `${(totalBull / (totalBull + totalBear)) * 100}%`,
                    background: "linear-gradient(90deg, #00e676, #00c853)",
                    transition: "width 0.5s ease",
                  }}
                />
                <div
                  style={{
                    width: `${(totalBear / (totalBull + totalBear)) * 100}%`,
                    background: "linear-gradient(90deg, #ff1744, #d50000)",
                    transition: "width 0.5s ease",
                  }}
                />
              </>
            )}
          </div>
          <span
            style={{
              fontSize: "11px",
              fontFamily: "'JetBrains Mono', monospace",
              color: totalBull > totalBear ? "#00e676" : totalBear > totalBull ? "#ff1744" : "#64748b",
              fontWeight: 700,
            }}
          >
            {totalBull}L / {totalBear}S
          </span>
        </div>

        {/* Signal Grid — 2x2 */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "16px",
            marginBottom: "20px",
          }}
        >
          {SIGNAL_TYPES.map((st) => (
            <SignalCard key={st} signalType={st} data={signals[st] || {}} />
          ))}
        </div>

        {/* Bottom row: Confluence + Alerts */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          <ConfluencePanel signals={signals} symbol={symbol} />
          <AlertFeed alerts={alerts} />
        </div>

        {/* Footer */}
        <footer
          style={{
            textAlign: "center",
            padding: "20px 0 8px",
            color: "#334155",
            fontSize: "11px",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          Dr. Venom Trader v1.0.0 — {symbol} — {connected ? "🟢 Connected" : "🔴 Disconnected"}
          {" · "}
          <a href="/settings" style={{ color: "#475569", textDecoration: "underline" }}>⚙️ Settings</a>
        </footer>
      </div>
    </div>
  );
}
