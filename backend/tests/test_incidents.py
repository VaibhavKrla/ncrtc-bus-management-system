"""Phase 5 tests — IMS: incidents CRUD, state machine, panic, role scoping."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.main import app
from app.db.session import Base, get_db
from app.models.models import (
    User, Depot, Vehicle, Incident, IncidentEvent,
    UserRole, VehicleStatus, IncidentType, IncidentSeverity, IncidentStatus
)
from app.core.security import hash_password

TEST_DB_URL = "sqlite:///./test_ims.db"
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

    depot1 = Depot(name="IMS Depot 1", code="IMS1", address="Test")
    depot2 = Depot(name="IMS Depot 2", code="IMS2", address="Test")
    db.add_all([depot1, depot2])
    db.flush()

    vehicle = Vehicle(
        registration_no="DL-IMS-001", model="Test Bus",
        capacity=40, status=VehicleStatus.active, depot_id=depot1.id
    )
    db.add(vehicle)
    db.flush()

    admin = User(
        username="ims_admin", email="imsadmin@test.com",
        hashed_password=hash_password("pass"),
        full_name="IMS Admin", role=UserRole.admin
    )
    manager = User(
        username="ims_mgr", email="imsmgr@test.com",
        hashed_password=hash_password("pass"),
        full_name="IMS Manager", role=UserRole.depot_manager,
        depot_id=depot1.id
    )
    driver = User(
        username="ims_driver", email="imsdriver@test.com",
        hashed_password=hash_password("pass"),
        full_name="IMS Driver", role=UserRole.driver,
        depot_id=depot1.id
    )
    driver2 = User(
        username="ims_driver2", email="imsdriver2@test.com",
        hashed_password=hash_password("pass"),
        full_name="IMS Driver 2", role=UserRole.driver,
        depot_id=depot2.id
    )
    db.add_all([admin, manager, driver, driver2])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def get_token(username):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": "pass"})
    return res.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def get_ids():
    db = TestSession()
    depot = db.query(Depot).filter_by(code="IMS1").first()
    vehicle = db.query(Vehicle).filter_by(registration_no="DL-IMS-001").first()
    driver = db.query(User).filter_by(username="ims_driver").first()
    db.close()
    return depot.id, vehicle.id, driver.id


# ── Create incident ───────────────────────────────────────────────────────────

def test_create_incident_as_driver():
    token = get_token("ims_driver")
    depot_id, vehicle_id, _ = get_ids()
    res = client.post("/api/v1/incidents/", json={
        "title": "Engine warning light",
        "type": "breakdown",
        "severity": "P2",
        "vehicle_id": vehicle_id,
        "is_panic": False,
    }, headers=auth(token))
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Engine warning light"
    assert data["status"] == "open"
    assert data["severity"] == "P2"
    assert len(data["events"]) == 1


def test_create_incident_as_admin():
    token = get_token("ims_admin")
    depot_id, vehicle_id, _ = get_ids()
    res = client.post("/api/v1/incidents/", json={
        "title": "Admin raised incident",
        "type": "other",
        "severity": "P3",
        "is_panic": False,
    }, headers=auth(token))
    assert res.status_code == 201


def test_create_incident_unauthenticated():
    res = client.post("/api/v1/incidents/", json={
        "title": "No auth", "type": "other", "severity": "P3", "is_panic": False
    })
    assert res.status_code == 401


# ── Panic button ──────────────────────────────────────────────────────────────

def test_panic_creates_p1_incident():
    token = get_token("ims_driver")
    _, vehicle_id, _ = get_ids()
    res = client.post(
        f"/api/v1/incidents/panic?vehicle_id={vehicle_id}&lat=28.64&lng=77.33",
        headers=auth(token)
    )
    assert res.status_code == 201
    data = res.json()
    assert data["severity"] == "P1"
    assert data["is_panic"] is True
    assert data["status"] == "open"
    assert "PANIC" in data["title"]


def test_admin_cannot_panic():
    """Panic is driver/conductor only."""
    token = get_token("ims_admin")
    res = client.post("/api/v1/incidents/panic", headers=auth(token))
    assert res.status_code == 403


# ── List + role scoping ───────────────────────────────────────────────────────

def test_driver_sees_only_own_incidents():
    # Driver 1 raises incident
    token1 = get_token("ims_driver")
    client.post("/api/v1/incidents/", json={
        "title": "Driver 1 incident", "type": "breakdown", "severity": "P3", "is_panic": False
    }, headers=auth(token1))

    # Driver 2 raises incident
    token2 = get_token("ims_driver2")
    client.post("/api/v1/incidents/", json={
        "title": "Driver 2 incident", "type": "other", "severity": "P3", "is_panic": False
    }, headers=auth(token2))

    # Driver 1 should only see their own
    res = client.get("/api/v1/incidents/", headers=auth(token1))
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert all("Driver 1" in t for t in titles)
    assert not any("Driver 2" in t for t in titles)


def test_admin_sees_all_incidents():
    token_d1 = get_token("ims_driver")
    token_d2 = get_token("ims_driver2")
    token_admin = get_token("ims_admin")

    client.post("/api/v1/incidents/", json={"title": "Inc A", "type": "other", "severity": "P3", "is_panic": False}, headers=auth(token_d1))
    client.post("/api/v1/incidents/", json={"title": "Inc B", "type": "other", "severity": "P3", "is_panic": False}, headers=auth(token_d2))

    res = client.get("/api/v1/incidents/", headers=auth(token_admin))
    assert res.status_code == 200
    assert len(res.json()) >= 2


# ── State machine ─────────────────────────────────────────────────────────────

def create_incident_and_get_id(token):
    res = client.post("/api/v1/incidents/", json={
        "title": "State machine test", "type": "breakdown", "severity": "P1", "is_panic": False
    }, headers=auth(token))
    return res.json()["id"]


def test_valid_transition_open_to_acknowledged():
    mgr_token = get_token("ims_mgr")
    inc_id = create_incident_and_get_id(mgr_token)
    res = client.post(f"/api/v1/incidents/{inc_id}/transition",
        json={"to_status": "acknowledged", "note": "On it"},
        headers=auth(mgr_token))
    assert res.status_code == 200
    assert res.json()["status"] == "acknowledged"
    assert len(res.json()["events"]) == 2


def test_invalid_transition_open_to_resolved():
    mgr_token = get_token("ims_mgr")
    inc_id = create_incident_and_get_id(mgr_token)
    res = client.post(f"/api/v1/incidents/{inc_id}/transition",
        json={"to_status": "resolved"},
        headers=auth(mgr_token))
    assert res.status_code == 400


def test_full_state_machine_flow():
    mgr_token = get_token("ims_mgr")
    inc_id = create_incident_and_get_id(mgr_token)

    for to_status in ["acknowledged", "in_progress", "resolved", "closed"]:
        res = client.post(f"/api/v1/incidents/{inc_id}/transition",
            json={"to_status": to_status, "note": f"Moving to {to_status}"},
            headers=auth(mgr_token))
        assert res.status_code == 200, f"Failed at {to_status}: {res.json()}"
        assert res.json()["status"] == to_status

    # Cannot transition from closed
    res = client.post(f"/api/v1/incidents/{inc_id}/transition",
        json={"to_status": "open"}, headers=auth(mgr_token))
    assert res.status_code == 400


def test_sla_fields_present():
    token = get_token("ims_admin")
    inc_id = create_incident_and_get_id(token)
    res = client.get(f"/api/v1/incidents/{inc_id}", headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert "sla_breached" in data
    assert "sla_remaining_mins" in data
