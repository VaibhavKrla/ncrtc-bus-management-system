from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class VehiclePositionOut(BaseModel):
    vehicle_id: int
    registration_no: str
    model: Optional[str]
    status: str
    depot_id: int
    depot_name: Optional[str]
    lat: float
    lng: float
    speed_kmh: float
    heading: float
    last_ping: datetime
    driver_name: Optional[str] = None
    route_name: Optional[str] = None

    model_config = {"from_attributes": True}


class GpsPingOut(BaseModel):
    id: int
    vehicle_id: int
    lat: float
    lng: float
    speed_kmh: float
    heading: float
    ts: datetime

    model_config = {"from_attributes": True}


class VehicleHistoryOut(BaseModel):
    vehicle_id: int
    registration_no: str
    date: str
    pings: List[GpsPingOut]


class VehicleOut(BaseModel):
    id: int
    registration_no: str
    model: Optional[str]
    capacity: int
    status: str
    depot_id: int

    model_config = {"from_attributes": True}
