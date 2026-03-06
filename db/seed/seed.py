"""
Main seeder orchestrator.
Generates all mock data for the CeyLog logistics database.
Run: python -m db.seed.seed
"""
import asyncio
import os
import time
import asyncpg


async def get_connection():
    """Get database connection using Docker service DNS."""
    url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://user:password@postgres:5432/ceylog"
    )
    # asyncpg uses plain postgresql:// URLs
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url)


async def get_row_counts(conn):
    """Print row counts for all tables."""
    tables = [
        "core.districts", "core.companies", "core.contacts",
        "core.vendors", "core.products",
        "warehouse.facilities", "warehouse.inventory_items",
        "warehouse.stock_movements", "warehouse.staff",
        "fleet.vehicles", "fleet.drivers", "fleet.routes",
        "fleet.trips", "fleet.gps_pings", "fleet.maintenance_logs",
        "operations.orders", "operations.order_items",
        "operations.shipments", "operations.tracking_events",
        "operations.incidents", "operations.sla_contracts",
        "finance.invoices", "finance.payments",
        "finance.operational_costs", "finance.sla_breaches",
    ]
    total = 0
    print("\n" + "=" * 50)
    print("ROW COUNTS")
    print("=" * 50)
    for table in tables:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        total += count
        print(f"  {table:<40} {count:>8,}")
    print("-" * 50)
    print(f"  {'TOTAL':<40} {total:>8,}")
    print("=" * 50 + "\n")


async def main():
    print("=" * 50)
    print("LogisticsMind AI — Data Seeder")
    print("=" * 50)

    conn = await get_connection()

    # Check if already seeded
    count = await conn.fetchval("SELECT COUNT(*) FROM core.districts")
    if count > 0:
        print("Database already seeded. Skipping.")
        await get_row_counts(conn)
        await conn.close()
        return

    start = time.time()

    # Import and run generators in order
    from db.seed.generators.core import seed_core
    from db.seed.generators.warehouse import seed_warehouse
    from db.seed.generators.fleet import seed_fleet
    from db.seed.generators.operations import seed_operations
    from db.seed.generators.finance import seed_finance
    from db.seed.anomalies import inject_anomalies

    print("\n[1/6] Seeding core data...")
    await seed_core(conn)

    print("\n[2/6] Seeding warehouse data...")
    await seed_warehouse(conn)

    print("\n[3/6] Seeding fleet data...")
    await seed_fleet(conn)

    print("\n[4/6] Seeding operations data...")
    await seed_operations(conn)

    print("\n[5/6] Seeding finance data...")
    await seed_finance(conn)

    print("\n[6/6] Injecting anomalies...")
    await inject_anomalies(conn)

    elapsed = time.time() - start
    print(f"\nSeeding completed in {elapsed:.1f}s")

    await get_row_counts(conn)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
