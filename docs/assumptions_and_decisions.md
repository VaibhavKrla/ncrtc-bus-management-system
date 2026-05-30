# NCRTC BMS — Assumptions & Key Decisions

**Required submission document as per project brief.**

---

## Team

| Member | Role |
|--------|------|
| [Member 1 name] | Backend (FastAPI, models, services, tests) |
| [Member 2 name] | Frontend (React, maps, scheduling UI) |
| [Member 3 name] | DevOps, integration, docs |

*(Update with actual names before submission)*

---

## Section 1 — Necessary Assumptions

### 1.1 GPS & Vehicle Tracking
- **Assumption:** Real GPS hardware is not available for this submission. Vehicle positions are simulated by a background tick script (`tick.py`) that inserts GPS pings every 5 seconds using physics-based movement (heading + speed with small random variance). This is explicitly disclosed on the live map page with a disclaimer badge.
- **Assumption:** We assumed that a GPS ping interval of 5 seconds is acceptable for the demo. In production, intervals would be 1–5 seconds depending on network conditions.
- **Assumption:** Vehicle positions are constrained to the Delhi-NCR bounding box (lat: 28.40–28.85, lng: 77.00–77.55).

### 1.2 Data & Seeding
- **Assumption:** No real NCRTC operational data was available. All seed data (depots, routes, vehicles, staff names, incidents, notices) is fabricated but geographically plausible — depot coordinates, stop locations, and route names are based on real NCRTC feeder bus network areas in Delhi-NCR.
- **Assumption:** Three depots were seeded (Anand Vihar, Sahibabad, Noida Sector 62) as representative of the network. The system supports any number of depots.
- **Assumption:** 15 vehicles (5 per depot) was deemed sufficient to demonstrate all AVLS features without making the map cluttered.

### 1.3 Authentication
- **Assumption:** We used username + password authentication (JWT). We assumed SSO/LDAP integration with NCRTC's HR system is out of scope for this submission.
- **Assumption:** Token expiry is set to 60 minutes. In production this would be shorter (15 min) with a refresh token mechanism.
- **Assumption:** Password complexity rules are not enforced in the demo — demo passwords are intentionally simple (e.g. `admin123`).

### 1.4 Scheduling
- **Assumption:** One duty per driver per day. The schema supports multiple duties per day (different shifts) but the roster UI and seed data uses one per day for clarity.
- **Assumption:** "Conductor" role exists in the system but conductor duties are not separately tracked in the scheduling module. Conductors can acknowledge their duty via the driver portal.
- **Assumption:** Leave management (leave requests, leave approval) is out of scope and flagged as a stretch item.

### 1.5 Incidents
- **Assumption:** Photo upload for incidents is not implemented. The schema has a `photo_url` column and the raise form has a placeholder, but actual file upload (S3 presigned URLs) is out of scope.
- **Assumption:** Incident assignment is manual (manager assigns via the detail panel). Auto-assignment based on proximity or workload is a future feature.
- **Assumption:** Geolocation via `navigator.geolocation` is used for the panic button. This works on HTTPS; on HTTP (local dev) it may fail — we fall back to null lat/lng in that case.

### 1.6 Notices
- **Assumption:** Notice body is plain text. Rich text (HTML) editing and PDF attachments are out of scope but the schema has a `photo_url` column ready for attachments.
- **Assumption:** Bilingual support (Hindi + English) is not implemented. This was listed as a stretch item.

### 1.7 Infrastructure
- **Assumption:** The system is deployed locally via Docker Compose. AWS deployment is described in the architecture document (§9) but not set up as part of this submission — the project brief did not require a live URL.
- **Assumption:** Redis is wired and running but currently only provides structural groundwork (JWT blacklist ready, pub/sub ready). Active caching is not implemented in the demo.
- **Assumption:** The database uses SQLite in tests for speed, and PostgreSQL + PostGIS in production (docker-compose). There is a minor schema difference (no PostGIS geometry columns in SQLite tests) — documented as a known limitation.

---

## Section 2 — Key Architectural Decisions

### Decision 1: Monolith, not microservices
**Choice:** One FastAPI application with 4 module folders (`api/v1/endpoints/`, `services/`, `schemas/`).  
**Reason:** The PRD explicitly says "don't build microservices." For a 3-person team with a deadline, a monolith is faster to build, debug, and demo. All modules share the same DB session, making cross-module queries (e.g. duty + vehicle + driver for the roster) trivial without network calls.  
**Trade-off:** A true production system with thousands of concurrent GPS pings would benefit from a separate GPS ingest microservice, but this is documented rather than built.

### Decision 2: Polling first, WebSocket as stretch
**Choice:** Primary data fetching uses 5-second HTTP polling. WebSocket is implemented as a stretch feature with automatic polling fallback.  
**Reason:** Polling requires 10 lines of code; WebSocket requires 200 lines plus connection management, reconnection logic, and auth. Starting with polling meant we had a working live map in day 1 of Phase 3. WebSocket was added in Phase 7 as a genuine enhancement.  
**Trade-off:** Polling creates more HTTP traffic. At 15 vehicles × 5-second polls, this is negligible — roughly 12 requests/minute per connected user.

### Decision 3: Single PostgreSQL database with PostGIS
**Choice:** One Postgres instance with the PostGIS extension for all data.  
**Reason:** Postgres handles both relational data (duties, incidents) and geospatial data (stop locations, depot polygons) in one engine. Using a separate time-series DB for GPS pings would add operational complexity without a measurable benefit at demo scale.  
**Trade-off:** `gps_ping` will grow very quickly in production. The schema uses a composite index on `(vehicle_id, ts DESC)` and the architecture document describes partitioning + TimescaleDB as the production path.

### Decision 4: React + Vite (not Next.js or Angular)
**Choice:** React 18 with Vite bundler.  
**Reason:** The assignment listed React.js, Next.js, and Angular.js as options. Next.js SSR is not needed — all data is user-specific and fetched client-side after authentication. Angular has a steeper learning curve. Vite gives extremely fast HMR for developer productivity.  
**Trade-off:** No SSR/SEO — acceptable for an internal fleet management tool.

### Decision 5: Driver PWA on same codebase
**Choice:** `/driver` route in the same React app serves as the PWA driver portal.  
**Reason:** Maintaining two separate codebases (a driver app and an admin app) doubles the build/test surface for a 3-person team. The driver portal uses the same API client, auth store, and component library. A `manifest.json` enables "Add to Home Screen" on Android Chrome.  
**Trade-off:** Bundle size includes all admin code. This is acceptable for an internal app (staff have company devices on WiFi).

### Decision 6: State machine for incidents
**Choice:** Explicit `VALID_TRANSITIONS` dict enforced at the service layer, not just the UI.  
**Reason:** Incident state is critical operational data. Allowing arbitrary status changes (e.g. jumping from `open` to `resolved`) would produce meaningless audit trails. Enforcing transitions at the API layer means even direct API calls (Postman, scripts) cannot corrupt the state machine.  
**Trade-off:** Slightly more backend code; some workflow flexibility sacrificed (e.g. a manager cannot directly close an unacknowledged incident — they must acknowledge first).

### Decision 7: Seed script as the demo strategy
**Choice:** A comprehensive `seed.py` that runs automatically on `docker compose up` and creates a fully populated, realistic dataset.  
**Reason:** A blank system does not demonstrate capabilities. Evaluators need to see the roster grid with real duties, the map with moving buses, and incidents in various states — without manual data entry. The seed creates this in under 30 seconds.  
**Trade-off:** Seed data is fabricated and disclosed as such.

---

## Section 3 — What We Would Do Differently With More Time

1. **Real GPS ingest** — Replace tick script with an MQTT broker + ingest service consuming real (or realistically simulated) GPS frames.
2. **Token refresh** — Add refresh tokens and a Redis blacklist for logout/revocation.
3. **Pagination** — Add cursor-based pagination to all list endpoints (incidents, duties, GPS pings).
4. **Testcontainers** — Use `testcontainers-python` to run PostgreSQL+PostGIS in CI instead of SQLite, eliminating the geometry column gap.
5. **Leave management** — Drivers request leave; managers approve; roster auto-marks leave days.
6. **Push notifications** — Web push API for P1 incidents on driver PWA.
7. **Trip replay scrubber** — Animated playback of a vehicle's daily path on the history page.
8. **Bilingual UI** — Hindi + English using i18next, with a toggle on the driver portal.
