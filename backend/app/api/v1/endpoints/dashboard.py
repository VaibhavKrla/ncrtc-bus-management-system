from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.models import (
    User, Vehicle, Incident, Duty, Notice, NoticeRead,
    IncidentStatus, DutyStatus, UserRole, VehicleStatus
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=dict)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregated stats for the dashboard. Scoped by user role/depot."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    depot_id = current_user.depot_id if current_user.role == UserRole.depot_manager else None

    # ── Vehicles ──────────────────────────────────────────────────────────────
    vq = db.query(Vehicle)
    if depot_id:
        vq = vq.filter(Vehicle.depot_id == depot_id)
    total_vehicles = vq.count()
    active_vehicles = vq.filter(Vehicle.status == VehicleStatus.active).count()

    # ── Incidents ─────────────────────────────────────────────────────────────
    iq = db.query(Incident)
    if depot_id:
        iq = iq.filter(Incident.depot_id == depot_id)
    open_incidents = iq.filter(Incident.status == IncidentStatus.open).count()
    p1_active = iq.filter(
        Incident.severity == "P1",
        Incident.status.notin_([IncidentStatus.resolved, IncidentStatus.closed])
    ).count()

    # ── Duties today ──────────────────────────────────────────────────────────
    dq = db.query(Duty).filter(Duty.date == today)
    if depot_id:
        from app.models.models import User as U
        driver_ids = [u.id for u in db.query(U).filter(U.depot_id == depot_id).all()]
        dq = dq.filter(Duty.driver_id.in_(driver_ids))
    duties_today = dq.count()
    duties_acked = dq.filter(Duty.status == DutyStatus.acknowledged).count()

    # ── Notices ───────────────────────────────────────────────────────────────
    published_notices = db.query(Notice).filter(Notice.is_published == True).count()

    # ── Recent incidents (last 5) ─────────────────────────────────────────────
    riq = db.query(Incident)
    if depot_id:
        riq = riq.filter(Incident.depot_id == depot_id)
    recent_incidents = riq.order_by(Incident.created_at.desc()).limit(5).all()

    recent = []
    for inc in recent_incidents:
        raised = db.query(User).filter(User.id == inc.raised_by_id).first()
        recent.append({
            "id": inc.id,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "is_panic": inc.is_panic,
            "raised_by_name": raised.full_name if raised else None,
            "created_at": inc.created_at,
        })

    return {
        "vehicles": {"total": total_vehicles, "active": active_vehicles},
        "incidents": {"open": open_incidents, "p1_active": p1_active},
        "duties": {"today": duties_today, "acknowledged": duties_acked},
        "notices": {"published": published_notices},
        "recent_incidents": recent,
        "as_of": datetime.utcnow(),
    }
