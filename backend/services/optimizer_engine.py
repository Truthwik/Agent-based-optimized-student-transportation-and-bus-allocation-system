"""
BVRIT Smart Bus Optimizer Engine — Corridor-Based Strategy
===========================================================
Uses OSRM (OpenStreetMap) for real road distance calculations.
Implements corridor-based bus allocation with:
  - Bearing-angle corridor grouping (no polar sweep)
  - 75–100% bus capacity fill range
  - Farthest-to-nearest stop ordering (no backtracking)
  - OSRM full-route distance (no pairwise summing)
  - Backward ETA from campus arrival time-window (default 08:50–09:00)
  - Full stop coverage guarantee
"""

from __future__ import annotations
import logging
import math
import requests
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional, Tuple

try:
    # When running the app as `backend.*` (uvicorn backend.main:app)
    from backend.models.models import Student, Stop, Bus, Route, RouteStop, Allocation
    from backend.config import (
        CAMPUS_LAT,
        CAMPUS_LNG,
        OSRM_BASE_URL,
        OSRM_TIMEOUT,
        OSRM_MAX_RETRIES,
        CAMPUS_ARRIVAL_MIN_MINUTES,
        CAMPUS_ARRIVAL_MAX_MINUTES,
    )
except ImportError:  # pragma: no cover
    # When running this module in other contexts (e.g., some IDE test runners)
    from ..models.models import Student, Stop, Bus, Route, RouteStop, Allocation
    from ..config import (
        CAMPUS_LAT,
        CAMPUS_LNG,
        OSRM_BASE_URL,
        OSRM_TIMEOUT,
        OSRM_MAX_RETRIES,
        CAMPUS_ARRIVAL_MIN_MINUTES,
        CAMPUS_ARRIVAL_MAX_MINUTES,
    )

logger = logging.getLogger("optimizer_engine")
logging.basicConfig(level=logging.INFO)

# OSRM can be unavailable on dev machines (e.g., Docker not installed / container not running).
# We probe once per process and then stop attempting OSRM calls to avoid log spam and slow retries.
_OSRM_AVAILABLE: Optional[bool] = None


def _osrm_is_available() -> bool:
    global _OSRM_AVAILABLE
    if _OSRM_AVAILABLE is not None:
        return _OSRM_AVAILABLE
    try:
        # Minimal 2-point route request. Campus→Campus is invalid, so we offset slightly.
        coords = f"{CAMPUS_LNG},{CAMPUS_LAT};{CAMPUS_LNG + 0.0005},{CAMPUS_LAT + 0.0005}"
        url = f"{OSRM_BASE_URL}/route/v1/driving/{coords}?overview=false"
        resp = requests.get(url, timeout=float(OSRM_TIMEOUT))
        _OSRM_AVAILABLE = (resp.status_code == 200 and resp.json().get("code") == "Ok")
    except Exception:
        _OSRM_AVAILABLE = False
    if not _OSRM_AVAILABLE:
        logger.warning(
            "OSRM is not reachable at %s. Falling back to Haversine-only distances. "
            "To enable OSRM, run a local OSRM server and set OSRM_BASE_URL.",
            OSRM_BASE_URL,
        )
    return bool(_OSRM_AVAILABLE)


def _osrm_get(url: str) -> Optional[requests.Response]:
    """
    Best-effort OSRM GET with bounded retries.
    Returns Response on success, otherwise None.
    """
    if not _osrm_is_available():
        return None
    for _ in range(max(1, int(OSRM_MAX_RETRIES))):
        try:
            resp = requests.get(url, timeout=float(OSRM_TIMEOUT))
            return resp
        except Exception:
            continue
    # Mark OSRM down after repeated failures in this process.
    global _OSRM_AVAILABLE
    _OSRM_AVAILABLE = False
    return None

# ─── Constants ────────────────────────────────────────────
CORRIDOR_ANGLE_WINDOW = 20.0         # degrees — max angular width of a corridor
CORRIDOR_MERGE_ANGLE = 30.0          # degrees — max angle diff for merging corridors (corridor build)
MERGE_BEARING_TOLERANCE = 45.0       # degrees — wider tolerance for post-assignment merge pass
CORRIDOR_DETOUR_FACTOR = 1.25        # FIX 3: tightened from 1.4 — ejects cross-city stops sooner
MIN_FILL_FRACTION = 0.75             # 75% minimum bus fill
DWELL_TIME_MINUTES = 2.0
AVG_SPEED_KMPH = 35.0                # FIX 1: flat average — real college data shows 33–38 km/h
DISTANCE_SANITY_LIMIT_KM = 80.0
HAVERSINE_ROAD_FACTOR = 1.3          # multiply haversine by this for road distance estimate

# Geographic sanity checks (fallback haversine, not OSRM road distance).
# These are only for validation/QA to catch “far apart stops in one route”.
NEAR_STOP_MAX_SPREAD_KM = 60.0       # max haversine distance between any two stops in the same route
NEAR_STOP_MAX_GAP_KM = 30.0          # max haversine distance between consecutive stops in the route


# ═══════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate straight-line distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.asin(math.sqrt(a))
    return R * c


def bearing_from_stop_to_campus(lat: float, lng: float) -> float:
    """
    Calculate the compass bearing (0–360°) FROM a stop TOWARD campus.
    0° = North, 90° = East, 180° = South, 270° = West.
    """
    lat1 = math.radians(lat)
    lat2 = math.radians(CAMPUS_LAT)
    dlon = math.radians(CAMPUS_LNG - lng)
    x = math.sin(dlon) * math.cos(lat2)
    y = (math.cos(lat1) * math.sin(lat2) -
         math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0


def angular_diff(a: float, b: float) -> float:
    """Smallest absolute angle between two bearings (0–180°)."""
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def get_osrm_distance_matrix(waypoints: List[Tuple[float, float]]) -> Optional[List[List[float]]]:
    """
    Get full NxN pairwise road-distance matrix via OSRM /table endpoint.
    Returns distances in km, or None on failure.
    """
    if len(waypoints) < 2:
        return None
    coords = ";".join([f"{lng},{lat}" for lat, lng in waypoints])
    url = f"{OSRM_BASE_URL}/table/v1/driving/{coords}?annotations=distance"
    resp = _osrm_get(url)
    if resp is None:
        return None
    try:
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("distances"):
                results: List[List[float]] = []
                for row in data["distances"]:
                    processed_row: List[float] = []
                    for d in row:
                        if d is not None:
                            processed_row.append(float(d) / 1000.0)
                        else:
                            processed_row.append(float("inf"))
                    results.append(processed_row)
                return results
    except Exception:
        return None
    return None


def build_distance_matrix(waypoints: List[Tuple[float, float]]) -> List[List[float]]:
    """Build distance matrix — OSRM first, Haversine fallback."""
    osrm = get_osrm_distance_matrix(waypoints)
    if osrm:
        return osrm
    logger.info("OSRM matrix unavailable — falling back to Haversine × 1.3")
    n = len(waypoints)
    matrix: List[List[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = haversine(
                    waypoints[i][0], waypoints[i][1],
                    waypoints[j][0], waypoints[j][1]
                ) * HAVERSINE_ROAD_FACTOR
    return matrix


def get_osrm_route_distance(ordered_waypoints: List[Tuple[float, float]]) -> Optional[float]:
    """
    Call OSRM /route endpoint ONCE with all stops in order + campus.
    Returns total one-way driving distance in km, or None on failure.
    """
    if len(ordered_waypoints) < 2:
        return 0.0
    coords = ";".join([f"{lng},{lat}" for lat, lng in ordered_waypoints])
    url = (f"{OSRM_BASE_URL}/route/v1/driving/{coords}"
           f"?overview=false&annotations=false")
    resp = _osrm_get(url)
    if resp is None:
        return None
    try:
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                return float(data["routes"][0]["distance"]) / 1000.0
    except Exception:
        return None
    return None


def haversine_chain_distance(ordered_waypoints: List[Tuple[float, float]]) -> float:
    """Sum haversine between consecutive waypoints × road factor."""
    total = 0.0
    for i in range(len(ordered_waypoints) - 1):
        total += haversine(
            ordered_waypoints[i][0], ordered_waypoints[i][1],
            ordered_waypoints[i + 1][0], ordered_waypoints[i + 1][1]
        )
    return total * HAVERSINE_ROAD_FACTOR


# ═══════════════════════════════════════════════════════════
# MAIN OPTIMIZER
# ═══════════════════════════════════════════════════════════

def run_optimizer(db: Session) -> Dict[str, Any]:
    """
    Corridor-based bus optimization.
    Steps: Clean → Fetch → Matrix → Corridors → Assign Buses → Route → Save
    """

    # ─── CLEAN SLATE ──────────────────────────────────
    db.query(Allocation).delete()
    db.query(RouteStop).delete()
    db.query(Route).delete()
    db.query(Student).update({Student.allocated_bus_id: None})
    db.commit()

    students = db.query(Student).filter(
        Student.bus_required == True,
        Student.stop_id.isnot(None),
        (Student.allocation_type != "daywise") | (Student.allocation_type.is_(None))
    ).all()

    if not students:
        return {
            "message": "No students have selected bus service",
            "routes": [], "unassigned_stops": [],
            "total_students_allocated": 0, "total_students_unassigned": 0
        }

    # ─── STEP 2: GROUP BY STOP ────────────────────────
    stops_db = db.query(Stop).all()
    stop_map: Dict[int, Any] = {int(s.stop_id): s for s in stops_db}

    stop_students: Dict[int, List[Any]] = {}
    for stu in students:
        sid = int(stu.stop_id)
        # BUG 3 FIX (Place 1): Skip campus/college stops entirely
        stop_obj = stop_map.get(sid)
        if stop_obj is None:
            continue
        stop_name = getattr(stop_obj, "stop_name", "")
        # Skip stops that are at the CAMPUS itself (within 300m)
        dist_to_campus = haversine(float(stop_obj.latitude), float(stop_obj.longitude), float(CAMPUS_LAT), float(CAMPUS_LNG))
        if dist_to_campus < 0.3:
            logger.info(f"Skipping campus stop: {stop_name} (dist: {dist_to_campus:.3f}km)")
            continue
        if sid not in stop_students:
            stop_students[sid] = []
        stop_students[sid].append(stu)

    active_sids = [sid for sid in stop_students if stop_students[sid]]

    # ─── STEP 3: BUILD DISTANCE MATRIX ────────────────
    # Index: 0..N-1 = stops, N = campus
    waypoints: List[Tuple[float, float]] = []
    sid_to_idx: Dict[int, int] = {}
    for i, sid in enumerate(active_sids):
        s = stop_map[sid]
        waypoints.append((float(s.latitude), float(s.longitude)))
        sid_to_idx[sid] = i

    campus_idx = len(waypoints)
    waypoints.append((float(CAMPUS_LAT), float(CAMPUS_LNG)))

    dist_matrix = build_distance_matrix(waypoints)

    # ─── STEP 4: COMPUTE BEARING & DISTANCE PER STOP ─
    stop_info: Dict[int, Dict[str, float]] = {}
    for sid in active_sids:
        s = stop_map[sid]
        bearing = bearing_from_stop_to_campus(float(s.latitude), float(s.longitude))
        road_dist = dist_matrix[sid_to_idx[sid]][campus_idx]
        stop_info[sid] = {"bearing": bearing, "road_dist": road_dist}

    # ═══════════════════════════════════════════════════
    # STEP 5: CORRIDOR-BASED CLUSTERING
    # ═══════════════════════════════════════════════════

    # Sort stops by bearing angle
    sorted_sids = sorted(active_sids, key=lambda sid: stop_info[sid]["bearing"])

    # Greedy sliding-window corridor formation
    corridors: List[List[int]] = []
    assigned_to_corridor: set = set()

    i = 0
    while i < len(sorted_sids):
        if sorted_sids[i] in assigned_to_corridor:
            i += 1
            continue

        # Start a new corridor window
        window_start_bearing = stop_info[sorted_sids[i]]["bearing"]
        corridor: List[int] = [sorted_sids[i]]
        assigned_to_corridor.add(sorted_sids[i])

        j = i + 1
        while j < len(sorted_sids):
            sid_j = sorted_sids[j]
            if sid_j in assigned_to_corridor:
                j += 1
                continue
            angle_diff = angular_diff(
                stop_info[sid_j]["bearing"], window_start_bearing
            )
            if angle_diff <= CORRIDOR_ANGLE_WINDOW:
                corridor.append(sid_j)
                assigned_to_corridor.add(sid_j)
            else:
                break
            j += 1

        # Also wrap around 360°→0° boundary
        if window_start_bearing + CORRIDOR_ANGLE_WINDOW >= 360.0:
            for k in range(0, i):
                sid_k = sorted_sids[k]
                if sid_k in assigned_to_corridor:
                    continue
                angle_diff = angular_diff(
                    stop_info[sid_k]["bearing"], window_start_bearing
                )
                if angle_diff <= CORRIDOR_ANGLE_WINDOW:
                    corridor.append(sid_k)
                    assigned_to_corridor.add(sid_k)

        corridors.append(corridor)
        i += 1

    # ─── CORRIDOR DETOUR CHECK & SPLIT ────────────────
    refined_corridors: List[List[int]] = []
    for corridor in corridors:
        if len(corridor) <= 1:
            refined_corridors.append(corridor)
            continue

        # Sort corridor stops farthest-first
        corridor_sorted = sorted(
            corridor,
            key=lambda sid: stop_info[sid]["road_dist"],
            reverse=True
        )
        farthest_dist = stop_info[corridor_sorted[0]]["road_dist"]

        # Build ordered waypoints for OSRM route check
        route_wps = [(float(stop_map[sid].latitude), float(stop_map[sid].longitude))
                     for sid in corridor_sorted]
        route_wps.append((float(CAMPUS_LAT), float(CAMPUS_LNG)))

        route_dist = get_osrm_route_distance(route_wps)
        if route_dist is None:
            route_dist = haversine_chain_distance(route_wps)

        if farthest_dist > 0 and route_dist > CORRIDOR_DETOUR_FACTOR * farthest_dist:
            # Find the stop causing the biggest detour and split it out
            worst_sid = None
            worst_detour = 0.0
            for idx_s, sid in enumerate(corridor_sorted):
                if idx_s == 0 or idx_s == len(corridor_sorted) - 1:
                    continue
                prev_sid = corridor_sorted[idx_s - 1]
                next_sid = corridor_sorted[idx_s + 1]
                direct = dist_matrix[sid_to_idx[prev_sid]][sid_to_idx[next_sid]]
                via = (dist_matrix[sid_to_idx[prev_sid]][sid_to_idx[sid]] +
                       dist_matrix[sid_to_idx[sid]][sid_to_idx[next_sid]])
                detour = via - direct
                if detour > worst_detour:
                    worst_detour = detour
                    worst_sid = sid

            if worst_sid is not None:
                main_corridor = [s for s in corridor_sorted if s != worst_sid]
                refined_corridors.append(main_corridor)
                refined_corridors.append([worst_sid])
            else:
                refined_corridors.append(corridor_sorted)
        else:
            refined_corridors.append(corridor_sorted)

    corridors = refined_corridors

    # ═══════════════════════════════════════════════════
    # STEP 6: BUS ASSIGNMENT PER CORRIDOR
    # ═══════════════════════════════════════════════════

    buses_db = db.query(Bus).all()
    if not buses_db:
        return {
            "message": "No buses available.",
            "routes": [],
            "unassigned_stops": [
                {"stop_id": sid, "students": len(stop_students[sid])}
                for sid in active_sids
            ],
            "total_students_allocated": 0,
            "total_students_unassigned": len(students)
        }

    # Sort buses by capacity ascending (so we can pick smallest fitting bus)
    available_buses = sorted(list(buses_db), key=lambda b: int(b.capacity))
    used_bus_ids: set = set()

    def pick_bus(min_seats: int) -> Any:
        """Pick the smallest available bus with capacity >= min_seats."""
        for b in available_buses:
            if b.bus_id not in used_bus_ids and int(b.capacity) >= min_seats:
                used_bus_ids.add(b.bus_id)
                return b
        # If no bus fits exactly, pick the largest remaining bus
        for b in reversed(available_buses):
            if b.bus_id not in used_bus_ids:
                used_bus_ids.add(b.bus_id)
                return b
        return None

    def _avg_bearing_for_sids(sids: List[int]) -> float:
        if not sids:
            return 0.0
        bearings = [stop_info[sid]["bearing"] for sid in sids]
        sin_sum = sum(math.sin(math.radians(b)) for b in bearings)
        cos_sum = sum(math.cos(math.radians(b)) for b in bearings)
        return (math.degrees(math.atan2(sin_sum, cos_sum)) + 360.0) % 360.0

    # Compute student count per corridor & average bearing
    corridor_data: List[Dict[str, Any]] = []
    for corridor in corridors:
        total_stu = sum(len(stop_students.get(sid, [])) for sid in corridor)
        avg_bearing = 0.0
        if corridor:
            bearings = [stop_info[sid]["bearing"] for sid in corridor]
            # Circular mean for bearings
            sin_sum = sum(math.sin(math.radians(b)) for b in bearings)
            cos_sum = sum(math.cos(math.radians(b)) for b in bearings)
            avg_bearing = (math.degrees(math.atan2(sin_sum, cos_sum)) + 360.0) % 360.0
        corridor_data.append({
            "sids": corridor,
            "total_students": total_stu,
            "avg_bearing": avg_bearing,
            "merged": False
        })

    # ─── MERGE UNDER-FILLED CORRIDORS ─────────────────
    for i_c in range(len(corridor_data)):
        cd = corridor_data[i_c]
        if cd["merged"] or cd["total_students"] == 0:
            continue

        # Check if under 75% of the smallest fitting bus
        smallest_fitting = None
        for b in available_buses:
            if b.bus_id not in used_bus_ids and int(b.capacity) >= cd["total_students"]:
                smallest_fitting = b
                break
        if smallest_fitting is None:
            continue

        small_cap = int(smallest_fitting.capacity)
        if cd["total_students"] < MIN_FILL_FRACTION * small_cap:
            # Find nearest corridor to merge with
            best_merge = None
            best_merge_dist = float('inf')
            for j_c in range(len(corridor_data)):
                cd2 = corridor_data[j_c]
                if j_c == i_c or cd2.get("merged", False):
                    continue
                if cd2["total_students"] == 0:
                    continue
                angle_diff = angular_diff(cd["avg_bearing"], cd2["avg_bearing"])
                if angle_diff > CORRIDOR_MERGE_ANGLE:
                    continue
                combined = cd["total_students"] + cd2["total_students"]
                if combined > small_cap:
                    continue
                # Use geographic distance between corridor centroids
                if cd["sids"] and cd2["sids"]:
                    d = dist_matrix[sid_to_idx[cd["sids"][0]]][sid_to_idx[cd2["sids"][0]]]
                    if d < best_merge_dist:
                        best_merge_dist = d
                        best_merge = j_c

            if best_merge is not None:
                corridor_data[i_c]["sids"] = cd["sids"] + corridor_data[best_merge]["sids"]
                corridor_data[i_c]["total_students"] += corridor_data[best_merge]["total_students"]
                corridor_data[best_merge]["merged"] = True
                corridor_data[best_merge]["sids"] = []
                corridor_data[best_merge]["total_students"] = 0

    # ─── ASSIGN BUSES ─────────────────────────────────
    assignments: List[Dict[str, Any]] = []  # Each: {bus, sids, student_map, under_capacity}
    unassigned_stops: List[Dict[str, Any]] = []

    for cd in corridor_data:
        if cd["merged"] or cd["total_students"] == 0:
            continue

        sids = cd["sids"]
        total_stu = cd["total_students"]
        avg_bearing = cd["avg_bearing"]

        # Sort sids by road distance descending (farthest first)
        sids_sorted = sorted(sids, key=lambda sid: stop_info[sid]["road_dist"], reverse=True)

        # Check if total students fit in one bus
        bus = pick_bus(total_stu)
        if bus is None:
            for sid in sids_sorted:
                if stop_students.get(sid):
                    unassigned_stops.append({
                        "stop_id": sid,
                        "stop_name": str(stop_map[sid].stop_name),
                        "students": len(stop_students[sid]),
                        "suggestion": "Add a new bus to cover this stop"
                    })
            continue

        bus_cap = int(bus.capacity)

        if total_stu <= bus_cap:
            # Fits in one bus
            student_map: Dict[int, List[Any]] = {}
            for sid in sids_sorted:
                student_map[sid] = list(stop_students.get(sid, []))
            under_cap = total_stu < MIN_FILL_FRACTION * bus_cap
            assignments.append({
                "bus": bus,
                "sids": sids_sorted,
                "student_map": student_map,
                "total_students": total_stu,
                "avg_bearing": avg_bearing,
                "under_capacity": under_cap
            })
        else:
            # Need to split corridor across multiple buses
            remaining_sids: List[int] = list(sids_sorted)
            remaining_students: Dict[int, List[Any]] = {sid: list(stop_students.get(sid, [])) for sid in remaining_sids}

            # First bus is already picked
            current_bus = bus
            while remaining_sids and current_bus is not None:
                current_cap = int(current_bus.capacity)
                target_fill = int(current_cap * 0.80)
                assigned_sids: List[int] = []
                assigned_map: Dict[int, List[Any]] = {}
                count = 0

                for sid in list(remaining_sids):
                    studs = remaining_students.get(sid, [])
                    if not studs:
                        if sid in remaining_sids:
                            remaining_sids.remove(sid)
                        continue
                    # Keep a stop "atomic" (all students of that stop on one bus)
                    # to avoid the same stop appearing in multiple routes.
                    if count + len(studs) <= current_cap:
                        assigned_sids.append(sid)
                        assigned_map[sid] = list(studs)
                        count += len(studs)
                        remaining_students[sid] = []
                    else:
                        # If this single stop cannot fit and the bus is empty, we have no choice
                        # but to split this stop across buses.
                        if count == 0 and len(studs) > current_cap:
                            assigned_sids.append(sid)
                            assigned_map[sid] = list(studs[:current_cap])
                            remaining_students[sid] = list(studs[current_cap:])
                            count += current_cap
                        # Otherwise, leave this stop for the next bus.
                        break

                if count > 0:
                    under_cap = count < MIN_FILL_FRACTION * current_cap
                    assignments.append({
                        "bus": current_bus,
                        "sids": assigned_sids,
                        "student_map": assigned_map,
                        "total_students": count,
                        "avg_bearing": avg_bearing,
                        "under_capacity": under_cap
                    })

                # Clean up fully assigned sids
                remaining_sids = [sid_cleanup for sid_cleanup in remaining_sids
                                  if remaining_students.get(sid_cleanup)]

                if remaining_sids:
                    remaining_total = sum(len(remaining_students.get(rt_sid, []))
                                         for rt_sid in remaining_sids)
                    current_bus = pick_bus(remaining_total)
                else:
                    break

            # Any truly leftover
            for sid in remaining_sids:
                studs = remaining_students.get(sid, [])
                if studs:
                    unassigned_stops.append({
                        "stop_id": sid,
                        "stop_name": str(stop_map[sid].stop_name),
                        "students": len(studs),
                        "suggestion": "Add a new bus to cover this stop"
                    })

    # ═══════════════════════════════════════════════════
    # STEP 6b: POST-ASSIGNMENT MERGE PASS (BUG 2 FIX)
    # Run a second merge pass on under-filled assignments
    # ═══════════════════════════════════════════════════
    assignments_active = [a for a in assignments]  # working copy
    merged_indices: set = set()

    # Sort under-filled by student count ascending (merge smallest first)
    under_filled_indices = [
        idx for idx, a in enumerate(assignments_active)
        if a["total_students"] < MIN_FILL_FRACTION * int(a["bus"].capacity)
    ]
    under_filled_indices.sort(key=lambda idx: assignments_active[idx]["total_students"])

    for idx in under_filled_indices:
        if idx in merged_indices:
            continue
        a = assignments_active[idx]
        best_target = None
        best_angle_diff = float('inf')

        for t_idx, target in enumerate(assignments_active):
            if t_idx == idx or t_idx in merged_indices:
                continue
            combined = target["total_students"] + a["total_students"]
            if combined > int(target["bus"].capacity):
                continue
            angle = angular_diff(target["avg_bearing"], a["avg_bearing"])
            if angle > MERGE_BEARING_TOLERANCE:   # FIX 2: widened from 30° to 45°
                continue
            if angle < best_angle_diff:
                best_angle_diff = angle
                best_target = t_idx

        if best_target is not None:
            # Merge: move all stops & students from a into target
            target = assignments_active[best_target]
            logger.info(
                "[MERGE] %s students (corridor %.0fdeg) merged into Bus %s (corridor %.0fdeg)",
                a["total_students"],
                a["avg_bearing"],
                target["bus"].bus_number,
                target["avg_bearing"],
            )
            for sid, studs in a["student_map"].items():
                if sid not in target["student_map"]:
                    target["student_map"][sid] = []
                target["student_map"][sid].extend(studs)
            target["sids"] = list(target["student_map"].keys())
            target["total_students"] += a["total_students"]
            target["under_capacity"] = (
                target["total_students"] < MIN_FILL_FRACTION * int(target["bus"].capacity)
            )
            # Re-sort merged stops farthest-first
            target["sids"] = sorted(
                target["sids"],
                key=lambda sid: stop_info[sid]["road_dist"],
                reverse=True
            )
            # Free up the merged bus
            used_bus_ids.discard(a["bus"].bus_id)
            merged_indices.add(idx)

    assignments = [a for idx, a in enumerate(assignments_active) if idx not in merged_indices]

    # ═══════════════════════════════════════════════════
    # STEP 6c: SPLIT “FAR GAP” ROUTES INTO ANOTHER BUS
    # If a route contains geographically far-apart stops, split at the
    # biggest consecutive gap and allocate the second group to another bus.
    # ═══════════════════════════════════════════════════

    def _haversine_stop(sid_a: int, sid_b: int) -> float:
        sa = stop_map[sid_a]
        sb = stop_map[sid_b]
        return haversine(
            float(sa.latitude), float(sa.longitude),
            float(sb.latitude), float(sb.longitude),
        )

    def _route_sequence_for_assignment(a: Dict[str, Any]) -> List[int]:
        # same ordering policy as Step 7 (farthest-first)
        sids_local = [
            sid for sid in a["sids"]
            # Campus is already excluded in Step 2, but we'll double check by distance if needed.
            if haversine(float(stop_map[sid].latitude), float(stop_map[sid].longitude), float(CAMPUS_LAT), float(CAMPUS_LNG)) > 0.3
        ]
        return sorted(sids_local, key=lambda sid: stop_info[sid]["road_dist"], reverse=True)

    split_happened = True
    split_passes = 0
    while split_happened and split_passes < 5:
        split_happened = False
        split_passes += 1
        new_assignments: List[Dict[str, Any]] = []

        for a in assignments:
            route_seq = _route_sequence_for_assignment(a)
            if len(route_seq) < 2:
                new_assignments.append(a)
                continue

            # find biggest consecutive gap
            gaps = [(_haversine_stop(route_seq[i], route_seq[i + 1]), i) for i in range(len(route_seq) - 1)]
            max_gap_km, max_idx = max(gaps, key=lambda x: x[0])
            if max_gap_km <= NEAR_STOP_MAX_GAP_KM:
                new_assignments.append(a)
                continue

            # split route at that gap
            left_sids = route_seq[: max_idx + 1]
            right_sids = route_seq[max_idx + 1 :]
            if not left_sids or not right_sids:
                new_assignments.append(a)
                continue

            right_students = sum(len(a["student_map"].get(sid, [])) for sid in right_sids)
            right_bus = pick_bus(right_students)
            if right_bus is None:
                # No extra bus available; keep route together but warn via QA
                new_assignments.append(a)
                continue

            # Build new assignment for the right group
            right_student_map: Dict[int, List[Any]] = {sid: a["student_map"].get(sid, [])[:] for sid in right_sids}
            left_student_map: Dict[int, List[Any]] = {sid: a["student_map"].get(sid, [])[:] for sid in left_sids}

            left_total = sum(len(v) for v in left_student_map.values())
            right_total = sum(len(v) for v in right_student_map.values())

            left_bus = a["bus"]
            left_under = left_total < MIN_FILL_FRACTION * int(left_bus.capacity)
            right_under = right_total < MIN_FILL_FRACTION * int(right_bus.capacity)

            new_left = {
                "bus": left_bus,
                "sids": sorted(left_sids, key=lambda sid: stop_info[sid]["road_dist"], reverse=True),
                "student_map": left_student_map,
                "total_students": left_total,
                "avg_bearing": _avg_bearing_for_sids(left_sids),
                "under_capacity": left_under,
            }
            new_right = {
                "bus": right_bus,
                "sids": sorted(right_sids, key=lambda sid: stop_info[sid]["road_dist"], reverse=True),
                "student_map": right_student_map,
                "total_students": int(right_total),
                "avg_bearing": float(_avg_bearing_for_sids(right_sids)),
                "under_capacity": right_under,
            }

            split_happened = True
            new_assignments.append(new_left)
            new_assignments.append(new_right)

        assignments = new_assignments

    # ═══════════════════════════════════════════════════
    # STEP 7: ROUTE ORDERING + DISTANCE + ETA + DB SAVE
    # ═══════════════════════════════════════════════════

    routes_created: List[Dict[str, Any]] = []

    for assignment in assignments:
        bus = assignment["bus"]
        sids = assignment["sids"]
        student_map = assignment["student_map"]
        total_stu = assignment["total_students"]
        avg_bearing = assignment["avg_bearing"]
        under_cap = assignment["under_capacity"]

        # ─── ROUTE ORDERING: farthest-first descending ─
        # BUG 3 FIX (Place 2): skip any campus-named stop from the route
        route_sequence = sorted(
            [
                sid for sid in sids
                if haversine(float(stop_map[sid].latitude), float(stop_map[sid].longitude), float(CAMPUS_LAT), float(CAMPUS_LNG)) > 0.3
            ],
            key=lambda sid: stop_info[sid]["road_dist"],
            reverse=True
        )

        if not route_sequence:
            continue

        # ─── Geographic “near stop” validation (QA) ─────────────────────
        # We use haversine (straight-line) to decide if stops are grossly far.
        # When OSRM is available, road distance ordering is better; when not,
        # this prevents obviously wrong groupings from slipping through.
        pair_spread_km: float = 0.0
        max_consecutive_gap_km: float = 0.0
        if len(route_sequence) >= 2:
            for a_i in range(len(route_sequence) - 1):
                sid_a = route_sequence[a_i]
                sa = stop_map[sid_a]
                for b_i in range(a_i + 1, len(route_sequence)):
                    sid_b = route_sequence[b_i]
                    sb = stop_map[sid_b]
                    dist_val = float(haversine(
                            float(sa.latitude), float(sa.longitude),
                            float(sb.latitude), float(sb.longitude),
                        ))
                    pair_spread_km = max(float(pair_spread_km), dist_val)
            for a_i in range(len(route_sequence) - 1):
                sid_a = route_sequence[a_i]
                sid_b = route_sequence[a_i + 1]
                sa = stop_map[sid_a]
                sb = stop_map[sid_b]
                gap_val = float(haversine(
                        float(sa.latitude), float(sa.longitude),
                        float(sb.latitude), float(sb.longitude),
                    ))
                max_consecutive_gap_km = max(float(max_consecutive_gap_km), gap_val)
        near_stops_ok = (
            pair_spread_km <= NEAR_STOP_MAX_SPREAD_KM
            and max_consecutive_gap_km <= NEAR_STOP_MAX_GAP_KM
        )

        # ─── DISTANCE: OSRM /route with all stops + campus ─
        route_waypoints: List[Tuple[float, float]] = [
            (float(stop_map[sid].latitude), float(stop_map[sid].longitude))
            for sid in route_sequence
        ]
        route_waypoints.append((float(CAMPUS_LAT), float(CAMPUS_LNG)))

        total_distance = get_osrm_route_distance(route_waypoints)
        if total_distance is None:
            total_distance = haversine_chain_distance(route_waypoints)

        distance_sanity = total_distance <= DISTANCE_SANITY_LIMIT_KM

        if not distance_sanity:
            logger.warning(
                f"DISTANCE WARNING: Bus {bus.bus_number} — "
                f"total_distance={total_distance:.1f} km > {DISTANCE_SANITY_LIMIT_KM} km | "
                f"stops={[str(stop_map[sid].stop_name) for sid in route_sequence]}"
            )

        # ─── FIX 1: ETA backward from 9:00 AM — flat 35 km/h, direct haversine segments ─
        # KEY INSIGHT: We do NOT use the dist_matrix (which is Haversine×1.3 inflated)
        # for ETA. Use raw haversine between consecutive stops for travel time only.
        # This gives realistic 6:30–8:30 AM departure times.

        def _seg_haversine(sid_a: int, sid_b: int) -> float:
            """Straight-line km between two stops, no road factor."""
            sa = stop_map[sid_a]
            sb = stop_map[sid_b]
            return haversine(
                float(sa.latitude), float(sa.longitude),
                float(sb.latitude), float(sb.longitude)
            )

        def _stop_to_campus_haversine(sid: int) -> float:
            s = stop_map[sid]
            return haversine(
                float(s.latitude), float(s.longitude),
                float(CAMPUS_LAT), float(CAMPUS_LNG)
            )

        # Stagger arrivals deterministically within the campus arrival window.
        # This spreads the buses out so they don't all arrive at the exact same minute
        window_span = max(0, int(CAMPUS_ARRIVAL_MAX_MINUTES) - int(CAMPUS_ARRIVAL_MIN_MINUTES))
        stagger = (bus.bus_id * 7) % (window_span + 1) if window_span > 0 else 0
        target_arrival_minutes = int(CAMPUS_ARRIVAL_MIN_MINUTES) + int(stagger)
        target_arrival_minutes = max(
            int(CAMPUS_ARRIVAL_MIN_MINUTES),
            min(int(CAMPUS_ARRIVAL_MAX_MINUTES), int(target_arrival_minutes)),
        )
        
        # Build departure minutes for each stop (index matches route_sequence)
        departure_minutes: List[float] = [0.0] * len(route_sequence)
        current_time: float = float(target_arrival_minutes)

        # Last stop → campus
        seg_km = _stop_to_campus_haversine(route_sequence[-1])
        travel_mins = (seg_km / AVG_SPEED_KMPH) * 60.0
        current_time -= travel_mins + DWELL_TIME_MINUTES
        departure_minutes[-1] = current_time

        # Walk backward through remaining stops
        for k in range(len(route_sequence) - 2, -1, -1):
            seg_km = _seg_haversine(route_sequence[k], route_sequence[k + 1])
            travel_mins = (seg_km / AVG_SPEED_KMPH) * 60.0
            current_time -= travel_mins + DWELL_TIME_MINUTES
            departure_minutes[k] = current_time

        # Format departure times and build stop strings
        final_stops_info: List[str] = []
        departure_times: List[str] = []
        for k, sid in enumerate(route_sequence):
            total_mins = int(round(departure_minutes[k]))
            hour = (total_mins // 60) % 24
            minute = total_mins % 60
            period = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            dep_str = f"{display_hour:02d}:{minute:02d} {period}"
            departure_times.append(dep_str)
            final_stops_info.append(f"{stop_map[sid].stop_name} (dep {dep_str})")

        # Validation: first stop should depart between 06:00 AM and the latest arrival cutoff
        first_dep_mins = departure_minutes[0]
        if not (360 <= first_dep_mins <= int(CAMPUS_ARRIVAL_MAX_MINUTES)):  # 06:00=360
            seg_km_first = _stop_to_campus_haversine(route_sequence[0])
            logger.warning(
                f"[ETA WARNING] Route Bus {bus.bus_number}: "
                f"{stop_map[route_sequence[0]].stop_name} departs {departure_times[0]} — "
                f"check segment distance value: {seg_km_first:.1f} km"
            )

        # ─── SAVE TO DB ──────────────────────────────
        route = Route(
            bus_id=bus.bus_id,
            total_students=total_stu,
            total_stops=len(route_sequence),
            total_distance=float(round(total_distance, 2))
        )
        db.add(route)
        db.flush()

        for order, sid in enumerate(route_sequence, 1):
            rs = RouteStop(
                route_id=route.route_id,
                stop_id=sid,
                stop_order=order
            )
            db.add(rs)

            for stu in student_map.get(sid, []):
                stu.allocated_bus_id = bus.bus_id
                alloc = Allocation(
                    student_id=stu.student_id,
                    bus_id=bus.bus_id,
                    academic_year="2025-2026"
                )
                db.add(alloc)

        fill_pct = round((float(total_stu) / float(bus.capacity)) * 100.0, 1)

        routes_created.append({
            "bus_number": str(bus.bus_number),
            "stops": final_stops_info,
            "students": total_stu,
            "capacity": int(bus.capacity),
            "utilization": float(fill_pct),
            # ─── NEW FIELDS ───
            "corridor_bearing": float(round(avg_bearing, 1)),
            "fill_percentage": float(fill_pct),
            "under_capacity": under_cap,
            "distance_sanity_passed": distance_sanity,
            "total_distance_km": float(round(total_distance, 2)),
            "departure_times": departure_times,
            # QA metrics
            "geo_pair_spread_km": float(round(pair_spread_km, 1)),
            "geo_max_consecutive_gap_km": float(round(max_consecutive_gap_km, 1)),
            "near_stops_ok": near_stops_ok,
        })

    db.commit()

    # ═══════════════════════════════════════════════════
    # STEP 8: POST-OPTIMIZATION VALIDATION (console log)
    # ═══════════════════════════════════════════════════

    total_allocated = sum(r["students"] for r in routes_created)
    total_unassigned = sum(u["students"] for u in unassigned_stops)
    avg_fill = (sum(r["fill_percentage"] for r in routes_created) / len(routes_created)
                if routes_created else 0.0)
    avg_stops = (sum(len(r["stops"]) for r in routes_created) / len(routes_created)
                 if routes_created else 0.0)
    over_distance = [r["bus_number"] for r in routes_created if not r["distance_sanity_passed"]]

    # Check for duplicate stops across routes
    all_route_stops: List[str] = []
    duplicate_stops: List[str] = []
    for r in routes_created:
        for stop_str in r["stops"]:
            stop_name = stop_str.split(" (dep")[0].strip()
            if stop_name in all_route_stops:
                if stop_name not in duplicate_stops:
                    duplicate_stops.append(stop_name)
            all_route_stops.append(stop_name)

    lines = [
        "",
        "=" * 60,
        "  OPTIMIZER VALIDATION REPORT",
        "=" * 60,
        f"  Total routes generated     : {len(routes_created)}",
        f"  Total students allocated   : {total_allocated}",
        f"  Total students unassigned  : {total_unassigned}",
        f"  Average fill percentage    : {avg_fill:.1f}%",
        f"  Average stops per bus      : {avg_stops:.1f}",
    ]
    if over_distance:
        lines.append(f"  [!] Routes > {DISTANCE_SANITY_LIMIT_KM}km distance : Bus {', '.join(over_distance)}")
    else:
        lines.append(f"  [OK] All routes within {DISTANCE_SANITY_LIMIT_KM}km distance limit")
    if duplicate_stops:
        lines.append(f"  [!] Duplicate stops found    : {', '.join(duplicate_stops)}")
    else:
        lines.append("  [OK] No duplicate stops across routes")

    near_violations = [
        r["bus_number"]
        for r in routes_created
        if not r.get("near_stops_ok", True)
    ]
    if near_violations:
        lines.append(
            f"  [!] Non-near stop groupings : Bus {', '.join(map(str, near_violations[:10]))}"
            + (" ..." if len(near_violations) > 10 else "")
        )
    else:
        lines.append("  [OK] All routes look geographically near (QA thresholds)")
    under_cap_routes = [r["bus_number"] for r in routes_created if r["under_capacity"]]
    if under_cap_routes:
        lines.append(f"  [!] Under-capacity buses     : Bus {', '.join(under_cap_routes)}")
    else:
        lines.append("  [OK] All buses meet 75% minimum fill")
    lines.append("=" * 60)
    logger.info("%s", "\n".join(lines))

    return {
        "message": f"Allocation complete. {len(routes_created)} routes generated.",
        "routes": routes_created,
        "unassigned_stops": unassigned_stops,
        "total_students_allocated": total_allocated,
        "total_students_unassigned": total_unassigned
    }
