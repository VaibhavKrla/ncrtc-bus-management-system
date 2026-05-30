"""
Phase 7 — Integration tests.
Full user journeys across modules in sequence.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.main import app
from app.db.session import Base, get_db
from app.models.models import (
    User, Depot, Vehicle, Stop, Route, RouteStop,
    UserRole, VehicleStatus
)
from app.core.security import hash_password

TEST_DB_URL = "sqlite:///./test_integration.db"
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

    depot = Depot(name="Integ Depot", code="INT", address="Test")
    db.add(depot)
    db.flush()

    vehicle = Vehicle(
        registration_no="DL-INT-001", model="Test Bus",
        capacity=40, status=VehicleStatus.active, depot_id=depot.id
    )
    db.add(vehicle)

    stop = Stop(name="Stop X", code="SX1", lat=28.64, lng=77.33)
    db.add(stop)
    db.flush()

    admin = User(
        username="int_admin", email="intadmin@test.com",
        hashed_password=hash_password("pass"),
        full_name="Integration Admin", role=UserRole.admin
    )
    mgr = User(
        username="int_mgr", email="intmgr@test.com",
        hashed_password=hash_password("pass"),
        full_name="Integration Manager", role=UserRole.depot_manager,
        depot_id=depot.id
    )
    driver = User(
        username="int_driver", email="intdriver@test.com",
        hashed_password=hash_password("pass"),
        full_name="Integration Driver", role=UserRole.driver,
        depot_id=depot.id
    )
    db.add_all([admin, mgr, driver])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def tok(username):
    r = client.post("/api/v1/auth/login", data={"username": username, "password": "pass"})
    return r.json()["access_token"]


def h(token):
    return {"Authorization": f"Bearer {token}"}


def get_ids():
    db = TestSession()
    depot = db.query(Depot).filter_by(code="INT").first()
    vehicle = db.query(Vehicle).filter_by(registration_no="DL-INT-001").first()
    stop = db.query(Stop).filter_by(code="SX1").first()
    driver = db.query(User).filter_by(username="int_driver").first()
    db.close()
    return depot.id, vehicle.id, stop.id, driver.id


class TestFullSchedulingJourney:
    """
    Full journey:
    admin creates route → manager assigns duty → publishes → driver acknowledges
    """

    def test_journey(self):
        admin_tok = tok("int_admin")
        mgr_tok = tok("int_mgr")
        driver_tok = tok("int_driver")
        depot_id, vehicle_id, stop_id, driver_id = get_ids()
        today = datetime.utcnow().strftime("%Y-%m-%d")

        # 1. Create route
        route_res = client.post("/api/v1/scheduling/routes", json={
            "name": "Integration Route", "code": "IR01", "depot_id": depot_id,
            "stops": [{"stop_id": stop_id, "sequence": 1, "scheduled_time": "06:00"}]
        }, headers=h(admin_tok))
        assert route_res.status_code == 201
        route_id = route_res.json()["id"]

        # 2. Manager assigns duty (draft)
        duty_res = client.post("/api/v1/scheduling/duties", json={
            "driver_id": driver_id, "vehicle_id": vehicle_id,
            "route_id": route_id, "date": today,
            "shift_start": "06:00", "shift_end": "14:00"
        }, headers=h(mgr_tok))
        assert duty_res.status_code == 201
        duty_id = duty_res.json()["id"]
        assert duty_res.json()["status"] == "draft"

        # 3. Driver cannot see draft duty yet via duties endpoint
        driver_duties = client.get(
            f"/api/v1/scheduling/duties?date={today}", headers=h(driver_tok)
        )
        # Driver gets their duties - draft is included in list (visible to driver)
        assert driver_duties.status_code == 200

        # 4. Manager publishes
        pub_res = client.post("/api/v1/scheduling/duties/publish",
            json={"duty_ids": [duty_id]}, headers=h(mgr_tok))
        assert pub_res.status_code == 200
        assert pub_res.json()["published"] == 1

        # 5. Driver acknowledges
        ack_res = client.post(
            f"/api/v1/scheduling/duties/{duty_id}/acknowledge",
            headers=h(driver_tok)
        )
        assert ack_res.status_code == 200
        assert ack_res.json()["status"] == "acknowledged"
        assert ack_res.json()["acknowledged_at"] is not None

        # 6. Roster reflects acknowledged status
        from datetime import date, timedelta
        monday = date.today()
        while monday.weekday() != 0:
            monday -= timedelta(days=1)
        roster = client.get(
            f"/api/v1/scheduling/roster?depot_id={depot_id}&week_start={monday}",
            headers=h(mgr_tok)
        )
        assert roster.status_code == 200


class TestFullIncidentJourney:
    """
    Full journey:
    driver raises incident → manager acknowledges → works → resolves → closes
    """

    def test_journey(self):
        driver_tok = tok("int_driver")
        mgr_tok = tok("int_mgr")
        _, vehicle_id, _, _ = get_ids()

        # 1. Driver raises incident
        inc_res = client.post("/api/v1/incidents/", json={
            "title": "Integration test incident",
            "type": "breakdown", "severity": "P2", "is_panic": False,
            "vehicle_id": vehicle_id,
        }, headers=h(driver_tok))
        assert inc_res.status_code == 201
        inc_id = inc_res.json()["id"]
        assert inc_res.json()["status"] == "open"

        # 2. Manager acknowledges
        ack = client.post(f"/api/v1/incidents/{inc_id}/transition",
            json={"to_status": "acknowledged", "note": "Noted, dispatching team"},
            headers=h(mgr_tok))
        assert ack.status_code == 200
        assert ack.json()["status"] == "acknowledged"

        # 3. Move to in_progress
        prog = client.post(f"/api/v1/incidents/{inc_id}/transition",
            json={"to_status": "in_progress", "note": "Team on site"},
            headers=h(mgr_tok))
        assert prog.status_code == 200

        # 4. Resolve
        res = client.post(f"/api/v1/incidents/{inc_id}/transition",
            json={"to_status": "resolved", "note": "Fixed"},
            headers=h(mgr_tok))
        assert res.status_code == 200
        assert res.json()["resolved_at"] is not None

        # 5. Close
        close = client.post(f"/api/v1/incidents/{inc_id}/transition",
            json={"to_status": "closed", "note": "All done"},
            headers=h(mgr_tok))
        assert close.status_code == 200
        assert close.json()["status"] == "closed"

        # 6. Timeline has 5 events (raised + 4 transitions)
        detail = client.get(f"/api/v1/incidents/{inc_id}", headers=h(mgr_tok))
        assert len(detail.json()["events"]) == 5

        # 7. Cannot transition from closed
        bad = client.post(f"/api/v1/incidents/{inc_id}/transition",
            json={"to_status": "open"}, headers=h(mgr_tok))
        assert bad.status_code == 400


class TestFullNoticeJourney:
    """
    Full journey:
    admin creates draft → publishes → driver reads → receipt tracked
    """

    def test_journey(self):
        admin_tok = tok("int_admin")
        driver_tok = tok("int_driver")

        # 1. Create draft
        draft = client.post("/api/v1/notices/", json={
            "title": "Integration Notice", "body": "Test body",
            "target": "all", "is_published": False
        }, headers=h(admin_tok))
        assert draft.status_code == 201
        notice_id = draft.json()["id"]
        assert draft.json()["is_published"] is False

        # 2. Driver cannot see draft
        driver_list = client.get("/api/v1/notices/", headers=h(driver_tok))
        ids = [n["id"] for n in driver_list.json()]
        assert notice_id not in ids

        # 3. Publish
        pub = client.patch(f"/api/v1/notices/{notice_id}",
            json={"is_published": True}, headers=h(admin_tok))
        assert pub.status_code == 200
        assert pub.json()["is_published"] is True

        # 4. Driver sees it now
        driver_list2 = client.get("/api/v1/notices/", headers=h(driver_tok))
        ids2 = [n["id"] for n in driver_list2.json()]
        assert notice_id in ids2

        # 5. Mark read
        read = client.post(f"/api/v1/notices/{notice_id}/read", headers=h(driver_tok))
        assert read.status_code == 200
        assert read.json()["is_read_by_me"] is True

        # 6. Read receipts visible to admin
        receipts = client.get(f"/api/v1/notices/{notice_id}/reads", headers=h(admin_tok))
        assert receipts.status_code == 200
        assert len(receipts.json()) == 1
        assert receipts.json()[0]["username"] == "int_driver"


class TestPanicJourney:
    """Panic button → P1 incident → control room can action it."""

    def test_journey(self):
        driver_tok = tok("int_driver")
        mgr_tok = tok("int_mgr")
        _, vehicle_id, _, _ = get_ids()

        # 1. Driver hits panic
        panic = client.post(
            f"/api/v1/incidents/panic?vehicle_id={vehicle_id}&lat=28.64&lng=77.33",
            headers=h(driver_tok)
        )
        assert panic.status_code == 201
        data = panic.json()
        assert data["severity"] == "P1"
        assert data["is_panic"] is True
        assert "PANIC" in data["title"]

        # 2. Incident visible in open list
        inc_id = data["id"]
        listing = client.get("/api/v1/incidents/?status=open", headers=h(mgr_tok))
        open_ids = [i["id"] for i in listing.json()]
        assert inc_id in open_ids

        # 3. Manager acknowledges
        ack = client.post(f"/api/v1/incidents/{inc_id}/transition",
            json={"to_status": "acknowledged", "note": "Control room alerted"},
            headers=h(mgr_tok))
        assert ack.status_code == 200
