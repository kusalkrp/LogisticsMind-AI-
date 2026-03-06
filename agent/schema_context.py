"""Full schema context for SQL generation — injected into LLM prompts."""

SCHEMA_CONTEXT = """
## CeyLog Logistics Database Schema

### Schema: core
- core.districts (id SERIAL PK, name, province, area_km2, lat, lng) — 25 Sri Lankan districts
- core.companies (id UUID PK, name, registration_no, industry, district_id FK→districts, address, credit_limit, credit_days, is_active, onboarded_at) — 500 client companies
- core.contacts (id UUID PK, company_id FK→companies, name, role, phone, email, is_primary) — company contacts
- core.vendors (id UUID PK, name, vendor_type [fuel/maintenance/packaging/cold_chain], district_id FK→districts, contract_start, contract_end, rating, is_active) — 150 suppliers
- core.products (id UUID PK, sku, name, category [electronics/perishables/pharma/industrial/fmcg], subcategory, weight_kg, volume_m3, is_hazardous, requires_cold, unit_value, vendor_id FK→vendors) — 2,000 products

### Schema: warehouse
- warehouse.facilities (id UUID PK, code, name, district_id FK→districts, facility_type [distribution_center/cold_storage/bonded/transit], capacity_m3, current_util_pct, has_cold_chain, has_hazmat, lat, lng, opened_at, is_active) — 18 warehouses
- warehouse.inventory_items (id UUID PK, facility_id FK→facilities, product_id FK→products, company_id FK→companies, quantity, reserved_qty, batch_no, expiry_date, unit_cost, last_counted_at, location_code) — 40,000 stock positions
- warehouse.stock_movements (id UUID PK, facility_id FK, product_id FK, company_id FK, movement_type [receipt/dispatch/transfer_in/transfer_out/adjustment/damage], quantity, reference_id, unit_cost, moved_by, moved_at, notes) — 150,000 movements over 2 years
- warehouse.staff (id UUID PK, facility_id FK, name, role [manager/picker/loader/security/supervisor], shift [morning/afternoon/night], hired_at, is_active) — 300 staff

### Schema: fleet
- fleet.vehicles (id UUID PK, plate_no UNIQUE, vehicle_type [lorry/van/motorbike/refrigerated_truck/container], make, model, year, capacity_kg, capacity_m3, has_cold_chain, has_gps, fuel_type [diesel/petrol/electric/hybrid], base_facility FK→facilities, status [active/maintenance/retired/breakdown], last_service_at, next_service_at, purchased_at, mileage_km) — 200 vehicles
- fleet.drivers (id UUID PK, employee_id UNIQUE, name, license_no, license_type [B1/B2/C1/CE], license_expiry, phone, district_id FK→districts, base_facility FK→facilities, rating, total_trips, hired_at, is_active) — 180 drivers
- fleet.routes (id UUID PK, code UNIQUE, name, origin_district FK→districts, dest_district FK→districts, distance_km, est_duration_hr, route_type [express/standard/rural/cross_province], waypoints JSONB, is_active) — 80 routes
- fleet.trips (id UUID PK, route_id FK→routes, vehicle_id FK→vehicles, driver_id FK→drivers, trip_date DATE, scheduled_depart, actual_depart, scheduled_arrive, actual_arrive, status [scheduled/in_transit/completed/cancelled/breakdown], distance_actual_km, fuel_used_l, fuel_cost, toll_cost, notes) — 15,000 trips over 2 years
- fleet.gps_pings (id BIGSERIAL PK, trip_id FK→trips, lat, lng, speed_kmh, heading, recorded_at) — 500,000 GPS pings
- fleet.maintenance_logs (id UUID PK, vehicle_id FK→vehicles, vendor_id FK→vendors, service_type [oil_change/tyre/engine/electrical/body], description, cost, mileage_at_service, serviced_at, next_due_km, next_due_date) — 3,000 records

### Schema: operations
- operations.orders (id UUID PK, order_no UNIQUE, company_id FK→companies, contact_id FK→contacts, order_type [standard/express/bulk/cold_chain/hazmat], priority [low/normal/high/critical], origin_facility FK→facilities, dest_district FK→districts, dest_address, dest_lat, dest_lng, requested_by TIMESTAMP, status [draft/confirmed/processing/dispatched/delivered/cancelled], special_instructions, created_at) — 25,000 orders
- operations.order_items (id UUID PK, order_id FK→orders, product_id FK→products, quantity, unit_price, total_price) — 60,000 line items
- operations.shipments (id UUID PK, shipment_no UNIQUE, order_id FK→orders, trip_id FK→trips, origin_facility FK→facilities, dest_district FK→districts, dest_address, weight_kg, volume_m3, status [created/picked/loaded/in_transit/delivered/returned/lost], scheduled_pickup, actual_pickup, scheduled_delivery, actual_delivery, delivery_photo, recipient_name, recipient_sig, pod_notes) — 28,000 shipments
- operations.tracking_events (id UUID PK, shipment_id FK→shipments, event_type [created/picked_up/in_warehouse/loaded/departed/arrived_hub/out_for_delivery/delivered/failed_attempt/returned/exception], facility_id FK, trip_id FK, lat, lng, notes, recorded_by, recorded_at) — 180,000 events
- operations.incidents (id UUID PK, incident_no UNIQUE, incident_type [delay/damage/theft/accident/weather/breakdown/customer_rejection/wrong_address], severity [low/medium/high/critical], shipment_id FK→shipments, trip_id FK→trips, vehicle_id FK→vehicles, driver_id FK→drivers, district_id FK→districts, description, financial_impact, resolved, occurred_at, reported_at, resolved_at) — 2,500 incidents
- operations.sla_contracts (id UUID PK, company_id FK→companies, order_type, max_transit_hr, penalty_per_hr, free_attempts, is_active) — 800 SLA definitions

### Schema: finance
- finance.invoices (id UUID PK, invoice_no UNIQUE, company_id FK→companies, order_id FK→orders, invoice_date, due_date, subtotal, tax_amount, discount_amount, total_amount, paid_amount, status [draft/sent/partial/paid/overdue/written_off], currency DEFAULT 'LKR') — 24,000 invoices
- finance.payments (id UUID PK, invoice_id FK→invoices, company_id FK→companies, amount, payment_method [bank_transfer/cheque/cash/online], reference_no, payment_date, received_at) — 22,000 payments
- finance.operational_costs (id UUID PK, cost_type [fuel/maintenance/labour/warehouse_rent/insurance/toll/sla_penalty/damage_claim], reference_id, facility_id FK→facilities, vendor_id FK→vendors, amount, description, cost_date, approved_by, created_at) — 35,000 cost records
- finance.sla_breaches (id UUID PK, shipment_id FK→shipments, sla_contract_id FK→sla_contracts, breach_hours, penalty_amount, waived, waive_reason, created_at) — 3,200 breaches

### Analytical Views (schema: analytics)
- analytics.route_performance — route_id, route_code, route_name, origin_district, dest_district, distance_km, route_type, total_trips, completed_trips, delayed_trips, on_time_pct, avg_delay_hours, avg_fuel_per_km, avg_fuel_cost
- analytics.driver_performance — driver_id, employee_id, driver_name, base_facility, total_trips, completed_trips, delayed_trips, on_time_pct, avg_fuel_per_km, total_fuel_cost, incident_count
- analytics.warehouse_utilisation — facility_id, facility_code, facility_name, district_name, province, facility_type, capacity_m3, current_util_pct, has_cold_chain, has_hazmat, lat, lng, unique_products, total_items
- analytics.monthly_shipments — month, total_shipments, delivered, returned, on_time, on_time_pct, avg_delay_hours, total_weight_kg, total_volume_m3

### Key Query Patterns
- For district names: always JOIN core.districts
- For route performance: use analytics.route_performance or JOIN fleet.routes + fleet.trips
- For on-time rate: compare actual_arrive vs scheduled_arrive (trips) or actual_delivery vs scheduled_delivery (shipments)
- For delay hours: EXTRACT(EPOCH FROM (actual - scheduled)) / 3600
- For fuel efficiency: fuel_used_l / NULLIF(distance_actual_km, 0)
- For payment delays: payment_date - due_date (from finance.payments JOIN finance.invoices)
- For seasonal patterns: GROUP BY DATE_TRUNC('month', date_column)
"""
