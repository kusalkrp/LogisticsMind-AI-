import React, { useState } from 'react';

const SCHEMA = {
  core: {
    districts: ['id', 'name', 'province', 'area_km2', 'lat', 'lng'],
    companies: ['id', 'name', 'registration_no', 'industry', 'district_id', 'credit_limit', 'is_active'],
    contacts: ['id', 'company_id', 'name', 'role', 'phone', 'email'],
    vendors: ['id', 'name', 'vendor_type', 'district_id', 'rating'],
    products: ['id', 'sku', 'name', 'category', 'weight_kg', 'unit_value'],
  },
  warehouse: {
    facilities: ['id', 'code', 'name', 'district_id', 'facility_type', 'capacity_m3', 'current_util_pct'],
    inventory_items: ['id', 'facility_id', 'product_id', 'quantity', 'batch_no'],
    stock_movements: ['id', 'facility_id', 'movement_type', 'quantity', 'moved_at'],
    staff: ['id', 'facility_id', 'name', 'role', 'shift'],
  },
  fleet: {
    vehicles: ['id', 'plate_no', 'vehicle_type', 'status', 'mileage_km'],
    drivers: ['id', 'employee_id', 'name', 'rating', 'total_trips'],
    routes: ['id', 'code', 'name', 'distance_km', 'route_type'],
    trips: ['id', 'route_id', 'vehicle_id', 'driver_id', 'trip_date', 'status'],
    gps_pings: ['id', 'trip_id', 'lat', 'lng', 'speed_kmh'],
    maintenance_logs: ['id', 'vehicle_id', 'service_type', 'cost'],
  },
  operations: {
    orders: ['id', 'order_no', 'company_id', 'order_type', 'status', 'created_at'],
    shipments: ['id', 'shipment_no', 'status', 'scheduled_delivery', 'actual_delivery'],
    tracking_events: ['id', 'shipment_id', 'event_type', 'recorded_at'],
    incidents: ['id', 'incident_type', 'severity', 'financial_impact'],
  },
  finance: {
    invoices: ['id', 'invoice_no', 'total_amount', 'status', 'due_date'],
    payments: ['id', 'invoice_id', 'amount', 'payment_date'],
    operational_costs: ['id', 'cost_type', 'amount', 'cost_date'],
    sla_breaches: ['id', 'breach_hours', 'penalty_amount'],
  },
};


export default function SchemaExplorer() {
  const [expanded, setExpanded] = useState({});

  function toggle(key) {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Operational Schema
      </div>
      <div className="glass-card" style={{ padding: '8px', background: 'rgba(255, 255, 255, 0.01)' }}>
        {Object.entries(SCHEMA).map(([schema, tables]) => (
          <div key={schema} style={{ marginBottom: '4px' }}>
            <div 
              style={{ 
                cursor: 'pointer', 
                padding: '6px 10px', 
                borderRadius: '6px', 
                fontSize: '13px', 
                color: 'var(--accent-gold)', 
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'background 0.2s'
              }} 
              onClick={() => toggle(schema)}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(232, 184, 75, 0.1)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{ fontSize: '10px', opacity: 0.7 }}>{expanded[schema] ? '▼' : '▶'}</span>
              <span style={{ opacity: 0.9 }}>{schema}</span>
            </div>
            
            {expanded[schema] && (
              <div style={{ marginLeft: '12px', borderLeft: '1px solid rgba(255, 255, 255, 0.05)', paddingLeft: '4px', marginTop: '4px' }}>
                {Object.entries(tables).map(([table, cols]) => (
                  <div key={table}>
                    <div 
                      style={{ 
                        cursor: 'pointer', 
                        padding: '4px 10px', 
                        fontSize: '12px', 
                        color: 'var(--text-main)', 
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        opacity: expanded[`${schema}.${table}`] ? 1 : 0.7
                      }} 
                      onClick={() => toggle(`${schema}.${table}`)}
                    >
                      <span style={{ fontSize: '9px', opacity: 0.5 }}>{expanded[`${schema}.${table}`] ? '▼' : '▶'}</span>
                      {table}
                    </div>
                    {expanded[`${schema}.${table}`] && (
                      <div style={{ marginLeft: '24px', display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '2px', marginBottom: '6px' }}>
                        {cols.map(col => (
                          <div key={col} style={{ fontSize: '11px', color: 'var(--text-dim)', opacity: 0.5, display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.2)' }}></span>
                            {col}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
