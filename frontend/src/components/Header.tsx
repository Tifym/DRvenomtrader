"use client";

import { useEffect, useState } from "react";
import type { PriceData } from "@/types/signals";

interface HeaderProps {
  price: PriceData | null;
  connected: boolean;
  symbol: string;
  symbols: string[];
  onSymbolChange: (s: string) => void;
}

export default function Header({ price, connected, symbol, symbols, onSymbolChange }: HeaderProps) {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const formattedPrice = price?.price
    ? price.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : "---";

  return (
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "16px 24px",
        background: "rgba(26, 31, 46, 0.7)",
        backdropFilter: "blur(20px)",
        borderRadius: "16px",
        border: "1px solid rgba(45, 55, 72, 0.5)",
        marginBottom: "24px",
        flexWrap: "wrap",
        gap: "12px",
      }}
    >
      {/* Logo + Title */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <div
          style={{
            width: "42px",
            height: "42px",
            borderRadius: "12px",
            background: "linear-gradient(135deg, #7c4dff, #00bcd4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "20px",
            boxShadow: "0 4px 16px rgba(124,77,255,0.3)",
          }}
        >
          🐍
        </div>
        <div>
          <h1
            style={{
              fontSize: "22px",
              fontWeight: 800,
              background: "linear-gradient(135deg, #e2e8f0, #00bcd4)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              letterSpacing: "-0.5px",
            }}
          >
            Dr. Venom Trader
          </h1>
          <p style={{ fontSize: "11px", color: "#64748b" }}>Real-Time Signal Engine</p>
        </div>
      </div>

      {/* Center: Symbol selector + Price */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <select
          value={symbol}
          onChange={(e) => onSymbolChange(e.target.value)}
          style={{
            background: "rgba(17, 24, 39, 0.8)",
            border: "1px solid rgba(45, 55, 72, 0.5)",
            borderRadius: "10px",
            color: "#e2e8f0",
            padding: "8px 14px",
            fontSize: "14px",
            fontWeight: 700,
            fontFamily: "'JetBrains Mono', monospace",
            cursor: "pointer",
            outline: "none",
          }}
        >
          {symbols.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <div
          style={{
            padding: "8px 18px",
            background: "rgba(17, 24, 39, 0.6)",
            borderRadius: "10px",
            border: "1px solid rgba(45, 55, 72, 0.5)",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "18px",
            fontWeight: 700,
            color: "#e2e8f0",
            letterSpacing: "0.5px",
          }}
        >
          ${formattedPrice}
        </div>
      </div>

      {/* Right: Status + Clock */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 14px",
            background: connected ? "rgba(0,230,118,0.08)" : "rgba(255,23,68,0.08)",
            borderRadius: "10px",
            border: `1px solid ${connected ? "rgba(0,230,118,0.3)" : "rgba(255,23,68,0.3)"}`,
          }}
        >
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: connected ? "#00e676" : "#ff1744",
              boxShadow: connected ? "0 0 8px rgba(0,230,118,0.6)" : "0 0 8px rgba(255,23,68,0.6)",
              animation: connected ? "none" : "pulse-bear 2s infinite",
            }}
          />
          <span style={{ fontSize: "12px", fontWeight: 600, color: "#94a3b8" }}>
            {connected ? "LIVE" : "OFFLINE"}
          </span>
        </div>

        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "13px",
            color: "#94a3b8",
            padding: "8px 14px",
            background: "rgba(17, 24, 39, 0.6)",
            borderRadius: "10px",
            border: "1px solid rgba(45, 55, 72, 0.5)",
          }}
        >
          {time.toLocaleTimeString("en-US", { hour12: false })}
        </div>
      </div>
    </header>
  );
}
