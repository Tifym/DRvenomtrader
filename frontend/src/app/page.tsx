"use client";

import { useState, useEffect, useRef } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { SignalType } from "@/types/signals";
import Header from "@/components/Header";
import SignalCard from "@/components/SignalCard";
import ConfluencePanel from "@/components/ConfluencePanel";
import AlertFeed from "@/components/AlertFeed";
import SignalChart from "@/components/SignalChart";
import SignalBiasPanel from "@/components/SignalBiasPanel";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"];
const SIGNAL_TYPES: SignalType[] = ["ALFA", "BETA", "DELTA", "GAMMA"];

export default function Dashboard() {
  const [symbol, setSymbol] = useState(SYMBOLS[0]);
  const [exchange, setExchange] = useState("Both");
  const { signals, price, connected, alerts } = useWebSocket(symbol, exchange);

  const totalBull = Object.values(signals).reduce(
    (sum, tfs) => sum + Object.values(tfs).filter((s: any) => s?.direction === "LONG").length,
    0
  );
  const totalBear = Object.values(signals).reduce(
    (sum, tfs) => sum + Object.values(tfs).filter((s: any) => s?.direction === "SHORT").length,
    0
  );

  // Audio & Desktop Alerts
  const prevConfluenceRef = useRef({ bull: 0, bear: 0 });

  useEffect(() => {
    // Request notification permission
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    const prev = prevConfluenceRef.current;
    
    // Alert logic: If confluence reaches >= 3 for the first time
    if (totalBull >= 3 && prev.bull < 3) {
      playAlert("BUY");
      showNotification("Venom BUY Alert", `Strong long confluence (${totalBull}) on ${symbol}`);
    } else if (totalBear >= 3 && prev.bear < 3) {
      playAlert("SELL");
      showNotification("Venom SELL Alert", `Strong short confluence (${totalBear}) on ${symbol}`);
    }

    prevConfluenceRef.current = { bull: totalBull, bear: totalBear };
  }, [totalBull, totalBear, symbol]);

  const playAlert = (type: "BUY" | "SELL") => {
    // Using a synthetic beep or an Audio object if assets are available
    // For now we use the web audio API for a quick clean beep
    if (typeof window === "undefined") return;
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      if (type === "BUY") {
        osc.frequency.setValueAtTime(800, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.1);
      } else {
        osc.frequency.setValueAtTime(600, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(300, ctx.currentTime + 0.1);
      }
      
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
      
      osc.start();
      osc.stop(ctx.currentTime + 0.5);
    } catch (e) {
      console.log("Audio alert blocked by browser");
    }
  };

  const showNotification = (title: string, body: string) => {
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body, icon: "/favicon.ico" });
    }
  };

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
          exchange={exchange}
          onExchangeChange={setExchange}
        />

        {/* Overall premium bias panel */}
        <div style={{ marginBottom: "20px" }}>
          <SignalBiasPanel totalBull={totalBull} totalBear={totalBear} />
        </div>

        {/* Main Chart */}
        <div style={{ marginBottom: "20px" }}>
          <SignalChart symbol={symbol} price={price} signals={signals} />
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
