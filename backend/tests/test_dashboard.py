"""Phase 7 tests — dashboard stats endpoint."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.main import app
from app.db.session import Base, get_db
from app.models.models import (
    User, Depot, Vehicle, Incident, Duty, Route, Notice,
    UserRole, VehicleStatus, IncidentStatus, IncidentSeverity,
    IncidentType, DutyStatus
)
from app.core.security import hash_password

TEST_DB_URL = "sqlite:///./test_dash.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestSession()

    depot = Depot(name="Dash Depot", code="DSH", address="Test")
    db.add(depot)
    db.flush()

    vehicle = Vehicle(
        registration_no="DL-DASH-001", model="Test Bus",
        capacity=40, status=VehicleStatus.active, depot_id=depot.id
    )
    db.add(vehicle)
    db.flush()

    admin = User(
        username="dash_admin", email="dashadmin@test.com",
        hashed_password=hash_password("pass"),
        full_name="Dash Admin", role=UserRole.admin
    )
    mgr = User(
        username="dash_mgr", email="dashmgr@test.com",
        hashed_password=hash_password("pass"),
        full_name="Dash Manager", role=UserRole.depot_manager,
        depot_id=depot.id
    )
    driver = User(
        username="dash_driver", email="dashdriver@test.com",
        hashed_password=hash_password("pass"),
        full_name="Dash Driver", role=UserRole.driver,
        depot_id=depot.id
    )
    db.add_all([admin, mgr, driver])
    db.flush()

    # Open incident
    inc = Incident(
        title="Test P1", type=IncidentType.breakdown,
        severity=IncidentSeverity.P1, status=IncidentStatus.open,
        raised_by_id=driver.id, depot_id=depot.id,
        vehicle_id=vehicle.id, is_panic=False,
        created_at=datetime.utcnow()
    )
    db.add(inc)

    # Today duty
    route = Route(name="Test Route", code="TR99", depot_id=depot.id)
    db.add(route)
    db.flush()

    duty = Duty(
        driver_id=driver.id, vehicle_id=vehicle.id,
        route_id=route.id, date=datetime.utcnow().strftime("%Y-%m-%d"),
        shift_start="06:00", shift_end="14:00",
        status=DutyStatus.acknowledged,
        acknowledged_at=datetime.utcnow()
    )
    db.add(duty)

    # Published notice
    notice = Notice(
        title="Test Notice", body="Test body",
        is_published=True, published_at=datetime.utcnow(),
        created_by_id=admin.id
    )
    db.add(notice)

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def get_token(username):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": "pass"})
    return res.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_stats_admin():
    token = get_token("dash_admin")
    res = client.get("/api/v1/dashboard/stats", headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert "vehicles" in data
    assert "incidents" in data
    assert "duties" in data
    assert "notices" in data
    assert "recent_incidents" in data
    assert data["vehicles"]["total"] >= 1
    assert data["incidents"]["open"] >= 1
    assert data["duties"]["today"] >= 1
    assert data["notices"]["published"] >= 1


def test_dashboard_stats_manager_scoped():
    """Depot manager should see only their depot's data."""
    token = get_token("dash_mgr")
    res = client.get("/api/v1/dashboard/stats", headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["incidents"]["open"] >= 1


def test_dashboard_recent_incidents_structure():
    token = get_token("dash_admin")
    res = client.get("/api/v1/dashboard/stats", headers=auth(token))
    data = res.json()
    if data["recent_incidents"]:
        inc = data["recent_incidents"][0]
        assert "id" in inc
        assert "title" in inc
        assert "severity" in inc
        assert "status" in inc
        assert "is_panic" in inc


def test_dashboard_unauthenticated():
    res = client.get("/api/v1/dashboard/stats")
    assert res.status_code == 401
