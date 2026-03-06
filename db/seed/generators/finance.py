"""Finance data generators: invoices, payments, operational_costs, sla_breaches."""
import random
import uuid
from datetime import datetime, timedelta


async def seed_finance(conn):
    """Seed all finance schema tables."""
    company_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.companies")]
    order_ids = [r["id"] for r in await conn.fetch("SELECT id FROM operations.orders LIMIT 24000")]
    shipment_ids = [r["id"] for r in await conn.fetch("SELECT id FROM operations.shipments")]
    sla_ids = [r["id"] for r in await conn.fetch("SELECT id FROM operations.sla_contracts")]
    facility_ids = [r["id"] for r in await conn.fetch("SELECT id FROM warehouse.facilities")]
    vendor_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.vendors")]

    now = datetime.now()

    # 1. Invoices (24,000)
    print("  Inserting 24,000 invoices...")
    invoices = []
    invoice_data = []  # for payments reference
    for i in range(24000):
        iid = uuid.uuid4()
        cid = random.choice(company_ids)
        oid = order_ids[i] if i < len(order_ids) else random.choice(order_ids)

        inv_date = (now - timedelta(days=random.randint(0, 730))).date()
        credit_days = random.choice([14, 30, 45, 60])
        due_date = inv_date + timedelta(days=credit_days)

        subtotal = round(random.uniform(5000, 500000), 2)
        tax = round(subtotal * 0.08, 2)  # 8% tax
        discount = round(subtotal * random.uniform(0, 0.05), 2)
        total = round(subtotal + tax - discount, 2)

        # Status distribution
        r = random.random()
        if r < 0.65:
            status = "paid"
            paid = total
        elif r < 0.80:
            status = "partial"
            paid = round(total * random.uniform(0.2, 0.8), 2)
        elif r < 0.90:
            status = "sent"
            paid = 0
        elif r < 0.95:
            status = "overdue"
            paid = 0
        else:
            status = "draft"
            paid = 0

        invoices.append((
            iid, f"INV-{inv_date.year}-{i+1:05d}",
            cid, oid, inv_date, due_date,
            subtotal, tax, discount, total, paid, status, "LKR"
        ))
        invoice_data.append({"id": iid, "company_id": cid, "total": total, "due_date": due_date, "status": status})

        if len(invoices) >= 1000:
            await conn.executemany(
                """INSERT INTO finance.invoices (id, invoice_no, company_id, order_id,
                   invoice_date, due_date, subtotal, tax_amount, discount_amount,
                   total_amount, paid_amount, status, currency)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
                invoices
            )
            invoices = []
            if (i + 1) % 5000 == 0:
                print(f"    {i+1:,} invoices...")
    if invoices:
        await conn.executemany(
            """INSERT INTO finance.invoices (id, invoice_no, company_id, order_id,
               invoice_date, due_date, subtotal, tax_amount, discount_amount,
               total_amount, paid_amount, status, currency)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
            invoices
        )

    # 2. Payments (22,000)
    print("  Inserting 22,000 payments...")
    payments = []
    paid_invoices = [inv for inv in invoice_data if inv["status"] in ("paid", "partial")]
    payment_count = 0
    for inv in paid_invoices:
        if payment_count >= 22000:
            break
        # 90% pay within credit terms, 10% late
        if random.random() < 0.9:
            pay_date = inv["due_date"] - timedelta(days=random.randint(0, 10))
        else:
            pay_date = inv["due_date"] + timedelta(days=random.randint(1, 30))

        payments.append((
            uuid.uuid4(), inv["id"], inv["company_id"],
            inv["total"] if inv["status"] == "paid" else round(inv["total"] * random.uniform(0.3, 0.8), 2),
            random.choice(["bank_transfer", "cheque", "cash", "online"]),
            f"PAY-{random.randint(100000, 999999)}",
            pay_date,
            datetime.combine(pay_date, datetime.min.time()) + timedelta(hours=random.randint(8, 17))
        ))
        payment_count += 1

        if len(payments) >= 1000:
            await conn.executemany(
                """INSERT INTO finance.payments (id, invoice_id, company_id, amount,
                   payment_method, reference_no, payment_date, received_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
                payments
            )
            payments = []
            if payment_count % 5000 == 0:
                print(f"    {payment_count:,} payments...")
    if payments:
        await conn.executemany(
            """INSERT INTO finance.payments (id, invoice_id, company_id, amount,
               payment_method, reference_no, payment_date, received_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
            payments
        )

    # 3. Operational costs (35,000)
    print("  Inserting 35,000 operational costs...")
    cost_types = ["fuel", "maintenance", "labour", "warehouse_rent", "insurance", "toll", "sla_penalty", "damage_claim"]
    costs = []
    for i in range(35000):
        costs.append((
            uuid.uuid4(),
            random.choice(cost_types),
            None,
            random.choice(facility_ids),
            random.choice(vendor_ids),
            round(random.uniform(500, 200000), 2),
            f"Operational cost - {random.choice(cost_types)}",
            (now - timedelta(days=random.randint(0, 730))).date(),
            None,
            now - timedelta(days=random.randint(0, 730))
        ))

        if len(costs) >= 1000:
            await conn.executemany(
                """INSERT INTO finance.operational_costs (id, cost_type, reference_id,
                   facility_id, vendor_id, amount, description, cost_date, approved_by, created_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                costs
            )
            costs = []
            if (i + 1) % 10000 == 0:
                print(f"    {i+1:,} operational costs...")
    if costs:
        await conn.executemany(
            """INSERT INTO finance.operational_costs (id, cost_type, reference_id,
               facility_id, vendor_id, amount, description, cost_date, approved_by, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            costs
        )

    # 4. SLA breaches (3,200)
    print("  Inserting 3,200 SLA breaches...")
    breaches = []
    for i in range(3200):
        breach_hrs = round(random.uniform(1, 48), 2)
        penalty = round(breach_hrs * random.uniform(500, 5000), 2)
        waived = random.random() < 0.15
        breaches.append((
            uuid.uuid4(),
            random.choice(shipment_ids),
            random.choice(sla_ids) if sla_ids else None,
            breach_hrs,
            penalty,
            waived,
            "Goodwill waiver" if waived else None,
            now - timedelta(days=random.randint(0, 730))
        ))
    await conn.executemany(
        """INSERT INTO finance.sla_breaches (id, shipment_id, sla_contract_id,
           breach_hours, penalty_amount, waived, waive_reason, created_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
        breaches
    )

    print(f"  Finance seeding complete: 24,000 invoices, {payment_count:,} payments, "
          f"35,000 operational costs, 3,200 SLA breaches")
