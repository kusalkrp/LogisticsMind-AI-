-- Vehicle master
CREATE TABLE fleet.vehicles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plate_no        VARCHAR(20) UNIQUE NOT NULL,
    vehicle_type    VARCHAR(50),
    make            VARCHAR(100),
    model           VARCHAR(100),
    year            INTEGER,
    capacity_kg     DECIMAL(10,2),
    capacity_m3     DECIMAL(10,2),
    has_cold_chain  BOOLEAN DEFAULT FALSE,
    has_gps         BOOLEAN DEFAULT TRUE,
    fuel_type       VARCHAR(20),
    base_facility   UUID REFERENCES warehouse.facilities(id),
    status          VARCHAR(30),
    last_service_at DATE,
    next_service_at DATE,
    purchased_at    DATE,
    mileage_km      INTEGER
);

CREATE INDEX idx_vehicles_status ON fleet.vehicles(status);
CREATE INDEX idx_vehicles_type ON fleet.vehicles(vehicle_type);
CREATE INDEX idx_vehicles_base ON fleet.vehicles(base_facility);

-- Driver master
CREATE TABLE fleet.drivers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     VARCHAR(20) UNIQUE,
    name            VARCHAR(255),
    license_no      VARCHAR(50),
    license_type    VARCHAR(20),
    license_expiry  DATE,
    phone           VARCHAR(20),
    district_id     INTEGER REFERENCES core.districts(id),
    base_facility   UUID REFERENCES warehouse.facilities(id),
    rating          DECIMAL(3,2),
    total_trips     INTEGER DEFAULT 0,
    hired_at        DATE,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_drivers_district ON fleet.drivers(district_id);
CREATE INDEX idx_drivers_base ON fleet.drivers(base_facility);
CREATE INDEX idx_drivers_is_active ON fleet.drivers(is_active);

-- Route definitions
CREATE TABLE fleet.routes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(30) UNIQUE,
    name            VARCHAR(255),
    origin_district INTEGER REFERENCES core.districts(id),
    dest_district   INTEGER REFERENCES core.districts(id),
    distance_km     DECIMAL(8,2),
    est_duration_hr DECIMAL(5,2),
    route_type      VARCHAR(30),
    waypoints       JSONB,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_routes_origin ON fleet.routes(origin_district);
CREATE INDEX idx_routes_dest ON fleet.routes(dest_district);
CREATE INDEX idx_routes_type ON fleet.routes(route_type);

-- Individual trips
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
    status          VARCHAR(30),
    distance_actual_km DECIMAL(8,2),
    fuel_used_l     DECIMAL(8,2),
    fuel_cost       DECIMAL(10,2),
    toll_cost       DECIMAL(8,2),
    notes           TEXT
);

CREATE INDEX idx_trips_route ON fleet.trips(route_id);
CREATE INDEX idx_trips_vehicle ON fleet.trips(vehicle_id);
CREATE INDEX idx_trips_driver ON fleet.trips(driver_id);
CREATE INDEX idx_trips_date ON fleet.trips(trip_date);
CREATE INDEX idx_trips_status ON fleet.trips(status);

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

CREATE INDEX idx_gps_pings_trip ON fleet.gps_pings(trip_id);
CREATE INDEX idx_gps_pings_recorded_at ON fleet.gps_pings(recorded_at);

-- Vehicle maintenance records
CREATE TABLE fleet.maintenance_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id      UUID REFERENCES fleet.vehicles(id),
    vendor_id       UUID REFERENCES core.vendors(id),
    service_type    VARCHAR(100),
    description     TEXT,
    cost            DECIMAL(10,2),
    mileage_at_service INTEGER,
    serviced_at     TIMESTAMP,
    next_due_km     INTEGER,
    next_due_date   DATE
);

CREATE INDEX idx_maintenance_vehicle ON fleet.maintenance_logs(vehicle_id);
CREATE INDEX idx_maintenance_vendor ON fleet.maintenance_logs(vendor_id);
CREATE INDEX idx_maintenance_serviced_at ON fleet.maintenance_logs(serviced_at);
