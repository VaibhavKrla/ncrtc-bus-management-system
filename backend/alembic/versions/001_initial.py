"""initial schema - all 12 tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "depot",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("polygon", Geometry("POLYGON", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "vehicle",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("registration_no", sa.String(20), unique=True, nullable=False),
        sa.Column("model", sa.String(100)),
        sa.Column("capacity", sa.Integer, server_default="40"),
        sa.Column("status", sa.String(20), server_default="idle"),
        sa.Column("depot_id", sa.Integer, sa.ForeignKey("depot.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(120), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100)),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("depot_id", sa.Integer, sa.ForeignKey("depot.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_user_username", "user", ["username"])

    op.create_table(
        "stop",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
        sa.Column("location", Geometry("POINT", srid=4326), nullable=True),
    )

    op.create_table(
        "route",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("depot_id", sa.Integer, sa.ForeignKey("depot.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "route_stop",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("route_id", sa.Integer, sa.ForeignKey("route.id"), nullable=False),
        sa.Column("stop_id", sa.Integer, sa.ForeignKey("stop.id"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("scheduled_time", sa.String(5)),
        sa.UniqueConstraint("route_id", "sequence"),
    )

    op.create_table(
        "duty",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("driver_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicle.id"), nullable=False),
        sa.Column("route_id", sa.Integer, sa.ForeignKey("route.id"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("shift_start", sa.String(5), nullable=False),
        sa.Column("shift_end", sa.String(5), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("acknowledged_at", sa.DateTime, nullable=True),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_duty_date_depot", "duty", ["date"])

    op.create_table(
        "gps_ping",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicle.id"), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
        sa.Column("speed_kmh", sa.Float, server_default="0"),
        sa.Column("heading", sa.Float, server_default="0"),
        sa.Column("location", Geometry("POINT", srid=4326), nullable=True),
        sa.Column("ts", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_gps_vehicle_ts", "gps_ping", ["vehicle_id", "ts"])

    op.create_table(
        "incident",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(5), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicle.id"), nullable=True),
        sa.Column("depot_id", sa.Integer, sa.ForeignKey("depot.id"), nullable=True),
        sa.Column("raised_by_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("assigned_to_id", sa.Integer, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("is_panic", sa.Boolean, server_default="false"),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_incident_status", "incident", ["status"])
    op.create_index("ix_incident_depot", "incident", ["depot_id"])

    op.create_table(
        "incident_event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("incident_id", sa.Integer, sa.ForeignKey("incident.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=True),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_incident_event_incident", "incident_event", ["incident_id"])

    op.create_table(
        "notice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("target", sa.String(20), server_default="all"),
        sa.Column("target_depot_id", sa.Integer, sa.ForeignKey("depot.id"), nullable=True),
        sa.Column("target_role", sa.String(20), nullable=True),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("is_published", sa.Boolean, server_default="false"),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "notice_read",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("notice_id", sa.Integer, sa.ForeignKey("notice.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("read_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("notice_id", "user_id"),
    )


def downgrade():
    op.drop_table("notice_read")
    op.drop_table("notice")
    op.drop_table("incident_event")
    op.drop_table("incident")
    op.drop_table("gps_ping")
    op.drop_table("duty")
    op.drop_table("route_stop")
    op.drop_table("route")
    op.drop_table("stop")
    op.drop_table("user")
    op.drop_table("vehicle")
    op.drop_table("depot")
