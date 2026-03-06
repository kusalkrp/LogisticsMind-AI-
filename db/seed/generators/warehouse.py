"""Warehouse data generators: facilities, inventory, stock movements, staff."""
import random
import uuid
from datetime import datetime, timedelta

# 18 warehouse facilities with codes mapped to districts
WAREHOUSE_DEFS = [
    {"code": "WH-COL-01", "name": "Colombo Main Distribution Center", "district": "Colombo", "type": "distribution_center", "capacity": 15000, "cold": True, "hazmat": True, "lat": 6.9344, "lng": 79.8428},
    {"code": "WH-COL-02", "name": "Colombo Port Warehouse", "district": "Colombo", "type": "bonded", "capacity": 12000, "cold": False, "hazmat": True, "lat": 6.9422, "lng": 79.8500},
    {"code": "WH-KAN-01", "name": "Kandy Regional Hub", "district": "Kandy", "type": "distribution_center", "capacity": 8000, "cold": True, "hazmat": False, "lat": 7.2906, "lng": 80.6337},
    {"code": "WH-GAL-01", "name": "Galle Southern Hub", "district": "Galle", "type": "distribution_center", "capacity": 6000, "cold": True, "hazmat": False, "lat": 6.0535, "lng": 80.2210},
    {"code": "WH-JAF-01", "name": "Jaffna Northern Hub", "district": "Jaffna", "type": "distribution_center", "capacity": 5000, "cold": False, "hazmat": False, "lat": 9.6615, "lng": 80.0255},
    {"code": "WH-TRC-01", "name": "Trincomalee Eastern Hub", "district": "Trincomalee", "type": "distribution_center", "capacity": 5000, "cold": False, "hazmat": False, "lat": 8.5874, "lng": 81.2152},
    {"code": "WH-BAT-01", "name": "Batticaloa Transit Point", "district": "Batticaloa", "type": "transit", "capacity": 3000, "cold": False, "hazmat": False, "lat": 7.7310, "lng": 81.6747},
    {"code": "WH-KUR-01", "name": "Kurunegala NW Hub", "district": "Kurunegala", "type": "distribution_center", "capacity": 7000, "cold": True, "hazmat": False, "lat": 7.4818, "lng": 80.3609},
    {"code": "WH-PUT-01", "name": "Puttalam Coastal Warehouse", "district": "Puttalam", "type": "transit", "capacity": 3500, "cold": False, "hazmat": False, "lat": 8.0408, "lng": 79.8394},
    {"code": "WH-ANU-01", "name": "Anuradhapura NC Hub", "district": "Anuradhapura", "type": "distribution_center", "capacity": 6000, "cold": False, "hazmat": False, "lat": 8.3114, "lng": 80.4037},
    {"code": "WH-POL-01", "name": "Polonnaruwa Storage", "district": "Polonnaruwa", "type": "transit", "capacity": 3000, "cold": False, "hazmat": False, "lat": 7.9403, "lng": 81.0188},
    {"code": "WH-BAD-01", "name": "Badulla Uva Hub", "district": "Badulla", "type": "distribution_center", "capacity": 4000, "cold": True, "hazmat": False, "lat": 6.9934, "lng": 81.0550},
    {"code": "WH-RAT-01", "name": "Ratnapura Sabaragamuwa Hub", "district": "Ratnapura", "type": "distribution_center", "capacity": 4500, "cold": False, "hazmat": False, "lat": 6.6828, "lng": 80.3992},
    {"code": "WH-HAM-01", "name": "Hambantota Southern Storage", "district": "Hambantota", "type": "transit", "capacity": 3500, "cold": False, "hazmat": False, "lat": 6.1429, "lng": 81.1212},
    {"code": "WH-MAT-01", "name": "Matara Cold Storage", "district": "Matara", "type": "cold_storage", "capacity": 4000, "cold": True, "hazmat": False, "lat": 5.9549, "lng": 80.5550},
    {"code": "WH-NUW-01", "name": "Nuwara Eliya Highland Store", "district": "Nuwara Eliya", "type": "cold_storage", "capacity": 2500, "cold": True, "hazmat": False, "lat": 6.9497, "lng": 80.7891},
    {"code": "WH-KEG-01", "name": "Kegalle Transit Hub", "district": "Kegalle", "type": "transit", "capacity": 3000, "cold": False, "hazmat": False, "lat": 7.2513, "lng": 80.3464},
    {"code": "WH-MON-01", "name": "Monaragala Rural Hub", "district": "Monaragala", "type": "distribution_center", "capacity": 3500, "cold": False, "hazmat": False, "lat": 6.8728, "lng": 81.3507},
]

SL_FIRST_NAMES = [
    "Ashan", "Kamal", "Nimal", "Saman", "Ruwan", "Dinesh", "Pradeep", "Chaminda",
    "Nuwan", "Lakshan", "Dilshan", "Thilina", "Kasun", "Sajith", "Mahela",
    "Kumari", "Nilmini", "Chathurika", "Sewwandi", "Dilini"
]
SL_LAST_NAMES = [
    "Perera", "Silva", "Fernando", "Jayawardena", "Wickramasinghe", "Bandara",
    "Dissanayake", "Gunasekara", "Rathnayake", "Samaraweera"
]

MOVEMENT_TYPES = ["receipt", "dispatch", "transfer_in", "transfer_out", "adjustment", "damage"]
STAFF_ROLES = ["manager", "picker", "loader", "security", "supervisor"]
SHIFTS = ["morning", "afternoon", "night"]


async def seed_warehouse(conn):
    """Seed all warehouse schema tables."""
    # Get district name->id mapping
    districts = {r["name"]: r["id"] for r in await conn.fetch("SELECT id, name FROM core.districts")}

    # 1. Facilities (18)
    print("  Inserting 18 facilities...")
    facility_ids = []
    for wh in WAREHOUSE_DEFS:
        fid = uuid.uuid4()
        facility_ids.append(fid)
        util = round(random.uniform(35, 92), 2)
        opened = datetime.now().date() - timedelta(days=random.randint(365, 2500))
        await conn.execute(
            """INSERT INTO warehouse.facilities (id, code, name, district_id, facility_type,
               capacity_m3, current_util_pct, has_cold_chain, has_hazmat, lat, lng, opened_at, is_active)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
            fid, wh["code"], wh["name"], districts[wh["district"]], wh["type"],
            wh["capacity"], util, wh["cold"], wh["hazmat"], wh["lat"], wh["lng"],
            opened, True
        )

    # Get product and company IDs
    product_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.products")]
    company_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.companies")]

    # 2. Inventory items (40,000)
    print("  Inserting 40,000 inventory items...")
    batch = []
    seen = set()
    count = 0
    while count < 40000:
        fid = random.choice(facility_ids)
        pid = random.choice(product_ids)
        cid = random.choice(company_ids)
        key = (fid, pid, cid)
        if key in seen:
            continue
        seen.add(key)
        batch.append((
            uuid.uuid4(), fid, pid, cid,
            random.randint(1, 5000),
            random.randint(0, 500),
            f"B-{random.randint(10000, 99999)}",
            (datetime.now() + timedelta(days=random.randint(30, 365))).date() if random.random() < 0.3 else None,
            round(random.uniform(10, 5000), 2),
            datetime.now() - timedelta(days=random.randint(1, 90)),
            f"A{random.randint(1,20):02d}-R{random.randint(1,50):02d}-B{random.randint(1,10):02d}"
        ))
        count += 1
        if len(batch) >= 1000:
            await conn.executemany(
                """INSERT INTO warehouse.inventory_items (id, facility_id, product_id, company_id,
                   quantity, reserved_qty, batch_no, expiry_date, unit_cost, last_counted_at, location_code)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                batch
            )
            batch = []
            if count % 10000 == 0:
                print(f"    {count:,} inventory items...")
    if batch:
        await conn.executemany(
            """INSERT INTO warehouse.inventory_items (id, facility_id, product_id, company_id,
               quantity, reserved_qty, batch_no, expiry_date, unit_cost, last_counted_at, location_code)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            batch
        )

    # 3. Stock movements (150,000)
    print("  Inserting 150,000 stock movements...")
    # Get staff IDs (will be created next, use None for now)
    batch = []
    now = datetime.now()
    for i in range(150000):
        moved_at = now - timedelta(days=random.randint(0, 730), hours=random.randint(0, 23))
        batch.append((
            uuid.uuid4(),
            random.choice(facility_ids),
            random.choice(product_ids),
            random.choice(company_ids),
            random.choice(MOVEMENT_TYPES),
            random.randint(1, 2000),
            None,  # reference_id
            round(random.uniform(10, 5000), 2),
            None,  # moved_by
            moved_at,
            None  # notes
        ))
        if len(batch) >= 1000:
            await conn.executemany(
                """INSERT INTO warehouse.stock_movements (id, facility_id, product_id, company_id,
                   movement_type, quantity, reference_id, unit_cost, moved_by, moved_at, notes)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                batch
            )
            batch = []
            if (i + 1) % 10000 == 0:
                print(f"    {i+1:,} stock movements...")
    if batch:
        await conn.executemany(
            """INSERT INTO warehouse.stock_movements (id, facility_id, product_id, company_id,
               movement_type, quantity, reference_id, unit_cost, moved_by, moved_at, notes)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            batch
        )

    # 4. Staff (300)
    print("  Inserting 300 warehouse staff...")
    staff = []
    for i in range(300):
        staff.append((
            uuid.uuid4(),
            random.choice(facility_ids),
            f"{random.choice(SL_FIRST_NAMES)} {random.choice(SL_LAST_NAMES)}",
            random.choice(STAFF_ROLES),
            random.choice(SHIFTS),
            (datetime.now() - timedelta(days=random.randint(90, 2000))).date(),
            random.random() > 0.05
        ))
    await conn.executemany(
        """INSERT INTO warehouse.staff (id, facility_id, name, role, shift, hired_at, is_active)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        staff
    )

    print(f"  Warehouse seeding complete: 18 facilities, {count} inventory items, 150,000 movements, 300 staff")
