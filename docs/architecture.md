# Dr. Venom Trader — Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        NGINX (Port 80)                         │
│                     Reverse Proxy + SSL                        │
├──────────────────────┬──────────────────────────────────────────┤
│   /api/* → Backend   │   /* → Frontend   │   /ws/* → WebSocket │
└──────────┬───────────┴──────┬────────────┴──────────┬──────────┘
           │                  │                       │
     ┌─────▼─────┐    ┌──────▼──────┐         ┌──────▼──────┐
     │  FastAPI   │    │  Next.js    │         │  FastAPI WS │
     │  Backend   │    │  Frontend   │         │  Broadcast  │
     │  :8000     │    │  :3000      │         │  :8000/ws   │
     └─────┬──┬──┘    └─────────────┘         └─────────────┘
           │  │
     ┌─────▼──▼─────────────────────┐
     │  PostgreSQL │    Redis       │
     │  :5432      │    :6379       │
     └─────────────┴────────────────┘
```

## Signal Engine Flow

```
Exchange WebSocket → Data Collector → Redis Cache
                                         │
                                    Signal Engine
                                    ├── ALFA (Fibonacci)
                                    ├── BETA (Divergences)
                                    ├── DELTA (Bollinger)
                                    └── GAMMA (Liquidations)
                                         │
                                    ┌────▼────┐
                                    │ REST API │ ──→ Frontend Polling
                                    │   +      │
                                    │ WS Push  │ ──→ Real-time Updates
                                    └────┬────┘
                                         │
                                    Alert Engine
                                    ├── Telegram
                                    ├── Discord
                                    └── Browser Push
```

## Technology Stack

| Layer      | Technology             | Purpose                     |
|------------|------------------------|-----------------------------|
| Frontend   | Next.js 15 + TypeScript| Dashboard UI                |
| Styling    | Tailwind CSS v4        | Utility-first CSS           |
| Components | shadcn/ui + Radix      | Accessible UI primitives    |
| Backend    | Python 3.12 + FastAPI  | API + Signal Engine         |
| Database   | PostgreSQL 16          | Persistent storage          |
| Cache      | Redis 7                | Real-time data + pub/sub    |
| Proxy      | Nginx 1.27             | Reverse proxy + SSL         |
| Container  | Docker Compose         | Orchestration               |

## Development Stages

1. **Stage 1** — Project Setup & Architecture ✅
2. **Stage 2** — Data Layer & Real-Time Infrastructure
3. **Stage 3** — Signal Engine (ALFA, BETA, DELTA, GAMMA)
4. **Stage 4** — Frontend Dashboard
5. **Stage 5** — Alert System
6. **Stage 6** — Configuration & Polish
