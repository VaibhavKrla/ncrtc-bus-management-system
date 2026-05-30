"""
Phase 1 tests — auth endpoints and DB models.
Run with: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.models.models import User, Depot, UserRole
from app.core.security import hash_password

# ── Test DB (in-memory SQLite for speed) ──────────────────────────────────────
TEST_DB_URL = "sqlite:///./test.db"
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
    # Seed a depot + test users
    depot = Depot(name="Test Depot", code="TST", address="Test Address")
    db.add(depot)
    db.flush()
    admin = User(
        username="testadmin", email="testadmin@test.com",
        hashed_password=hash_password("testpass"),
        full_name="Test Admin", role=UserRole.admin
    )
    driver = User(
        username="testdriver", email="testdriver@test.com",
        hashed_password=hash_password("testpass"),
        full_name="Test Driver", role=UserRole.driver,
        depot_id=depot.id
    )
    db.add_all([admin, driver])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_login_success():
    res = client.post("/api/v1/auth/login", data={
        "username": "testadmin", "password": "testpass"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["username"] == "testadmin"


def test_login_wrong_password():
    res = client.post("/api/v1/auth/login", data={
        "username": "testadmin", "password": "wrongpass"
    })
    assert res.status_code == 401


def test_login_unknown_user():
    res = client.post("/api/v1/auth/login", data={
        "username": "nobody", "password": "pass"
    })
    assert res.status_code == 401


def test_get_me():
    # Login first
    token_res = client.post("/api/v1/auth/login", data={
        "username": "testadmin", "password": "testpass"
    })
    token = token_res.json()["access_token"]

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["username"] == "testadmin"


def test_get_me_no_token():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_driver_login():
    res = client.post("/api/v1/auth/login", data={
        "username": "testdriver", "password": "testpass"
    })
    assert res.status_code == 200
    assert res.json()["role"] == "driver"
