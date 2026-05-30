from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Vehicle, GpsPing, Duty, User, Depot, DutyStatus


def get_live_positions(db: Session, depot_id: Optional[int] = None) -> List[dict]:
    """
    Return the latest GPS ping for every active vehicle.
    Optionally filter by depot.
    """
    # Subquery: max ping id per vehicle
    latest_ping_sq = (
        db.query(
            GpsPing.vehicle_id,
            func.max(GpsPing.id).label("max_id")
        )
        .group_by(GpsPing.vehicle_id)
        .subquery()
    )

    rows = (
        db.query(Vehicle, GpsPing, Depot)
        .join(latest_ping_sq, Vehicle.id == latest_ping_sq.c.vehicle_id)
        .join(GpsPing, GpsPing.id == latest_ping_sq.c.max_id)
        .join(Depot, Vehicle.depot_id == Depot.id)
    )

    if depot_id:
        rows = rows.filter(Vehicle.depot_id == depot_id)

    results = []
    today = datetime.utcnow().strftime("%Y-%m-%d")

    for vehicle, ping, depot in rows.all():
        # Find today's active duty for this vehicle
        duty = (
            db.query(Duty)
            .filter(
                Duty.vehicle_id == vehicle.id,
                Duty.date == today,
                Duty.status.in_([DutyStatus.published, DutyStatus.acknowledged])
            )
            .first()
        )

        driver_name = None
        route_name = None
        if duty:
            driver = db.query(User).filter(User.id == duty.driver_id).first()
            driver_name = driver.full_name if driver else None
            route_name = duty.route.name if duty.route else None

        results.append({
            "vehicle_id": vehicle.id,
            "registration_no": vehicle.registration_no,
            "model": vehicle.model,
            "status": vehicle.status,
            "depot_id": vehicle.depot_id,
            "depot_name": depot.name,
            "lat": ping.lat,
            "lng": ping.lng,
            "speed_kmh": ping.speed_kmh,
            "heading": ping.heading,
            "last_ping": ping.ts,
            "driver_name": driver_name,
            "route_name": route_name,
        })

    return results


def get_vehicle_trail(db: Session, vehicle_id: int, minutes: int = 30) -> List[GpsPing]:
    """Last N minutes of pings for the side panel trail."""
    since = datetime.utcnow() - timedelta(minutes=minutes)
    return (
        db.query(GpsPing)
        .filter(GpsPing.vehicle_id == vehicle_id, GpsPing.ts >= since)
        .order_by(GpsPing.ts.asc())
        .all()
    )


def get_vehicle_history(db: Session, vehicle_id: int, date: str) -> List[GpsPing]:
    """Full day GPS history for history page."""
    start = datetime.strptime(date, "%Y-%m-%d")
    end = start + timedelta(days=1)
    return (
        db.query(GpsPing)
        .filter(
            GpsPing.vehicle_id == vehicle_id,
            GpsPing.ts >= start,
            GpsPing.ts < end,
        )
        .order_by(GpsPing.ts.asc())
        .all()
    )


def get_all_vehicles(db: Session, depot_id: Optional[int] = None) -> List[Vehicle]:
    q = db.query(Vehicle)
    if depot_id:
        q = q.filter(Vehicle.depot_id == depot_id)
    return q.order_by(Vehicle.registration_no).all()


def get_depots(db: Session):
    from app.models.models import Depot
    return db.query(Depot).order_by(Depot.name).all()
