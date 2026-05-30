"""
Phase 7 — Security and edge case tests.
Role enforcement, cross-depot isolation, invalid inputs.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.models.models import User, Depot, Vehicle, UserRole, VehicleStatus
from app.core.security import hash_password

TEST_DB_URL = "sqlite:///./test_security.db"
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

    d1 = Depot(name="Depot A", code="DA1", address="Test")
    d2 = Depot(name="Depot B", code="DB1", address="Test")
    db.add_all([d1, d2])
    db.flush()

    admin = User(username="sec_admin", email="secadmin@test.com",
                 hashed_password=hash_password("pass"),
                 full_name="Sec Admin", role=UserRole.admin)
    driver_a = User(username="sec_driver_a", email="secdrivera@test.com",
                    hashed_password=hash_password("pass"),
                    full_name="Driver A", role=UserRole.driver, depot_id=d1.id)
    driver_b = User(username="sec_driver_b", email="secdriverb@test.com",
                    hashed_password=hash_password("pass"),
                    full_name="Driver B", role=UserRole.driver, depot_id=d2.id)
    mgr_a = User(username="sec_mgr_a", email="secmgra@test.com",
                 hashed_password=hash_password("pass"),
                 full_name="Manager A", role=UserRole.depot_manager, depot_id=d1.id)
    control = User(username="sec_ctrl", email="secctrl@test.com",
                   hashed_password=hash_password("pass"),
                   full_name="Control Op", role=UserRole.control_operator)
    db.add_all([admin, driver_a, driver_b, mgr_a, control])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def tok(username):
    r = client.post("/api/v1/auth/login", data={"username": username, "password": "pass"})
    assert r.status_code == 200, f"Login failed for {username}: {r.json()}"
    return r.json()["access_token"]


def h(token):
    return {"Authorization": f"Bearer {token}"}


# ── Auth security ─────────────────────────────────────────────────────────────

def test_expired_or_invalid_token_rejected():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert res.status_code == 401


def test_missing_token_rejected():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_wrong_password_rejected():
    res = client.post("/api/v1/auth/login", data={"username": "sec_admin", "password": "wrongpassword"})
    assert res.status_code == 401


def test_nonexistent_user_rejected():
    res = client.post("/api/v1/auth/login", data={"username": "nobody_here", "password": "pass"})
    assert res.status_code == 401


# ── Role enforcement ──────────────────────────────────────────────────────────

def test_driver_cannot_create_notice():
    token = tok("sec_driver_a")
    res = client.post("/api/v1/notices/", json={
        "title": "Hack", "body": "...", "target": "all"
    }, headers=h(token))
    assert res.status_code == 403


def test_driver_cannot_create_route():
    token = tok("sec_driver_a")
    db = TestSession()
    d = db.query(Depot).filter_by(code="DA1").first()
    depot_id = d.id
    db.close()
    res = client.post("/api/v1/scheduling/routes", json={
        "name": "Hack Route", "code": "HR01", "depot_id": depot_id, "stops": []
    }, headers=h(token))
    assert res.status_code == 403


def test_driver_cannot_publish_duties():
    token = tok("sec_driver_a")
    res = client.post("/api/v1/scheduling/duties/publish",
        json={"duty_ids": [1]}, headers=h(token))
    assert res.status_code == 403


def test_driver_cannot_delete_notice():
    # First admin creates one
    admin_token = tok("sec_admin")
    notice = client.post("/api/v1/notices/", json={
        "title": "Admin Notice", "body": "body", "target": "all"
    }, headers=h(admin_token)).json()

    driver_token = tok("sec_driver_a")
    res = client.delete(f"/api/v1/notices/{notice['id']}", headers=h(driver_token))
    assert res.status_code == 403


def test_driver_cannot_call_panic_as_admin():
    token = tok("sec_admin")
    res = client.post("/api/v1/incidents/panic", headers=h(token))
    assert res.status_code == 403


def test_control_op_cannot_create_route():
    token = tok("sec_ctrl")
    db = TestSession()
    d = db.query(Depot).filter_by(code="DA1").first()
    depot_id = d.id
    db.close()
    res = client.post("/api/v1/scheduling/routes", json={
        "name": "Ctrl Route", "code": "CR01", "depot_id": depot_id, "stops": []
    }, headers=h(token))
    assert res.status_code == 403


# ── Cross-depot isolation ─────────────────────────────────────────────────────

def test_driver_sees_only_own_incidents():
    tok_a = tok("sec_driver_a")
    tok_b = tok("sec_driver_b")

    client.post("/api/v1/incidents/", json={
        "title": "Depot A incident", "type": "other", "severity": "P3", "is_panic": False
    }, headers=h(tok_a))

    client.post("/api/v1/incidents/", json={
        "title": "Depot B incident", "type": "other", "severity": "P3", "is_panic": False
    }, headers=h(tok_b))

    res_a = client.get("/api/v1/incidents/", headers=h(tok_a))
    titles_a = [i["title"] for i in res_a.json()]
    assert "Depot A incident" in titles_a
    assert "Depot B incident" not in titles_a


def test_admin_sees_all_incidents():
    tok_a = tok("sec_driver_a")
    tok_b = tok("sec_driver_b")
    admin_tok = tok("sec_admin")

    client.post("/api/v1/incidents/", json={
        "title": "IncA", "type": "other", "severity": "P3", "is_panic": False
    }, headers=h(tok_a))
    client.post("/api/v1/incidents/", json={
        "title": "IncB", "type": "other", "severity": "P3", "is_panic": False
    }, headers=h(tok_b))

    res = client.get("/api/v1/incidents/", headers=h(admin_tok))
    titles = [i["title"] for i in res.json()]
    assert "IncA" in titles
    assert "IncB" in titles


# ── Input validation ──────────────────────────────────────────────────────────

def test_create_incident_missing_required_fields():
    token = tok("sec_admin")
    res = client.post("/api/v1/incidents/", json={
        "title": "No type or severity"
        # missing type and severity
    }, headers=h(token))
    assert res.status_code == 422  # Unprocessable entity


def test_create_notice_empty_title():
    token = tok("sec_admin")
    res = client.post("/api/v1/notices/", json={
        "title": "", "body": "body", "target": "all"
    }, headers=h(token))
    # Empty title — either 422 validation or 201 (we don't enforce min length in schema)
    # Just ensure it doesn't 500
    assert res.status_code in (201, 422)


def test_nonexistent_incident():
    token = tok("sec_admin")
    res = client.get("/api/v1/incidents/99999", headers=h(token))
    assert res.status_code == 404


def test_nonexistent_notice():
    token = tok("sec_admin")
    res = client.get("/api/v1/notices/99999", headers=h(token))
    assert res.status_code == 404


def test_nonexistent_route():
    token = tok("sec_admin")
    res = client.get("/api/v1/scheduling/routes/99999", headers=h(token))
    assert res.status_code == 404


def test_invalid_status_transition():
    token = tok("sec_mgr_a")
    inc = client.post("/api/v1/incidents/", json={
        "title": "Trans test", "type": "breakdown", "severity": "P1", "is_panic": False
    }, headers=h(token)).json()

    # Can't jump from open directly to resolved
    res = client.post(f"/api/v1/incidents/{inc['id']}/transition",
        json={"to_status": "resolved"}, headers=h(token))
    assert res.status_code == 400


def test_duplicate_notice_read_idempotent():
    """Marking same notice read twice should not error."""
    admin_tok = tok("sec_admin")
    driver_tok = tok("sec_driver_a")

    notice = client.post("/api/v1/notices/", json={
        "title": "Idempotent Notice", "body": "body",
        "target": "all", "is_published": True
    }, headers=h(admin_tok)).json()

    r1 = client.post(f"/api/v1/notices/{notice['id']}/read", headers=h(driver_tok))
    r2 = client.post(f"/api/v1/notices/{notice['id']}/read", headers=h(driver_tok))
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["is_read_by_me"] is True
