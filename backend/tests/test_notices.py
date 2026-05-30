"""
Phase 2 tests — notices CRUD, publish, read receipts.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.models.models import User, Depot, UserRole, Notice, NoticeTarget
from app.core.security import hash_password

TEST_DB_URL = "sqlite:///./test_notices.db"
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
    depot = Depot(name="Test Depot", code="TST", address="Test")
    db.add(depot)
    db.flush()
    admin = User(
        username="admin2", email="admin2@test.com",
        hashed_password=hash_password("pass"), full_name="Admin",
        role=UserRole.admin
    )
    driver = User(
        username="driver2", email="driver2@test.com",
        hashed_password=hash_password("pass"), full_name="Driver",
        role=UserRole.driver, depot_id=depot.id
    )
    db.add_all([admin, driver])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def get_token(username, password="pass"):
    res = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    return res.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_create_notice_as_admin():
    token = get_token("admin2")
    res = client.post("/api/v1/notices/", json={
        "title": "Test Notice", "body": "Hello staff", "target": "all", "is_published": True
    }, headers=auth(token))
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Test Notice"
    assert data["is_published"] is True


def test_driver_cannot_create_notice():
    token = get_token("driver2")
    res = client.post("/api/v1/notices/", json={
        "title": "Hack", "body": "...", "target": "all"
    }, headers=auth(token))
    assert res.status_code == 403


def test_list_notices_driver_sees_published():
    admin_token = get_token("admin2")
    # Create published notice
    client.post("/api/v1/notices/", json={
        "title": "Published", "body": "Read me", "target": "all", "is_published": True
    }, headers=auth(admin_token))
    # Create draft notice
    client.post("/api/v1/notices/", json={
        "title": "Draft", "body": "...", "target": "all", "is_published": False
    }, headers=auth(admin_token))

    driver_token = get_token("driver2")
    res = client.get("/api/v1/notices/", headers=auth(driver_token))
    assert res.status_code == 200
    titles = [n["title"] for n in res.json()]
    assert "Published" in titles
    assert "Draft" not in titles


def test_mark_read():
    admin_token = get_token("admin2")
    notice = client.post("/api/v1/notices/", json={
        "title": "Read me", "body": "body", "target": "all", "is_published": True
    }, headers=auth(admin_token)).json()

    driver_token = get_token("driver2")
    res = client.post(f"/api/v1/notices/{notice['id']}/read", headers=auth(driver_token))
    assert res.status_code == 200
    assert res.json()["is_read_by_me"] is True


def test_read_receipts():
    admin_token = get_token("admin2")
    notice = client.post("/api/v1/notices/", json={
        "title": "Receipts test", "body": "body", "target": "all", "is_published": True
    }, headers=auth(admin_token)).json()

    driver_token = get_token("driver2")
    client.post(f"/api/v1/notices/{notice['id']}/read", headers=auth(driver_token))

    res = client.get(f"/api/v1/notices/{notice['id']}/reads", headers=auth(admin_token))
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["username"] == "driver2"


def test_publish_draft():
    admin_token = get_token("admin2")
    draft = client.post("/api/v1/notices/", json={
        "title": "Draft notice", "body": "body", "target": "all", "is_published": False
    }, headers=auth(admin_token)).json()
    assert draft["is_published"] is False

    updated = client.patch(f"/api/v1/notices/{draft['id']}", json={
        "is_published": True
    }, headers=auth(admin_token)).json()
    assert updated["is_published"] is True
    assert updated["published_at"] is not None


def test_delete_notice():
    admin_token = get_token("admin2")
    notice = client.post("/api/v1/notices/", json={
        "title": "Delete me", "body": "body", "target": "all"
    }, headers=auth(admin_token)).json()

    res = client.delete(f"/api/v1/notices/{notice['id']}", headers=auth(admin_token))
    assert res.status_code == 204

    res2 = client.get(f"/api/v1/notices/{notice['id']}", headers=auth(admin_token))
    assert res2.status_code == 404
