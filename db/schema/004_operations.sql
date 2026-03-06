-- Customer orders
CREATE TABLE operations.orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no        VARCHAR(30) UNIQUE NOT NULL,
    company_id      UUID REFERENCES core.companies(id),
    contact_id      UUID REFERENCES core.contacts(id),
    order_type      VARCHAR(50),
    priority        VARCHAR(20),
    origin_facility UUID REFERENCES warehouse.facilities(id),
    dest_district   INTEGER REFERENCES core.districts(id),
    dest_address    TEXT,
    dest_lat        DECIMAL(9,6),
    dest_lng        DECIMAL(9,6),
    requested_by    TIMESTAMP,
    status          VARCHAR(30),
    special_instructions TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_company ON operations.orders(company_id);
CREATE INDEX idx_orders_status ON operations.orders(status);
CREATE INDEX idx_orders_created_at ON operations.orders(created_at);
CREATE INDEX idx_orders_origin ON operations.orders(origin_facility);
CREATE INDEX idx_orders_dest_district ON operations.orders(dest_district);
CREATE INDEX idx_orders_type ON operations.orders(order_type);

-- Order line items
CREATE TABLE operations.order_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id    UUID REFERENCES operations.orders(id),
    product_id  UUID REFERENCES core.products(id),
    quantity    INTEGER NOT NULL,
    unit_price  DECIMAL(12,2),
    total_price DECIMAL(14,2)
);

CREATE INDEX idx_order_items_order ON operations.order_items(order_id);
CREATE INDEX idx_order_items_product ON operations.order_items(product_id);

-- Shipments (one order can split into multiple shipments)
CREATE TABLE operations.shipments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_no     VARCHAR(30) UNIQUE,
    order_id        UUID REFERENCES operations.orders(id),
    trip_id         UUID REFERENCES fleet.trips(id),
    origin_facility UUID REFERENCES warehouse.facilities(id),
    dest_district   INTEGER REFERENCES core.districts(id),
    dest_address    TEXT,
    weight_kg       DECIMAL(10,2),
    volume_m3       DECIMAL(10,2),
    status          VARCHAR(30),
    scheduled_pickup  TIMESTAMP,
    actual_pickup     TIMESTAMP,
    scheduled_delivery TIMESTAMP,
    actual_delivery   TIMESTAMP,
    delivery_photo  VARCHAR(500),
    recipient_name  VARCHAR(255),
    recipient_sig   BOOLEAN DEFAULT FALSE,
    pod_notes       TEXT
);

CREATE INDEX idx_shipments_order ON operations.shipments(order_id);
CREATE INDEX idx_shipments_trip ON operations.shipments(trip_id);
CREATE INDEX idx_shipments_status ON operations.shipments(status);
CREATE INDEX idx_shipments_origin ON operations.shipments(origin_facility);
CREATE INDEX idx_shipments_dest ON operations.shipments(dest_district);
CREATE INDEX idx_shipments_scheduled_delivery ON operations.shipments(scheduled_delivery);
CREATE INDEX idx_shipments_actual_delivery ON operations.shipments(actual_delivery);

-- Tracking events per shipment
CREATE TABLE operations.tracking_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID REFERENCES operations.shipments(id),
    event_type      VARCHAR(50),
    facility_id     UUID REFERENCES warehouse.facilities(id),
    trip_id         UUID REFERENCES fleet.trips(id),
    lat             DECIMAL(9,6),
    lng             DECIMAL(9,6),
    notes           TEXT,
    recorded_by     UUID,
    recorded_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tracking_shipment ON operations.tracking_events(shipment_id);
CREATE INDEX idx_tracking_event_type ON operations.tracking_events(event_type);
CREATE INDEX idx_tracking_recorded_at ON operations.tracking_events(recorded_at);

-- Incidents (delays, damage, theft, accidents)
CREATE TABLE operations.incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_no     VARCHAR(30) UNIQUE,
    incident_type   VARCHAR(50),
    severity        VARCHAR(20),
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

CREATE INDEX idx_incidents_type ON operations.incidents(incident_type);
CREATE INDEX idx_incidents_severity ON operations.incidents(severity);
CREATE INDEX idx_incidents_shipment ON operations.incidents(shipment_id);
CREATE INDEX idx_incidents_trip ON operations.incidents(trip_id);
CREATE INDEX idx_incidents_district ON operations.incidents(district_id);
CREATE INDEX idx_incidents_occurred_at ON operations.incidents(occurred_at);

-- SLA definitions per company/order_type
CREATE TABLE operations.sla_contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID REFERENCES core.companies(id),
    order_type      VARCHAR(50),
    max_transit_hr  INTEGER,
    penalty_per_hr  DECIMAL(10,2),
    free_attempts   INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_sla_company ON operations.sla_contracts(company_id);
