# LogisticsMind AI — System Design

> Production-scale Sri Lankan logistics & supply chain intelligence platform.
> Conversational AI agent over a complex relational database.
> Portfolio-grade. Built on Conversify.

---

## 1. Vision

LogisticsMind AI is a natural language analytics platform for a fictional
Sri Lankan logistics company — **CeyLog** — operating island-wide with
warehouses, fleets, vendors, and thousands of daily shipments.

A logistics analyst opens a chat and asks:
- "Which routes had the most delays last month?"
- "Show me warehouse utilisation across all districts"
- "Are there any unusual patterns in Colombo shipments this week?"
- "Forecast next quarter's freight volume for the Northern Province"

The AI agent answers in plain English, generates charts, detects anomalies,
and forecasts trends — using nothing but conversation.

---

## 2. The Database — CeyLog Production Schema

### 18 Tables, 4 Schemas, 200k+ Mock Rows

```
ceylog/
├── core/           — master data (companies, locations, contacts)
├── fleet/          — vehicles, drivers, routes, trips
├── warehouse/      — facilities, inventory, movements, capacity
├── operations/     — shipments, orders, tracking, incidents
└── finance/        — invoices, payments, costs, SLAs
```

### Entity Relationship Overview

```
                    ┌─────────────┐
                    │   vendors   │
                    └──────┬──────┘
                           │ supplies
                    ┌──────▼──────┐
                    │  products   │
                    └──────┬──────┘
                           │ stored in
          ┌────────────────▼───────────────────┐
          │              warehouses             │
          │  (inventory_items, stock_movements) │
          └────────────────┬───────────────────┘
                           │ dispatched via
     ┌─────────────────────▼──────────────────────┐
     │                  shipments                  │
     │  (orders → shipments → tracking_events)     │
     └──────┬──────────────────────────┬───────────┘
            │                          │
     ┌──────▼──────┐           ┌───────▼──────┐
     │    trips    │           │   incidents   │
     │  (vehicle + │           │  (delays,     │
     │   driver +  │           │   damage,     │
     │   route)    │           │   theft)      │
     └──────┬──────┘           └───────────────┘
            │
     ┌──────▼──────┐
     │   vehicles  │
     │   drivers   │
     │   routes    │
     └─────────────┘
```

---

## 3. Full Database Schema

### Schema: core

```sql
-- Geographic regions of Sri Lanka
CREATE TABLE core.districts (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    province      VARCHAR(100) NOT NULL,
    area_km2      DECIMAL(10,2),
    lat           DECIMAL(9,6),
    lng           DECIMAL(9,6)
);
-- 25 rows — all Sri Lanka districts

-- Company master (CeyLog's clients)
CREATE TABLE core.companies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    registration_no VARCHAR(50) UNIQUE,
    industry        VARCHAR(100),   -- retail, manufacturing, pharma, fmcg, agriculture
    district_id     INTEGER REFERENCES core.districts(id),
    address         TEXT,
    credit_limit    DECIMAL(15,2),
    credit_days     INTEGER DEFAULT 30,
    is_active       BOOLEAN DEFAULT TRUE,
    onboarded_at    TIMESTAMP DEFAULT NOW()
);
-- ~500 rows

-- Contacts per company
CREATE TABLE core.contacts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID REFERENCES core.companies(id),
    name        VARCHAR(255),
    role        VARCHAR(100),
    phone       VARCHAR(20),
    email       VARCHAR(255),
    is_primary  BOOLEAN DEFAULT FALSE
);

-- Vendor master (suppliers to CeyLog)
CREATE TABLE core.vendors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    vendor_type     VARCHAR(100),  -- fuel, maintenance, packaging, cold_chain
    district_id     INTEGER REFERENCES core.districts(id),
    contract_start  DATE,
    contract_end    DATE,
    rating          DECIMAL(3,2),  -- 1.00 - 5.00
    is_active       BOOLEAN DEFAULT TRUE
);
-- ~150 rows

-- Product catalogue
CREATE TABLE core.products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku             VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    category        VARCHAR(100),  -- electronics, perishables, pharma, industrial, fmcg
    subcategory     VARCHAR(100),
    weight_kg       DECIMAL(8,3),
    volume_m3       DECIMAL(8,4),
    is_hazardous    BOOLEAN DEFAULT FALSE,
    requires_cold   BOOLEAN DEFAULT FALSE,
    unit_value      DECIMAL(12,2),
    vendor_id       UUID REFERENCES core.vendors(id)
);
-- ~2,000 rows
```

---

### Schema: warehouse

```sql
-- Warehouse facilities
CREATE TABLE warehouse.facilities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(20) UNIQUE NOT NULL,  -- WH-COL-01, WH-KAN-01
    name            VARCHAR(255),
    district_id     INTEGER REFERENCES core.districts(id),
    facility_type   VARCHAR(50),   -- distribution_center, cold_storage, bonded, transit
    capacity_m3     DECIMAL(12,2),
    current_util_pct DECIMAL(5,2), -- computed / updated daily
    has_cold_chain  BOOLEAN DEFAULT FALSE,
    has_hazmat      BOOLEAN DEFAULT FALSE,
    lat             DECIMAL(9,6),
    lng             DECIMAL(9,6),
    opened_at       DATE,
    is_active       BOOLEAN DEFAULT TRUE
);
-- 18 rows — major CeyLog warehouses island-wide

-- Inventory positions
CREATE TABLE warehouse.inventory_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID REFERENCES warehouse.facilities(id),
    product_id      UUID REFERENCES core.products(id),
    company_id      UUID REFERENCES core.companies(id),
    quantity        INTEGER NOT NULL DEFAULT 0,
    reserved_qty    INTEGER NOT NULL DEFAULT 0,  -- allocated to pending shipments
    batch_no        VARCHAR(100),
    expiry_date     DATE,
    unit_cost       DECIMAL(12,2),
    last_counted_at TIMESTAMP,
    location_code   VARCHAR(50),    -- aisle-rack-bin within warehouse
    UNIQUE (facility_id, product_id, company_id, batch_no)
);
-- ~40,000 rows

-- Every stock movement (receipts, dispatches, adjustments, transfers)
CREATE TABLE warehouse.stock_movements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID REFERENCES warehouse.facilities(id),
    product_id      UUID REFERENCES core.products(id),
    company_id      UUID REFERENCES core.companies(id),
    movement_type   VARCHAR(50),   -- receipt, dispatch, transfer_in, transfer_out, adjustment, damage
    quantity        INTEGER NOT NULL,
    reference_id    UUID,          -- shipment_id or purchase_order_id
    unit_cost       DECIMAL(12,2),
    moved_by        UUID,          -- staff id
    moved_at        TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);
-- ~150,000 rows — 2 years of history

-- Warehouse staff
CREATE TABLE warehouse.staff (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID REFERENCES warehouse.facilities(id),
    name            VARCHAR(255),
    role            VARCHAR(100),  -- manager, picker, loader, security, supervisor
    shift           VARCHAR(20),   -- morning, afternoon, night
    hired_at        DATE,
    is_active       BOOLEAN DEFAULT TRUE
);
-- ~300 rows
```

---

### Schema: fleet

```sql
-- Vehicle master
CREATE TABLE fleet.vehicles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plate_no        VARCHAR(20) UNIQUE NOT NULL,
    vehicle_type    VARCHAR(50),    -- lorry, van, motorbike, refrigerated_truck, container
    make            VARCHAR(100),
    model           VARCHAR(100),
    year            INTEGER,
    capacity_kg     DECIMAL(10,2),
    capacity_m3     DECIMAL(10,2),
    has_cold_chain  BOOLEAN DEFAULT FALSE,
    has_gps         BOOLEAN DEFAULT TRUE,
    fuel_type       VARCHAR(20),    -- diesel, petrol, electric, hybrid
    base_facility   UUID REFERENCES warehouse.facilities(id),
    status          VARCHAR(30),    -- active, maintenance, retired, breakdown
    last_service_at DATE,
    next_service_at DATE,
    purchased_at    DATE,
    mileage_km      INTEGER
);
-- ~200 rows

-- Driver master
CREATE TABLE fleet.drivers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     VARCHAR(20) UNIQUE,
    name            VARCHAR(255),
    license_no      VARCHAR(50),
    license_type    VARCHAR(20),    -- B1, B2, C1, CE (heavy vehicle classes)
    license_expiry  DATE,
    phone           VARCHAR(20),
    district_id     INTEGER REFERENCES core.districts(id),
    base_facility   UUID REFERENCES warehouse.facilities(id),
    rating          DECIMAL(3,2),  -- computed from delivery performance
    total_trips     INTEGER DEFAULT 0,
    hired_at        DATE,
    is_active       BOOLEAN DEFAULT TRUE
);
-- ~180 rows

-- Route definitions (fixed recurring routes)
CREATE TABLE fleet.routes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(30) UNIQUE,   -- RT-COL-KAN-001
    name            VARCHAR(255),
    origin_district INTEGER REFERENCES core.districts(id),
    dest_district   INTEGER REFERENCES core.districts(id),
    distance_km     DECIMAL(8,2),
    est_duration_hr DECIMAL(5,2),
    route_type      VARCHAR(30),   -- express, standard, rural, cross_province
    waypoints       JSONB,         -- [{district_id, order, est_minutes}]
    is_active       BOOLEAN DEFAULT TRUE
);
-- ~80 routes

-- Individual trips (vehicle + driver + route + date)
CREATE TABLE fleet.trips (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id        UUID REFERENCES fleet.routes(id),
    vehicle_id      UUID REFERENCES fleet.vehicles(id),
    driver_id       UUID REFERENCES fleet.drivers(id),
    trip_date       DATE NOT NULL,
    scheduled_depart TIMESTAMP,
    actual_depart   TIMESTAMP,
    scheduled_arrive TIMESTAMP,
    actual_arrive   TIMESTAMP,
    status          VARCHAR(30),   -- scheduled, in_transit, completed, cancelled, breakdown
    distance_actual_km DECIMAL(8,2),
    fuel_used_l     DECIMAL(8,2),
    fuel_cost       DECIMAL(10,2),
    toll_cost       DECIMAL(8,2),
    notes           TEXT
);
-- ~15,000 rows — 2 years

-- GPS tracking pings per trip
CREATE TABLE fleet.gps_pings (
    id          BIGSERIAL PRIMARY KEY,
    trip_id     UUID REFERENCES fleet.trips(id),
    lat         DECIMAL(9,6),
    lng         DECIMAL(9,6),
    speed_kmh   DECIMAL(6,2),
    heading     DECIMAL(5,2),
    recorded_at TIMESTAMP NOT NULL
);
-- ~500,000 rows (partitioned by month)

-- Vehicle maintenance records
CREATE TABLE fleet.maintenance_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id      UUID REFERENCES fleet.vehicles(id),
    vendor_id       UUID REFERENCES core.vendors(id),
    service_type    VARCHAR(100),  -- oil_change, tyre, engine, electrical, body
    description     TEXT,
    cost            DECIMAL(10,2),
    mileage_at_service INTEGER,
    serviced_at     TIMESTAMP,
    next_due_km     INTEGER,
    next_due_date   DATE
);
-- ~3,000 rows
```

---

### Schema: operations

```sql
-- Customer orders
CREATE TABLE operations.orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no        VARCHAR(30) UNIQUE NOT NULL,  -- ORD-2024-00001
    company_id      UUID REFERENCES core.companies(id),
    contact_id      UUID REFERENCES core.contacts(id),
    order_type      VARCHAR(50),   -- standard, express, bulk, cold_chain, hazmat
    priority        VARCHAR(20),   -- low, normal, high, critical
    origin_facility UUID REFERENCES warehouse.facilities(id),
    dest_district   INTEGER REFERENCES core.districts(id),
    dest_address    TEXT,
    dest_lat        DECIMAL(9,6),
    dest_lng        DECIMAL(9,6),
    requested_by    TIMESTAMP,     -- customer's requested delivery date
    status          VARCHAR(30),   -- draft, confirmed, processing, dispatched, delivered, cancelled
    special_instructions TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
-- ~25,000 rows

-- Order line items
CREATE TABLE operations.order_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id    UUID REFERENCES operations.orders(id),
    product_id  UUID REFERENCES core.products(id),
    quantity    INTEGER NOT NULL,
    unit_price  DECIMAL(12,2),
    total_price DECIMAL(14,2)
);
-- ~60,000 rows

-- Shipments (one order can split into multiple shipments)
CREATE TABLE operations.shipments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_no     VARCHAR(30) UNIQUE,   -- SHP-2024-00001
    order_id        UUID REFERENCES operations.orders(id),
    trip_id         UUID REFERENCES fleet.trips(id),
    origin_facility UUID REFERENCES warehouse.facilities(id),
    dest_district   INTEGER REFERENCES core.districts(id),
    dest_address    TEXT,
    weight_kg       DECIMAL(10,2),
    volume_m3       DECIMAL(10,2),
    status          VARCHAR(30),   -- created, picked, loaded, in_transit, delivered, returned, lost
    scheduled_pickup  TIMESTAMP,
    actual_pickup     TIMESTAMP,
    scheduled_delivery TIMESTAMP,
    actual_delivery   TIMESTAMP,
    delivery_photo  VARCHAR(500),  -- S3 URL
    recipient_name  VARCHAR(255),
    recipient_sig   BOOLEAN DEFAULT FALSE,
    pod_notes       TEXT           -- proof of delivery notes
);
-- ~28,000 rows

-- Tracking events per shipment (full audit trail)
CREATE TABLE operations.tracking_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID REFERENCES operations.shipments(id),
    event_type      VARCHAR(50),   -- created, picked_up, in_warehouse, loaded, departed,
                                   -- arrived_hub, out_for_delivery, delivered, failed_attempt,
                                   -- returned, exception
    facility_id     UUID REFERENCES warehouse.facilities(id),
    trip_id         UUID REFERENCES fleet.trips(id),
    lat             DECIMAL(9,6),
    lng             DECIMAL(9,6),
    notes           TEXT,
    recorded_by     UUID,
    recorded_at     TIMESTAMP DEFAULT NOW()
);
-- ~180,000 rows

-- Incidents (delays, damage, theft, accidents)
CREATE TABLE operations.incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_no     VARCHAR(30) UNIQUE,
    incident_type   VARCHAR(50),   -- delay, damage, theft, accident, weather, breakdown,
                                   -- customer_rejection, wrong_address
    severity        VARCHAR(20),   -- low, medium, high, critical
    shipment_id     UUID REFERENCES operations.shipments(id),
    trip_id         UUID REFERENCES fleet.trips(id),
    vehicle_id      UUID REFERENCES fleet.vehicles(id),
    driver_id       UUID REFERENCES fleet.drivers(id),
    district_id     INTEGER REFERENCES core.districts(id),
    description     TEXT,
    financial_impact DECIMAL(12,2),
    resolved        BOOLEAN DEFAULT FALSE,
    occurred_at     TIMESTAMP,
    reported_at     TIMESTAMP DEFAULT NOW(),
    resolved_at     TIMESTAMP
);
-- ~2,500 rows

-- SLA definitions per company/order_type
CREATE TABLE operations.sla_contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID REFERENCES core.companies(id),
    order_type      VARCHAR(50),
    max_transit_hr  INTEGER,       -- hours allowed
    penalty_per_hr  DECIMAL(10,2), -- LKR per hour breach
    free_attempts   INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE
);
-- ~800 rows
```

---

### Schema: finance

```sql
-- Invoices raised to customers
CREATE TABLE finance.invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_no      VARCHAR(30) UNIQUE,
    company_id      UUID REFERENCES core.companies(id),
    order_id        UUID REFERENCES operations.orders(id),
    invoice_date    DATE,
    due_date        DATE,
    subtotal        DECIMAL(14,2),
    tax_amount      DECIMAL(12,2),
    discount_amount DECIMAL(12,2),
    total_amount    DECIMAL(14,2),
    paid_amount     DECIMAL(14,2) DEFAULT 0,
    status          VARCHAR(30),   -- draft, sent, partial, paid, overdue, written_off
    currency        VARCHAR(3) DEFAULT 'LKR'
);
-- ~24,000 rows

-- Payments received
CREATE TABLE finance.payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID REFERENCES finance.invoices(id),
    company_id      UUID REFERENCES core.companies(id),
    amount          DECIMAL(14,2),
    payment_method  VARCHAR(50),   -- bank_transfer, cheque, cash, online
    reference_no    VARCHAR(100),
    payment_date    DATE,
    received_at     TIMESTAMP DEFAULT NOW()
);
-- ~22,000 rows

-- Operational costs (fuel, maintenance, warehouse ops)
CREATE TABLE finance.operational_costs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cost_type       VARCHAR(50),   -- fuel, maintenance, labour, warehouse_rent,
                                   -- insurance, toll, sla_penalty, damage_claim
    reference_id    UUID,          -- trip_id, maintenance_id, incident_id etc
    facility_id     UUID REFERENCES warehouse.facilities(id),
    vendor_id       UUID REFERENCES core.vendors(id),
    amount          DECIMAL(14,2),
    description     TEXT,
    cost_date       DATE,
    approved_by     UUID,
    created_at      TIMESTAMP DEFAULT NOW()
);
-- ~35,000 rows

-- SLA breach tracking
CREATE TABLE finance.sla_breaches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID REFERENCES operations.shipments(id),
    sla_contract_id UUID REFERENCES operations.sla_contracts(id),
    breach_hours    DECIMAL(8,2),
    penalty_amount  DECIMAL(12,2),
    waived          BOOLEAN DEFAULT FALSE,
    waive_reason    TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
-- ~3,200 rows
```

---

## 4. Mock Data Scale

| Table | Rows | Notes |
|-------|------|-------|
| core.districts | 25 | All Sri Lanka districts |
| core.companies | 500 | Fictional clients |
| core.vendors | 150 | Suppliers and contractors |
| core.products | 2,000 | Mixed categories |
| warehouse.facilities | 18 | Island-wide warehouses |
| warehouse.inventory_items | 40,000 | Current stock positions |
| warehouse.stock_movements | 150,000 | 2 years history |
| fleet.vehicles | 200 | Mixed fleet |
| fleet.drivers | 180 | Active + inactive |
| fleet.routes | 80 | Defined routes |
| fleet.trips | 15,000 | 2 years history |
| fleet.gps_pings | 500,000 | Partitioned by month |
| operations.orders | 25,000 | 2 years |
| operations.order_items | 60,000 | Line items |
| operations.shipments | 28,000 | 2 years |
| operations.tracking_events | 180,000 | Full audit trail |
| operations.incidents | 2,500 | Incidents and exceptions |
| finance.invoices | 24,000 | Billing history |
| finance.payments | 22,000 | Payment receipts |
| finance.operational_costs | 35,000 | Cost records |
| **TOTAL** | **~1.1M rows** | |

---

## 5. Embedded Anomalies (For AI Detection)

The mock data includes deliberate patterns for the AI to discover:

| Anomaly | What It Is | Where |
|---------|-----------|-------|
| Route RT-COL-JAF-003 | 40% higher delay rate than similar routes | fleet.trips |
| Driver DRV-0042 | Fuel consumption 2x fleet average | fleet.trips |
| Warehouse WH-GAL-01 | Capacity always reported at exactly 87% | warehouse.facilities |
| Company COMP-0187 | Pays invoices 15 days late consistently | finance.payments |
| Product SKU-PHARM-099 | Damage rate 5x category average | operations.incidents |
| November spike | Shipment volume +60% every November (seasonal) | operations.shipments |
| Colombo → Jaffna | Delivery success rate drops 30% in rainy months | operations.shipments |
| Vehicle VH-0031 | Breakdown every ~8,000km exactly | fleet.maintenance_logs |

---

## 6. AI Agent Architecture

### Built on Conversify

```python
agent = ConversifyAgent(
    persona=LOGISTICSMIND_PERSONA,
    tools=[
        query_database,
        generate_chart,
        detect_anomalies,
        forecast_metric,
        explain_query,
        get_schema_info,
    ],
    llm="gemini"
)
```

### The 6 Agent Tools

**1. query_database**
Converts natural language to SQL, executes it, returns results.
Handles joins across all 5 schemas automatically.

**2. generate_chart**
Takes query results and renders charts: bar, line, pie, heatmap,
map (choropleth by district), scatter.
Returns chart as base64 PNG or Plotly JSON.

**3. detect_anomalies**
Runs statistical analysis over a specified metric and time window.
Returns outliers with explanations.

**4. forecast_metric**
Uses time-series forecasting (Prophet or simple linear regression)
to project a metric N periods forward.

**5. explain_query**
Shows the SQL that was generated for any natural language question.
Useful for building trust with analysts.

**6. get_schema_info**
Returns table/column descriptions when the agent needs to
understand the data model before querying.

---

## 7. Example Conversations

```
User: Which routes have the worst on-time delivery rate?

Agent: [calls query_database]
       [calls generate_chart → bar chart]
       "The 5 worst-performing routes by on-time rate are:
        1. RT-COL-JAF-003: 58% on-time (vs 89% network average)
        2. RT-KAN-BAT-007: 71% on-time
        ...
        RT-COL-JAF-003 stands out significantly — want me to
        investigate what's driving its delays?"

User: Yes, dig into it

Agent: [calls query_database → incident types on that route]
       [calls detect_anomalies → fuel and timing patterns]
       "Three factors are driving the JAF-003 delays:
        - 67% of delays occur during June-October (monsoon season)
        - Vehicle VH-0089 accounts for 40% of trips on this route
          and has the highest breakdown rate in the fleet
        - Average loading time at WH-COL-02 is 2.3hr vs 1.1hr
          fleet average — a warehouse bottleneck"

User: Show me warehouse utilisation across all districts as a map

Agent: [calls query_database → current utilisation by district]
       [calls generate_chart → choropleth map]
       [renders Sri Lanka map with colour-coded utilisation]
       "Colombo district warehouses are at 94% utilisation —
        critically high. Northern Province is at 31%.
        Want me to model the cost of redistributing inventory?"
```

---

## 8. Technology Stack

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 (with TimescaleDB for gps_pings) |
| Mock data | Python + Faker + custom generators |
| Agent framework | Conversify (built on LangGraph) |
| LLM | Gemini 1.5 Pro |
| SQL generation | LLM + schema context injection |
| Charts | Plotly (interactive) + Matplotlib (static) |
| Forecasting | Facebook Prophet |
| Anomaly detection | statistical z-score + IQR + LLM explanation |
| API | FastAPI |
| Frontend | React + Recharts dashboard |
| Auth | API key per session |

---

## 9. What Makes This Portfolio-Grade

1. **18 tables across 5 schemas** — complex real-world relational design
2. **1.1M mock rows** — production-scale data volume
3. **Embedded anomalies** — AI has real patterns to discover
4. **Geographic data** — Sri Lanka districts with lat/lng
5. **Time-series history** — 2 years of operational data
6. **Conversify integration** — demonstrates the framework in action
7. **Full analytics stack** — NL query + charts + anomaly + forecast
8. **Real business logic** — SLA breaches, credit limits, cold chain

Any recruiter or client seeing this immediately understands: this person
can design complex systems and build AI that works on real data.
