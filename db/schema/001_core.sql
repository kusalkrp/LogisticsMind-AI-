-- Geographic regions of Sri Lanka
CREATE TABLE core.districts (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    province      VARCHAR(100) NOT NULL,
    area_km2      DECIMAL(10,2),
    lat           DECIMAL(9,6),
    lng           DECIMAL(9,6)
);

CREATE INDEX idx_districts_province ON core.districts(province);

-- Company master (CeyLog's clients)
CREATE TABLE core.companies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    registration_no VARCHAR(50) UNIQUE,
    industry        VARCHAR(100),
    district_id     INTEGER REFERENCES core.districts(id),
    address         TEXT,
    credit_limit    DECIMAL(15,2),
    credit_days     INTEGER DEFAULT 30,
    is_active       BOOLEAN DEFAULT TRUE,
    onboarded_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_companies_district ON core.companies(district_id);
CREATE INDEX idx_companies_industry ON core.companies(industry);
CREATE INDEX idx_companies_is_active ON core.companies(is_active);
CREATE INDEX idx_companies_onboarded_at ON core.companies(onboarded_at);

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

CREATE INDEX idx_contacts_company ON core.contacts(company_id);

-- Vendor master (suppliers to CeyLog)
CREATE TABLE core.vendors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    vendor_type     VARCHAR(100),
    district_id     INTEGER REFERENCES core.districts(id),
    contract_start  DATE,
    contract_end    DATE,
    rating          DECIMAL(3,2),
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_vendors_district ON core.vendors(district_id);
CREATE INDEX idx_vendors_type ON core.vendors(vendor_type);
CREATE INDEX idx_vendors_is_active ON core.vendors(is_active);

-- Product catalogue
CREATE TABLE core.products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku             VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    category        VARCHAR(100),
    subcategory     VARCHAR(100),
    weight_kg       DECIMAL(8,3),
    volume_m3       DECIMAL(8,4),
    is_hazardous    BOOLEAN DEFAULT FALSE,
    requires_cold   BOOLEAN DEFAULT FALSE,
    unit_value      DECIMAL(12,2),
    vendor_id       UUID REFERENCES core.vendors(id)
);

CREATE INDEX idx_products_category ON core.products(category);
CREATE INDEX idx_products_vendor ON core.products(vendor_id);
CREATE INDEX idx_products_sku ON core.products(sku);
