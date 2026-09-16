"""Grafici Plotly della simulazione."""
import plotly.graph_objects as go
import pandas as pd


DEFAULT_FUND_COLORS = [
    "#1c6e8c", "#d85c3a", "#2f9e44", "#845ef7", "#f08c00", "#c2255c",
    "#0c8599", "#e67700", "#5c7cfa", "#37b24d",
]


def accumulation_chart(result: pd.DataFrame, series: list[tuple[str, str]] | None = None) -> go.Figure:
    """Disegna il confronto tra TFR, INPS e uno o più fondi pensione."""
    figure = go.Figure()

    if series is None:
        default_columns = []
        for column in ["Montante TFR non investito", "Montante INPS"]:
            if column in result.columns:
                default_columns.append((column, "TFR in azienda" if column.startswith("Montante TFR") else "INPS"))
        for column in result.columns:
            if column.startswith("Montante ") and column not in {"Montante TFR non investito", "Montante INPS"}:
                default_columns.append((column, column.replace("Montante ", "")))
        series = default_columns

    color_map = {
        "Montante TFR non investito": "#d4a72c",
        "Montante INPS": "#7a7a7a",
    }

    for index, (column, label) in enumerate(series):
        if column not in result.columns:
            continue
        color = color_map.get(column)
        if color is None:
            color = DEFAULT_FUND_COLORS[index % len(DEFAULT_FUND_COLORS)]
        figure.add_trace(go.Scatter(
            x=result["Anno"], y=result[column], mode="lines", name=label,
            line={"width": 3, "color": color},
            hovertemplate="%{x}: € %{y:,.0f}<extra></extra>",
        ))

    figure.update_layout(
        template="plotly_white", height=500, margin={"l": 10, "r": 10, "t": 20, "b": 10},
        xaxis_title="Anno", yaxis_title="Montante lordo (€)",
        legend={"orientation": "h", "y": 1.08}, hovermode="x unified",
    )
    return figure
