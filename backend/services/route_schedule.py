"""Lookup scheduled bus departure time at a stop for a given bus route."""
from __future__ import annotations

import math
from typing import List, Optional

from sqlalchemy.orm import Session

from ..config import (
    CAMPUS_LAT,
    CAMPUS_LNG,
    CAMPUS_ARRIVAL_MAX_MINUTES,
    CAMPUS_ARRIVAL_MIN_MINUTES,
)
from ..models.models import Route, RouteStop, Stop

# Match optimizer_engine backward-ETA constants
_AVG_SPEED_KMPH = 35.0
_DWELL_TIME_MINUTES = 2.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.asin(math.sqrt(a))
    return r * c


def _mins_to_display(total_mins: int) -> str:
    hour = (total_mins // 60) % 24
    minute = total_mins % 60
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour:02d}:{minute:02d} {period}"


def _target_campus_arrival_minutes(bus_id: int) -> int:
    window_span = max(0, int(CAMPUS_ARRIVAL_MAX_MINUTES) - int(CAMPUS_ARRIVAL_MIN_MINUTES))
    stagger = (bus_id * 7) % (window_span + 1) if window_span > 0 else 0
    target = int(CAMPUS_ARRIVAL_MIN_MINUTES) + int(stagger)
    return max(
        int(CAMPUS_ARRIVAL_MIN_MINUTES),
        min(int(CAMPUS_ARRIVAL_MAX_MINUTES), int(target)),
    )


def _compute_departure_at_stop(
    db: Session, route: Route, bus_id: int, stop_id: int
) -> Optional[str]:
    """
    Same backward ETA as optimizer_engine when scheduled_departure was never stored
    (e.g. column added after allocation, or legacy rows).
    """
    rss: List[RouteStop] = (
        db.query(RouteStop)
        .filter(RouteStop.route_id == route.route_id)
        .order_by(RouteStop.stop_order)
        .all()
    )
    if not rss:
        return None
    route_sequence = [rs.stop_id for rs in rss]
    if stop_id not in route_sequence:
        return None
    idx = route_sequence.index(stop_id)

    stop_map: dict[int, Stop] = {}
    for rs in rss:
        s = rs.stop
        if s is None:
            s = db.query(Stop).filter(Stop.stop_id == rs.stop_id).first()
        if s is None:
            return None
        stop_map[rs.stop_id] = s

    target_arrival_minutes = _target_campus_arrival_minutes(bus_id)
    n = len(route_sequence)
    departure_minutes: List[float] = [0.0] * n
    current_time = float(target_arrival_minutes)

    def seg_km(sid_a: int, sid_b: int) -> float:
        sa, sb = stop_map[sid_a], stop_map[sid_b]
        return _haversine_km(
            float(sa.latitude), float(sa.longitude),
            float(sb.latitude), float(sb.longitude),
        )

    def to_campus_km(sid: int) -> float:
        s = stop_map[sid]
        return _haversine_km(
            float(s.latitude), float(s.longitude),
            float(CAMPUS_LAT), float(CAMPUS_LNG),
        )

    seg = to_campus_km(route_sequence[-1])
    current_time -= (seg / _AVG_SPEED_KMPH) * 60.0 + _DWELL_TIME_MINUTES
    departure_minutes[-1] = current_time

    for k in range(n - 2, -1, -1):
        seg = seg_km(route_sequence[k], route_sequence[k + 1])
        current_time -= (seg / _AVG_SPEED_KMPH) * 60.0 + _DWELL_TIME_MINUTES
        departure_minutes[k] = current_time

    return _mins_to_display(int(round(departure_minutes[idx])))


def scheduled_departure_at_stop(db: Session, bus_id: int, stop_id: Optional[int]) -> Optional[str]:
    """
    Return planned departure time at this stop (e.g. '08:30 AM').
    Uses DB column when set; otherwise recomputes using the same logic as the optimizer
    so passes stay correct without re-running allocation.
    """
    if stop_id is None:
        return None
    route = (
        db.query(Route)
        .filter(Route.bus_id == bus_id)
        .order_by(Route.route_id.desc())
        .first()
    )
    if not route:
        return None
    rs = (
        db.query(RouteStop)
        .filter(RouteStop.route_id == route.route_id, RouteStop.stop_id == stop_id)
        .first()
    )
    if not rs:
        return None
    dep = getattr(rs, "scheduled_departure", None)
    if dep:
        return dep
    return _compute_departure_at_stop(db, route, bus_id, stop_id)
