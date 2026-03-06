-- Analytical views for common queries

-- Route performance summary
CREATE OR REPLACE VIEW analytics.route_performance AS
SELECT
    r.id AS route_id,
    r.code AS route_code,
    r.name AS route_name,
    d_orig.name AS origin_district,
    d_dest.name AS dest_district,
    r.distance_km,
    r.route_type,
    COUNT(t.id) AS total_trips,
    COUNT(t.id) FILTER (WHERE t.status = 'completed') AS completed_trips,
    COUNT(t.id) FILTER (WHERE t.actual_arrive > t.scheduled_arrive) AS delayed_trips,
    ROUND(
        100.0 * COUNT(t.id) FILTER (WHERE t.actual_arrive <= t.scheduled_arrive)
        / NULLIF(COUNT(t.id) FILTER (WHERE t.status = 'completed'), 0),
        1
    ) AS on_time_pct,
    ROUND(AVG(EXTRACT(EPOCH FROM (t.actual_arrive - t.scheduled_arrive)) / 3600)::numeric, 2) AS avg_delay_hours,
    ROUND(AVG(t.fuel_used_l / NULLIF(t.distance_actual_km, 0))::numeric, 3) AS avg_fuel_per_km,
    ROUND(AVG(t.fuel_cost)::numeric, 2) AS avg_fuel_cost
FROM fleet.routes r
JOIN core.districts d_orig ON r.origin_district = d_orig.id
JOIN core.districts d_dest ON r.dest_district = d_dest.id
LEFT JOIN fleet.trips t ON t.route_id = r.id
GROUP BY r.id, r.code, r.name, d_orig.name, d_dest.name, r.distance_km, r.route_type;

-- Driver performance summary
CREATE OR REPLACE VIEW analytics.driver_performance AS
SELECT
    d.id AS driver_id,
    d.employee_id,
    d.name AS driver_name,
    d.base_facility,
    COUNT(t.id) AS total_trips,
    COUNT(t.id) FILTER (WHERE t.status = 'completed') AS completed_trips,
    COUNT(t.id) FILTER (WHERE t.actual_arrive > t.scheduled_arrive) AS delayed_trips,
    ROUND(
        100.0 * COUNT(t.id) FILTER (WHERE t.actual_arrive <= t.scheduled_arrive)
        / NULLIF(COUNT(t.id) FILTER (WHERE t.status = 'completed'), 0),
        1
    ) AS on_time_pct,
    ROUND(AVG(t.fuel_used_l / NULLIF(t.distance_actual_km, 0))::numeric, 3) AS avg_fuel_per_km,
    ROUND(SUM(t.fuel_cost)::numeric, 2) AS total_fuel_cost,
    COUNT(DISTINCT i.id) AS incident_count
FROM fleet.drivers d
LEFT JOIN fleet.trips t ON t.driver_id = d.id
LEFT JOIN operations.incidents i ON i.driver_id = d.id
GROUP BY d.id, d.employee_id, d.name, d.base_facility;

-- Warehouse utilisation summary
CREATE OR REPLACE VIEW analytics.warehouse_utilisation AS
SELECT
    f.id AS facility_id,
    f.code AS facility_code,
    f.name AS facility_name,
    d.name AS district_name,
    d.province,
    f.facility_type,
    f.capacity_m3,
    f.current_util_pct,
    f.has_cold_chain,
    f.has_hazmat,
    f.lat,
    f.lng,
    COUNT(DISTINCT ii.product_id) AS unique_products,
    COALESCE(SUM(ii.quantity), 0) AS total_items
FROM warehouse.facilities f
JOIN core.districts d ON f.district_id = d.id
LEFT JOIN warehouse.inventory_items ii ON ii.facility_id = f.id
GROUP BY f.id, f.code, f.name, d.name, d.province, f.facility_type,
         f.capacity_m3, f.current_util_pct, f.has_cold_chain, f.has_hazmat, f.lat, f.lng;

-- Monthly shipment volume
CREATE OR REPLACE VIEW analytics.monthly_shipments AS
SELECT
    DATE_TRUNC('month', s.scheduled_delivery) AS month,
    COUNT(s.id) AS total_shipments,
    COUNT(s.id) FILTER (WHERE s.status = 'delivered') AS delivered,
    COUNT(s.id) FILTER (WHERE s.status = 'returned') AS returned,
    COUNT(s.id) FILTER (WHERE s.actual_delivery <= s.scheduled_delivery) AS on_time,
    ROUND(
        100.0 * COUNT(s.id) FILTER (WHERE s.actual_delivery <= s.scheduled_delivery)
        / NULLIF(COUNT(s.id) FILTER (WHERE s.status = 'delivered'), 0),
        1
    ) AS on_time_pct,
    ROUND(AVG(EXTRACT(EPOCH FROM (s.actual_delivery - s.scheduled_delivery)) / 3600)::numeric, 2) AS avg_delay_hours,
    ROUND(SUM(s.weight_kg)::numeric, 0) AS total_weight_kg,
    ROUND(SUM(s.volume_m3)::numeric, 0) AS total_volume_m3
FROM operations.shipments s
WHERE s.scheduled_delivery IS NOT NULL
GROUP BY DATE_TRUNC('month', s.scheduled_delivery)
ORDER BY month;
