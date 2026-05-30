from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.models import IncidentType, IncidentSeverity, IncidentStatus


class IncidentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: IncidentType
    severity: IncidentSeverity
    vehicle_id: Optional[int] = None
    depot_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_panic: bool = False


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[IncidentSeverity] = None
    assigned_to_id: Optional[int] = None


class StatusTransition(BaseModel):
    to_status: IncidentStatus
    note: Optional[str] = None


class IncidentEventOut(BaseModel):
    id: int
    user_id: Optional[int]
    actor_name: Optional[str] = None
    from_status: Optional[IncidentStatus]
    to_status: Optional[IncidentStatus]
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    vehicle_id: Optional[int]
    registration_no: Optional[str] = None
    depot_id: Optional[int]
    depot_name: Optional[str] = None
    raised_by_id: int
    raised_by_name: Optional[str] = None
    assigned_to_id: Optional[int]
    assigned_to_name: Optional[str] = None
    lat: Optional[float]
    lng: Optional[float]
    is_panic: bool
    created_at: datetime
    resolved_at: Optional[datetime]
    events: List[IncidentEventOut] = []

    model_config = {"from_attributes": True}
