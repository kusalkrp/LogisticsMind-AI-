"""Tool registry for LogisticsMind AI agent."""
from agent.tools.query_database import query_database
from agent.tools.generate_chart import generate_chart
from agent.tools.detect_anomalies import detect_anomalies
from agent.tools.forecast_metric import forecast_metric
from agent.tools.explain_query import explain_query
from agent.tools.get_schema_info import get_schema_info

TOOL_REGISTRY = {
    "query_database": query_database,
    "generate_chart": generate_chart,
    "detect_anomalies": detect_anomalies,
    "forecast_metric": forecast_metric,
    "explain_query": explain_query,
    "get_schema_info": get_schema_info,
}

TOOL_SCHEMAS = [
    {
        "name": "query_database",
        "description": "Query the CeyLog logistics database using natural language. Use for finding data, calculating metrics, comparing performance, looking up records.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Natural language question to answer with data"},
                "time_range_days": {"type": "string", "description": "How many days back to query. Default 90."},
            },
            "required": ["question"]
        }
    },
    {
        "name": "generate_chart",
        "description": (
            "Generate a chart from data. Call AFTER query_database when a visual would help. "
            "chart_type options: bar, line, pie, scatter, heatmap, area, map, table. "
            "For map charts: x_column=label column (e.g. facility_name), y_column=metric column (e.g. current_util_pct). "
            "The data MUST include 'lat' and 'lng' columns for map charts. "
            "For bar/line: x_column=category or time column, y_column=numeric metric."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON array of data rows from query_database"},
                "chart_type": {"type": "string", "description": "bar|line|pie|scatter|heatmap|area|map|table"},
                "x_column": {"type": "string", "description": "For map: label column (facility_name). For bar/line: category column."},
                "y_column": {"type": "string", "description": "For map: numeric metric column (current_util_pct). For bar/line: numeric value column."},
                "title": {"type": "string"},
                "color_column": {"type": "string", "description": "Optional column for color grouping"},
            },
            "required": ["data", "chart_type", "x_column", "y_column", "title"]
        }
    },
    {
        "name": "detect_anomalies",
        "description": "Detect unusual patterns or outliers in a metric. Use when asked about anomalies, unusual behaviour, or when data looks suspicious.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string", "description": "delivery_delay_hours|fuel_consumption_per_km|incident_rate|payment_delay_days|damage_rate"},
                "entity_type": {"type": "string", "description": "route|driver|vehicle|company|product"},
                "time_range_days": {"type": "string", "description": "Days back to analyse. Default 90."},
            },
            "required": ["metric_name", "entity_type"]
        }
    },
    {
        "name": "forecast_metric",
        "description": "Forecast a KPI for future periods. Use when asked to predict, project, or estimate future values.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "shipment_volume|revenue|delay_rate|fuel_cost"},
                "periods": {"type": "string", "description": "Number of future periods. Default 3."},
                "period_type": {"type": "string", "description": "month|week|day"},
            },
            "required": ["metric"]
        }
    },
    {
        "name": "explain_query",
        "description": "Show the SQL query that would answer a question, without executing it. Use when analyst asks to see the query or wants to understand the data logic.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to generate SQL for"},
            },
            "required": ["question"]
        }
    },
    {
        "name": "get_schema_info",
        "description": "Get information about the database schema — table structures, column names, relationships. Use when unsure which table to query.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Table name or topic area (e.g. 'shipments', 'driver performance', 'finance')"},
            },
            "required": ["topic"]
        }
    },
]
