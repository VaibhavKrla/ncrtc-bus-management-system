"""
Full seed script — runs automatically on docker compose up.
3 depots · 15 vehicles · 24 users (all roles) · 10 stops · 5 routes
7 days of duties · 2hrs GPS history per vehicle · 8 incidents · 5 notices
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.models.models import (
    Depot, Vehicle, User, Stop, Route, RouteStop,
    Duty, GpsPing, Incident, IncidentEvent, Notice, NoticeRead,
    UserRole, VehicleStatus, DutyStatus,
    IncidentType, IncidentSeverity, IncidentStatus, NoticeTarget
)
from app.core.security import hash_password

# ── NCR geo data ──────────────────────────────────────────────────────────────
DEPOTS = [
    {"name": "Anand Vihar Depot",    "code": "AVD", "address": "Anand Vihar, Delhi",    "lat": 28.6450, "lng": 77.3152},
    {"name": "Sahibabad Depot",       "code": "SBD", "address": "Sahibabad, Ghaziabad",  "lat": 28.6692, "lng": 77.3562},
    {"name": "Noida Sector 62 Depot", "code": "N62", "address": "Sector 62, Noida",      "lat": 28.6274, "lng": 77.3717},
]

STOPS_DATA = [
    {"name": "Anand Vihar ISBT",   "code": "AVI", "lat": 28.6462, "lng": 77.3155},
    {"name": "Kaushambi",          "code": "KAU", "lat": 28.6430, "lng": 77.3218},
    {"name": "Vaishali",           "code": "VAI", "lat": 28.6452, "lng": 77.3376},
    {"name": "Sahibabad",          "code": "SAH", "lat": 28.6688, "lng": 77.3558},
    {"name": "Raj Nagar Extn",     "code": "RNE", "lat": 28.6801, "lng": 77.4211},
    {"name": "Noida Sector 62",    "code": "N62", "lat": 28.6274, "lng": 77.3717},
    {"name": "Noida Sector 52",    "code": "N52", "lat": 28.6179, "lng": 77.3600},
    {"name": "Noida City Centre",  "code": "NCC", "lat": 28.5740, "lng": 77.3590},
    {"name": "Mohan Nagar",        "code": "MOH", "lat": 28.6903, "lng": 77.4020},
    {"name": "Indirapuram",        "code": "IND", "lat": 28.6417, "lng": 77.3697},
]

VEHICLE_MODELS = ["Tata Starbus", "Ashok Leyland Viking", "Volvo B7R", "Force Traveller", "Eicher Skyline"]
DRIVER_NAMES = [
    "Ramesh Kumar","Suresh Singh","Amit Sharma","Vijay Yadav","Rajesh Gupta",
    "Deepak Verma","Manoj Tiwari","Santosh Patel","Arun Mishra","Praveen Nair",
    "Harish Joshi","Dinesh Chauhan","Rakesh Pandey","Sanjay Dubey","Ajay Shukla",
]
CONDUCTOR_NAMES = ["Mohan Das","Ravi Kumar","Sonu Singh","Pankaj Rao","Geeta Devi"]

ROUTE_DEFS = [
    {"name": "Anand Vihar–Vaishali Express", "code": "R001", "depot_idx": 0, "stop_ids": [0,1,2],      "times": ["06:00","06:25","06:50"]},
    {"name": "Sahibabad–Raj Nagar Loop",     "code": "R002", "depot_idx": 1, "stop_ids": [3,8,4],      "times": ["06:00","06:30","07:00"]},
    {"name": "Noida 62–City Centre",         "code": "R003", "depot_idx": 2, "stop_ids": [5,6,7],      "times": ["06:00","06:25","06:55"]},
    {"name": "Indirapuram Circular",         "code": "R004", "depot_idx": 1, "stop_ids": [9,2,3],      "times": ["07:00","07:30","07:55"]},
    {"name": "AV–Noida Cross",               "code": "R005", "depot_idx": 0, "stop_ids": [0,9,6,7],   "times": ["07:30","07:55","08:20","08:45"]},
]

INCIDENTS_DATA = [
    {"title":"Engine overheating — R001","type":IncidentType.breakdown,"sev":IncidentSeverity.P1,"status":IncidentStatus.in_progress,"panic":False,"hrs_ago":3},
    {"title":"Passenger complaint — rude behaviour","type":IncidentType.complaint,"sev":IncidentSeverity.P3,"status":IncidentStatus.open,"panic":False,"hrs_ago":12},
    {"title":"Minor collision at Kaushambi junction","type":IncidentType.accident,"sev":IncidentSeverity.P2,"status":IncidentStatus.acknowledged,"panic":False,"hrs_ago":6},
    {"title":"PANIC: Driver emergency on R003","type":IncidentType.breakdown,"sev":IncidentSeverity.P1,"status":IncidentStatus.resolved,"panic":True,"hrs_ago":24},
    {"title":"Flat tyre — DL-05 vehicle","type":IncidentType.breakdown,"sev":IncidentSeverity.P2,"status":IncidentStatus.closed,"panic":False,"hrs_ago":48},
    {"title":"AC not working — passenger discomfort","type":IncidentType.other,"sev":IncidentSeverity.P3,"status":IncidentStatus.open,"panic":False,"hrs_ago":2},
    {"title":"Bus breakdown on NH-9","type":IncidentType.breakdown,"sev":IncidentSeverity.P1,"status":IncidentStatus.acknowledged,"panic":False,"hrs_ago":1},
    {"title":"Windshield crack reported","type":IncidentType.other,"sev":IncidentSeverity.P2,"status":IncidentStatus.open,"panic":False,"hrs_ago":5},
]

NOTICES_DATA = [
    {"title":"Mandatory safety drill — 15 Jan 2025",
     "body":"All drivers and conductors must attend the mandatory safety drill at their respective depots on 15 January 2025 at 09:00 AM. Attendance is compulsory. Absentees will be marked accordingly.",
     "target":NoticeTarget.all},
    {"title":"New uniform policy — effective 1 Feb 2025",
     "body":"As per NCRTC directive dated 10 Dec 2024, all field staff must wear the updated uniform from 1st February 2025 onwards. New uniforms are available at depot stores. Please collect by 28 January.",
     "target":NoticeTarget.role},
    {"title":"Anand Vihar depot — gate change",
     "body":"The main entry gate for Anand Vihar depot is changed to Gate 3 effective immediately due to ongoing construction work near Gate 1. All vehicles must use Gate 3 until further notice.",
     "target":NoticeTarget.depot},
    {"title":"Republic Day operations — 26 January",
     "body":"Operations on 26 January will run on a special reduced schedule. Duty rosters have been updated. Please check your assignments carefully. Additional incentive pay applicable for Republic Day duties.",
     "target":NoticeTarget.all},
    {"title":"GPS device maintenance reminder",
     "body":"All drivers are reminded to report any GPS device malfunction immediately to the depot control room. Do not attempt to repair devices yourself. Faulty device reporting ensures accurate tracking.",
     "target":NoticeTarget.role},
]


def seed():
    db = SessionLocal()
    try:
        if db.query(Depot).count() > 0:
            print("✅ Already seeded — skipping.")
            return

        print("🌱 Seeding full database...")

        # ── 1. Depots ─────────────────────────────────────────────────────────
        depots = []
        for d in DEPOTS:
            depot = Depot(name=d["name"], code=d["code"], address=d["address"])
            db.add(depot)
            depots.append(depot)
        db.flush()
        print(f"   ✓ {len(depots)} depots")

        # ── 2. Vehicles (5 per depot = 15 total) ─────────────────────────────
        vehicles = []
        all_depot_vehicles = {}
        reg = 1
        for depot in depots:
            dvs = []
            for i in range(5):
                v = Vehicle(
                    registration_no=f"DL-{reg:02d}-NC-{1000+reg}",
                    model=random.choice(VEHICLE_MODELS),
                    capacity=random.choice([32, 40, 45]),
                    status=VehicleStatus.active,
                    depot_id=depot.id,
                )
                db.add(v)
                vehicles.append(v)
                dvs.append(v)
                reg += 1
            all_depot_vehicles[depot.id] = dvs
        db.flush()
        print(f"   ✓ {len(vehicles)} vehicles")

        # ── 3. Users ──────────────────────────────────────────────────────────
        # Admin + 2 control operators (no depot)
        admin = User(username="admin", email="admin@ncrtc.in",
                     hashed_password=hash_password("admin123"),
                     full_name="System Administrator", role=UserRole.admin)
        db.add(admin)

        ctrl_users = []
        for i in range(2):
            u = User(username=f"control{i+1}", email=f"control{i+1}@ncrtc.in",
                     hashed_password=hash_password("control123"),
                     full_name=f"Control Operator {i+1}", role=UserRole.control_operator)
            db.add(u)
            ctrl_users.append(u)
        db.flush()

        # Per depot: 1 manager + 5 drivers + 1 conductor
        depot_managers, all_drivers, all_conductors = [], [], []
        drivers_by_depot = {}
        driver_name_idx = 0
        conductor_name_idx = 0

        for depot in depots:
            mgr = User(
                username=f"mgr_{depot.code.lower()}",
                email=f"mgr_{depot.code.lower()}@ncrtc.in",
                hashed_password=hash_password("manager123"),
                full_name=f"Manager {depot.name.split()[0]}",
                role=UserRole.depot_manager, depot_id=depot.id
            )
            db.add(mgr)
            depot_managers.append(mgr)

            drivers = []
            for j in range(5):
                name = DRIVER_NAMES[driver_name_idx % len(DRIVER_NAMES)]
                driver_name_idx += 1
                uname = f"driver_{depot.code.lower()}_{j+1}"
                d = User(
                    username=uname, email=f"{uname}@ncrtc.in",
                    hashed_password=hash_password("driver123"),
                    full_name=name, role=UserRole.driver, depot_id=depot.id
                )
                db.add(d)
                drivers.append(d)
                all_drivers.append(d)
            drivers_by_depot[depot.id] = drivers

            cname = CONDUCTOR_NAMES[conductor_name_idx % len(CONDUCTOR_NAMES)]
            conductor_name_idx += 1
            cond = User(
                username=f"cond_{depot.code.lower()}_1",
                email=f"cond_{depot.code.lower()}_1@ncrtc.in",
                hashed_password=hash_password("cond123"),
                full_name=cname, role=UserRole.conductor, depot_id=depot.id
            )
            db.add(cond)
            all_conductors.append(cond)

        db.flush()
        total_users = 1 + 2 + len(depots)*7
        print(f"   ✓ {total_users} users")

        # ── 4. Stops ──────────────────────────────────────────────────────────
        stops = []
        for s in STOPS_DATA:
            stop = Stop(name=s["name"], code=s["code"], lat=s["lat"], lng=s["lng"])
            db.add(stop)
            stops.append(stop)
        db.flush()
        print(f"   ✓ {len(stops)} stops")

        # ── 5. Routes ─────────────────────────────────────────────────────────
        routes = []
        depot_routes = {d.id: [] for d in depots}
        for rd in ROUTE_DEFS:
            depot = depots[rd["depot_idx"]]
            route = Route(name=rd["name"], code=rd["code"], depot_id=depot.id)
            db.add(route)
            db.flush()
            for seq, (stop_idx, t) in enumerate(zip(rd["stop_ids"], rd["times"])):
                rs = RouteStop(route_id=route.id, stop_id=stops[stop_idx].id,
                               sequence=seq+1, scheduled_time=t)
                db.add(rs)
            routes.append(route)
            depot_routes[depot.id].append(route)
        db.flush()
        print(f"   ✓ {len(routes)} routes")

        # ── 6. Duties — 7 days (past 3 + today + future 3) ───────────────────
        shifts = [("06:00","14:00"),("14:00","22:00"),("22:00","06:00")]
        today = datetime.utcnow().date()
        duties_created = 0

        for day_offset in range(-3, 4):
            day = today + timedelta(days=day_offset)
            day_str = str(day)
            for depot in depots:
                dvs = all_depot_vehicles[depot.id]
                drs = drivers_by_depot[depot.id]
                rts = depot_routes[depot.id]
                if not rts:
                    continue
                for idx, driver in enumerate(drs):
                    vehicle = dvs[idx % len(dvs)]
                    route = rts[idx % len(rts)]
                    shift = shifts[idx % len(shifts)]
                    if day_offset < 0:
                        status = DutyStatus.acknowledged
                        ack_at = datetime(day.year, day.month, day.day, 5, 30)
                    elif day_offset == 0:
                        status = DutyStatus.acknowledged if idx < 3 else DutyStatus.published
                        ack_at = datetime(day.year, day.month, day.day, 5, 30) if idx < 3 else None
                    else:
                        status = DutyStatus.published
                        ack_at = None
                    duty = Duty(
                        driver_id=driver.id, vehicle_id=vehicle.id,
                        route_id=route.id, date=day_str,
                        shift_start=shift[0], shift_end=shift[1],
                        status=status, acknowledged_at=ack_at,
                        created_by_id=admin.id
                    )
                    db.add(duty)
                    duties_created += 1
        db.flush()
        print(f"   ✓ {duties_created} duties (7 days × 3 depots × 5 drivers)")

        # ── 7. GPS pings — 2 hrs history per vehicle, every 2 min ────────────
        ping_count = 0
        for vehicle in vehicles:
            depot_data = next(d for d in DEPOTS if d["code"] == next(
                dep.code for dep in depots if dep.id == vehicle.depot_id))
            blat, blng = depot_data["lat"], depot_data["lng"]
            clat, clng = blat + random.uniform(-0.02, 0.02), blng + random.uniform(-0.02, 0.02)
            heading = random.uniform(0, 360)
            speed = random.uniform(15, 40)
            for mins_ago in range(120, 0, -2):
                heading = (heading + random.uniform(-8, 8)) % 360
                speed = max(0, min(55, speed + random.uniform(-3, 3)))
                import math
                dist = (speed / 3600) * 120
                clat += (dist / 111.0) * math.cos(math.radians(heading)) + random.uniform(-0.0003, 0.0003)
                clng += (dist / (111.0 * math.cos(math.radians(clat)))) * math.sin(math.radians(heading)) + random.uniform(-0.0003, 0.0003)
                clat = max(28.40, min(28.85, clat))
                clng = max(77.00, min(77.55, clng))
                ping = GpsPing(
                    vehicle_id=vehicle.id,
                    lat=round(clat, 6), lng=round(clng, 6),
                    speed_kmh=round(speed, 1), heading=round(heading, 1),
                    ts=datetime.utcnow() - timedelta(minutes=mins_ago)
                )
                db.add(ping)
                ping_count += 1
        db.flush()
        print(f"   ✓ {ping_count} GPS pings ({ping_count//len(vehicles)} per vehicle)")

        # ── 8. Incidents ──────────────────────────────────────────────────────
        STATUS_FLOW = {
            IncidentStatus.open: [],
            IncidentStatus.acknowledged: [IncidentStatus.acknowledged],
            IncidentStatus.in_progress: [IncidentStatus.acknowledged, IncidentStatus.in_progress],
            IncidentStatus.resolved: [IncidentStatus.acknowledged, IncidentStatus.in_progress, IncidentStatus.resolved],
            IncidentStatus.closed: [IncidentStatus.acknowledged, IncidentStatus.in_progress, IncidentStatus.resolved, IncidentStatus.closed],
        }
        for i, inc_d in enumerate(INCIDENTS_DATA):
            depot = depots[i % len(depots)]
            mgr = depot_managers[i % len(depot_managers)]
            driver = drivers_by_depot[depot.id][0]
            created = datetime.utcnow() - timedelta(hours=inc_d["hrs_ago"])
            inc = Incident(
                title=inc_d["title"], type=inc_d["type"],
                severity=inc_d["sev"], status=inc_d["status"],
                vehicle_id=vehicles[i % len(vehicles)].id,
                depot_id=depot.id, raised_by_id=driver.id,
                assigned_to_id=mgr.id,
                lat=round(28.62 + random.uniform(-0.05, 0.05), 6),
                lng=round(77.33 + random.uniform(-0.05, 0.05), 6),
                is_panic=inc_d["panic"],
                created_at=created,
                resolved_at=created + timedelta(hours=2) if inc_d["status"] in (IncidentStatus.resolved, IncidentStatus.closed) else None
            )
            db.add(inc)
            db.flush()

            # Seed event log matching status
            event_time = created
            db.add(IncidentEvent(incident_id=inc.id, user_id=driver.id,
                                  to_status=IncidentStatus.open,
                                  note="Incident raised" + (" via PANIC" if inc_d["panic"] else ""),
                                  created_at=event_time))
            for st in STATUS_FLOW[inc_d["status"]]:
                event_time += timedelta(minutes=random.randint(10, 45))
                db.add(IncidentEvent(incident_id=inc.id, user_id=mgr.id,
                                      from_status=IncidentStatus.open if st == IncidentStatus.acknowledged else None,
                                      to_status=st, note=f"Status updated to {st.value}",
                                      created_at=event_time))
        db.flush()
        print(f"   ✓ {len(INCIDENTS_DATA)} incidents")

        # ── 9. Notices ────────────────────────────────────────────────────────
        for i, nd in enumerate(NOTICES_DATA):
            notice = Notice(
                title=nd["title"], body=nd["body"], target=nd["target"],
                target_depot_id=depots[0].id if nd["target"] == NoticeTarget.depot else None,
                target_role=UserRole.driver if nd["target"] == NoticeTarget.role else None,
                is_published=True,
                published_at=datetime.utcnow() - timedelta(days=i+1),
                created_by_id=admin.id
            )
            db.add(notice)
            db.flush()
            # 2–3 drivers have read each notice
            readers = random.sample(all_drivers, min(3, len(all_drivers)))
            for r in readers:
                db.add(NoticeRead(notice_id=notice.id, user_id=r.id,
                                   read_at=datetime.utcnow() - timedelta(hours=random.randint(1, 20))))
        db.flush()
        print(f"   ✓ {len(NOTICES_DATA)} notices")

        db.commit()
        print("\n✅ Seed complete!\n")
        print("Demo credentials:")
        print("  admin          / admin123    (System Admin)")
        print("  control1       / control123  (Control Operator)")
        print("  mgr_avd        / manager123  (Depot Manager — Anand Vihar)")
        print("  mgr_sbd        / manager123  (Depot Manager — Sahibabad)")
        print("  driver_avd_1   / driver123   (Driver — Anand Vihar)")
        print("  driver_sbd_1   / driver123   (Driver — Sahibabad)")
        print("  driver_n62_1   / driver123   (Driver — Noida 62)")
        print("  cond_avd_1     / cond123     (Conductor)")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        import traceback; traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
