from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import User, UserRole
from app.schemas.incidents import IncidentCreate, IncidentUpdate, StatusTransition
from app.services import incidents as svc

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/", response_model=List[dict])
def list_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    depot_id: Optional[int] = Query(None),
    mine_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List incidents scoped by role. Supports filters: status, severity, depot, mine_only."""
    incidents = svc.get_incidents(db, current_user, status, severity, depot_id, mine_only)
    return [svc.enrich_incident(db, i) for i in incidents]


@router.post("/", response_model=dict, status_code=201)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Any logged-in user can raise an incident."""
    inc = svc.create_incident(db, payload, raised_by=current_user)
    return svc.enrich_incident(db, inc)


@router.post("/panic", response_model=dict, status_code=201)
def panic(
    vehicle_id: Optional[int] = Query(None),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("driver", "conductor")),
):
    """
    Driver panic button — creates a P1 incident immediately.
    Pass vehicle_id + lat/lng if available.
    """
    inc = svc.create_panic_incident(db, current_user, vehicle_id, lat, lng)
    return svc.enrich_incident(db, inc)


@router.get("/{incident_id}", response_model=dict)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inc = svc.get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return svc.enrich_incident(db, inc)


@router.patch("/{incident_id}", response_model=dict)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager", "control_operator")),
):
    """Update title, description, severity or assignee."""
    inc = svc.get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    updated = svc.update_incident(db, inc, payload, actor=current_user)
    return svc.enrich_incident(db, updated)


@router.post("/{incident_id}/transition", response_model=dict)
def transition_status(
    incident_id: int,
    payload: StatusTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Move incident through the state machine.
    open → acknowledged → in_progress → resolved → closed
    """
    inc = svc.get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        updated = svc.transition_status(db, inc, payload.to_status, payload.note, actor=current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return svc.enrich_incident(db, updated)
