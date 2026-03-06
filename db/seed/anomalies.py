"""Inject deliberate anomaly patterns for AI detection."""
import uuid
from datetime import datetime, timedelta


async def inject_anomalies(conn):
    """Inject all 8 anomaly patterns from the system design."""

    # 1. RT-COL-JAF-003 — 40% higher delay rate
    print("  Anomaly 1: RT-COL-JAF-003 high delay rate...")
    route = await conn.fetchrow("SELECT id FROM fleet.routes WHERE code = 'RT-COL-JAF-003'")
    if route:
        await conn.execute("""
            UPDATE fleet.trips
            SET actual_arrive = scheduled_arrive + INTERVAL '8 hours' * (0.5 + random())
            WHERE route_id = $1
              AND status = 'completed'
              AND actual_arrive IS NOT NULL
              AND random() < 0.4
        """, route["id"])
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM fleet.trips WHERE route_id = $1 AND actual_arrive > scheduled_arrive + INTERVAL '2 hours'",
            route["id"]
        )
        print(f"    {count} trips delayed on RT-COL-JAF-003")

    # 2. DRV-0042 — 2x fuel consumption
    print("  Anomaly 2: DRV-0042 excessive fuel consumption...")
    driver = await conn.fetchrow("SELECT id FROM fleet.drivers WHERE employee_id = 'DRV-0042'")
    if driver:
        await conn.execute("""
            UPDATE fleet.trips
            SET fuel_used_l = fuel_used_l * 2.1,
                fuel_cost = fuel_cost * 2.1
            WHERE driver_id = $1
              AND fuel_used_l IS NOT NULL
        """, driver["id"])
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM fleet.trips WHERE driver_id = $1 AND fuel_used_l IS NOT NULL",
            driver["id"]
        )
        print(f"    {count} trips updated for DRV-0042")

    # 3. WH-GAL-01 — capacity always at exactly 87%
    print("  Anomaly 3: WH-GAL-01 fixed utilisation at 87%...")
    await conn.execute("""
        UPDATE warehouse.facilities
        SET current_util_pct = 87.00
        WHERE code = 'WH-GAL-01'
    """)

    # 4. COMP-0187 (187th company) — 15 days late payments
    print("  Anomaly 4: Company 187 late payments...")
    company = await conn.fetchrow("""
        SELECT id FROM core.companies ORDER BY onboarded_at LIMIT 1 OFFSET 186
    """)
    if company:
        # Get invoices for this company
        invoices = await conn.fetch("""
            SELECT i.id, i.due_date FROM finance.invoices i
            WHERE i.company_id = $1
        """, company["id"])
        for inv in invoices:
            late_date = inv["due_date"] + timedelta(days=15)
            await conn.execute("""
                UPDATE finance.payments
                SET payment_date = $1
                WHERE invoice_id = $2
            """, late_date, inv["id"])
        print(f"    {len(invoices)} payments made 15 days late for company 187")

    # 5. SKU-PHARM-099 — 5x damage rate
    print("  Anomaly 5: SKU-PHARM-099 high damage rate...")
    product = await conn.fetchrow("SELECT id FROM core.products WHERE sku = 'SKU-PHAR-0099'")
    if not product:
        # Try alternate SKU pattern
        product = await conn.fetchrow("SELECT id FROM core.products WHERE sku LIKE 'SKU-PHAR-%' LIMIT 1")
    if product:
        # Get shipments containing orders with this product
        shipment_ids = await conn.fetch("""
            SELECT DISTINCT s.id FROM operations.shipments s
            JOIN operations.order_items oi ON oi.order_id = s.order_id
            WHERE oi.product_id = $1
            LIMIT 50
        """, product["id"])
        now = datetime.now()
        for i, ship in enumerate(shipment_ids):
            await conn.execute("""
                INSERT INTO operations.incidents (id, incident_no, incident_type, severity,
                    shipment_id, district_id, description, financial_impact, resolved,
                    occurred_at, reported_at)
                VALUES ($1, $2, 'damage', $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                uuid.uuid4(),
                f"INC-ANOM-{i+1:05d}",
                "high" if i % 3 == 0 else "medium",
                ship["id"],
                (await conn.fetchval("SELECT id FROM core.districts ORDER BY random() LIMIT 1")),
                "Product damage during handling — pharmaceutical item",
                round(5000 + i * 1000, 2),
                True,
                now - timedelta(days=i * 10),
                now - timedelta(days=i * 10 - 1)
            )
        print(f"    {len(shipment_ids)} damage incidents for pharma product")

    # 6. November spike — already handled in operations seed (60% boost)
    print("  Anomaly 6: November spike — built into seed data")

    # 7. Colombo → Jaffna rainy month delivery drop
    print("  Anomaly 7: Colombo-Jaffna rainy month performance drop...")
    if route:
        # Make June-October trips have worse outcomes
        await conn.execute("""
            UPDATE fleet.trips
            SET actual_arrive = scheduled_arrive + INTERVAL '12 hours' * random()
            WHERE route_id = $1
              AND status = 'completed'
              AND actual_arrive IS NOT NULL
              AND EXTRACT(MONTH FROM trip_date) BETWEEN 6 AND 10
              AND random() < 0.3
        """, route["id"])

    # 8. VH-0031 — breakdown every ~8000km
    print("  Anomaly 8: VH-0031 regular breakdowns at 8000km intervals...")
    vehicle = await conn.fetchrow("SELECT id FROM fleet.vehicles WHERE plate_no = 'VH-0031'")
    if vehicle:
        vendor_id = await conn.fetchval("SELECT id FROM core.vendors LIMIT 1")
        now = datetime.now()
        for km in range(8000, 500001, 8000):
            await conn.execute("""
                INSERT INTO fleet.maintenance_logs (id, vehicle_id, vendor_id, service_type,
                    description, cost, mileage_at_service, serviced_at, next_due_km, next_due_date)
                VALUES ($1, $2, $3, 'engine', 'Emergency breakdown repair', $4, $5, $6, $7, $8)
            """,
                uuid.uuid4(), vehicle["id"], vendor_id,
                round(25000 + km * 0.5, 2),
                km,
                now - timedelta(days=int((500000 - km) / 50)),
                km + 8000,
                (now + timedelta(days=60)).date()
            )
        print(f"    {500000 // 8000} breakdown records at 8000km intervals")

    print("  All anomalies injected successfully")
