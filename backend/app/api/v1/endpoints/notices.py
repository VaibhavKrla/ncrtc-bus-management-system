from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import User, Notice, UserRole
from app.schemas.notices import NoticeCreate, NoticeUpdate, NoticeOut, NoticeReadOut
from app.services import notices as svc

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("/", response_model=List[dict])
def list_notices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all notices visible to the current user."""
    all_notices = svc.get_notices_for_user(db, current_user)
    return [svc.enrich_notice(db, n, current_user) for n in all_notices]


@router.get("/all", response_model=List[dict])
def list_all_notices_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    """Admin/manager: list ALL notices including drafts."""
    notices = db.query(Notice).order_by(Notice.created_at.desc()).all()
    return [svc.enrich_notice(db, n, current_user) for n in notices]


@router.post("/", response_model=dict, status_code=201)
def create_notice(
    payload: NoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    """Create a new notice (draft or published)."""
    notice = svc.create_notice(db, payload, created_by_id=current_user.id)
    return svc.enrich_notice(db, notice, current_user)


@router.get("/{notice_id}", response_model=dict)
def get_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notice = svc.get_notice_by_id(db, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return svc.enrich_notice(db, notice, current_user)


@router.patch("/{notice_id}", response_model=dict)
def update_notice(
    notice_id: int,
    payload: NoticeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    notice = svc.get_notice_by_id(db, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    updated = svc.update_notice(db, notice, payload)
    return svc.enrich_notice(db, updated, current_user)


@router.delete("/{notice_id}", status_code=204)
def delete_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    notice = svc.get_notice_by_id(db, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    svc.delete_notice(db, notice)


@router.post("/{notice_id}/read", response_model=dict)
def mark_read(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notice as read by the current user."""
    notice = svc.get_notice_by_id(db, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    svc.mark_read(db, notice_id, current_user.id)
    return svc.enrich_notice(db, notice, current_user)


@router.get("/{notice_id}/reads", response_model=List[dict])
def get_read_receipts(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "depot_manager")),
):
    """Get list of users who have read this notice."""
    notice = svc.get_notice_by_id(db, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    reads = svc.get_read_receipts(db, notice_id)
    result = []
    for r in reads:
        result.append({
            "id": r.id,
            "notice_id": r.notice_id,
            "user_id": r.user_id,
            "read_at": r.read_at,
            "username": r.user.username if r.user else None,
            "full_name": r.user.full_name if r.user else None,
        })
    return result
