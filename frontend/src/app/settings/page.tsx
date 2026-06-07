"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface SignalSettingUpdate {
  signal_type: string;
  timeframe: string;
  parameters: any;
  is_active: boolean;
}

const TIMEFRAMES = ["GLOBAL", "1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"];

export default function SettingsPage() {
  const [settings, setSettings] = useState<SignalSettingUpdate[]>([]);
  const [activeTab, setActiveTab] = useState("ALFA");
  const [activeTF, setActiveTF] = useState("GLOBAL");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/settings/`)
      .then((r) => r.json())
      .then((data) => {
        if (data.settings) setSettings(data.settings);
      })
      .catch(console.error);
  }, []);

  const getParams = (signal_type: string, timeframe: string) => {
    const s = settings.find(s => s.signal_type === signal_type && s.timeframe === timeframe);
    return s?.parameters || {};
  };

  const updateParam = (signal_type: string, timeframe: string, key: string, value: any) => {
    setSettings(prev => {
      const idx = prev.findIndex(s => s.signal_type === signal_type && s.timeframe === timeframe);
      if (idx === -1) {
        return [...prev, { signal_type, timeframe, is_active: true, parameters: { [key]: value } }];
      }
      const newSettings = [...prev];
      newSettings[idx] = { ...newSettings[idx], parameters: { ...newSettings[idx].parameters, [key]: value } };
      return newSettings;
    });
  };

  const save = async () => {
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
  
  const exportSettings = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(settings));
    const a = document.createElement("a");
    a.href = dataStr;
    a.download = "drvenom_settings.json";
    a.click();
  };

  const inputStyle = { background: "rgba(17, 24, 39, 0.8)", border: "1px solid rgba(45, 55, 72, 0.5)", borderRadius: "8px", color: "#e2e8f0", padding: "8px 12px", width: "100%", outline: "none" };
  const labelStyle = { fontSize: "12px", fontWeight: 600 as const, color: "#94a3b8", marginBottom: "4px", display: "block" };
  
  const renderAlfa = () => {
    const params = getParams("ALFA", activeTF);
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div><label style={labelStyle}>Fib Zone Low</label><input type="number" step="0.001" value={params.fib_zone_low ?? 0.618} onChange={(e) => updateParam("ALFA", activeTF, "fib_zone_low", parseFloat(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>Fib Zone High</label><input type="number" step="0.001" value={params.fib_zone_high ?? 0.786} onChange={(e) => updateParam("ALFA", activeTF, "fib_zone_high", parseFloat(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>Prominence</label><input type="number" step="0.001" value={params.prominence ?? 0.005} onChange={(e) => updateParam("ALFA", activeTF, "prominence", parseFloat(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>Pivot Distance</label><input type="number" value={params.distance ?? 10} onChange={(e) => updateParam("ALFA", activeTF, "distance", parseInt(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>Use EMA 200 Filter</label><input type="checkbox" checked={params.use_ema_filter ?? true} onChange={(e) => updateParam("ALFA", activeTF, "use_ema_filter", e.target.checked)} /></div>
      </div>
    );
  };

  const renderBeta = () => {
    const params = getParams("BETA", activeTF);
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div><label style={labelStyle}>RSI Period</label><input type="number" value={params.rsi_period ?? 14} onChange={(e) => updateParam("BETA", activeTF, "rsi_period", parseInt(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>Pivot Distance</label><input type="number" value={params.pivot_distance ?? 5} onChange={(e) => updateParam("BETA", activeTF, "pivot_distance", parseInt(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>MACD Fast</label><input type="number" value={params.macd_fast ?? 12} onChange={(e) => updateParam("BETA", activeTF, "macd_fast", parseInt(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>MACD Slow</label><input type="number" value={params.macd_slow ?? 26} onChange={(e) => updateParam("BETA", activeTF, "macd_slow", parseInt(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>MACD Signal</label><input type="number" value={params.macd_signal ?? 9} onChange={(e) => updateParam("BETA", activeTF, "macd_signal", parseInt(e.target.value))} style={inputStyle} /></div>
      </div>
    );
  };

  const renderDelta = () => {
    const params = getParams("DELTA", activeTF);
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div><label style={labelStyle}>BB Length</label><input type="number" value={params.bb_length ?? 20} onChange={(e) => updateParam("DELTA", activeTF, "bb_length", parseInt(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>BB Std Dev</label><input type="number" step="0.1" value={params.bb_std ?? 2.0} onChange={(e) => updateParam("DELTA", activeTF, "bb_std", parseFloat(e.target.value))} style={inputStyle} /></div>
      </div>
    );
  };

  const renderGamma = () => {
    const params = getParams("GAMMA", activeTF);
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div><label style={labelStyle}>Min Total Volume ($)</label><input type="number" value={params.min_total_volume ?? 1000} onChange={(e) => updateParam("GAMMA", activeTF, "min_total_volume", parseInt(e.target.value))} style={inputStyle} /></div>
        <div><label style={labelStyle}>Strong Threshold ($M)</label><input type="number" step="0.1" value={params.strong_threshold_m ?? 10.0} onChange={(e) => updateParam("GAMMA", activeTF, "strong_threshold_m", parseFloat(e.target.value))} style={inputStyle} /></div>
      </div>
    );
  };

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(160deg, #0a0e17 0%, #0f1729 40%, #111827 100%)", padding: "20px" }}>
      <div style={{ maxWidth: "800px", margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <a href="/" style={{ color: "#64748b", textDecoration: "none", fontSize: "14px" }}>← Dashboard</a>
            <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#e2e8f0" }}>⚙️ Settings</h1>
          </div>
          <div style={{display: 'flex', gap: '8px'}}>
            <button onClick={exportSettings} style={{ padding: "10px 16px", borderRadius: "10px", border: "1px solid rgba(45,55,72,0.5)", background: "transparent", color: "#e2e8f0", cursor: "pointer" }}>Export JSON</button>
            <button onClick={save} disabled={saving} style={{ padding: "10px 24px", borderRadius: "10px", border: "none", cursor: "pointer", background: saved ? "rgba(0,230,118,0.2)" : "linear-gradient(135deg, #7c4dff, #00bcd4)", color: "#fff", fontWeight: 700 }}>
              {saving ? "Saving..." : saved ? "✓ Applied & Recomputing" : "Apply & Recompute"}
            </button>
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px", marginBottom: "20px", borderBottom: "1px solid rgba(45, 55, 72, 0.5)", paddingBottom: "10px" }}>
          {["ALFA", "BETA", "DELTA", "GAMMA"].map(t => (
            <button key={t} onClick={() => setActiveTab(t)} style={{ padding: "8px 16px", borderRadius: "8px", border: "none", cursor: "pointer", background: activeTab === t ? "rgba(124, 77, 255, 0.2)" : "transparent", color: activeTab === t ? "#7c4dff" : "#64748b", fontWeight: activeTab === t ? 700 : 500 }}>
              {t}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", gap: "4px", marginBottom: "20px", overflowX: "auto" }}>
          {TIMEFRAMES.map(tf => (
            <button key={tf} onClick={() => setActiveTF(tf)} style={{ padding: "4px 12px", borderRadius: "4px", border: "1px solid", borderColor: activeTF === tf ? "#00bcd4" : "rgba(45, 55, 72, 0.5)", background: activeTF === tf ? "rgba(0, 188, 212, 0.1)" : "transparent", color: activeTF === tf ? "#00bcd4" : "#64748b", fontSize: "12px", cursor: "pointer" }}>
              {tf}
            </button>
          ))}
        </div>

        <div style={{ background: "rgba(26, 31, 46, 0.6)", backdropFilter: "blur(16px)", borderRadius: "16px", border: "1px solid rgba(45, 55, 72, 0.5)", padding: "20px 24px" }}>
          {activeTab === "ALFA" && renderAlfa()}
          {activeTab === "BETA" && renderBeta()}
          {activeTab === "DELTA" && renderDelta()}
          {activeTab === "GAMMA" && renderGamma()}
        </div>
      </div>
    </div>
  );
}
