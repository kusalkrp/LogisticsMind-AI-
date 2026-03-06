"""Operations data generators: orders, order_items, shipments, tracking_events, incidents, sla_contracts."""
import random
import uuid
from datetime import datetime, timedelta

ORDER_TYPES = ["standard", "express", "bulk", "cold_chain", "hazmat"]
PRIORITIES = ["low", "normal", "normal", "normal", "high", "critical"]
ORDER_STATUSES = ["delivered", "delivered", "delivered", "delivered", "dispatched", "cancelled", "processing"]
SHIPMENT_STATUSES_DELIVERED = ["delivered"] * 75 + ["delivered"] * 20 + ["returned"] * 3 + ["lost"] * 2
INCIDENT_TYPES_WEIGHTED = (
    ["delay"] * 40 + ["damage"] * 25 + ["breakdown"] * 15 + ["weather"] * 10 +
    ["customer_rejection"] * 5 + ["wrong_address"] * 3 + ["theft"] * 2
)
SEVERITY_WEIGHTED = ["low"] * 30 + ["medium"] * 40 + ["high"] * 25 + ["critical"] * 5
TRACKING_EVENTS_SEQUENCE = [
    "created", "picked_up", "in_warehouse", "loaded", "departed",
    "arrived_hub", "out_for_delivery"
]


async def seed_operations(conn):
    """Seed all operations schema tables."""
    company_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.companies")]
    contact_ids = await conn.fetch("SELECT id, company_id FROM core.contacts WHERE is_primary = true")
    contact_map = {r["company_id"]: r["id"] for r in contact_ids}
    facility_ids = [r["id"] for r in await conn.fetch("SELECT id FROM warehouse.facilities")]
    district_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.districts")]
    product_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.products")]
    trip_ids = [r["id"] for r in await conn.fetch(
        "SELECT id FROM fleet.trips WHERE status = 'completed' ORDER BY trip_date DESC LIMIT 28000"
    )]
    vehicle_ids = [r["id"] for r in await conn.fetch("SELECT id FROM fleet.vehicles")]
    driver_ids = [r["id"] for r in await conn.fetch("SELECT id FROM fleet.drivers")]

    now = datetime.now()

    # 1. Orders (25,000) with November spike
    print("  Inserting 25,000 orders...")
    orders = []
    order_ids = []
    for i in range(25000):
        oid = uuid.uuid4()
        order_ids.append(oid)

        days_back = random.randint(0, 730)
        created = now - timedelta(days=days_back)
        month = created.month

        # November spike: 60% more orders
        if month == 11 and random.random() < 0.6:
            # Cluster more in November
            created = created.replace(month=11)

        cid = random.choice(company_ids)
        contact = contact_map.get(cid)

        orders.append((
            oid,
            f"ORD-{created.year}-{i+1:05d}",
            cid, contact,
            random.choice(ORDER_TYPES),
            random.choice(PRIORITIES),
            random.choice(facility_ids),
            random.choice(district_ids),
            f"{random.randint(1,999)} Main Road, District",
            round(5.5 + random.uniform(-0.5, 4.5), 6),
            round(79.5 + random.uniform(-0.5, 2.0), 6),
            created + timedelta(days=random.randint(1, 7)),
            random.choice(ORDER_STATUSES),
            None,
            created
        ))

        if len(orders) >= 1000:
            await conn.executemany(
                """INSERT INTO operations.orders (id, order_no, company_id, contact_id, order_type,
                   priority, origin_facility, dest_district, dest_address, dest_lat, dest_lng,
                   requested_by, status, special_instructions, created_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
                orders
            )
            orders = []
            if (i + 1) % 5000 == 0:
                print(f"    {i+1:,} orders...")
    if orders:
        await conn.executemany(
            """INSERT INTO operations.orders (id, order_no, company_id, contact_id, order_type,
               priority, origin_facility, dest_district, dest_address, dest_lat, dest_lng,
               requested_by, status, special_instructions, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
            orders
        )

    # 2. Order items (60,000) — ~2-3 per order
    print("  Inserting 60,000 order items...")
    items = []
    item_count = 0
    for oid in order_ids:
        n_items = random.randint(1, 5)
        for _ in range(n_items):
            if item_count >= 60000:
                break
            pid = random.choice(product_ids)
            qty = random.randint(1, 100)
            unit_price = round(random.uniform(100, 10000), 2)
            items.append((
                uuid.uuid4(), oid, pid, qty, unit_price, round(qty * unit_price, 2)
            ))
            item_count += 1

            if len(items) >= 1000:
                await conn.executemany(
                    """INSERT INTO operations.order_items (id, order_id, product_id, quantity, unit_price, total_price)
                       VALUES ($1,$2,$3,$4,$5,$6)""",
                    items
                )
                items = []
                if item_count % 10000 == 0:
                    print(f"    {item_count:,} order items...")
        if item_count >= 60000:
            break
    if items:
        await conn.executemany(
            """INSERT INTO operations.order_items (id, order_id, product_id, quantity, unit_price, total_price)
               VALUES ($1,$2,$3,$4,$5,$6)""",
            items
        )

    # 3. Shipments (28,000)
    print("  Inserting 28,000 shipments...")
    shipments = []
    shipment_ids = []
    trip_idx = 0
    for i in range(28000):
        sid = uuid.uuid4()
        shipment_ids.append(sid)

        # Assign order_id (some orders have 2 shipments)
        if i < 25000:
            oid = order_ids[i]
        else:
            oid = random.choice(order_ids[:25000])

        tid = trip_ids[trip_idx % len(trip_ids)] if trip_ids else None
        trip_idx += 1

        sched_pickup = now - timedelta(days=random.randint(0, 730))
        actual_pickup = sched_pickup + timedelta(hours=random.uniform(0, 4))
        sched_delivery = sched_pickup + timedelta(hours=random.uniform(6, 72))

        status = random.choice(SHIPMENT_STATUSES_DELIVERED)
        if status == "delivered":
            # 75% on time, 20% mild delay, 5% major delay
            r = random.random()
            if r < 0.75:
                actual_delivery = sched_delivery - timedelta(hours=random.uniform(0, 2))
            elif r < 0.95:
                actual_delivery = sched_delivery + timedelta(hours=random.uniform(0.5, 8))
            else:
                actual_delivery = sched_delivery + timedelta(hours=random.uniform(8, 48))
        else:
            actual_delivery = None

        shipments.append((
            sid,
            f"SHP-{sched_pickup.year}-{i+1:05d}",
            oid, tid,
            random.choice(facility_ids),
            random.choice(district_ids),
            f"{random.randint(1,999)} Delivery Rd",
            round(random.uniform(1, 5000), 2),
            round(random.uniform(0.01, 20), 2),
            status,
            sched_pickup, actual_pickup,
            sched_delivery, actual_delivery,
            None, None, False, None
        ))

        if len(shipments) >= 1000:
            await conn.executemany(
                """INSERT INTO operations.shipments (id, shipment_no, order_id, trip_id,
                   origin_facility, dest_district, dest_address, weight_kg, volume_m3, status,
                   scheduled_pickup, actual_pickup, scheduled_delivery, actual_delivery,
                   delivery_photo, recipient_name, recipient_sig, pod_notes)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)""",
                shipments
            )
            shipments = []
            if (i + 1) % 5000 == 0:
                print(f"    {i+1:,} shipments...")
    if shipments:
        await conn.executemany(
            """INSERT INTO operations.shipments (id, shipment_no, order_id, trip_id,
               origin_facility, dest_district, dest_address, weight_kg, volume_m3, status,
               scheduled_pickup, actual_pickup, scheduled_delivery, actual_delivery,
               delivery_photo, recipient_name, recipient_sig, pod_notes)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)""",
            shipments
        )

    # 4. Tracking events (180,000) — ~6-7 per shipment
    print("  Inserting 180,000 tracking events...")
    events = []
    event_count = 0
    for sid in shipment_ids:
        if event_count >= 180000:
            break
        base_time = now - timedelta(days=random.randint(0, 730))
        n_events = random.randint(5, 8)
        for j in range(n_events):
            if event_count >= 180000:
                break
            evt_type = TRACKING_EVENTS_SEQUENCE[j] if j < len(TRACKING_EVENTS_SEQUENCE) else "delivered"
            events.append((
                uuid.uuid4(), sid, evt_type,
                random.choice(facility_ids) if j < 4 else None,
                None,
                round(6.9 + random.uniform(-3, 3), 6),
                round(80.0 + random.uniform(-1, 2), 6),
                None, None,
                base_time + timedelta(hours=j * random.uniform(1, 8))
            ))
            event_count += 1

            if len(events) >= 1000:
                await conn.executemany(
                    """INSERT INTO operations.tracking_events (id, shipment_id, event_type,
                       facility_id, trip_id, lat, lng, notes, recorded_by, recorded_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    events
                )
                events = []
                if event_count % 50000 == 0:
                    print(f"    {event_count:,} tracking events...")
    if events:
        await conn.executemany(
            """INSERT INTO operations.tracking_events (id, shipment_id, event_type,
               facility_id, trip_id, lat, lng, notes, recorded_by, recorded_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            events
        )

    # 5. Incidents (2,500)
    print("  Inserting 2,500 incidents...")
    incidents = []
    for i in range(2500):
        occurred = now - timedelta(days=random.randint(0, 730))
        itype = random.choice(INCIDENT_TYPES_WEIGHTED)
        resolved = random.random() > 0.15
        incidents.append((
            uuid.uuid4(),
            f"INC-{occurred.year}-{i+1:05d}",
            itype,
            random.choice(SEVERITY_WEIGHTED),
            random.choice(shipment_ids),
            random.choice(trip_ids) if trip_ids else None,
            random.choice(vehicle_ids),
            random.choice(driver_ids),
            random.choice(district_ids),
            f"{itype.replace('_',' ').title()} incident during transit",
            round(random.uniform(1000, 500000), 2),
            resolved,
            occurred,
            occurred + timedelta(hours=random.randint(1, 24)),
            occurred + timedelta(days=random.randint(1, 30)) if resolved else None
        ))
    await conn.executemany(
        """INSERT INTO operations.incidents (id, incident_no, incident_type, severity,
           shipment_id, trip_id, vehicle_id, driver_id, district_id, description,
           financial_impact, resolved, occurred_at, reported_at, resolved_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
        incidents
    )

    # 6. SLA contracts (800)
    print("  Inserting 800 SLA contracts...")
    sla = []
    for i in range(800):
        sla.append((
            uuid.uuid4(),
            random.choice(company_ids),
            random.choice(ORDER_TYPES),
            random.choice([12, 24, 36, 48, 72]),
            round(random.uniform(500, 5000), 2),
            random.choice([1, 2, 3]),
            True
        ))
    await conn.executemany(
        """INSERT INTO operations.sla_contracts (id, company_id, order_type, max_transit_hr,
           penalty_per_hr, free_attempts, is_active)
           VALUES ($1,$2,$3,$4,$5,$6,$7)""",
        sla
    )

    print(f"  Operations seeding complete: 25,000 orders, {item_count:,} items, "
          f"28,000 shipments, {event_count:,} events, 2,500 incidents, 800 SLAs")
