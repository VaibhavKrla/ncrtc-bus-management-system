from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Notice, NoticeRead, NoticeTarget, User, UserRole
)


def get_notices_for_user(db: Session, user: User) -> List[Notice]:
    """Return all published notices visible to this user."""
    query = db.query(Notice).filter(Notice.is_published == True)

    if user.role in (UserRole.admin, UserRole.control_operator):
        # See everything
        pass
    else:
        # Filter by target
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Notice.target == NoticeTarget.all,
                (Notice.target == NoticeTarget.depot) & (Notice.target_depot_id == user.depot_id),
                (Notice.target == NoticeTarget.role) & (Notice.target_role == user.role),
            )
        )

    return query.order_by(Notice.published_at.desc()).all()


def get_notice_by_id(db: Session, notice_id: int) -> Optional[Notice]:
    return db.query(Notice).filter(Notice.id == notice_id).first()


def create_notice(db: Session, payload, created_by_id: int) -> Notice:
    notice = Notice(
        title=payload.title,
        body=payload.body,
        target=payload.target,
        target_depot_id=payload.target_depot_id,
        target_role=payload.target_role,
        is_published=payload.is_published,
        published_at=datetime.utcnow() if payload.is_published else None,
        created_by_id=created_by_id,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice


def update_notice(db: Session, notice: Notice, payload) -> Notice:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(notice, field, value)
    # Auto-set published_at when publishing for first time
    if payload.is_published and not notice.published_at:
        notice.published_at = datetime.utcnow()
    db.commit()
    db.refresh(notice)
    return notice


def delete_notice(db: Session, notice: Notice):
    db.delete(notice)
    db.commit()


def mark_read(db: Session, notice_id: int, user_id: int) -> NoticeRead:
    existing = db.query(NoticeRead).filter_by(
        notice_id=notice_id, user_id=user_id
    ).first()
    if existing:
        return existing
    nr = NoticeRead(notice_id=notice_id, user_id=user_id)
    db.add(nr)
    db.commit()
    db.refresh(nr)
    return nr


def get_read_receipts(db: Session, notice_id: int) -> List[NoticeRead]:
    return (
        db.query(NoticeRead)
        .filter(NoticeRead.notice_id == notice_id)
        .order_by(NoticeRead.read_at.desc())
        .all()
    )


def enrich_notice(db: Session, notice: Notice, user: User) -> dict:
    """Add read_count, total_target_count, is_read_by_me to a notice dict."""
    read_count = db.query(NoticeRead).filter(NoticeRead.notice_id == notice.id).count()
    is_read = db.query(NoticeRead).filter_by(notice_id=notice.id, user_id=user.id).first() is not None

    # Count target users
    uq = db.query(User).filter(User.is_active == True)
    if notice.target == NoticeTarget.depot and notice.target_depot_id:
        uq = uq.filter(User.depot_id == notice.target_depot_id)
    elif notice.target == NoticeTarget.role and notice.target_role:
        uq = uq.filter(User.role == notice.target_role)
    total = uq.count()

    d = {c.name: getattr(notice, c.name) for c in notice.__table__.columns}
    d["read_count"] = read_count
    d["total_target_count"] = total
    d["is_read_by_me"] = is_read
    return d
