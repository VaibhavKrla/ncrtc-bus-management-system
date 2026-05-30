from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.models import NoticeTarget, UserRole


class NoticeCreate(BaseModel):
    title: str
    body: str
    target: NoticeTarget = NoticeTarget.all
    target_depot_id: Optional[int] = None
    target_role: Optional[UserRole] = None
    is_published: bool = False


class NoticeUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    target: Optional[NoticeTarget] = None
    target_depot_id: Optional[int] = None
    target_role: Optional[UserRole] = None
    is_published: Optional[bool] = None


class NoticeOut(BaseModel):
    id: int
    title: str
    body: str
    target: NoticeTarget
    target_depot_id: Optional[int]
    target_role: Optional[UserRole]
    is_published: bool
    published_at: Optional[datetime]
    created_by_id: int
    created_at: datetime
    read_count: int = 0
    total_target_count: int = 0
    is_read_by_me: bool = False

    model_config = {"from_attributes": True}


class NoticeReadOut(BaseModel):
    id: int
    notice_id: int
    user_id: int
    read_at: datetime
    username: Optional[str] = None
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}
