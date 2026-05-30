from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Incident, IncidentEvent, IncidentStatus, IncidentSeverity,
    User, Vehicle, Depot, UserRole
)

# ── Valid state transitions ───────────────────────────────────────────────────
VALID_TRANSITIONS = {
    IncidentStatus.open:        [IncidentStatus.acknowledged, IncidentStatus.closed],
    IncidentStatus.acknowledged:[IncidentStatus.in_progress, IncidentStatus.closed],
    IncidentStatus.in_progress: [IncidentStatus.resolved, IncidentStatus.closed],
    IncidentStatus.resolved:    [IncidentStatus.closed],
    IncidentStatus.closed:      [],
}

# SLA minutes per severity
SLA_MINUTES = {
    IncidentSeverity.P1: 60,
    IncidentSeverity.P2: 240,
    IncidentSeverity.P3: 1440,
}


def get_incidents(
    db: Session,
    user: User,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    depot_id: Optional[int] = None,
    mine_only: bool = False,
) -> List[Incident]:
    q = db.query(Incident)

    # Scope by role
    if user.role == UserRole.driver:
        q = q.filter(Incident.raised_by_id == user.id)
    elif user.role == UserRole.depot_manager:
        q = q.filter(Incident.depot_id == user.depot_id)
    else:
        if depot_id:
            q = q.filter(Incident.depot_id == depot_id)

    if mine_only and user.role != UserRole.driver:
        q = q.filter(Incident.raised_by_id == user.id)
    if status:
        q = q.filter(Incident.status == status)
    if severity:
        q = q.filter(Incident.severity == severity)

    return q.order_by(Incident.created_at.desc()).all()


def get_incident(db: Session, incident_id: int) -> Optional[Incident]:
    return db.query(Incident).filter(Incident.id == incident_id).first()


def create_incident(db: Session, payload, raised_by: User) -> Incident:
    # Auto-set depot from user if not provided
    depot_id = payload.depot_id or raised_by.depot_id

    inc = Incident(
        title=payload.title,
        description=payload.description,
        type=payload.type,
        severity=payload.severity,
        status=IncidentStatus.open,
        vehicle_id=payload.vehicle_id,
        depot_id=depot_id,
        raised_by_id=raised_by.id,
        lat=payload.lat,
        lng=payload.lng,
        is_panic=payload.is_panic,
    )
    db.add(inc)
    db.flush()

    # First event
    event = IncidentEvent(
        incident_id=inc.id,
        user_id=raised_by.id,
        to_status=IncidentStatus.open,
        note="Incident raised" + (" via PANIC button" if payload.is_panic else ""),
    )
    db.add(event)
    db.commit()
    db.refresh(inc)
    return inc


def create_panic_incident(db: Session, driver: User, vehicle_id: Optional[int], lat: Optional[float], lng: Optional[float]) -> Incident:
    from app.schemas.incidents import IncidentCreate
    payload = IncidentCreate(
        title=f"PANIC: Emergency raised by {driver.full_name or driver.username}",
        description="Driver triggered panic button. Immediate assistance required.",
        type="breakdown",
        severity=IncidentSeverity.P1,
        vehicle_id=vehicle_id,
        depot_id=driver.depot_id,
        lat=lat,
        lng=lng,
        is_panic=True,
    )
    return create_incident(db, payload, raised_by=driver)


def transition_status(db: Session, incident: Incident, to_status: IncidentStatus, note: Optional[str], actor: User) -> Incident:
    allowed = VALID_TRANSITIONS.get(incident.status, [])
    if to_status not in allowed:
        raise ValueError(f"Cannot transition from {incident.status} to {to_status}. Allowed: {[s.value for s in allowed]}")

    from_status = incident.status
    incident.status = to_status
    if to_status == IncidentStatus.resolved:
        incident.resolved_at = datetime.utcnow()

    event = IncidentEvent(
        incident_id=incident.id,
        user_id=actor.id,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )
    db.add(event)
    db.commit()
    db.refresh(incident)
    return incident


def update_incident(db: Session, incident: Incident, payload, actor: User) -> Incident:
    if payload.title is not None:
        incident.title = payload.title
    if payload.description is not None:
        incident.description = payload.description
    if payload.severity is not None:
        incident.severity = payload.severity
    if payload.assigned_to_id is not None:
        incident.assigned_to_id = payload.assigned_to_id
        event = IncidentEvent(
            incident_id=incident.id,
            user_id=actor.id,
            note=f"Assigned to user ID {payload.assigned_to_id}",
        )
        db.add(event)
    db.commit()
    db.refresh(incident)
    return incident


def enrich_incident(db: Session, inc: Incident) -> dict:
    raised_by = db.query(User).filter(User.id == inc.raised_by_id).first()
    assigned_to = db.query(User).filter(User.id == inc.assigned_to_id).first() if inc.assigned_to_id else None
    vehicle = db.query(Vehicle).filter(Vehicle.id == inc.vehicle_id).first() if inc.vehicle_id else None
    depot = db.query(Depot).filter(Depot.id == inc.depot_id).first() if inc.depot_id else None

    events = []
    for e in sorted(inc.events, key=lambda x: x.created_at):
        actor = db.query(User).filter(User.id == e.user_id).first() if e.user_id else None
        events.append({
            "id": e.id,
            "user_id": e.user_id,
            "actor_name": actor.full_name if actor else "System",
            "from_status": e.from_status,
            "to_status": e.to_status,
            "note": e.note,
            "created_at": e.created_at,
        })

    # SLA breach check
    sla_mins = SLA_MINUTES.get(inc.severity)
    sla_breached = False
    sla_remaining_mins = None
    if sla_mins and inc.status not in (IncidentStatus.resolved, IncidentStatus.closed):
        elapsed = (datetime.utcnow() - inc.created_at).total_seconds() / 60
        sla_remaining_mins = round(sla_mins - elapsed)
        sla_breached = elapsed > sla_mins

    return {
        "id": inc.id,
        "title": inc.title,
        "description": inc.description,
        "type": inc.type,
        "severity": inc.severity,
        "status": inc.status,
        "vehicle_id": inc.vehicle_id,
        "registration_no": vehicle.registration_no if vehicle else None,
        "depot_id": inc.depot_id,
        "depot_name": depot.name if depot else None,
        "raised_by_id": inc.raised_by_id,
        "raised_by_name": raised_by.full_name if raised_by else None,
        "assigned_to_id": inc.assigned_to_id,
        "assigned_to_name": assigned_to.full_name if assigned_to else None,
        "lat": inc.lat,
        "lng": inc.lng,
        "is_panic": inc.is_panic,
        "created_at": inc.created_at,
        "resolved_at": inc.resolved_at,
        "sla_breached": sla_breached,
        "sla_remaining_mins": sla_remaining_mins,
        "events": events,
    }
