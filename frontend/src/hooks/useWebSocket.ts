"use client";

/**
 * Dr. Venom Trader - WebSocket Hook
 * React hook for real-time data streaming with auto-reconnect.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSMessage, AllSignals, PriceData } from "@/types/signals";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const RECONNECT_INTERVAL = 3000;

interface UseWebSocketReturn {
  signals: AllSignals;
  price: PriceData | null;
  connected: boolean;
  sendMessage: (msg: object) => void;
  alerts: Array<{ message: string; timestamp: number }>;
}

const EMPTY_SIGNALS: AllSignals = { ALFA: {}, BETA: {}, DELTA: {}, GAMMA: {} };

export function useWebSocket(symbol: string, exchange: string = "Both"): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [connected, setConnected] = useState(false);
  const [signals, setSignals] = useState<AllSignals>(EMPTY_SIGNALS);
  const [price, setPrice] = useState<PriceData | null>(null);
  const [alerts, setAlerts] = useState<Array<{ message: string; timestamp: number }>>([]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/ws/${symbol}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log("[WS] Connected to", symbol);
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        switch (msg.type) {
          case "snapshot":
            if (msg.signals) setSignals(msg.signals);
            if (msg.price) setPrice(msg.price as PriceData);
            break;
          case "signal_update":
            if (msg.data && msg.symbol) {
              setSignals((prev) => {
                const d = msg.data as { signal_type: string; timeframe: string };
                const sigType = d.signal_type as keyof AllSignals;
                const tf = d.timeframe;
                return { ...prev, [sigType]: { ...prev[sigType], [tf]: d } };
              });
            }
            break;
          case "price_update":
            if (msg.data) {
              const p = msg.data as PriceData;
              // Filter by exchange if not "Both"
              if (exchange === "Both" || p.source?.toLowerCase() === exchange.toLowerCase()) {
                setPrice(p);
              }
            }
            break;
          case "alert":
            if (msg.data) {
              const a = msg.data as { message: string };
              setAlerts((prev) => [...prev.slice(-49), { message: a.message, timestamp: Date.now() }]);
            }
            break;
        }
      } catch (e) {
        console.error("[WS] Parse error", e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectRef.current = setTimeout(connect, RECONNECT_INTERVAL);
    };

    ws.onerror = () => ws.close();
  }, [symbol]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { signals, price, connected, sendMessage, alerts };
}
