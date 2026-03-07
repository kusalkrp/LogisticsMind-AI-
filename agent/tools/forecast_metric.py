"""Time-series forecasting with Prophet."""
import os
import asyncpg
import pandas as pd
from prophet import Prophet

METRIC_QUERIES = {
    "shipment_volume": """
        SELECT DATE_TRUNC('month', scheduled_delivery)::date AS ds, COUNT(*)::float AS y
        FROM operations.shipments
        WHERE scheduled_delivery IS NOT NULL
        GROUP BY ds ORDER BY ds
    """,
    "revenue": """
        SELECT DATE_TRUNC('month', invoice_date)::date AS ds, SUM(total_amount)::float AS y
        FROM finance.invoices
        WHERE invoice_date IS NOT NULL
        GROUP BY ds ORDER BY ds
    """,
    "delay_rate": """
        SELECT DATE_TRUNC('month', trip_date)::date AS ds,
               (COUNT(*) FILTER (WHERE actual_arrive > scheduled_arrive))::float
               / NULLIF(COUNT(*) FILTER (WHERE status = 'completed'), 0) AS y
        FROM fleet.trips
        WHERE trip_date IS NOT NULL
        GROUP BY ds ORDER BY ds
    """,
    "fuel_cost": """
        SELECT DATE_TRUNC('month', trip_date)::date AS ds, SUM(fuel_cost)::float AS y
        FROM fleet.trips
        WHERE fuel_cost IS NOT NULL
        GROUP BY ds ORDER BY ds
    """,
}

SL_HOLIDAYS = pd.DataFrame({
    "holiday": ["sinhala_new_year", "sinhala_new_year", "vesak", "christmas"] * 3,
    "ds": pd.to_datetime([
        "2024-04-13", "2024-04-14", "2024-05-23", "2024-12-25",
        "2025-04-13", "2025-04-14", "2025-05-12", "2025-12-25",
        "2026-04-13", "2026-04-14", "2026-05-01", "2026-12-25",
    ]),
    "lower_window": [0] * 12,
    "upper_window": [1] * 12,
})


async def forecast_metric(
    metric: str,
    periods: str = "3",
    period_type: str = "month",
) -> dict:
    if metric not in METRIC_QUERIES:
        return {"success": False, "error": f"Unknown metric: {metric}"}

    query = METRIC_QUERIES[metric]
    url = os.environ.get("DATABASE_URL_SYNC", "postgresql://user:password@postgres:5432/ceylog")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(query)
    finally:
        await conn.close()

    if len(rows) < 6:
        return {"success": False, "error": "Insufficient historical data for forecasting"}

    df = pd.DataFrame([{"ds": r["ds"], "y": float(r["y"]) if r["y"] else 0} for r in rows])
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.dropna()

    n_periods = int(periods)
    freq_map = {"month": "MS", "week": "W", "day": "D"}
    freq = freq_map.get(period_type, "MS")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=(period_type == "day"),
        holidays=SL_HOLIDAYS,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=n_periods, freq=freq)
    forecast = model.predict(future)

    forecast_rows = forecast.tail(n_periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_dict("records")
    result = []
    for row in forecast_rows:
        result.append({
            "period": row["ds"].strftime("%Y-%m-%d"),
            "forecast": round(row["yhat"], 2),
            "lower": round(row["yhat_lower"], 2),
            "upper": round(row["yhat_upper"], 2),
        })

    last_val = df["y"].iloc[-1]
    first_forecast = result[0]["forecast"] if result else last_val
    change_pct = round(((first_forecast - last_val) / last_val) * 100, 1) if last_val else 0

    return {
        "success": True,
        "metric": metric,
        "periods": n_periods,
        "period_type": period_type,
        "forecast": result,
        "trend_direction": "up" if change_pct > 0 else "down",
        "change_pct": change_pct,
        "historical_points": len(df),
    }
