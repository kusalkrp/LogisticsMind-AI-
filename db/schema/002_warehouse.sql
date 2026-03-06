-- Warehouse facilities
CREATE TABLE warehouse.facilities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(20) UNIQUE NOT NULL,
    name            VARCHAR(255),
    district_id     INTEGER REFERENCES core.districts(id),
    facility_type   VARCHAR(50),
    capacity_m3     DECIMAL(12,2),
    current_util_pct DECIMAL(5,2),
    has_cold_chain  BOOLEAN DEFAULT FALSE,
    has_hazmat      BOOLEAN DEFAULT FALSE,
    lat             DECIMAL(9,6),
    lng             DECIMAL(9,6),
    opened_at       DATE,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_facilities_district ON warehouse.facilities(district_id);
CREATE INDEX idx_facilities_type ON warehouse.facilities(facility_type);
CREATE INDEX idx_facilities_is_active ON warehouse.facilities(is_active);

-- Inventory positions
CREATE TABLE warehouse.inventory_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID REFERENCES warehouse.facilities(id),
    product_id      UUID REFERENCES core.products(id),
    company_id      UUID REFERENCES core.companies(id),
    quantity        INTEGER NOT NULL DEFAULT 0,
    reserved_qty    INTEGER NOT NULL DEFAULT 0,
    batch_no        VARCHAR(100),
    expiry_date     DATE,
    unit_cost       DECIMAL(12,2),
    last_counted_at TIMESTAMP,
    location_code   VARCHAR(50),
    UNIQUE (facility_id, product_id, company_id, batch_no)
);

CREATE INDEX idx_inventory_facility ON warehouse.inventory_items(facility_id);
CREATE INDEX idx_inventory_product ON warehouse.inventory_items(product_id);
CREATE INDEX idx_inventory_company ON warehouse.inventory_items(company_id);

-- Every stock movement
CREATE TABLE warehouse.stock_movements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID REFERENCES warehouse.facilities(id),
    product_id      UUID REFERENCES core.products(id),
    company_id      UUID REFERENCES core.companies(id),
    movement_type   VARCHAR(50),
    quantity        INTEGER NOT NULL,
    reference_id    UUID,
    unit_cost       DECIMAL(12,2),
    moved_by        UUID,
    moved_at        TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);

CREATE INDEX idx_stock_movements_facility ON warehouse.stock_movements(facility_id);
CREATE INDEX idx_stock_movements_product ON warehouse.stock_movements(product_id);
CREATE INDEX idx_stock_movements_type ON warehouse.stock_movements(movement_type);
CREATE INDEX idx_stock_movements_moved_at ON warehouse.stock_movements(moved_at);

-- Warehouse staff
CREATE TABLE warehouse.staff (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id     UUID REFERENCES warehouse.facilities(id),
    name            VARCHAR(255),
    role            VARCHAR(100),
    shift           VARCHAR(20),
    hired_at        DATE,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_staff_facility ON warehouse.staff(facility_id);
