/**
 * Dr. Venom Trader - TypeScript Type Definitions
 */

export type SignalDirection = "LONG" | "SHORT" | "NEUTRAL";
export type SignalType = "ALFA" | "BETA" | "DELTA" | "GAMMA";

export interface SignalData {
  signal_type: SignalType;
  symbol: string;
  timeframe: string;
  direction: SignalDirection;
  strength: number;
  details: Record<string, unknown>;
  label: string;
}

export interface PriceData {
  symbol: string;
  price: number;
  index_price?: number;
  funding_rate?: number;
  timestamp: number;
  source?: string;
}

export interface SignalsByType {
  [timeframe: string]: SignalData;
}

export interface AllSignals {
  ALFA: SignalsByType;
  BETA: SignalsByType;
  DELTA: SignalsByType;
  GAMMA: SignalsByType;
}

export interface WSMessage {
  type: "signal_update" | "price_update" | "alert" | "snapshot" | "pong";
  symbol?: string;
  data?: unknown;
  signals?: AllSignals;
  price?: PriceData;
  timestamp?: number;
}

export interface AlertData {
  id: string;
  symbol: string;
  alert_type: string;
  message: string;
  channel: string;
  sent_at: string;
  acknowledged: boolean;
}

export const SIGNAL_META: Record<SignalType, { name: string; description: string; icon: string }> = {
  ALFA: { name: "ALFA", description: "Fibonacci Retracement", icon: "📐" },
  BETA: { name: "BETA", description: "Divergences (RSI + MACD)", icon: "📊" },
  DELTA: { name: "DELTA", description: "Bollinger Bands", icon: "📈" },
  GAMMA: { name: "GAMMA", description: "Liquidations", icon: "💧" },
};

export const TIMEFRAMES_BY_SIGNAL: Record<SignalType, string[]> = {
  ALFA: ["1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"],
  BETA: ["4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"],
  DELTA: ["4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"],
  GAMMA: ["1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"],
};
