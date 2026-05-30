import enum
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base

# ─────────────────────────────────────────
# Enums
# ─────────────────────────────────────────


class UserRole(str, enum.Enum):
    driver = "driver"
    conductor = "conductor"
    depot_manager = "depot_manager"
    control_operator = "control_operator"
    admin = "admin"


class VehicleStatus(str, enum.Enum):
    active = "active"
    idle = "idle"
    maintenance = "maintenance"
    breakdown = "breakdown"


class DutyStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    acknowledged = "acknowledged"
    completed = "completed"


class IncidentType(str, enum.Enum):
    breakdown = "breakdown"
    accident = "accident"
    complaint = "complaint"
    other = "other"


class IncidentSeverity(str, enum.Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class IncidentStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


# ─────────────────────────────────────────
# Table 1: Depot
# ─────────────────────────────────────────


class Depot(Base):
    __tablename__ = "depot"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    address = Column(Text)
    # PostGIS polygon for geofence (stretch feature)
    polygon = Column(Geometry("POLYGON", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    vehicles = relationship("Vehicle", back_populates="depot")
    users = relationship("User", back_populates="depot")
    routes = relationship("Route", back_populates="depot")


# ─────────────────────────────────────────
# Table 2: Vehicle
# ─────────────────────────────────────────


class Vehicle(Base):
    __tablename__ = "vehicle"

    id = Column(Integer, primary_key=True, index=True)
    registration_no = Column(String(20), unique=True, nullable=False)
    model = Column(String(100))
    capacity = Column(Integer, default=40)
    status = Column(String(20), default=VehicleStatus.idle.value)
    depot_id = Column(Integer, ForeignKey("depot.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    depot = relationship("Depot", back_populates="vehicles")
    duties = relationship("Duty", back_populates="vehicle")
    gps_pings = relationship("GpsPing", back_populates="vehicle")
    incidents = relationship("Incident", back_populates="vehicle")


# ─────────────────────────────────────────
# Table 3: User
# ─────────────────────────────────────────


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), nullable=False)
    depot_id = Column(
        Integer, ForeignKey("depot.id"), nullable=True
    )  # null for admin/control_op
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_duties = relationship("Duty", foreign_keys="Duty.created_by_id")

    # Relationships
    depot = relationship("Depot", back_populates="users")
    duties = relationship(
        "Duty", foreign_keys="Duty.driver_id", back_populates="driver"
    )
    raised_incidents = relationship(
        "Incident", foreign_keys="Incident.raised_by_id", back_populates="raised_by"
    )
    assigned_incidents = relationship(
        "Incident", foreign_keys="Incident.assigned_to_id", back_populates="assigned_to"
    )
    notice_reads = relationship("NoticeRead", back_populates="user")


# ─────────────────────────────────────────
# Table 4: Stop
# ─────────────────────────────────────────


class Stop(Base):
    __tablename__ = "stop"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=True)

    # Relationships
    route_stops = relationship("RouteStop", back_populates="stop")


# ─────────────────────────────────────────
# Table 5: Route
# ─────────────────────────────────────────


class Route(Base):
    __tablename__ = "route"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    depot_id = Column(Integer, ForeignKey("depot.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    depot = relationship("Depot", back_populates="routes")
    route_stops = relationship(
        "RouteStop", back_populates="route", order_by="RouteStop.sequence"
    )
    duties = relationship("Duty", back_populates="route")


# ─────────────────────────────────────────
# Table 6: RouteStop (junction)
# ─────────────────────────────────────────


class RouteStop(Base):
    __tablename__ = "route_stop"
    __table_args__ = (UniqueConstraint("route_id", "sequence"),)

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stop.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    scheduled_time = Column(String(5))  # HH:MM

    # Relationships
    route = relationship("Route", back_populates="route_stops")
    stop = relationship("Stop", back_populates="route_stops")


# ─────────────────────────────────────────
# Table 7: Duty
# ─────────────────────────────────────────


class Duty(Base):
    __tablename__ = "duty"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    shift_start = Column(String(5), nullable=False)  # HH:MM
    shift_end = Column(String(5), nullable=False)  # HH:MM
    status = Column(String(20), default=DutyStatus.draft.value)
    acknowledged_at = Column(DateTime, nullable=True)
    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    created_by = relationship("User", foreign_keys=[created_by_id])
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    driver = relationship("User", foreign_keys=[driver_id], back_populates="duties")
    vehicle = relationship("Vehicle", back_populates="duties")
    route = relationship("Route", back_populates="duties")


# ─────────────────────────────────────────
# Table 8: GpsPing
# ─────────────────────────────────────────


class GpsPing(Base):
    __tablename__ = "gps_ping"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id"), nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    speed_kmh = Column(Float, default=0.0)
    heading = Column(Float, default=0.0)  # degrees 0-360
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="gps_pings")


# ─────────────────────────────────────────
# Table 9: Incident
# ─────────────────────────────────────────


class Incident(Base):
    __tablename__ = "incident"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    type = Column(String(20), nullable=False)
    severity = Column(String(5), nullable=False)
    status = Column(String(20), default=IncidentStatus.open.value, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id"), nullable=True)
    depot_id = Column(Integer, ForeignKey("depot.id"), nullable=True, index=True)
    raised_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    is_panic = Column(Boolean, default=False)
    photo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="incidents")
    raised_by = relationship(
        "User", foreign_keys=[raised_by_id], back_populates="raised_incidents"
    )
    assigned_to = relationship(
        "User", foreign_keys=[assigned_to_id], back_populates="assigned_incidents"
    )
    events = relationship(
        "IncidentEvent", back_populates="incident", order_by="IncidentEvent.created_at"
    )


# ─────────────────────────────────────────
# Table 10: IncidentEvent (audit trail)
# ─────────────────────────────────────────


class IncidentEvent(Base):
    __tablename__ = "incident_event"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incident.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="events")


# ─────────────────────────────────────────
# Table 11: Notice
# ─────────────────────────────────────────


class NoticeTarget(str, enum.Enum):
    all = "all"
    depot = "depot"
    role = "role"


class Notice(Base):
    __tablename__ = "notice"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    target = Column(String(20), default=NoticeTarget.all.value)
    target_depot_id = Column(Integer, ForeignKey("depot.id"), nullable=True)
    target_role = Column(String(20), nullable=True)
    published_at = Column(DateTime, nullable=True)
    is_published = Column(Boolean, default=False)
    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reads = relationship("NoticeRead", back_populates="notice")


# ─────────────────────────────────────────
# Table 12: NoticeRead
# ─────────────────────────────────────────


class NoticeRead(Base):
    __tablename__ = "notice_read"
    __table_args__ = (UniqueConstraint("notice_id", "user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(Integer, ForeignKey("notice.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    read_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    notice = relationship("Notice", back_populates="reads")
    user = relationship("User", back_populates="notice_reads")
