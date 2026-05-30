"""Phase 4 tests — scheduling: routes, duties, publish, acknowledge."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app
from app.db.session import Base, get_db
from app.models.models import (
    User, Depot, Vehicle, Stop, Route, RouteStop, Duty,
    UserRole, VehicleStatus, DutyStatus
)
from app.core.security import hash_password

TEST_DB_URL = "sqlite:///./test_sched.db"
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

    depot = Depot(name="Sched Depot", code="SCD", address="Test")
    db.add(depot)
    db.flush()

    vehicle = Vehicle(
        registration_no="DL-SCHED-001", model="Test Bus",
        capacity=40, status=VehicleStatus.active, depot_id=depot.id
    )
    db.add(vehicle)
    db.flush()

    stop1 = Stop(name="Stop A", code="STA", lat=28.64, lng=77.33)
    stop2 = Stop(name="Stop B", code="STB", lat=28.65, lng=77.34)
    db.add_all([stop1, stop2])
    db.flush()

    admin = User(
        username="sched_admin", email="schedadmin@test.com",
        hashed_password=hash_password("pass"),
        full_name="Sched Admin", role=UserRole.admin
    )
    manager = User(
        username="sched_mgr", email="schedmgr@test.com",
        hashed_password=hash_password("pass"),
        full_name="Sched Manager", role=UserRole.depot_manager,
        depot_id=depot.id
    )
    driver = User(
        username="sched_driver", email="scheddriver@test.com",
        hashed_password=hash_password("pass"),
        full_name="Sched Driver", role=UserRole.driver,
        depot_id=depot.id
    )
    db.add_all([admin, manager, driver])
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
    depot = db.query(Depot).filter_by(code="SCD").first()
    vehicle = db.query(Vehicle).filter_by(registration_no="DL-SCHED-001").first()
    stop1 = db.query(Stop).filter_by(code="STA").first()
    stop2 = db.query(Stop).filter_by(code="STB").first()
    driver = db.query(User).filter_by(username="sched_driver").first()
    db.close()
    return depot.id, vehicle.id, stop1.id, stop2.id, driver.id


# ── Route tests ───────────────────────────────────────────────────────────────

def test_create_route():
    token = get_token("sched_admin")
    depot_id, _, stop1_id, stop2_id, _ = get_ids()
    res = client.post("/api/v1/scheduling/routes", json={
        "name": "Test Route", "code": "TR01", "depot_id": depot_id,
        "stops": [
            {"stop_id": stop1_id, "sequence": 1, "scheduled_time": "06:00"},
            {"stop_id": stop2_id, "sequence": 2, "scheduled_time": "06:30"},
        ]
    }, headers=auth(token))
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test Route"
    assert len(data["stops"]) == 2


def test_list_routes():
    token = get_token("sched_admin")
    res = client.get("/api/v1/scheduling/routes", headers=auth(token))
    assert res.status_code == 200


def test_driver_cannot_create_route():
    token = get_token("sched_driver")
    depot_id, _, stop1_id, _, _ = get_ids()
    res = client.post("/api/v1/scheduling/routes", json={
        "name": "Hack", "code": "H01", "depot_id": depot_id, "stops": []
    }, headers=auth(token))
    assert res.status_code == 403


# ── Duty tests ────────────────────────────────────────────────────────────────

def create_test_route(token, depot_id, stop1_id):
    res = client.post("/api/v1/scheduling/routes", json={
        "name": "Duty Test Route", "code": "DTR1", "depot_id": depot_id, "stops": [
            {"stop_id": stop1_id, "sequence": 1}
        ]
    }, headers=auth(token))
    return res.json()["id"]


def test_create_duty():
    token = get_token("sched_admin")
    depot_id, vehicle_id, stop1_id, _, driver_id = get_ids()
    route_id = create_test_route(token, depot_id, stop1_id)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    res = client.post("/api/v1/scheduling/duties", json={
        "driver_id": driver_id, "vehicle_id": vehicle_id,
        "route_id": route_id, "date": today,
        "shift_start": "06:00", "shift_end": "14:00"
    }, headers=auth(token))
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "draft"
    assert data["driver_id"] == driver_id


def test_publish_duty():
    token = get_token("sched_mgr")
    depot_id, vehicle_id, stop1_id, _, driver_id = get_ids()
    route_id = create_test_route(token, depot_id, stop1_id)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    duty = client.post("/api/v1/scheduling/duties", json={
        "driver_id": driver_id, "vehicle_id": vehicle_id,
        "route_id": route_id, "date": today,
        "shift_start": "06:00", "shift_end": "14:00"
    }, headers=auth(token)).json()

    res = client.post("/api/v1/scheduling/duties/publish",
        json={"duty_ids": [duty["id"]]}, headers=auth(token))
    assert res.status_code == 200
    assert res.json()["published"] == 1


def test_driver_acknowledge():
    admin_token = get_token("sched_admin")
    driver_token = get_token("sched_driver")
    depot_id, vehicle_id, stop1_id, _, driver_id = get_ids()
    route_id = create_test_route(admin_token, depot_id, stop1_id)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Create + publish
    duty = client.post("/api/v1/scheduling/duties", json={
        "driver_id": driver_id, "vehicle_id": vehicle_id,
        "route_id": route_id, "date": today,
        "shift_start": "06:00", "shift_end": "14:00"
    }, headers=auth(admin_token)).json()
    client.post("/api/v1/scheduling/duties/publish",
        json={"duty_ids": [duty["id"]]}, headers=auth(admin_token))

    # Driver acknowledges
    res = client.post(f"/api/v1/scheduling/duties/{duty['id']}/acknowledge",
        headers=auth(driver_token))
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_at"] is not None


def test_driver_cannot_acknowledge_others_duty():
    """Driver cannot ack a duty that isn't theirs."""
    admin_token = get_token("sched_admin")
    driver_token = get_token("sched_driver")
    depot_id, vehicle_id, stop1_id, _, driver_id = get_ids()

    # Create a duty for a different driver (admin) — just reuse admin id
    db = TestSession()
    admin = db.query(User).filter_by(username="sched_admin").first()
    admin_id = admin.id
    db.close()

    route_id = create_test_route(admin_token, depot_id, stop1_id)
    duty = client.post("/api/v1/scheduling/duties", json={
        "driver_id": admin_id, "vehicle_id": vehicle_id,
        "route_id": route_id, "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "shift_start": "06:00", "shift_end": "14:00"
    }, headers=auth(admin_token)).json()
    client.post("/api/v1/scheduling/duties/publish",
        json={"duty_ids": [duty["id"]]}, headers=auth(admin_token))

    res = client.post(f"/api/v1/scheduling/duties/{duty['id']}/acknowledge",
        headers=auth(driver_token))
    assert res.status_code == 400


def test_roster():
    token = get_token("sched_mgr")
    depot_id, _, _, _, _ = get_ids()
    from datetime import date, timedelta
    monday = date.today()
    while monday.weekday() != 0:
        monday -= timedelta(days=1)
    res = client.get(f"/api/v1/scheduling/roster?depot_id={depot_id}&week_start={monday}",
        headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert "drivers" in data
    assert "dates" in data
    assert len(data["dates"]) == 7
