from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import User, Route, Duty, UserRole
from app.schemas.scheduling import (
    RouteCreate, RouteUpdate, DutyCreate, DutyUpdate,
    BulkPublishRequest, StopCreate
)
from app.services import scheduling as svc

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


# ── Stops ─────────────────────────────────────────────────────────────────────

@router.get("/stops", response_model=List[dict])
def list_stops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stops = svc.get_all_stops(db)
    return [{"id": s.id, "name": s.name, "code": s.code, "lat": s.lat, "lng": s.lng} for s in stops]


@router.post("/stops", response_model=dict, status_code=201)
def create_stop(
    payload: StopCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    stop = svc.create_stop(db, payload)
    return {"id": stop.id, "name": stop.name, "code": stop.code, "lat": stop.lat, "lng": stop.lng}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/routes", response_model=List[dict])
def list_routes(
    depot_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filter_depot = depot_id
    if current_user.role == UserRole.depot_manager and not depot_id:
        filter_depot = current_user.depot_id
    routes = svc.get_routes(db, depot_id=filter_depot)
    return [svc.enrich_route(db, r) for r in routes]


@router.post("/routes", response_model=dict, status_code=201)
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    route = svc.create_route(db, payload)
    return svc.enrich_route(db, route)


@router.get("/routes/{route_id}", response_model=dict)
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    route = svc.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return svc.enrich_route(db, route)


@router.patch("/routes/{route_id}", response_model=dict)
def update_route(
    route_id: int,
    payload: RouteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    route = svc.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    updated = svc.update_route(db, route, payload)
    return svc.enrich_route(db, updated)


@router.delete("/routes/{route_id}", status_code=204)
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    route = svc.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    svc.delete_route(db, route)


# ── Roster ────────────────────────────────────────────────────────────────────

@router.get("/roster", response_model=dict)
def get_roster(
    depot_id: int = Query(...),
    week_start: str = Query(..., description="YYYY-MM-DD Monday"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    """7-day roster grid for a depot."""
    return svc.get_roster(db, depot_id, week_start)


# ── Duties ────────────────────────────────────────────────────────────────────

@router.get("/duties", response_model=List[dict])
def list_duties(
    depot_id: Optional[int] = Query(None),
    date: Optional[str] = Query(None),
    driver_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filter_depot = depot_id
    filter_driver = driver_id
    if current_user.role == UserRole.depot_manager:
        filter_depot = current_user.depot_id
    if current_user.role == UserRole.driver:
        filter_driver = current_user.id
    duties = svc.get_duties(db, depot_id=filter_depot, date=date, driver_id=filter_driver)
    return [svc.enrich_duty(db, d) for d in duties]


@router.post("/duties", response_model=dict, status_code=201)
def create_duty(
    payload: DutyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    duty = svc.create_duty(db, payload, created_by_id=current_user.id)
    return svc.enrich_duty(db, duty)


@router.get("/duties/{duty_id}", response_model=dict)
def get_duty(
    duty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duty = svc.get_duty(db, duty_id)
    if not duty:
        raise HTTPException(status_code=404, detail="Duty not found")
    return svc.enrich_duty(db, duty)


@router.patch("/duties/{duty_id}", response_model=dict)
def update_duty(
    duty_id: int,
    payload: DutyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    duty = svc.get_duty(db, duty_id)
    if not duty:
        raise HTTPException(status_code=404, detail="Duty not found")
    updated = svc.update_duty(db, duty, payload)
    return svc.enrich_duty(db, updated)


@router.delete("/duties/{duty_id}", status_code=204)
def delete_duty(
    duty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    duty = svc.get_duty(db, duty_id)
    if not duty:
        raise HTTPException(status_code=404, detail="Duty not found")
    svc.delete_duty(db, duty)


@router.post("/duties/publish", response_model=dict)
def publish_duties(
    payload: BulkPublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    """Bulk publish a list of draft duties → drivers can now see them."""
    count = svc.publish_duties(db, payload.duty_ids)
    return {"published": count}


@router.post("/duties/{duty_id}/acknowledge", response_model=dict)
def acknowledge_duty(
    duty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("driver")),
):
    """Driver acknowledges their published duty."""
    duty = svc.acknowledge_duty(db, duty_id, driver_id=current_user.id)
    if not duty:
        raise HTTPException(
            status_code=400,
            detail="Duty not found, not yours, or not in published state"
        )
    return svc.enrich_duty(db, duty)


# ── Drivers list (for assign form dropdowns) ──────────────────────────────────

@router.get("/drivers", response_model=List[dict])
def list_drivers(
    depot_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    filter_depot = depot_id
    if current_user.role == UserRole.depot_manager:
        filter_depot = current_user.depot_id
    q = db.query(User).filter(User.role == UserRole.driver, User.is_active == True)
    if filter_depot:
        q = q.filter(User.depot_id == filter_depot)
    users = q.order_by(User.full_name).all()
    return [{"id": u.id, "full_name": u.full_name, "username": u.username, "depot_id": u.depot_id} for u in users]


# ── Vehicles list for depot (assign form dropdown) ────────────────────────────

@router.get("/vehicles", response_model=List[dict])
def list_vehicles_for_scheduling(
    depot_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    from app.models.models import Vehicle
    filter_depot = depot_id
    if current_user.role == UserRole.depot_manager:
        filter_depot = current_user.depot_id
    q = db.query(Vehicle)
    if filter_depot:
        q = q.filter(Vehicle.depot_id == filter_depot)
    vehicles = q.order_by(Vehicle.registration_no).all()
    return [{"id": v.id, "registration_no": v.registration_no, "model": v.model, "depot_id": v.depot_id} for v in vehicles]
