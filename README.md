# NCRTC Bus Management System

Full-stack fleet management system for NCR Transport Corporation's feeder bus network.

## Quickstart

```bash
git clone https://github.com/VaibhavKrla/ncrtc-bus-management-system.git
cd ncrtc-bms
docker compose down -v
docker compose build --no-cache
docker compose up
```

On first start, automatically:
1. PostgreSQL + PostGIS spins up
2. Alembic runs all migrations
3. Full seed script runs (3 depots, 15 vehicles, 24 users, routes, 7 days duties, GPS history, incidents, notices)
4. Tick script starts inserting live GPS pings every 5s

| Service     | URL                         |
|-------------|-----------------------------|
| Frontend    | http://localhost:3000        |
| API docs    | http://localhost:8000/docs   |
| Backend     | http://localhost:8000        |

## Demo credentials

| Username       | Password      | Role             | Depot         |
|----------------|---------------|------------------|---------------|
| admin          | admin123      | Admin            | All           |
| control1       | control123    | Control Operator | All           |
| mgr_avd        | manager123    | Depot Manager    | Anand Vihar   |
| mgr_sbd        | manager123    | Depot Manager    | Sahibabad     |
| driver_avd_1   | driver123     | Driver           | Anand Vihar   |
| driver_sbd_1   | driver123     | Driver           | Sahibabad     |
| driver_n62_1   | driver123     | Driver           | Noida 62      |
| cond_avd_1     | cond123       | Conductor        | Anand Vihar   |

## Modules

| Module       | Routes                   | Description                                    |
|--------------|--------------------------|------------------------------------------------|
| Auth         | `/login`, `/me`          | JWT login, 5 roles, bcrypt                     |
| AVLS         | `/map`, `/map/history`   | Live map (polling 5s), trip history            |
| Scheduling   | `/scheduling`            | Routes CRUD, 7-day roster, duty assign/publish |
| IMS          | `/incidents`             | Incident tracking, panic button, state machine |
| CMS          | `/notices`               | Notices, targeting, read receipts              |
| Dashboard    | `/dashboard`             | Aggregated stats, recent incidents             |

## Architecture

```
ncrtc-bms/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   ← auth, avls, scheduling, incidents, notices, dashboard
│   │   ├── core/               ← config, JWT/bcrypt security
│   │   ├── db/                 ← SQLAlchemy session
│   │   ├── models/             ← 12 ORM models
│   │   ├── schemas/            ← Pydantic schemas per module
│   │   ├── services/           ← business logic (state machine, SLA, etc.)
│   │   ├── seed.py             ← full seed (auto-runs on startup)
│   │   └── tick.py             ← GPS simulation (5s ticks)
│   ├── alembic/                ← DB migrations
│   ├── tests/                  ← Pytest (auth, avls, scheduling, incidents, notices)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/         ← common/, map/, scheduling/, incidents/, notices/
│       ├── pages/              ← one page per module
│       ├── hooks/              ← useLivePositions (polling)
│       ├── services/           ← axios API clients per module
│       └── store/              ← Zustand auth store
├── docker-compose.yml          ← 5 services: db, redis, backend, frontend, tick_script
└── .github/workflows/ci.yml    ← GitHub Actions CI
```

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## Key design decisions

- **Monolith** not microservices — one FastAPI app, 4 module folders
- **Polling** (5s interval) not WebSocket for live map — simpler, reliable
- **Tick script** simulates GPS — no real devices needed for demo
- **PostGIS** for geo data, Redis for session cache
- **PWA** driver portal at `/driver` — same React codebase, mobile-first

> ⚠️ GPS positions are simulated by the tick script for demo purposes.
> In production, a real GPS ingest pipeline (MQTT/TCP) would replace this.

## Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Architecture | `docs/architecture.md` | System design, DB schema, module flows, production path |
| Assumptions | `docs/assumptions_and_decisions.md` | All assumptions made, key decisions with rationale |
| API docs | http://localhost:8000/docs | Auto-generated Swagger (live when running) |
<!-- | Demo script | `docs/demo_script.md` | 10-minute walkthrough for evaluators | -->
<!-- | Presentation | `docs/presentation_outline.md` | 12-slide deck outline with speaker notes | -->

## Test summary

```
tests/test_auth.py         7 tests  — login, /me, wrong password, no token
tests/test_avls.py         6 tests  — live positions, trail, history
tests/test_notices.py      7 tests  — CRUD, publish, read receipts
tests/test_scheduling.py   8 tests  — routes, duties, publish, acknowledge
tests/test_incidents.py   11 tests  — create, panic, state machine, SLA
tests/test_dashboard.py    4 tests  — stats, scoping, auth
tests/test_security.py    16 tests  — role enforcement, cross-depot, edge cases
tests/test_integration.py  4 tests  — full journeys end-to-end
─────────────────────────────────────
Total                     63 tests
```

Run: `cd backend && pytest tests/ -v`

## Stretch features implemented

- ⚡ **WebSocket live map** — `ws://localhost:8000/api/v1/ws/live` with automatic polling fallback (+3%)
- ⏱ **SLA timers** — P1=60min, P2=4hr, P3=24hr, breach detection + event logging (+2%)
- 🚨 **Panic button** — Driver PWA → instant P1 incident with geolocation (+included in IMS)
