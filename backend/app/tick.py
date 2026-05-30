"""
Tick script — runs as a separate container.
Every 5 seconds, inserts a GPS ping for each active vehicle,
simulating real bus movement along their routes.
Also runs SLA breach monitor every 60s in a background thread.
"""
import time
import random
import math
import threading
from datetime import datetime

from app.db.session import SessionLocal
from app.models.models import Vehicle, GpsPing, VehicleStatus


def move_coordinate(lat: float, lng: float, heading: float, speed_kmh: float) -> tuple:
    """Move a coordinate by ~5 seconds of movement at given speed/heading."""
    distance_km = (speed_kmh / 3600) * 5  # 5 second tick
    delta_lat = (distance_km / 111.0) * math.cos(math.radians(heading))
    delta_lng = (distance_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(math.radians(heading))
    new_lat = lat + delta_lat + random.uniform(-0.0002, 0.0002)
    new_lng = lng + delta_lng + random.uniform(-0.0002, 0.0002)
    # Clamp to Delhi-NCR bounding box
    new_lat = max(28.40, min(28.80, new_lat))
    new_lng = max(77.00, min(77.55, new_lng))
    return round(new_lat, 6), round(new_lng, 6)


def run():
    print("🚌 Tick script started — inserting GPS pings every 5s")
    print("🕐 SLA monitor thread starting...")

    # Start SLA monitor in background thread
    from app.services.sla_monitor import run_sla_monitor
    sla_thread = threading.Thread(target=run_sla_monitor, daemon=True)
    sla_thread.start()

    db = SessionLocal()

    # Track current position + heading per vehicle
    vehicle_state: dict = {}

    try:
        while True:
            vehicles = db.query(Vehicle).filter(
                Vehicle.status == VehicleStatus.active
            ).all()

            for vehicle in vehicles:
                if vehicle.id not in vehicle_state:
                    # Initialize from last known ping, or depot coords
                    last = (
                        db.query(GpsPing)
                        .filter(GpsPing.vehicle_id == vehicle.id)
                        .order_by(GpsPing.ts.desc())
                        .first()
                    )
                    if last:
                        vehicle_state[vehicle.id] = {
                            "lat": last.lat, "lng": last.lng,
                            "heading": last.heading or random.uniform(0, 360),
                            "speed": last.speed_kmh or random.uniform(10, 35),
                        }
                    else:
                        vehicle_state[vehicle.id] = {
                            "lat": 28.64 + random.uniform(-0.05, 0.05),
                            "lng": 77.33 + random.uniform(-0.05, 0.05),
                            "heading": random.uniform(0, 360),
                            "speed": random.uniform(10, 35),
                        }

                state = vehicle_state[vehicle.id]
                # Slightly vary speed and heading each tick
                state["speed"] = max(0, min(60, state["speed"] + random.uniform(-3, 3)))
                state["heading"] = (state["heading"] + random.uniform(-10, 10)) % 360

                new_lat, new_lng = move_coordinate(
                    state["lat"], state["lng"], state["heading"], state["speed"]
                )
                state["lat"], state["lng"] = new_lat, new_lng

                ping = GpsPing(
                    vehicle_id=vehicle.id,
                    lat=new_lat, lng=new_lng,
                    speed_kmh=round(state["speed"], 1),
                    heading=round(state["heading"], 1),
                    ts=datetime.utcnow(),
                )
                db.add(ping)

            db.commit()
            time.sleep(5)

    except KeyboardInterrupt:
        print("Tick script stopped.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
