from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.models import DutyStatus


# ── Route schemas ─────────────────────────────────────────────────────────────

class RouteStopIn(BaseModel):
    stop_id: int
    sequence: int
    scheduled_time: Optional[str] = None  # HH:MM


class RouteCreate(BaseModel):
    name: str
    code: str
    depot_id: int
    stops: List[RouteStopIn] = []


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None
    stops: Optional[List[RouteStopIn]] = None


class StopOut(BaseModel):
    id: int
    name: str
    code: str
    lat: float
    lng: float
    sequence: Optional[int] = None
    scheduled_time: Optional[str] = None

    model_config = {"from_attributes": True}


class RouteOut(BaseModel):
    id: int
    name: str
    code: str
    depot_id: int
    depot_name: Optional[str] = None
    is_active: bool
    stops: List[StopOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Stop schemas ──────────────────────────────────────────────────────────────

class StopCreate(BaseModel):
    name: str
    code: str
    lat: float
    lng: float


# ── Duty schemas ──────────────────────────────────────────────────────────────

class DutyCreate(BaseModel):
    driver_id: int
    vehicle_id: int
    route_id: int
    date: str          # YYYY-MM-DD
    shift_start: str   # HH:MM
    shift_end: str     # HH:MM


class DutyUpdate(BaseModel):
    driver_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    route_id: Optional[int] = None
    date: Optional[str] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    status: Optional[DutyStatus] = None


class DutyOut(BaseModel):
    id: int
    driver_id: int
    driver_name: Optional[str] = None
    vehicle_id: int
    registration_no: Optional[str] = None
    route_id: int
    route_name: Optional[str] = None
    date: str
    shift_start: str
    shift_end: str
    status: DutyStatus
    acknowledged_at: Optional[datetime] = None
    depot_id: Optional[int] = None

    model_config = {"from_attributes": True}


class BulkPublishRequest(BaseModel):
    duty_ids: List[int]


class AcknowledgeRequest(BaseModel):
    duty_id: int
