# 🐍 Dr. Venom Trader

> **Professional real-time crypto trading signals dashboard — self-hosted, Dockerized, 24/7.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 📊 Signal Engines

| Signal | Name | Logic |
|--------|------|-------|
| **ALFA** | Fibonacci Retracement | Auto Fib zones (0.618–0.786), multi-timeframe, trend-aware |
| **BETA** | Divergences | Regular + Hidden divergences on RSI + MACD with pivot detection |
| **DELTA** | Bollinger Bands | Price vs upper/lower band touches with squeeze detection |
| **GAMMA** | Liquidations | Longs vs Shorts liquidated in $M via CoinGlass + exchange streams |

---

## 🚀 Quick Start (Ubuntu 24.04)

### Prerequisites

- Docker Engine 27+ and Docker Compose v2.30+
- Git

### 1. Clone & Configure

```bash
git clone <your-repo-url> drvenomtrader
cd drvenomtrader
cp .env.example .env
nano .env   # Set passwords and API keys
```

### 2. Start All Services

```bash
docker compose up -d --build
```

### 3. Verify

```bash
docker compose ps
curl http://localhost/health
curl http://localhost/api/status
```

### 4. Access

- **Dashboard**: `http://your-server-ip`
- **Settings**: `http://your-server-ip/settings`
- **API Docs** (debug mode): `http://your-server-ip/api/docs`

---

## 🏗️ Project Structure

```
drvenomtrader/
├── docker-compose.yml
├── .env.example / .env
├── backend/                        # Python 3.12 + FastAPI
│   ├── app/
│   │   ├── main.py                 # App entry + lifespan
│   │   ├── config.py               # Pydantic settings
│   │   ├── database.py             # Async SQLAlchemy
│   │   ├── redis_client.py         # Redis manager
│   │   ├── api/
│   │   │   ├── router.py           # Signal + market data endpoints
│   │   │   ├── alerts.py           # Alert history + test endpoints
│   │   │   └── settings.py         # Runtime config endpoints
│   │   ├── models/base.py          # ORM: Symbol, SignalState, AlertLog
│   │   ├── services/
│   │   │   ├── binance_ws.py       # Binance Futures WebSocket
│   │   │   ├── bybit_ws.py         # Bybit V5 WebSocket (backup)
│   │   │   ├── coinglass.py        # CoinGlass liquidation API
│   │   │   ├── candle_cache.py     # Redis cache layer
│   │   │   ├── data_manager.py     # Data source orchestrator
│   │   │   └── alerts/
│   │   │       ├── telegram.py     # Telegram bot alerts
│   │   │       ├── discord.py      # Discord webhook alerts
│   │   │       └── confluence.py   # Confluence detection + alerting
│   │   ├── signals/
│   │   │   ├── base.py             # BaseSignal ABC + SignalResult
│   │   │   ├── alfa.py             # Fibonacci Retracement
│   │   │   ├── beta.py             # RSI + MACD Divergences
│   │   │   ├── delta.py            # Bollinger Bands
│   │   │   ├── gamma.py            # Liquidation imbalance
│   │   │   └── engine.py           # Signal computation loop
│   │   └── ws/
│   │       ├── manager.py          # WS connection manager
│   │       └── routes.py           # WS endpoint /ws/{symbol}
│   └── alembic/                    # Database migrations
├── frontend/                       # Next.js 15 + TypeScript
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Main dashboard
│       │   ├── settings/page.tsx   # Admin settings
│       │   ├── layout.tsx          # Root layout
│       │   └── globals.css         # Design system
│       ├── components/
│       │   ├── Header.tsx          # Nav + price + status
│       │   ├── SignalCard.tsx      # Signal type card
│       │   ├── SignalBox.tsx       # Timeframe box + tooltip
│       │   ├── ConfluencePanel.tsx # Confluence detector
│       │   └── AlertFeed.tsx       # Alert history feed
│       ├── hooks/useWebSocket.ts   # Real-time WS hook
│       ├── lib/api.ts              # REST API client
│       └── types/signals.ts        # TypeScript definitions
├── nginx/                          # Reverse proxy
│   ├── Dockerfile
│   └── nginx.conf                  # API + WS + frontend routing
└── docs/architecture.md
```

---

## 🌐 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Docker health check |
| GET | `/api/status` | System status |
| GET | `/api/signals/{symbol}` | All signals for symbol |
| GET | `/api/signals/{symbol}/compute` | Force recompute |
| GET | `/api/signals/{symbol}/{type}` | Specific signal type |
| GET | `/api/price/{symbol}` | Current price |
| GET | `/api/liquidations/{symbol}` | Liquidation aggregates |
| GET | `/api/candles/{symbol}/{tf}` | Cached candles |
| GET | `/api/settings/` | Current config |
| POST | `/api/settings/` | Update config |
| POST | `/api/alerts/test/telegram` | Test Telegram |
| POST | `/api/alerts/test/discord` | Test Discord |
| WS | `/ws/{symbol}` | Real-time stream |

---

## 🔔 Alert System

- **Telegram**: Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- **Discord**: Configure `DISCORD_WEBHOOK_URL`
- **Browser**: Real-time via WebSocket (automatic)
- **Confluence**: Fires when 3+ signals align on same direction/timeframe

---

## ⚙️ Configuration

All signal parameters are configurable at runtime via the Settings page (`/settings`):

| Parameter | Default | Description |
|-----------|---------|-------------|
| Fib Zone Low | 0.618 | ALFA golden zone lower bound |
| Fib Zone High | 0.786 | ALFA golden zone upper bound |
| RSI Period | 14 | BETA RSI calculation period |
| BB Period | 20 | DELTA Bollinger Band period |
| BB Std Dev | 2.0 | DELTA standard deviation multiplier |
| Confluence Threshold | 3 | Min aligned signals for alert |

---

## 📝 License

Private — All rights reserved.
