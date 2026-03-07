"""Statistical anomaly detection with LLM explanation."""
import os
import asyncpg
import numpy as np
from agent.core.llm import get_llm

METRIC_QUERIES = {
    ("delivery_delay_hours", "route"): """
        SELECT r.code AS entity, r.name AS entity_name,
               AVG(EXTRACT(EPOCH FROM (t.actual_arrive - t.scheduled_arrive)) / 3600) AS metric_value,
               COUNT(*) AS sample_size
        FROM fleet.trips t
        JOIN fleet.routes r ON t.route_id = r.id
        WHERE t.status = 'completed' AND t.actual_arrive IS NOT NULL AND t.scheduled_arrive IS NOT NULL
          AND t.trip_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY r.code, r.name
        HAVING COUNT(*) >= 5
    """,
    ("fuel_consumption_per_km", "driver"): """
        SELECT d.employee_id AS entity, d.name AS entity_name,
               AVG(t.fuel_used_l / NULLIF(t.distance_actual_km, 0)) AS metric_value,
               COUNT(*) AS sample_size
        FROM fleet.trips t
        JOIN fleet.drivers d ON t.driver_id = d.id
        WHERE t.status = 'completed' AND t.fuel_used_l IS NOT NULL AND t.distance_actual_km > 0
          AND t.trip_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY d.employee_id, d.name
        HAVING COUNT(*) >= 5
    """,
    ("incident_rate", "vehicle"): """
        SELECT v.plate_no AS entity, v.plate_no AS entity_name,
               COUNT(i.id)::float / NULLIF(COUNT(DISTINCT t.id), 0) AS metric_value,
               COUNT(DISTINCT t.id) AS sample_size
        FROM fleet.vehicles v
        LEFT JOIN fleet.trips t ON t.vehicle_id = v.id AND t.trip_date >= CURRENT_DATE - INTERVAL '{days} days'
        LEFT JOIN operations.incidents i ON i.vehicle_id = v.id AND i.occurred_at >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY v.plate_no
        HAVING COUNT(DISTINCT t.id) >= 3
    """,
    ("payment_delay_days", "company"): """
        SELECT c.name AS entity, c.name AS entity_name,
               AVG(p.payment_date - i.due_date) AS metric_value,
               COUNT(*) AS sample_size
        FROM finance.payments p
        JOIN finance.invoices i ON p.invoice_id = i.id
        JOIN core.companies c ON p.company_id = c.id
        WHERE p.payment_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY c.name
        HAVING COUNT(*) >= 3
    """,
    ("damage_rate", "product"): """
        SELECT pr.sku AS entity, pr.name AS entity_name,
               COUNT(inc.id)::float / NULLIF(COUNT(DISTINCT s.id), 0) AS metric_value,
               COUNT(DISTINCT s.id) AS sample_size
        FROM core.products pr
        JOIN operations.order_items oi ON oi.product_id = pr.id
        JOIN operations.shipments s ON s.order_id = oi.order_id
        LEFT JOIN operations.incidents inc ON inc.shipment_id = s.id AND inc.incident_type = 'damage'
        GROUP BY pr.sku, pr.name
        HAVING COUNT(DISTINCT s.id) >= 3
    """,
}


async def detect_anomalies(
    metric_name: str,
    entity_type: str,
    time_range_days: str = "365",
) -> dict:
    key = (metric_name, entity_type)
    if key not in METRIC_QUERIES:
        return {"success": False, "error": f"Unknown metric/entity: {metric_name}/{entity_type}",
                "anomalies": []}

    query = METRIC_QUERIES[key].format(days=time_range_days)

    url = os.environ.get("DATABASE_URL_SYNC", "postgresql://user:password@postgres:5432/ceylog")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(query)
    finally:
        await conn.close()

    if not rows or len(rows) < 3:
        return {"success": True, "anomalies": [], "message": "Insufficient data for anomaly detection"}

    entities = [r["entity"] for r in rows]
    names = [r["entity_name"] for r in rows]
    values = [float(r["metric_value"]) if r["metric_value"] is not None else 0.0 for r in rows]
    samples = [int(r["sample_size"]) for r in rows]

    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr)

    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1

    anomalies = []
    for i, val in enumerate(values):
        z_score = (val - mean) / std if std > 0 else 0
        is_iqr_outlier = val < (q1 - 1.5 * iqr) or val > (q3 + 1.5 * iqr)

        if abs(z_score) > 2.0 or is_iqr_outlier:
            anomalies.append({
                "entity": entities[i],
                "entity_name": names[i],
                "value": round(val, 4),
                "z_score": round(z_score, 2),
                "mean": round(mean, 4),
                "std": round(std, 4),
                "sample_size": samples[i],
                "direction": "high" if z_score > 0 else "low",
            })

    anomalies.sort(key=lambda a: abs(a["z_score"]), reverse=True)
    anomalies = anomalies[:10]

    # LLM explanation
    if anomalies:
        explanation = await get_llm().generate(
            system="You are a logistics data analyst. Explain each anomaly in 1-2 sentences. Be specific about the numbers.",
            messages=[{"role": "user", "content":
                f"Metric: {metric_name} by {entity_type}\nMean: {mean:.4f}, Std: {std:.4f}\n"
                f"Anomalies: {anomalies}"
            }],
            tier="flash"
        )
        for a in anomalies:
            a["explanation"] = explanation
    else:
        explanation = "No significant anomalies detected."

    return {
        "success": True,
        "metric": metric_name,
        "entity_type": entity_type,
        "total_entities": len(entities),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "summary": explanation if isinstance(explanation, str) else "",
    }
