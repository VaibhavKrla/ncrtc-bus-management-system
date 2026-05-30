from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Route, RouteStop, Stop, Duty, User, Vehicle, Depot,
    DutyStatus, UserRole
)


# ── Stops ─────────────────────────────────────────────────────────────────────

def get_all_stops(db: Session) -> List[Stop]:
    return db.query(Stop).order_by(Stop.name).all()


def create_stop(db: Session, payload) -> Stop:
    stop = Stop(
        name=payload.name, code=payload.code,
        lat=payload.lat, lng=payload.lng
    )
    db.add(stop)
    db.commit()
    db.refresh(stop)
    return stop


# ── Routes ────────────────────────────────────────────────────────────────────

def get_routes(db: Session, depot_id: Optional[int] = None) -> List[Route]:
    q = db.query(Route)
    if depot_id:
        q = q.filter(Route.depot_id == depot_id)
    return q.order_by(Route.name).all()


def get_route(db: Session, route_id: int) -> Optional[Route]:
    return db.query(Route).filter(Route.id == route_id).first()


def create_route(db: Session, payload, created_by_depot_id: Optional[int] = None) -> Route:
    route = Route(
        name=payload.name,
        code=payload.code,
        depot_id=payload.depot_id,
    )
    db.add(route)
    db.flush()
    _sync_route_stops(db, route, payload.stops or [])
    db.commit()
    db.refresh(route)
    return route


def update_route(db: Session, route: Route, payload) -> Route:
    if payload.name is not None:
        route.name = payload.name
    if payload.code is not None:
        route.code = payload.code
    if payload.is_active is not None:
        route.is_active = payload.is_active
    if payload.stops is not None:
        _sync_route_stops(db, route, payload.stops)
    db.commit()
    db.refresh(route)
    return route


def delete_route(db: Session, route: Route):
    db.query(RouteStop).filter(RouteStop.route_id == route.id).delete()
    db.delete(route)
    db.commit()


def _sync_route_stops(db: Session, route: Route, stops_in: list):
    """Replace all route stops with the new list."""
    db.query(RouteStop).filter(RouteStop.route_id == route.id).delete()
    for s in stops_in:
        rs = RouteStop(
            route_id=route.id,
            stop_id=s.stop_id,
            sequence=s.sequence,
            scheduled_time=s.scheduled_time,
        )
        db.add(rs)


def enrich_route(db: Session, route: Route) -> dict:
    depot = db.query(Depot).filter(Depot.id == route.depot_id).first()
    stops = []
    for rs in sorted(route.route_stops, key=lambda x: x.sequence):
        stop = rs.stop
        stops.append({
            "id": stop.id, "name": stop.name, "code": stop.code,
            "lat": stop.lat, "lng": stop.lng,
            "sequence": rs.sequence, "scheduled_time": rs.scheduled_time,
        })
    return {
        "id": route.id, "name": route.name, "code": route.code,
        "depot_id": route.depot_id,
        "depot_name": depot.name if depot else None,
        "is_active": route.is_active,
        "stops": stops,
        "created_at": route.created_at,
    }


# ── Duties ────────────────────────────────────────────────────────────────────

def get_duties(db: Session, depot_id: Optional[int] = None,
               date: Optional[str] = None, driver_id: Optional[int] = None) -> List[Duty]:
    q = db.query(Duty)
    if depot_id:
        # Filter duties where driver belongs to this depot
        driver_ids = [u.id for u in db.query(User).filter(User.depot_id == depot_id).all()]
        q = q.filter(Duty.driver_id.in_(driver_ids))
    if date:
        q = q.filter(Duty.date == date)
    if driver_id:
        q = q.filter(Duty.driver_id == driver_id)
    return q.order_by(Duty.date, Duty.shift_start).all()


def get_duty(db: Session, duty_id: int) -> Optional[Duty]:
    return db.query(Duty).filter(Duty.id == duty_id).first()


def create_duty(db: Session, payload, created_by_id: int) -> Duty:
    duty = Duty(
        driver_id=payload.driver_id,
        vehicle_id=payload.vehicle_id,
        route_id=payload.route_id,
        date=payload.date,
        shift_start=payload.shift_start,
        shift_end=payload.shift_end,
        status=DutyStatus.draft,
        created_by_id=created_by_id,
    )
    db.add(duty)
    db.commit()
    db.refresh(duty)
    return duty


def update_duty(db: Session, duty: Duty, payload) -> Duty:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(duty, field, value)
    db.commit()
    db.refresh(duty)
    return duty


def delete_duty(db: Session, duty: Duty):
    db.delete(duty)
    db.commit()


def publish_duties(db: Session, duty_ids: List[int]) -> int:
    updated = (
        db.query(Duty)
        .filter(Duty.id.in_(duty_ids), Duty.status == DutyStatus.draft)
        .all()
    )
    for d in updated:
        d.status = DutyStatus.published
    db.commit()
    return len(updated)


def acknowledge_duty(db: Session, duty_id: int, driver_id: int) -> Optional[Duty]:
    duty = db.query(Duty).filter(
        Duty.id == duty_id,
        Duty.driver_id == driver_id,
        Duty.status == DutyStatus.published,
    ).first()
    if not duty:
        return None
    duty.status = DutyStatus.acknowledged
    duty.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(duty)
    return duty


def enrich_duty(db: Session, duty: Duty) -> dict:
    driver = db.query(User).filter(User.id == duty.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == duty.vehicle_id).first()
    route = db.query(Route).filter(Route.id == duty.route_id).first()
    driver_depot_id = driver.depot_id if driver else None
    return {
        "id": duty.id,
        "driver_id": duty.driver_id,
        "driver_name": driver.full_name if driver else None,
        "vehicle_id": duty.vehicle_id,
        "registration_no": vehicle.registration_no if vehicle else None,
        "route_id": duty.route_id,
        "route_name": route.name if route else None,
        "date": duty.date,
        "shift_start": duty.shift_start,
        "shift_end": duty.shift_end,
        "status": duty.status,
        "acknowledged_at": duty.acknowledged_at,
        "depot_id": driver_depot_id,
    }


# ── Roster helper ─────────────────────────────────────────────────────────────

def get_roster(db: Session, depot_id: int, week_start: str) -> dict:
    """
    Returns a roster object for the UI grid.
    week_start: YYYY-MM-DD (Monday)
    Returns: { drivers: [...], dates: [...], duties: { driver_id: { date: duty } } }
    """
    from datetime import timedelta
    start = datetime.strptime(week_start, "%Y-%m-%d").date()
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    drivers = db.query(User).filter(
        User.depot_id == depot_id,
        User.role == UserRole.driver,
        User.is_active == True,
    ).order_by(User.full_name).all()

    driver_ids = [d.id for d in drivers]
    duties = db.query(Duty).filter(
        Duty.driver_id.in_(driver_ids),
        Duty.date.in_(dates),
    ).all()

    duty_map = {}
    for duty in duties:
        if duty.driver_id not in duty_map:
            duty_map[duty.driver_id] = {}
        duty_map[duty.driver_id][duty.date] = enrich_duty(db, duty)

    return {
        "depot_id": depot_id,
        "week_start": week_start,
        "dates": dates,
        "drivers": [
            {"id": d.id, "full_name": d.full_name, "username": d.username}
            for d in drivers
        ],
        "duties": duty_map,
    }
