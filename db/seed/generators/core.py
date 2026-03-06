"""Core data generators: districts, companies, contacts, vendors, products."""
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# All 25 Sri Lankan districts with real data
SRI_LANKA_DISTRICTS = [
    {"name": "Colombo", "province": "Western", "area_km2": 699, "lat": 6.9271, "lng": 79.8612},
    {"name": "Gampaha", "province": "Western", "area_km2": 1387, "lat": 7.0840, "lng": 80.0098},
    {"name": "Kalutara", "province": "Western", "area_km2": 1598, "lat": 6.5854, "lng": 80.1142},
    {"name": "Kandy", "province": "Central", "area_km2": 1940, "lat": 7.2906, "lng": 80.6337},
    {"name": "Matale", "province": "Central", "area_km2": 1993, "lat": 7.4675, "lng": 80.6234},
    {"name": "Nuwara Eliya", "province": "Central", "area_km2": 1741, "lat": 6.9497, "lng": 80.7891},
    {"name": "Galle", "province": "Southern", "area_km2": 1652, "lat": 6.0535, "lng": 80.2210},
    {"name": "Matara", "province": "Southern", "area_km2": 1283, "lat": 5.9549, "lng": 80.5550},
    {"name": "Hambantota", "province": "Southern", "area_km2": 2609, "lat": 6.1429, "lng": 81.1212},
    {"name": "Jaffna", "province": "Northern", "area_km2": 1025, "lat": 9.6615, "lng": 80.0255},
    {"name": "Kilinochchi", "province": "Northern", "area_km2": 1279, "lat": 9.3803, "lng": 80.3770},
    {"name": "Mannar", "province": "Northern", "area_km2": 1996, "lat": 8.9810, "lng": 79.9044},
    {"name": "Mullaitivu", "province": "Northern", "area_km2": 2617, "lat": 9.2671, "lng": 80.8142},
    {"name": "Vavuniya", "province": "Northern", "area_km2": 1967, "lat": 8.7514, "lng": 80.4971},
    {"name": "Trincomalee", "province": "Eastern", "area_km2": 2727, "lat": 8.5874, "lng": 81.2152},
    {"name": "Batticaloa", "province": "Eastern", "area_km2": 2854, "lat": 7.7310, "lng": 81.6747},
    {"name": "Ampara", "province": "Eastern", "area_km2": 4415, "lat": 7.2964, "lng": 81.6820},
    {"name": "Kurunegala", "province": "North Western", "area_km2": 4816, "lat": 7.4818, "lng": 80.3609},
    {"name": "Puttalam", "province": "North Western", "area_km2": 3072, "lat": 8.0408, "lng": 79.8394},
    {"name": "Anuradhapura", "province": "North Central", "area_km2": 7179, "lat": 8.3114, "lng": 80.4037},
    {"name": "Polonnaruwa", "province": "North Central", "area_km2": 3293, "lat": 7.9403, "lng": 81.0188},
    {"name": "Badulla", "province": "Uva", "area_km2": 2861, "lat": 6.9934, "lng": 81.0550},
    {"name": "Monaragala", "province": "Uva", "area_km2": 5639, "lat": 6.8728, "lng": 81.3507},
    {"name": "Ratnapura", "province": "Sabaragamuwa", "area_km2": 3275, "lat": 6.6828, "lng": 80.3992},
    {"name": "Kegalle", "province": "Sabaragamuwa", "area_km2": 1693, "lat": 7.2513, "lng": 80.3464},
]

INDUSTRIES = ["retail", "manufacturing", "pharma", "fmcg", "agriculture"]
VENDOR_TYPES = ["fuel", "maintenance", "packaging", "cold_chain"]
COMPANY_SUFFIXES = ["(Pvt) Ltd", "PLC", "& Co", "Holdings", "Enterprises", "Group", "Trading"]

SL_FIRST_NAMES = [
    "Ashan", "Kamal", "Nimal", "Saman", "Ruwan", "Dinesh", "Pradeep", "Chaminda",
    "Nuwan", "Lakshan", "Dilshan", "Thilina", "Kasun", "Sajith", "Mahela",
    "Kumari", "Nilmini", "Chathurika", "Sewwandi", "Dilini", "Hansika", "Kavindi",
    "Rashmi", "Tharushi", "Isuri", "Sanduni", "Nethmi", "Hiruni", "Amaya", "Devi"
]

SL_LAST_NAMES = [
    "Perera", "Silva", "Fernando", "Jayawardena", "Wickramasinghe", "Bandara",
    "Dissanayake", "Gunasekara", "Rathnayake", "Samaraweera", "Herath",
    "Amarasinghe", "Wijesinghe", "Rajapaksa", "Senanayake", "Karunaratne",
    "De Mel", "Cooray", "Abeysekara", "Kumarasinghe"
]

PRODUCT_CATEGORIES = {
    "electronics": ["mobile", "laptop", "tablet", "camera", "appliance", "cable", "battery", "charger"],
    "perishables": ["dairy", "meat", "seafood", "fruit", "vegetable", "bakery", "frozen"],
    "pharma": ["tablet", "capsule", "syrup", "injection", "ointment", "drops", "inhaler"],
    "industrial": ["steel", "cement", "pipe", "wire", "bolt", "chemical", "lubricant"],
    "fmcg": ["soap", "detergent", "shampoo", "toothpaste", "beverage", "snack", "rice", "flour"]
}


def sl_name():
    return f"{random.choice(SL_FIRST_NAMES)} {random.choice(SL_LAST_NAMES)}"


def sl_company_name():
    base = random.choice([
        f"{random.choice(SL_LAST_NAMES)} {random.choice(COMPANY_SUFFIXES)}",
        f"{random.choice(SL_FIRST_NAMES)}{random.choice(SL_LAST_NAMES)} {random.choice(COMPANY_SUFFIXES)}",
        f"Ceylon {fake.word().title()} {random.choice(COMPANY_SUFFIXES)}",
        f"Lanka {fake.word().title()} {random.choice(COMPANY_SUFFIXES)}",
        f"Sri {fake.word().title()} {random.choice(COMPANY_SUFFIXES)}",
    ])
    return base


async def seed_core(conn):
    """Seed all core schema tables."""
    # 1. Districts
    print("  Inserting 25 districts...")
    for d in SRI_LANKA_DISTRICTS:
        await conn.execute(
            """INSERT INTO core.districts (name, province, area_km2, lat, lng)
               VALUES ($1, $2, $3, $4, $5)""",
            d["name"], d["province"], d["area_km2"], d["lat"], d["lng"]
        )

    district_ids = [r["id"] for r in await conn.fetch("SELECT id FROM core.districts ORDER BY id")]

    # 2. Companies (500)
    print("  Inserting 500 companies...")
    companies = []
    for i in range(500):
        cid = uuid.uuid4()
        companies.append((
            cid,
            sl_company_name(),
            f"REG-{i+1:04d}-{random.randint(1000,9999)}",
            random.choice(INDUSTRIES),
            random.choice(district_ids),
            f"{random.randint(1,999)} {fake.street_name()}, {random.choice([d['name'] for d in SRI_LANKA_DISTRICTS])}",
            round(random.uniform(100000, 10000000), 2),
            random.choice([14, 30, 45, 60]),
            True,
            datetime.now() - timedelta(days=random.randint(30, 730))
        ))
    await conn.executemany(
        """INSERT INTO core.companies (id, name, registration_no, industry, district_id,
           address, credit_limit, credit_days, is_active, onboarded_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
        companies
    )

    company_ids = [c[0] for c in companies]

    # 3. Contacts (1-3 per company)
    print("  Inserting contacts...")
    contacts = []
    for cid in company_ids:
        n_contacts = random.randint(1, 3)
        for j in range(n_contacts):
            contacts.append((
                uuid.uuid4(),
                cid,
                sl_name(),
                random.choice(["CEO", "Manager", "Logistics Head", "Procurement", "Finance"]),
                f"+94{random.randint(70,79)}{random.randint(1000000,9999999)}",
                f"{fake.user_name()}@{fake.domain_name()}",
                j == 0  # first contact is primary
            ))
    await conn.executemany(
        """INSERT INTO core.contacts (id, company_id, name, role, phone, email, is_primary)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        contacts
    )

    # 4. Vendors (150)
    print("  Inserting 150 vendors...")
    vendors = []
    for i in range(150):
        vid = uuid.uuid4()
        start = datetime.now().date() - timedelta(days=random.randint(180, 720))
        vendors.append((
            vid,
            f"{random.choice(SL_LAST_NAMES)} {random.choice(VENDOR_TYPES).title()} Services",
            random.choice(VENDOR_TYPES),
            random.choice(district_ids),
            start,
            start + timedelta(days=random.choice([365, 730, 1095])),
            round(random.uniform(2.0, 5.0), 2),
            True
        ))
    await conn.executemany(
        """INSERT INTO core.vendors (id, name, vendor_type, district_id, contract_start,
           contract_end, rating, is_active)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        vendors
    )

    vendor_ids = [v[0] for v in vendors]

    # 5. Products (2000)
    print("  Inserting 2,000 products...")
    products = []
    sku_counter = 0
    for category, subcats in PRODUCT_CATEGORIES.items():
        cat_upper = category[:4].upper()
        n_products = 400  # 400 per category = 2000 total
        for i in range(n_products):
            sku_counter += 1
            subcat = random.choice(subcats)
            products.append((
                uuid.uuid4(),
                f"SKU-{cat_upper}-{sku_counter:04d}",
                f"{subcat.title()} {fake.word().title()} {random.choice(['Pro','Plus','Lite','Max',''])}".strip(),
                category,
                subcat,
                round(random.uniform(0.1, 500.0), 3),
                round(random.uniform(0.001, 2.0), 4),
                category == "industrial" and random.random() < 0.1,
                category == "perishables" or (category == "pharma" and random.random() < 0.3),
                round(random.uniform(50, 50000), 2),
                random.choice(vendor_ids)
            ))
    await conn.executemany(
        """INSERT INTO core.products (id, sku, name, category, subcategory, weight_kg,
           volume_m3, is_hazardous, requires_cold, unit_value, vendor_id)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
        products
    )

    print(f"  Core seeding complete: {len(district_ids)} districts, {len(companies)} companies, "
          f"{len(contacts)} contacts, {len(vendors)} vendors, {len(products)} products")
