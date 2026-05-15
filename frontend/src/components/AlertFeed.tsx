"use client";

/**
 * Alert feed panel showing recent alerts with timestamps.
 */
interface AlertFeedProps {
  alerts: Array<{ message: string; timestamp: number }>;
}

export default function AlertFeed({ alerts }: AlertFeedProps) {
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
        <span style={{ fontSize: "18px" }}>🔔</span>
        <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#e2e8f0", letterSpacing: "1px" }}>
          ALERTS
        </h2>
        <span
          style={{
            marginLeft: "auto",
            padding: "3px 10px",
            background: "rgba(255,193,7,0.1)",
            border: "1px solid rgba(255,193,7,0.3)",
            borderRadius: "6px",
            fontSize: "10px",
            fontWeight: 700,
            color: "#ffc107",
          }}
        >
          {alerts.length}
        </span>
      </div>

      <div
        style={{
          maxHeight: "200px",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
        }}
      >
        {alerts.length === 0 ? (
          <div
            style={{
              padding: "20px",
              textAlign: "center",
              color: "#475569",
              fontSize: "13px",
              background: "rgba(97,110,135,0.05)",
              borderRadius: "10px",
              border: "1px dashed rgba(97,110,135,0.2)",
            }}
          >
            No alerts yet
          </div>
        ) : (
          [...alerts].reverse().map((a, i) => (
            <div
              key={i}
              style={{
                padding: "8px 12px",
                background: "rgba(17,24,39,0.4)",
                borderRadius: "8px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span style={{ fontSize: "12px", color: "#e2e8f0", flex: 1 }}>{a.message}</span>
              <span
                style={{
                  fontSize: "10px",
                  color: "#475569",
                  fontFamily: "'JetBrains Mono', monospace",
                  whiteSpace: "nowrap",
                }}
              >
                {new Date(a.timestamp).toLocaleTimeString("en-US", { hour12: false })}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
