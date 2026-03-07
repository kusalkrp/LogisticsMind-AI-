"""Generate Plotly charts from query results."""
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

CEYLOG_NAVY = "#1B4F8C"
CEYLOG_GOLD = "#E8B84B"
CEYLOG_COLORS = [CEYLOG_NAVY, CEYLOG_GOLD, "#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B"]

CHART_LAYOUT = dict(
    plot_bgcolor="#0F1923",
    paper_bgcolor="#1A2535",
    font=dict(color="#E8EDF2"),
    margin=dict(l=40, r=20, t=50, b=40),
)


async def generate_chart(
    data: str,
    chart_type: str,
    x_column: str,
    y_column: str,
    title: str,
    color_column: str | None = None,
) -> dict:
    try:
        rows = json.loads(data) if isinstance(data, str) else data
        df = pd.DataFrame(rows)

        if df.empty:
            return {"success": False, "error": "No data to chart"}

        fig = None

        if chart_type == "bar":
            fig = px.bar(df, x=x_column, y=y_column, color=color_column,
                        title=title, color_discrete_sequence=CEYLOG_COLORS)
        elif chart_type == "line":
            fig = px.line(df, x=x_column, y=y_column, color=color_column,
                         title=title, color_discrete_sequence=CEYLOG_COLORS, markers=True)
        elif chart_type == "pie":
            fig = px.pie(df, names=x_column, values=y_column,
                        title=title, color_discrete_sequence=CEYLOG_COLORS)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_column, y=y_column, color=color_column,
                            title=title, color_discrete_sequence=CEYLOG_COLORS)
        elif chart_type == "heatmap":
            pivot = df.pivot_table(values=y_column, index=df.columns[0], columns=df.columns[1], aggfunc="mean")
            fig = go.Figure(data=go.Heatmap(z=pivot.values, x=pivot.columns.tolist(),
                                            y=pivot.index.tolist(), colorscale="Blues"))
            fig.update_layout(title=title)
        elif chart_type == "area":
            fig = px.area(df, x=x_column, y=y_column, color=color_column,
                         title=title, color_discrete_sequence=CEYLOG_COLORS)
        elif chart_type == "map":
            if "lat" in df.columns and "lng" in df.columns:
                # Drop rows with missing coordinates — scatter_mapbox requires valid lat/lng
                df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
                df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
                df = df.dropna(subset=["lat", "lng"])
                if df.empty:
                    return {"success": False, "error": "No rows with valid lat/lng after filtering nulls."}

                # Auto-detect the best label and metric columns for the map
                non_geo_cols = [c for c in df.columns if c not in ("lat", "lng")]
                numeric_cols = [c for c in non_geo_cols if pd.api.types.is_numeric_dtype(df[c])]
                text_cols = [c for c in non_geo_cols if not pd.api.types.is_numeric_dtype(df[c])]

                # Use y_column as metric if it's numeric, else pick first numeric non-geo col
                map_size_col = y_column if y_column in numeric_cols else (numeric_cols[0] if numeric_cols else None)
                # Use x_column as label if it's text, else pick first text col
                map_label_col = x_column if x_column in text_cols else (text_cols[0] if text_cols else None)

                # Ensure size column has only positive values (required by scatter_mapbox)
                if map_size_col:
                    df[map_size_col] = pd.to_numeric(df[map_size_col], errors="coerce").fillna(0).abs()

                fig = px.scatter_mapbox(
                    df, lat="lat", lon="lng",
                    size=map_size_col if map_size_col else None,
                    color=map_size_col,
                    hover_name=map_label_col,
                    hover_data={c: True for c in non_geo_cols},
                    title=title,
                    color_continuous_scale="Blues",
                    mapbox_style="carto-positron",
                    center={"lat": 7.87, "lon": 80.77}, zoom=7,
                    size_max=35,
                )
            else:
                return {"success": False, "error": "Map chart requires lat and lng columns in the data. Re-query including lat and lng from core.districts."}
        elif chart_type == "table":
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(df.columns), fill_color=CEYLOG_NAVY, font=dict(color="white")),
                cells=dict(values=[df[col] for col in df.columns], fill_color="#1A2535", font=dict(color="#E8EDF2"))
            )])
            fig.update_layout(title=title)
        else:
            fig = px.bar(df, x=x_column, y=y_column, title=title,
                        color_discrete_sequence=CEYLOG_COLORS)

        fig.update_layout(**CHART_LAYOUT)

        return {
            "success": True,
            "chart_json": fig.to_json(),
            "chart_type": chart_type,
            "row_count": len(df),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
