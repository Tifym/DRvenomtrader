"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface AppSettings {
  symbols: string[];
  fib_zone_low: number;
  fib_zone_high: number;
  bb_period: number;
  bb_std_dev: number;
  rsi_period: number;
  confluence_threshold: number;
  alert_telegram: boolean;
  alert_discord: boolean;
  coinglass_enabled: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testResult, setTestResult] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/settings/`)
      .then((r) => r.json())
      .then(setSettings)
      .catch(() => setSettings(null));
  }, []);

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await fetch(`${API_URL}/settings/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      /* ignore */
    }
    setSaving(false);
  };

  const testAlert = async (channel: "telegram" | "discord") => {
    setTestResult(`Sending ${channel} test...`);
    try {
      const res = await fetch(`${API_URL}/alerts/test/${channel}`, { method: "POST" });
      const data = await res.json();
      setTestResult(data.sent ? `${channel} ✓ sent` : `${channel} ✗ failed`);
    } catch {
      setTestResult(`${channel} ✗ error`);
    }
    setTimeout(() => setTestResult(""), 3000);
  };

  const inputStyle = {
    background: "rgba(17, 24, 39, 0.8)",
    border: "1px solid rgba(45, 55, 72, 0.5)",
    borderRadius: "8px",
    color: "#e2e8f0",
    padding: "8px 12px",
    fontSize: "14px",
    fontFamily: "'JetBrains Mono', monospace",
    width: "100%",
    outline: "none",
  };

  const labelStyle = {
    fontSize: "12px",
    fontWeight: 600 as const,
    color: "#94a3b8",
    marginBottom: "4px",
    display: "block" as const,
  };

  if (!settings) {
    return (
      <div style={{ minHeight: "100vh", background: "#0a0e17", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
        Loading settings...
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(160deg, #0a0e17 0%, #0f1729 40%, #111827 100%)", padding: "20px" }}>
      <div style={{ maxWidth: "800px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <a href="/" style={{ color: "#64748b", textDecoration: "none", fontSize: "14px" }}>← Dashboard</a>
            <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#e2e8f0" }}>⚙️ Settings</h1>
          </div>
          <button
            onClick={save}
            disabled={saving}
            style={{
              padding: "10px 24px", borderRadius: "10px", border: "none", cursor: "pointer",
              background: saved ? "rgba(0,230,118,0.2)" : "linear-gradient(135deg, #7c4dff, #00bcd4)",
              color: "#fff", fontWeight: 700, fontSize: "14px",
              transition: "all 0.3s ease",
            }}
          >
            {saving ? "Saving..." : saved ? "✓ Saved" : "Save Settings"}
          </button>
        </div>

        {/* ALFA Settings */}
        <Section title="📐 ALFA — Fibonacci Retracement">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={labelStyle}>Golden Zone Low</label>
              <input type="number" step="0.001" value={settings.fib_zone_low} onChange={(e) => setSettings({ ...settings, fib_zone_low: parseFloat(e.target.value) || 0.618 })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Golden Zone High</label>
              <input type="number" step="0.001" value={settings.fib_zone_high} onChange={(e) => setSettings({ ...settings, fib_zone_high: parseFloat(e.target.value) || 0.786 })} style={inputStyle} />
            </div>
          </div>
        </Section>

        {/* BETA Settings */}
        <Section title="📊 BETA — Divergences">
          <div>
            <label style={labelStyle}>RSI Period</label>
            <input type="number" value={settings.rsi_period} onChange={(e) => setSettings({ ...settings, rsi_period: parseInt(e.target.value) || 14 })} style={inputStyle} />
          </div>
        </Section>

        {/* DELTA Settings */}
        <Section title="📈 DELTA — Bollinger Bands">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={labelStyle}>BB Period</label>
              <input type="number" value={settings.bb_period} onChange={(e) => setSettings({ ...settings, bb_period: parseInt(e.target.value) || 20 })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>BB Std Dev</label>
              <input type="number" step="0.1" value={settings.bb_std_dev} onChange={(e) => setSettings({ ...settings, bb_std_dev: parseFloat(e.target.value) || 2.0 })} style={inputStyle} />
            </div>
          </div>
        </Section>

        {/* Confluence */}
        <Section title="🎯 Confluence">
          <div>
            <label style={labelStyle}>Alert Threshold (min aligned signals)</label>
            <input type="number" min="2" max="4" value={settings.confluence_threshold} onChange={(e) => setSettings({ ...settings, confluence_threshold: parseInt(e.target.value) || 3 })} style={inputStyle} />
          </div>
        </Section>

        {/* Symbols */}
        <Section title="💱 Symbols">
          <div>
            <label style={labelStyle}>Tracked Symbols (comma separated)</label>
            <input type="text" value={settings.symbols.join(", ")} onChange={(e) => setSettings({ ...settings, symbols: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} style={inputStyle} />
          </div>
        </Section>

        {/* Alert Channels */}
        <Section title="🔔 Alert Channels">
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <span style={{ color: "#e2e8f0", fontWeight: 600 }}>Telegram</span>
                <span style={{ marginLeft: "8px", fontSize: "11px", color: settings.alert_telegram ? "#00e676" : "#ff1744" }}>
                  {settings.alert_telegram ? "● Configured" : "● Not configured"}
                </span>
              </div>
              <button onClick={() => testAlert("telegram")} style={{ padding: "6px 14px", borderRadius: "8px", border: "1px solid rgba(45,55,72,0.5)", background: "rgba(17,24,39,0.8)", color: "#94a3b8", cursor: "pointer", fontSize: "12px" }}>
                Test
              </button>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <span style={{ color: "#e2e8f0", fontWeight: 600 }}>Discord</span>
                <span style={{ marginLeft: "8px", fontSize: "11px", color: settings.alert_discord ? "#00e676" : "#ff1744" }}>
                  {settings.alert_discord ? "● Configured" : "● Not configured"}
                </span>
              </div>
              <button onClick={() => testAlert("discord")} style={{ padding: "6px 14px", borderRadius: "8px", border: "1px solid rgba(45,55,72,0.5)", background: "rgba(17,24,39,0.8)", color: "#94a3b8", cursor: "pointer", fontSize: "12px" }}>
                Test
              </button>
            </div>
            <div>
              <span style={{ color: "#e2e8f0", fontWeight: 600 }}>CoinGlass API</span>
              <span style={{ marginLeft: "8px", fontSize: "11px", color: settings.coinglass_enabled ? "#00e676" : "#ff1744" }}>
                {settings.coinglass_enabled ? "● Active" : "● Not configured"}
              </span>
            </div>
            {testResult && (
              <div style={{ fontSize: "12px", color: testResult.includes("✓") ? "#00e676" : "#ffc107", padding: "8px 12px", background: "rgba(17,24,39,0.6)", borderRadius: "8px" }}>
                {testResult}
              </div>
            )}
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "rgba(26, 31, 46, 0.6)", backdropFilter: "blur(16px)", borderRadius: "16px", border: "1px solid rgba(45, 55, 72, 0.5)", padding: "20px 24px", marginBottom: "16px" }}>
      <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#e2e8f0", marginBottom: "16px", letterSpacing: "0.5px" }}>{title}</h2>
      {children}
    </div>
  );
}
