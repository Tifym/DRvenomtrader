/**
 * Dr. Venom Trader - API Client
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  getStatus: () => fetchJSON<{ status: string; signals: string[]; symbols: string[] }>("/status"),
  getSignals: (symbol: string) => fetchJSON<{ symbol: string; price: unknown; signals: unknown }>(`/signals/${symbol}`),
  computeSignals: (symbol: string) => fetchJSON<{ symbol: string; signals: unknown }>(`/signals/${symbol}/compute`),
  getPrice: (symbol: string) => fetchJSON<{ symbol: string; price: unknown }>(`/price/${symbol}`),
  getLiquidations: (symbol: string, tf: string) =>
    fetchJSON<{ data: unknown }>(`/liquidations/${symbol}?timeframe=${tf}`),
};
