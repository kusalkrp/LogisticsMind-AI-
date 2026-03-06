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
    status          VARCHAR(30),
    currency        VARCHAR(3) DEFAULT 'LKR'
);

CREATE INDEX idx_invoices_company ON finance.invoices(company_id);
CREATE INDEX idx_invoices_order ON finance.invoices(order_id);
CREATE INDEX idx_invoices_status ON finance.invoices(status);
CREATE INDEX idx_invoices_due_date ON finance.invoices(due_date);
CREATE INDEX idx_invoices_invoice_date ON finance.invoices(invoice_date);

-- Payments received
CREATE TABLE finance.payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID REFERENCES finance.invoices(id),
    company_id      UUID REFERENCES core.companies(id),
    amount          DECIMAL(14,2),
    payment_method  VARCHAR(50),
    reference_no    VARCHAR(100),
    payment_date    DATE,
    received_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_invoice ON finance.payments(invoice_id);
CREATE INDEX idx_payments_company ON finance.payments(company_id);
CREATE INDEX idx_payments_date ON finance.payments(payment_date);

-- Operational costs
CREATE TABLE finance.operational_costs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cost_type       VARCHAR(50),
    reference_id    UUID,
    facility_id     UUID REFERENCES warehouse.facilities(id),
    vendor_id       UUID REFERENCES core.vendors(id),
    amount          DECIMAL(14,2),
    description     TEXT,
    cost_date       DATE,
    approved_by     UUID,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_opcosts_type ON finance.operational_costs(cost_type);
CREATE INDEX idx_opcosts_facility ON finance.operational_costs(facility_id);
CREATE INDEX idx_opcosts_vendor ON finance.operational_costs(vendor_id);
CREATE INDEX idx_opcosts_date ON finance.operational_costs(cost_date);

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

CREATE INDEX idx_sla_breaches_shipment ON finance.sla_breaches(shipment_id);
CREATE INDEX idx_sla_breaches_contract ON finance.sla_breaches(sla_contract_id);
CREATE INDEX idx_sla_breaches_created_at ON finance.sla_breaches(created_at);
