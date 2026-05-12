# BVRIT Smart Bus Optimizer: Technical Architecture & Details

This document serves as an exhaustive breakdown of the APIs, algorithmic engines, data methodologies, feature pipelines, and tech stack powering the BVRIT Smart Bus Optimizer. Information was gathered by reverse-engineering the codebase (analyzing `services/optimizer_engine.py`, API controllers `routers/`, and frontend `Leaflet/OSRM` implementations).

---

## 1. Tech Stack Overview

### Backend Infrastructure
- **Server Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, highly performant web framework).
- **Database**: **MySQL** with relational schemas.
- **ORM & Data Mapping**: **SQLAlchemy** is used for object mapping and executing optimized SQL transactions.
- **Schema Validation**: **Pydantic** (v2) is used strictly for data sanitization, request framing, and response formatting (e.g. `schemas.py`).
- **Server Gateway**: **Uvicorn** (ASGI server) to serve the concurrent requests securely.
- **Cryptography**: **PyJWT** constructs securely signed Bearer Tokens.

### Frontend Technologies
- **Core Interfaces**: Pure Vanilla HTML5, CSS3, and JavaScript. 
- **Mapping Engine**: **Leaflet.js**. An open-source interactive mapping library utilized for fetching map tiles and rendering custom GeoJSON markers on the front end.
- **QR Generation**: **QRCode.js** to synthetically render boarding tickets completely client-side without relying on image downloads.

---

## 2. Bus Routing Engines & Mathematics

The intelligence of the platform lives inside `backend/services/optimizer_engine.py`, defining how the system intelligently strings geographical stops together to form non-overlapping, efficient bus routes.

### A. The Geographic Route Building Engine
Instead of matching adjacent stops indiscriminately (which causes winding gridlocks), the system intelligently builds geometric "corridors" and executes physical routing modifications dynamically based on these logic steps:

1. **Bearing Angle Isolation**: All bus stops are evaluated based on their absolute compass bearing angle (0-360 degrees) mapped linearly toward the destination (main campus).
2. **Corridor Window Sweeping**: A **Greedy Sliding-Window algorithm** sweeps angles and groups stops into sequential linear corridors. Groups must strictly belong within a tight `20-degree` angular window gap. 
3. **Farthest-First Sorting (Anti-Backtracking)**: Within each clustered corridor, stops are reordered by distance descending (farthest from campus first). This rigidly enforces logical one-way routing and prevents buses from weaving loops.
4. **Detour Rejection Filter**: The system executes a virtual run using mapping distances. If the total routed distance structurally inflates `> 1.25x` linearly, a detour violation occurs. The algorithmic filter detects the specific vertex/stop causing the geometric warping and uniquely ejects it from the route segment.
5. **Far-Gap Route Splitting (30km Limits)**: Post-allocation, the system calculates sequential Haversine distance gaps in generated routes. If the straight-line gap between consecutive stops structurally breaches `30km`, it severs the sequence immediately and diverts the remainder onto a secondary, isolated fleet instance if available.
6. **Efficiency Convergence Pass**: If an isolated corridor fails to reach its `75% MIN_FILL_FRACTION` payload requirement, an auxiliary pass evaluates a larger `45-degree` geographical radius to intercept and structurally merge smaller fleets, aiming for 80-100% capacity loading.

### B. Route Calculation Implementations
Two major programmatic routing engines support the Optimizer Engine:
1. **OSRM (Open Source Routing Machine)**: 
   - Resolves actual physical geographic pathing over registered roadways.
   - The backend bulk leverages `/table/v1/driving/` to generate pair-wise matrices internally to compute detours.
   - Leverages `/route/v1/driving/` sequentially to fetch exact drive times dynamically.
2. **Haversine Formula Math Check**:
   - Used as an internal **fallback algorithm** if OSRM servers drop connectivity. It calculates the spherical Earth-distance strictly separating coordinates, mathematically inflating results uniquely utilizing a `1.3x HAVERSINE_ROAD_FACTOR` multiplier to predictively cover winding roads.

### C. Route Tracking & Geofencing
In the tracking interface (`tracking.html`), a javascript polling-loop fetches bus Latitudes dynamically. A client-side Geofence `haversine()` mathematical listener proactively measures radial proximity continuously against the user's intended route pick-up stop. **When spherical distance < `0.5km`**, the interface renders a synchronous Geofence UI alert stating the bus is physically nearing.

---

## 3. Comprehensive Feature Set

### 1. Robust Fleet Tracking
- A driver triggers the `Start Trip` protocol.
- Local mobile GPS coordinates ping iteratively safely returning dynamic patch data directly to MySQL.
- Over `tracking.html`, the system uses `leaflet.js` transposing real cartographic routes into an active dashboard relaying algorithmic driver speeds mapped dynamically onto expected travel times.

### 2. Multi-Tier Authentication & RBAC
- Access tokens securely authenticate roles uniquely bound across `Student`, `Driver`, `Coordinator`, and `Admin`.
- **First Login Route Inteception**: A secure routing gateway intercepts raw credentials if detected in an unhandled default state (`bvrit123`). Routing natively kicks defaulting users directly to an inescapable password-change loop prior to granting broader dashboard resources.

### 3. Allocation Re-Routing Framework
- Student interfaces transmit geo-locational selections.
- Admins trigger the `generate-allocation` endpoint enforcing the mathematical routing algorithm.
- Students possess pipelines to dispatch `StopChangeRequests`. Upon confirmation, system routes actively re-balance the bus population parameters safely decoupled from other nodes.

### 4. Announcements Matrix
- Coordinators track and broadcast route disruption protocols smoothly onto student dashboards integrating secure, dynamically-tracked expiration thresholds.

---

## 4. Primary API Layouts (Routers)

The project organizes Web Routing systematically based heavily around distinct endpoints.

- **`auth.py`** (`/auth/`): Includes `/login` parser and cross-schema resolving `/change-password` triggers.
- **`student.py`** (`/students/`): Endpoints granting retrieval logic regarding active assignments (`/me`), all configured stops (`/stops`), active resolving systems for issues (`/complaints`), and dynamic QR generation endpoints reflecting bus assignments (`/day-pass`).
- **`driver.py`** (`/driver/`): Operational `/trip/start`, `/trip/end` and coordinate tracking inputs safely isolated under PATCH protocols scaling securely.
- **`admin.py`** (`/admin/`): Structural backend logic routing executing the engine `/generate-allocation`, manipulating active vehicle configurations `/buses`, or controlling the active stops logic `/stops`.
- **`tracking.py`** (`/tracking/`): The authenticated bridge endpoints effectively allowing remote UI frameworks to independently pull `/bus/{bus_id}` active positional matrices for localized mapping.
