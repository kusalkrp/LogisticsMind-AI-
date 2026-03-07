"""Fleet data generators: vehicles, drivers, routes, trips, gps_pings, maintenance_logs."""
import random
import uuid
import json
from datetime import datetime, timedelta

SL_FIRST_NAMES = [
    "Ashan", "Kamal", "Nimal", "Saman", "Ruwan", "Dinesh", "Pradeep", "Chaminda",
    "Nuwan", "Lakshan", "Dilshan", "Thilina", "Kasun", "Sajith", "Mahela",
    "Bandula", "Roshan", "Suresh", "Jagath", "Ranjith", "Lalith", "Kapila",
    "Asanka", "Wimal", "Ajith"
]
SL_LAST_NAMES = [
    "Perera", "Silva", "Fernando", "Jayawardena", "Wickramasinghe", "Bandara",
    "Dissanayake", "Gunasekara", "Rathnayake", "Samaraweera", "Herath",
    "Amarasinghe", "Wijesinghe"
]

VEHICLE_TYPES = ["lorry", "van", "motorbike", "refrigerated_truck", "container"]
VEHICLE_MAKES = ["TATA", "Ashok Leyland", "Isuzu", "Mitsubishi", "Toyota", "Mahindra", "Daihatsu"]
FUEL_TYPES = ["diesel", "petrol", "electric", "hybrid"]
VEHICLE_STATUSES = ["active", "active", "active", "active", "maintenance", "retired", "breakdown"]
LICENSE_TYPES = ["B1", "B2", "C1", "CE"]
ROUTE_TYPES = ["express", "standard", "rural", "cross_province"]
TRIP_STATUSES_WEIGHTED = (
    ["completed"] * 90 + ["cancelled"] * 5 + ["breakdown"] * 5
)
SERVICE_TYPES = ["oil_change", "tyre", "engine", "electrical", "body"]


async def seed_fleet(conn):
    """Seed all fleet schema tables."""
    # Get facility and district IDs
    facilities = await conn.fetch("SELECT id, code FROM warehouse.facilities")
    facility_ids = [r["id"] for r in facilities]
    districts = await conn.fetch("SELECT id, name FROM core.districts ORDER BY id")
    district_map = {r["name"]: r["id"] for r in districts}
    district_ids = [r["id"] for r in districts]
    vendor_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.vendors WHERE vendor_type = 'maintenance'")]
    if not vendor_ids:
        vendor_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.vendors LIMIT 30")]

    # 1. Vehicles (200) — include VH-0031 and VH-0089
    print("  Inserting 200 vehicles...")
    vehicles = []
    for i in range(200):
        vid = uuid.uuid4()
        plate = f"VH-{i+1:04d}"
        vtype = random.choice(VEHICLE_TYPES)
        vehicles.append((
            vid, plate, vtype,
            random.choice(VEHICLE_MAKES),
            f"Model-{random.choice(['X','Y','Z','A','B'])}{random.randint(100,999)}",
            random.randint(2015, 2024),
            round(random.uniform(500, 20000), 2),
            round(random.uniform(5, 80), 2),
            vtype == "refrigerated_truck",
            True,
            random.choice(FUEL_TYPES),
            random.choice(facility_ids),
            random.choice(VEHICLE_STATUSES),
            (datetime.now() - timedelta(days=random.randint(30, 180))).date(),
            (datetime.now() + timedelta(days=random.randint(30, 180))).date(),
            (datetime.now() - timedelta(days=random.randint(365, 2500))).date(),
            random.randint(10000, 500000)
        ))
    await conn.executemany(
        """INSERT INTO fleet.vehicles (id, plate_no, vehicle_type, make, model, year,
           capacity_kg, capacity_m3, has_cold_chain, has_gps, fuel_type, base_facility,
           status, last_service_at, next_service_at, purchased_at, mileage_km)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)""",
        vehicles
    )
    vehicle_ids = [v[0] for v in vehicles]
    vehicle_plate_map = {v[1]: v[0] for v in vehicles}

    # 2. Drivers (180) — include DRV-0042
    print("  Inserting 180 drivers...")
    drivers = []
    for i in range(180):
        did = uuid.uuid4()
        emp_id = f"DRV-{i+1:04d}"
        drivers.append((
            did, emp_id,
            f"{random.choice(SL_FIRST_NAMES)} {random.choice(SL_LAST_NAMES)}",
            f"LIC-{random.randint(100000, 999999)}",
            random.choice(LICENSE_TYPES),
            (datetime.now() + timedelta(days=random.randint(30, 730))).date(),
            f"+94{random.randint(70,79)}{random.randint(1000000,9999999)}",
            random.choice(district_ids),
            random.choice(facility_ids),
            round(random.uniform(3.0, 5.0), 2),
            0,  # total_trips updated after trips are created
            (datetime.now() - timedelta(days=random.randint(180, 2500))).date(),
            random.random() > 0.05
        ))
    await conn.executemany(
        """INSERT INTO fleet.drivers (id, employee_id, name, license_no, license_type,
           license_expiry, phone, district_id, base_facility, rating, total_trips, hired_at, is_active)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
        drivers
    )
    driver_ids = [d[0] for d in drivers]
    driver_emp_map = {d[1]: d[0] for d in drivers}

    # 3. Routes (80) — include RT-COL-JAF-003
    print("  Inserting 80 routes...")
    routes = []
    route_ids = []
    # Pre-define RT-COL-JAF-003
    colombo_id = district_map["Colombo"]
    jaffna_id = district_map["Jaffna"]

    district_pairs = set()
    # Ensure RT-COL-JAF-003 exists
    district_pairs.add((colombo_id, jaffna_id))

    while len(district_pairs) < 80:
        orig = random.choice(district_ids)
        dest = random.choice(district_ids)
        if orig != dest:
            district_pairs.add((orig, dest))

    for idx, (orig, dest) in enumerate(district_pairs):
        rid = uuid.uuid4()
        route_ids.append(rid)
        if orig == colombo_id and dest == jaffna_id and idx == 0:
            code = "RT-COL-JAF-003"
            name = "Colombo to Jaffna Express"
            rtype = "cross_province"
            distance = 398.0
            duration = 8.5
        else:
            orig_name = next(d["name"][:3].upper() for d in districts if d["id"] == orig)
            dest_name = next(d["name"][:3].upper() for d in districts if d["id"] == dest)
            code = f"RT-{orig_name}-{dest_name}-{idx+1:03d}"
            name = f"Route {code}"
            rtype = random.choice(ROUTE_TYPES)
            distance = round(random.uniform(30, 500), 2)
            duration = round(distance / random.uniform(40, 60), 2)

        routes.append((
            rid, code, name, orig, dest, distance, duration, rtype,
            json.dumps([]), True
        ))

    await conn.executemany(
        """INSERT INTO fleet.routes (id, code, name, origin_district, dest_district,
           distance_km, est_duration_hr, route_type, waypoints, is_active)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
        routes
    )

    # 4. Trips (15,000) over 2 years
    print("  Inserting 15,000 trips...")
    trips = []
    trip_ids = []
    now = datetime.now()
    for i in range(15000):
        tid = uuid.uuid4()
        trip_ids.append(tid)

        # Seasonal weighting: more trips Oct-Jan
        days_back = random.randint(0, 730)
        trip_date = (now - timedelta(days=days_back)).date()
        month = trip_date.month
        if month in [10, 11, 12, 1] and random.random() < 0.3:
            # Increase density for high season
            days_back = random.randint(0, 730)
            trip_date = (now - timedelta(days=days_back)).date()

        route = random.choice(routes)
        route_distance = float(route[5])
        route_duration = float(route[6])
        status = random.choice(TRIP_STATUSES_WEIGHTED)

        sched_depart = datetime.combine(trip_date, datetime.min.time()) + timedelta(hours=random.randint(5, 18))
        actual_depart = sched_depart + timedelta(minutes=random.randint(-15, 60))
        sched_arrive = sched_depart + timedelta(hours=route_duration)

        if status == "completed":
            # ~85% on-time baseline; anomalous routes fixed by anomalies.py after seeding
            delay = random.uniform(-1.5, 0.5) if random.random() < 0.85 else random.uniform(0.5, 4.0)
            actual_arrive = sched_arrive + timedelta(hours=delay)
        else:
            actual_arrive = None

        fuel_per_km = random.uniform(0.08, 0.15)
        distance_actual = route_distance * random.uniform(0.95, 1.1) if status == "completed" else None
        fuel_used = round(distance_actual * fuel_per_km, 2) if distance_actual else None
        fuel_cost = round(fuel_used * random.uniform(350, 420), 2) if fuel_used else None

        trips.append((
            tid, route[0], random.choice(vehicle_ids), random.choice(driver_ids),
            trip_date, sched_depart, actual_depart if status != "cancelled" else None,
            sched_arrive, actual_arrive, status,
            round(distance_actual, 2) if distance_actual else None,
            fuel_used, fuel_cost,
            round(random.uniform(0, 500), 2) if status == "completed" else None,
            None
        ))

        if len(trips) >= 1000:
            await conn.executemany(
                """INSERT INTO fleet.trips (id, route_id, vehicle_id, driver_id, trip_date,
                   scheduled_depart, actual_depart, scheduled_arrive, actual_arrive, status,
                   distance_actual_km, fuel_used_l, fuel_cost, toll_cost, notes)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
                trips
            )
            trips = []
            if (i + 1) % 5000 == 0:
                print(f"    {i+1:,} trips...")
    if trips:
        await conn.executemany(
            """INSERT INTO fleet.trips (id, route_id, vehicle_id, driver_id, trip_date,
               scheduled_depart, actual_depart, scheduled_arrive, actual_arrive, status,
               distance_actual_km, fuel_used_l, fuel_cost, toll_cost, notes)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
            trips
        )

    # 5. GPS pings (500,000) — ~33 per completed trip
    print("  Inserting 500,000 GPS pings (this may take a while)...")
    completed_trips = await conn.fetch(
        """SELECT id, actual_depart, actual_arrive FROM fleet.trips
           WHERE status = 'completed' AND actual_depart IS NOT NULL AND actual_arrive IS NOT NULL
           LIMIT 15200"""
    )

    batch = []
    ping_count = 0
    for trip in completed_trips:
        if ping_count >= 500000:
            break
        start = trip["actual_depart"]
        end = trip["actual_arrive"]
        if not start or not end or end <= start:
            continue
        duration_min = (end - start).total_seconds() / 60
        n_pings = min(int(duration_min / 5), 50)  # one ping every 5 min, max 50
        if n_pings < 2:
            n_pings = 2

        base_lat = 6.9 + random.uniform(-2.5, 2.8)
        base_lng = 79.8 + random.uniform(-0.5, 1.8)

        for j in range(n_pings):
            t = start + timedelta(minutes=j * 5)
            batch.append((
                trip["id"],
                round(base_lat + j * random.uniform(-0.01, 0.01), 6),
                round(base_lng + j * random.uniform(-0.01, 0.01), 6),
                round(random.uniform(0, 80), 2),
                round(random.uniform(0, 360), 2),
                t
            ))
            ping_count += 1

            if len(batch) >= 5000:
                await conn.executemany(
                    """INSERT INTO fleet.gps_pings (trip_id, lat, lng, speed_kmh, heading, recorded_at)
                       VALUES ($1,$2,$3,$4,$5,$6)""",
                    batch
                )
                batch = []
                if ping_count % 50000 == 0:
                    print(f"    {ping_count:,} GPS pings...")

    if batch:
        await conn.executemany(
            """INSERT INTO fleet.gps_pings (trip_id, lat, lng, speed_kmh, heading, recorded_at)
               VALUES ($1,$2,$3,$4,$5,$6)""",
            batch
        )

    # 6. Maintenance logs (3,000)
    print("  Inserting 3,000 maintenance logs...")
    maint = []
    for i in range(3000):
        vid = random.choice(vehicle_ids)
        maint.append((
            uuid.uuid4(), vid,
            random.choice(vendor_ids) if vendor_ids else None,
            random.choice(SERVICE_TYPES),
            f"Routine {random.choice(SERVICE_TYPES)} service",
            round(random.uniform(5000, 150000), 2),
            random.randint(10000, 500000),
            now - timedelta(days=random.randint(0, 730)),
            random.randint(10000, 500000),
            (now + timedelta(days=random.randint(30, 180))).date()
        ))
    await conn.executemany(
        """INSERT INTO fleet.maintenance_logs (id, vehicle_id, vendor_id, service_type,
           description, cost, mileage_at_service, serviced_at, next_due_km, next_due_date)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
        maint
    )

    # Update driver total_trips
    await conn.execute("""
        UPDATE fleet.drivers d SET total_trips = (
            SELECT COUNT(*) FROM fleet.trips t WHERE t.driver_id = d.id
        )
    """)

    print(f"  Fleet seeding complete: 200 vehicles, 180 drivers, 80 routes, "
          f"15,000 trips, {ping_count:,} GPS pings, 3,000 maintenance logs")
