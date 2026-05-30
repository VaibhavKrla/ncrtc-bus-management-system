# NCRTC Bus Management System — Architecture Document

**Version:** 1.0  

---

## 1. System Overview

The NCRTC Bus Management System (BMS) is a full-stack web application that provides fleet management capabilities for the NCR Transport Corporation's feeder bus network. It covers four operational modules: Automatic Vehicle Location System (AVLS), Scheduling, Incident Management (IMS), and Content Management (CMS).

The system is built as a **single deployable monolith** with a clear internal module structure, containerised via Docker Compose for local development and demo purposes.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│                                                                 │
│   Browser (React + Vite)          Driver PWA (/driver route)   │
│   Admin · Manager · Control Op    Driver · Conductor           │
└────────────────┬────────────────────────────┬───────────────────┘
                 │ HTTPS / JSON               │ HTTPS / JSON
                 │ WebSocket (ws://)          │
                 ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│                                                                 │
│  /api/v1/auth        JWT login, bcrypt, role enforcement       │
│  /api/v1/avls        Live positions, trail, history            │
│  /api/v1/scheduling  Routes, duties, roster, publish           │
│  /api/v1/incidents   Raise, state machine, panic, SLA          │
│  /api/v1/notices     CRUD, targeting, read receipts            │
│  /api/v1/dashboard   Aggregated stats                          │
│  /api/v1/ws/live     WebSocket live positions (stretch)        │
└───────────┬─────────────────────────────┬───────────────────────┘
            │ SQLAlchemy ORM              │ Redis client
            ▼                            ▼
┌───────────────────────┐    ┌───────────────────────────────────┐
│  PostgreSQL + PostGIS │    │  Redis 7                          │
│                       │    │  JWT session blacklist (future)   │
│  12 core tables       │    │  API response cache (future)      │
│  Spatial indexes      │    └───────────────────────────────────┘
└───────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Background Services                           │
│                                                                 │
│  tick.py         GPS simulation — inserts pings every 5s       │
│  sla_monitor.py  SLA breach detection — runs every 60s         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer       | Technology              | Reason                                                  |
|-------------|-------------------------|----------------------------------------------------------|
| Backend     | FastAPI (Python 3.11)   | Async-ready, auto-generates OpenAPI docs at /docs        |
| ORM         | SQLAlchemy 2.0          | Type-safe queries, Alembic migration support             |
| Migrations  | Alembic                 | Schema versioning, repeatable rollouts                   |
| Database    | PostgreSQL 15 + PostGIS | Relational + spatial data in one engine                  |
| Cache       | Redis 7                 | Session cache; future use for pub/sub and rate limiting  |
| Frontend    | React 18 + Vite         | Fast HMR, modern JSX, good ecosystem                     |
| Maps        | Leaflet + OpenStreetMap | Open-source, no API key, runs offline                    |
| State       | Zustand                 | Lightweight, no boilerplate compared to Redux            |
| Auth        | JWT + bcrypt            | Stateless tokens; bcrypt for password hashing            |
| Containers  | Docker + Docker Compose | Single-command startup, reproducible environment         |
| CI          | GitHub Actions          | Free for public repos, integrates with PRs               |

---

## 4. Database Schema

### 4.1 Entity Relationship Summary

```
depot ──< vehicle ──< gps_ping
depot ──< user
depot ──< route ──< route_stop >── stop
user (driver) ──< duty >── vehicle, route
user ──< incident (raised_by, assigned_to)
incident ──< incident_event
user (admin) ──< notice
notice ──< notice_read >── user
```

### 4.2 Table Descriptions

| Table           | Rows (seed) | Purpose                                              |
|-----------------|-------------|------------------------------------------------------|
| depot           | 3           | Physical bus depots with geofence polygon            |
| vehicle         | 15          | Fleet vehicles with status                           |
| user            | 24          | All staff (5 roles)                                  |
| stop            | 10          | Bus stops with lat/lng                               |
| route           | 5           | Named routes with depot ownership                    |
| route_stop      | 17          | Ordered stops per route with scheduled times         |
| duty            | 105         | Driver–vehicle–route assignments per day             |
| gps_ping        | ~5,400      | Vehicle positions (60 pings × 15 vehicles × history) |
| incident        | 8           | Operational incidents with full state machine        |
| incident_event  | ~24         | Audit trail for every status change                  |
| notice          | 5           | Staff communications with targeting                  |
| notice_read     | ~15         | Per-user read receipts                               |

### 4.3 Key Indexes

```sql
-- Most critical: live map query (latest ping per vehicle)
CREATE INDEX ix_gps_vehicle_ts ON gps_ping (vehicle_id, ts DESC);

-- Duty roster view
CREATE INDEX ix_duty_date ON duty (date);

-- Incident list filters
CREATE INDEX ix_incident_status ON incident (status);
CREATE INDEX ix_incident_depot  ON incident (depot_id);
```

---

## 5. Module Architecture

### 5.1 AVLS (Automatic Vehicle Location System)

**Data flow:**
```
tick.py (every 5s) ──INSERT──> gps_ping
                                    │
Browser polls GET /avls/live ──────>│ 
  OR WebSocket ws/live push ────────┘
  └── SELECT MAX(id) per vehicle ──> Leaflet markers
```

**Live map query pattern** — uses a subquery to get the latest ping per vehicle in a single DB round-trip:
```sql
SELECT v.*, p.lat, p.lng, p.speed_kmh, p.ts
FROM vehicle v
JOIN (SELECT vehicle_id, MAX(id) as max_id FROM gps_ping GROUP BY vehicle_id) latest
  ON v.id = latest.vehicle_id
JOIN gps_ping p ON p.id = latest.max_id
```

**GPS simulation note:** Positions are generated by `tick.py` using physics-based movement (heading + speed with small random variance). In production this would be replaced by a real GPS ingest pipeline (see §8).

### 5.2 Scheduling

**Roster grid:** The `/scheduling/roster` endpoint returns a denormalized grid object:
```json
{
  "dates": ["2025-01-13", "2025-01-14", ...],
  "drivers": [{ "id": 1, "full_name": "..." }],
  "duties": {
    "1": { "2025-01-13": { duty object }, "2025-01-14": null }
  }
}
```
This avoids N+1 queries — all duties for the depot × week are fetched in one query.

**Duty state machine:**
```
draft ──publish──> published ──acknowledge──> acknowledged ──> completed
```

### 5.3 IMS (Incident Management)

**State machine** with strict transition enforcement:
```
open → acknowledged → in_progress → resolved → closed
         └─────────────────────────────────────> closed (early close allowed)
```

Invalid transitions return HTTP 400 with allowed next states. Every transition creates an `incident_event` row — this gives a complete audit trail for every incident.

**SLA timers:**
- P1: 60 minutes
- P2: 4 hours (240 minutes)
- P3: 24 hours (1,440 minutes)

The `sla_monitor.py` service checks every 60s and logs a breach event the first time SLA is exceeded. The frontend shows remaining time or breach status on every incident card.

**Panic button flow:**
```
Driver taps PANIC
  └──> geolocation API (3s timeout)
  └──> POST /incidents/panic?vehicle_id=&lat=&lng=
  └──> Auto-creates P1 incident with is_panic=true
  └──> Appears at top of incident list for control room
```

### 5.4 CMS (Notices)

**Targeting logic** — three modes:
- `all`: every user sees it
- `depot`: only users with `depot_id = target_depot_id`
- `role`: only users with matching role

Read receipts use a `UNIQUE(notice_id, user_id)` constraint so calling `/notices/{id}/read` is idempotent — safe to call multiple times.

---

## 6. Authentication & Authorisation

**JWT flow:**
```
POST /auth/login {username, password}
  └──> bcrypt.verify(password, hashed_password)
  └──> jwt.encode({ sub: username, role: role, exp: +60min })
  └──> Returns: { access_token, role, depot_id, ... }

Every protected route:
  └──> OAuth2PasswordBearer extracts token from Authorization: Bearer ...
  └──> decode_token() validates signature + expiry
  └──> get_current_user() fetches user from DB
  └──> require_roles(*roles) checks role membership
```

**Role permission matrix:**

| Endpoint category          | driver | conductor | depot_manager | control_operator | admin |
|----------------------------|:------:|:---------:|:-------------:|:----------------:|:-----:|
| View live map              | ✗      | ✗         | ✓             | ✓                | ✓     |
| Scheduling: view roster    | ✗      | ✗         | ✓             | ✗                | ✓     |
| Scheduling: assign duties  | ✗      | ✗         | ✓             | ✗                | ✓     |
| Acknowledge own duty       | ✓      | ✗         | ✗             | ✗                | ✗     |
| Raise incident             | ✓      | ✓         | ✓             | ✓                | ✓     |
| Panic button               | ✓      | ✓         | ✗             | ✗                | ✗     |
| Transition incident status | ✗      | ✗         | ✓             | ✓                | ✓     |
| Publish notices            | ✗      | ✗         | ✓             | ✗                | ✓     |
| Delete notice              | ✗      | ✗         | ✗             | ✗                | ✓     |
| Dashboard stats            | ✗      | ✗         | ✓             | ✓                | ✓     |

**Depot scoping:** `depot_manager` and `driver` roles automatically see only data belonging to their `depot_id`. Admins and control operators see all depots.

---

## 7. Frontend Architecture

```
src/
├── pages/          One page component per route
├── components/     Organised by module (common/, map/, scheduling/, incidents/, notices/)
├── hooks/          useLivePositions (WS + polling fallback)
├── services/       One API service file per module (thin wrappers around axios)
└── store/          Zustand auth store (token + user object)
```

**Driver PWA:** The same React application serves the driver portal at `/driver`. It is a responsive, mobile-first layout with a bottom tab bar. The `/public/manifest.json` enables "Add to Home Screen" on Android Chrome.

**WebSocket + polling fallback:** `useLivePositions` attempts a WebSocket connection first. If the WS handshake does not complete within 3 seconds, it silently falls back to 5-second polling. The map shows a mode badge (`⚡ WebSocket` or `🔄 Polling 5s`) so the demo audience can see the difference.

---

## 8. What a Production GPS Ingest Pipeline Would Look Like

The tick script is a demo substitute. In production:

```
GPS device (on each bus)
  └──> sends NMEA / proprietary binary over TCP or MQTT
  └──> GPS Ingest Service (separate microservice)
        ├── Parses and validates incoming frames
        ├── Publishes to Redis pub/sub channel: gps:{depot_id}
        └── Writes to PostgreSQL gps_ping table (bulk insert, ~5s batches)

WebSocket gateway (or FastAPI)
  └── Subscribes to Redis pub/sub
  └── Fans out to connected browser clients per depot
```

Scaling considerations:
- Partition `gps_ping` table by `ts` (monthly) — data grows fast
- Keep only last 30 days hot; archive older data to S3/Parquet
- Use TimescaleDB extension for time-series queries instead of raw PostgreSQL

---

## 9. Deployment (Future / AWS)

For production on AWS the recommended setup would be:

| Component       | AWS Service                                    |
|-----------------|------------------------------------------------|
| Backend         | ECS Fargate (2 tasks: backend + tick)          |
| Database        | RDS PostgreSQL (with PostGIS extension)        |
| Cache           | ElastiCache Redis                              |
| Frontend        | S3 + CloudFront (static build)                 |
| CI/CD           | GitHub Actions → ECR → ECS rolling deploy      |
| Secrets         | AWS Secrets Manager                            |
| Monitoring      | CloudWatch + X-Ray                             |

---

## 10. Known Limitations (Honest Assessment)

| Limitation                         | Impact          | Production fix                                  |
|------------------------------------|-----------------|--------------------------------------------------|
| GPS is simulated by tick script    | Demo only       | Real GPS ingest via MQTT/TCP                    |
| No token refresh / blacklist       | Session expires | Add refresh token + Redis blacklist             |
| Redis not used beyond wiring       | Unused capacity | Session cache, pub/sub for WS fanout            |
| No file upload for incident photos | Feature gap     | S3 presigned URLs + multipart form              |
| No pagination on list endpoints    | Perf at scale   | Cursor-based pagination (limit/offset)          |
| SQLite in tests, Postgres in prod  | Schema drift    | Use testcontainers for PostgreSQL in CI         |
| Single-node Docker Compose         | No HA           | ECS multi-AZ with RDS multi-AZ standby          |
