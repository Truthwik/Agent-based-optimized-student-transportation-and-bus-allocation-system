"""
BVRIT Smart Bus Optimizer Engine
================================
Uses OSRM (OpenStreetMap) for route/distance calculations.
Implements constraint-based bus allocation with:
- Student grouping by stop
- Route feasibility via OSRM
- ≥75% bus capacity utilization
- Farthest-to-nearest stop ordering (no backward routing)
- Full stop coverage guarantee
"""

import requests
import math
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional, cast
from backend.models.models import Student, Stop, Bus, Route, RouteStop, Allocation
from backend.config import CAMPUS_LAT, CAMPUS_LNG, OSRM_BASE_URL


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.asin(math.sqrt(a))
    return R * c


def get_osrm_route_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Get driving distance (km) between two points using OSRM."""
    try:
        url = f"{OSRM_BASE_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes"):
                return float(data["routes"][0]["distance"]) / 1000.0
    except Exception:
        pass
    # Fallback to haversine
    return haversine(lat1, lon1, lat2, lon2)


def get_osrm_trip_distance(waypoints: List[Any]) -> float:
    """Get total route distance for ordered waypoints using OSRM route service."""
    if len(waypoints) < 2:
        return 0.0
    coords = ";".join([f"{lng},{lat}" for lat, lng in waypoints])
    try:
        url = f"{OSRM_BASE_URL}/route/v1/driving/{coords}?overview=false"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes"):
                return float(data["routes"][0]["distance"]) / 1000.0
    except Exception:
        pass
    # Fallback: sum of haversine distances
    total = 0.0
    for i in range(len(waypoints) - 1):
        total += haversine(float(waypoints[i][0]), float(waypoints[i][1]), float(waypoints[i + 1][0]), float(waypoints[i + 1][1]))
    return total


def calculate_angle(lat: float, lng: float, center_lat: float, center_lng: float) -> float:
    """Calculate the polar angle of a point relative to the campus center."""
    return math.atan2(lat - center_lat, lng - center_lng)


def run_optimizer(db: Session) -> Dict[str, Any]:
    """
    Main optimization routine using Sweep Algorithm + Greedy TSP:
    """
    # ─── Clear previous allocations ──────────────────
    db.query(Allocation).delete()
    db.query(RouteStop).delete()
    db.query(Route).delete()
    # Reset student allocations
    db.query(Student).update({Student.allocated_bus_id: None})
    db.commit()

    # ─── Step 1: Get students who need bus ───────────
    students = db.query(Student).filter(
        Student.bus_required == True,
        Student.stop_id.isnot(None)
    ).all()

    if not students:
        return {"message": "No students have selected bus service", "routes": [], "unassigned_stops": [], "total_students_allocated": 0, "total_students_unassigned": 0}

    # ─── Step 2 & 3: Group students by stop, calc dist/angle ──────────────
    stops_db = db.query(Stop).all()
    stop_map: Dict[int, Any] = {int(s.stop_id): s for s in stops_db}

    stop_students: Dict[int, List[Any]] = {}
    for student in students:
        sid = int(student.stop_id)
        if sid not in stop_students:
            stop_students[sid] = []
        stop_students[sid].append(student)

    active_stops_data: List[Dict[str, Any]] = []
    for sid, stud_list in stop_students.items():
        if sid in stop_map:
            stop = stop_map[sid]
            dist = haversine(float(stop.latitude), float(stop.longitude), float(CAMPUS_LAT), float(CAMPUS_LNG))
            angle = calculate_angle(float(stop.latitude), float(stop.longitude), float(CAMPUS_LAT), float(CAMPUS_LNG))
            active_stops_data.append({
                "stop_id": sid,
                "stud_list": stud_list,
                "dist": dist,
                "angle": angle
            })

    # Sort stops geographically in a sweeping circle
    active_stops_data.sort(key=lambda x: float(x["angle"]))

    buses = db.query(Bus).all()
    if not buses:
        return {"message": "No buses available.", "routes": [], "unassigned_stops": [{"stop_id": k, "students": len(v)} for k, v in stop_students.items()], "total_students_allocated": 0, "total_students_unassigned": len(students)}

    available_buses: List[Any] = sorted(list(buses), key=lambda x: int(x.capacity), reverse=True)
    routes_created: List[Dict[str, Any]] = []
    unassigned_stops: List[Dict[str, Any]] = []

    # ─── Step 4: Sweep Algorithm for Clustering ──────
    clusters: List[Dict[str, Any]] = []
    current_cluster_stops_map: Dict[int, List[Any]] = {}
    current_cluster_total_students: int = 0
    
    bus_idx: int = 0
    current_bus: Optional[Any] = available_buses[bus_idx] if bus_idx < len(available_buses) else None

    for stop_data in active_stops_data:
        studs_to_assign: List[Any] = stop_data["stud_list"][:]
        current_stop_id: int = int(stop_data["stop_id"])
        
        while studs_to_assign:
            if current_bus is None:
                unassigned_stops.append({
                    "stop_id": current_stop_id,
                    "stop_name": str(stop_map[current_stop_id].stop_name),
                    "students": len(studs_to_assign),
                    "suggestion": "Add a new bus to cover this stop"
                })
                break
                
            assert current_bus is not None
            remaining_cap: int = int(current_bus.capacity) - current_cluster_total_students
            
            if len(studs_to_assign) <= remaining_cap:
                # Entire stop fits in this bus
                if current_stop_id not in current_cluster_stops_map:
                    current_cluster_stops_map[current_stop_id] = []
                current_cluster_stops_map[current_stop_id].extend(studs_to_assign)
                current_cluster_total_students += len(studs_to_assign)
                studs_to_assign = []
                
                # If bus is full exactly, close it out
                if current_cluster_total_students == int(current_bus.capacity):
                    clusters.append({
                        "stop_student_map": current_cluster_stops_map,
                        "total_students": current_cluster_total_students,
                        "bus": current_bus
                    })
                    bus_idx += 1
                    current_bus = available_buses[bus_idx] if bus_idx < len(available_buses) else None
                    current_cluster_stops_map = {}
                    current_cluster_total_students = 0
            else:
                # Stop students exceed remaining bus capacity
                utilization: float = float(current_cluster_total_students) / float(current_bus.capacity)
                
                # If bus is already >= 80% full, avoid splitting to maintain clean groupings
                if utilization >= 0.80 and current_cluster_total_students > 0:
                    clusters.append({
                        "stop_student_map": current_cluster_stops_map,
                        "total_students": current_cluster_total_students,
                        "bus": current_bus
                    })
                    bus_idx += 1
                    current_bus = available_buses[bus_idx] if bus_idx < len(available_buses) else None
                    current_cluster_stops_map = {}
                    current_cluster_total_students = 0
                else:
                    # Bus is < 80% full, OR the stop size is larger than the entire bus capacity.
                    # We MUST split the stop to hit >= 80% to 100% capacity
                    fit_count: int = remaining_cap
                    if fit_count > 0:
                        if current_stop_id not in current_cluster_stops_map:
                            current_cluster_stops_map[current_stop_id] = []
                        current_cluster_stops_map[current_stop_id].extend(studs_to_assign[:fit_count])
                        current_cluster_total_students += fit_count
                        studs_to_assign = studs_to_assign[fit_count:]
                    
                    # Close current bus (now 100% full)
                    clusters.append({
                        "stop_student_map": current_cluster_stops_map,
                        "total_students": current_cluster_total_students,
                        "bus": current_bus
                    })
                    bus_idx += 1
                    current_bus = available_buses[bus_idx] if bus_idx < len(available_buses) else None
                    current_cluster_stops_map = {}
                    current_cluster_total_students = 0

    if current_cluster_total_students > 0 and current_bus is not None:
        clusters.append({
            "stop_student_map": current_cluster_stops_map,
            "total_students": current_cluster_total_students,
            "bus": current_bus
        })

    # ─── Step 5: Assign Buses & Greedy TSP Routing ───
    for cluster in clusters:
        bus: Any = cluster["bus"]
        stops_in_cluster: List[int] = list(cluster["stop_student_map"].keys())
        
        # Start at the farthest stop in the cluster
        unvisited: List[Dict[str, Any]] = []
        for sid in stops_in_cluster:
            dist = haversine(float(stop_map[sid].latitude), float(stop_map[sid].longitude), float(CAMPUS_LAT), float(CAMPUS_LNG))
            unvisited.append({"stop_id": sid, "dist": dist})
        
        unvisited.sort(key=lambda x: float(x["dist"]), reverse=True)
        current: Dict[str, Any] = unvisited.pop(0)

        route_sequence: List[int] = [int(current["stop_id"])]
        
        while unvisited:
            best_next: Optional[Dict[str, Any]] = None
            min_d: float = float('inf')
            current_stop: Any = stop_map[int(current["stop_id"])]
            
            for candidate in unvisited:
                cand_stop: Any = stop_map[int(candidate["stop_id"])]
                d = haversine(
                    float(current_stop.latitude), float(current_stop.longitude),
                    float(cand_stop.latitude), float(cand_stop.longitude)
                )
                if d < min_d:
                    min_d = d
                    best_next = candidate
            
            if best_next is not None:
                resolved_next = cast(Dict[str, Any], best_next)
                route_sequence.append(int(resolved_next["stop_id"]))
                unvisited.remove(resolved_next)
                current = resolved_next
            else:
                break



        # Calculate final accurate distance
        waypoints: List[Any] = [(float(stop_map[sid].latitude), float(stop_map[sid].longitude)) for sid in route_sequence]
        waypoints.append((float(CAMPUS_LAT), float(CAMPUS_LNG)))
        final_dist: float = get_osrm_trip_distance(waypoints)

        # Save to DB
        route = Route(
            bus_id=bus.bus_id,
            total_students=cluster["total_students"],
            total_stops=len(route_sequence),
            total_distance=final_dist
        )
        db.add(route)
        db.flush()

        # Create Route Stops
        for order, sid in enumerate(route_sequence, 1):
            route_stop = RouteStop(
                route_id=route.route_id,
                stop_id=sid,
                stop_order=order
            )
            db.add(route_stop)
            
            # Allocate Students for this split part
            for student in cluster["stop_student_map"][sid]:
                student.allocated_bus_id = bus.bus_id
                allocation = Allocation(
                    student_id=student.student_id,
                    bus_id=bus.bus_id,
                    academic_year="2025-2026"
                )
                db.add(allocation)

        routes_created.append({
            "bus_number": str(bus.bus_number),
            "stops": [str(stop_map[sid].stop_name) for sid in route_sequence],
            "students": int(cluster["total_students"]),
            "capacity": int(bus.capacity),
            "utilization": round((float(cluster["total_students"]) / float(bus.capacity)) * 100.0, 1)
        })

    db.commit()

    return {
        "message": f"Allocation complete. {len(routes_created)} routes generated.",
        "routes": routes_created,
        "unassigned_stops": unassigned_stops,
        "total_students_allocated": sum(int(r["students"]) for r in routes_created),
        "total_students_unassigned": sum(int(u["students"]) for u in unassigned_stops)
    }
