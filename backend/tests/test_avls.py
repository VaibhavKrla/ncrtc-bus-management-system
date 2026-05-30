"""Phase 3 tests — AVLS live positions and history endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app
from app.db.session import Base, get_db
from app.models.models import User, Depot, Vehicle, GpsPing, UserRole, VehicleStatus
from app.core.security import hash_password

TEST_DB_URL = "sqlite:///./test_avls.db"
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
    depot = Depot(name="Test Depot", code="TST2", address="Test")
    db.add(depot)
    db.flush()

    vehicle = Vehicle(
        registration_no="DL-01-TEST-0001", model="Tata Starbus",
        capacity=40, status=VehicleStatus.active, depot_id=depot.id
    )
    db.add(vehicle)
    db.flush()

    admin = User(
        username="avls_admin", email="avls@test.com",
        hashed_password=hash_password("pass"),
        full_name="Admin", role=UserRole.admin
    )
    db.add(admin)
    db.flush()

    # Seed GPS pings
    now = datetime.utcnow()
    for i in range(10):
        ping = GpsPing(
            vehicle_id=vehicle.id,
            lat=28.64 + i * 0.001,
            lng=77.33 + i * 0.001,
            speed_kmh=30.0,
            heading=90.0,
            ts=now - timedelta(minutes=i * 3),
        )
        db.add(ping)

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def get_token():
    res = client.post("/api/v1/auth/login", data={"username": "avls_admin", "password": "pass"})
    return res.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_live_positions():
    token = get_token()
    res = client.get("/api/v1/avls/live", headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["registration_no"] == "DL-01-TEST-0001"
    assert "lat" in data[0]
    assert "lng" in data[0]
    assert "speed_kmh" in data[0]


def test_live_positions_unauthenticated():
    res = client.get("/api/v1/avls/live")
    assert res.status_code == 401


def test_vehicle_trail():
    token = get_token()
    db = TestSession()
    vehicle = db.query(Vehicle).filter_by(registration_no="DL-01-TEST-0001").first()
    vid = vehicle.id
    db.close()

    res = client.get(f"/api/v1/avls/vehicles/{vid}/trail?minutes=30", headers=auth(token))
    assert res.status_code == 200
    trail = res.json()
    assert len(trail) > 0
    assert "lat" in trail[0]
    assert "lng" in trail[0]


def test_vehicle_history():
    token = get_token()
    db = TestSession()
    vehicle = db.query(Vehicle).filter_by(registration_no="DL-01-TEST-0001").first()
    vid = vehicle.id
    db.close()

    today = datetime.utcnow().strftime("%Y-%m-%d")
    res = client.get(f"/api/v1/avls/vehicles/{vid}/history?date={today}", headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["vehicle_id"] == vid
    assert "pings" in data
    assert len(data["pings"]) > 0


def test_vehicle_list():
    token = get_token()
    res = client.get("/api/v1/avls/vehicles", headers=auth(token))
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_depots_list():
    token = get_token()
    res = client.get("/api/v1/avls/depots", headers=auth(token))
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["code"] == "TST2"
