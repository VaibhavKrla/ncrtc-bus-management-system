from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.models import User, Vehicle
from app.services import avls as svc

router = APIRouter(prefix="/avls", tags=["avls"])


@router.get("/live", response_model=List[dict])
def live_positions(
    depot_id: Optional[int] = Query(None, description="Filter by depot"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Live positions of all active vehicles (latest ping per vehicle).
    Depot managers see only their depot unless depot_id is passed.
    """
    filter_depot = depot_id
    if current_user.role == "depot_manager" and not depot_id:
        filter_depot = current_user.depot_id
    return svc.get_live_positions(db, depot_id=filter_depot)


@router.get("/vehicles/{vehicle_id}/trail", response_model=List[dict])
def vehicle_trail(
    vehicle_id: int,
    minutes: int = Query(30, ge=5, le=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Last N minutes of pings for a vehicle (side panel polyline)."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    pings = svc.get_vehicle_trail(db, vehicle_id, minutes)
    return [
        {"lat": p.lat, "lng": p.lng, "speed_kmh": p.speed_kmh,
         "heading": p.heading, "ts": p.ts}
        for p in pings
    ]


@router.get("/vehicles/{vehicle_id}/history", response_model=dict)
def vehicle_history(
    vehicle_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full day GPS history for the history/replay page."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    pings = svc.get_vehicle_history(db, vehicle_id, date)
    return {
        "vehicle_id": vehicle_id,
        "registration_no": vehicle.registration_no,
        "date": date,
        "pings": [
            {"lat": p.lat, "lng": p.lng, "speed_kmh": p.speed_kmh,
             "heading": p.heading, "ts": p.ts}
            for p in pings
        ]
    }


@router.get("/vehicles", response_model=List[dict])
def list_vehicles(
    depot_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all vehicles (for dropdowns in history page)."""
    filter_depot = depot_id
    if current_user.role == "depot_manager" and not depot_id:
        filter_depot = current_user.depot_id
    vehicles = svc.get_all_vehicles(db, depot_id=filter_depot)
    return [
        {"id": v.id, "registration_no": v.registration_no,
         "model": v.model, "status": v.status, "depot_id": v.depot_id}
        for v in vehicles
    ]


@router.get("/depots", response_model=List[dict])
def list_depots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all depots (for the depot filter dropdown)."""
    depots = svc.get_depots(db)
    return [{"id": d.id, "name": d.name, "code": d.code} for d in depots]
