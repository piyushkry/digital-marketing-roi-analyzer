"""Consistent, accessible Plotly charts for the dashboard."""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

COLORS = {
    "Google Ads": "#2457A7",
    "Meta Ads": "#3B82F6",
    "Email Marketing": "#10B981",
    "Influencer Marketing": "#F59E0B",
}
PAPER = "#FFFFFF"
INK = "#142B4A"
GRID = "#E5EAF2"


def _polish(fig, title, y_title=""):
    fig.update_layout(
        title={"text": title, "font": {"size": 17, "color": INK}},
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font={"family": "Inter, Segoe UI, sans-serif", "color": INK, "size": 12},
        margin={"l": 54, "r": 22, "t": 58, "b": 26},
        xaxis={"title": {"text": "", "font": {"color": INK}}, "showgrid": False,
               "linecolor": GRID, "tickfont": {"color": INK}},
        yaxis={"title": {"text": y_title, "font": {"color": INK}}, "gridcolor": GRID,
               "zerolinecolor": GRID, "tickfont": {"color": INK}},
        legend={"font": {"color": INK}, "title": {"font": {"color": INK}}},
        hoverlabel={"bgcolor": "#10213D", "font": {"color": "#FFFFFF"}},
    )
    return fig


def channel_bar(data, metric, title, currency=False):
    fig = px.bar(
        data, x="Channel", y=metric, color="Channel", color_discrete_map=COLORS,
        text_auto=".2s", category_orders={"Channel": list(COLORS)},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    _polish(fig, title, "INR (₹)" if currency else metric)
    fig.update_layout(showlegend=False)
    fig.update_yaxes(tickprefix="₹" if currency else "", separatethousands=True)
    return fig


def revenue_spend_chart(data):
    """Compare observed revenue and spend by channel in the filtered period."""
    fig = go.Figure()
    for label, field, color in [("Revenue", "Revenue", "#10B981"), ("Marketing spend", "Ad_Spend", "#2457A7")]:
        fig.add_bar(x=data["Channel"], y=data[field], name=label, marker_color=color,
                    hovertemplate=f"%{{x}}<br>{label}: ₹%{{y:,.0f}}<extra></extra>")
    fig.update_layout(barmode="group", legend_title_text="", yaxis_tickprefix="₹", yaxis_separatethousands=True)
    return _polish(fig, "Revenue vs. marketing spend", "INR (₹)")


def channel_contribution_chart(data):
    fig = px.pie(data, names="Channel", values="Revenue", hole=0.62,
                 color="Channel", color_discrete_map=COLORS, category_orders={"Channel": list(COLORS)})
    fig.update_traces(textposition="inside", textinfo="percent",
                      hovertemplate="%{label}<br>Revenue: ₹%{value:,.0f}<br>Share: %{percent}<extra></extra>")
    _polish(fig, "Revenue contribution by channel")
    fig.update_layout(
        height=400,
        margin={"l": 8, "r": 8, "t": 58, "b": 72},
        legend_title_text="",
        legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.08,
                "font": {"color": INK, "size": 12}},
    )
    total_revenue = data["Revenue"].sum()
    fig.add_annotation(
        text=f"Revenue<br><b>₹{total_revenue:,.0f}</b>", x=0.5, y=0.52,
        xref="paper", yref="paper", showarrow=False,
        font={"family": "Inter, Segoe UI, sans-serif", "size": 12, "color": INK},
    )
    return fig


def funnel_chart(data):
    annotations = []
    for _, row in data.iterrows():
        conversion = row["Conversion from prior (%)"]
        dropoff = row["Drop-off from prior (%)"]
        if conversion != conversion:
            annotations.append("Entry stage")
        else:
            annotations.append(f"Conv. {conversion:.1f}% · Drop {dropoff:.1f}%")
    fig = go.Figure(go.Funnel(
        y=data["Stage"], x=data["Volume"], text=annotations,
        textinfo="value+text", textfont={"color": "#FFFFFF", "size": 12},
        marker={"color": ["#2563EB", "#345DCE", "#7C3AED", "#059669"]},
        connector={"line": {"color": "#CFD8E6", "width": 1}},
        customdata=data[["Conversion from prior (%)", "Drop-off from prior (%)"]],
        hovertemplate=("<b>%{y}</b><br>Volume: %{x:,.0f}<br>Conversion from prior: %{customdata[0]:.1f}%"
                       "<br>Drop-off from prior: %{customdata[1]:.1f}%<extra></extra>"),
    ))
    fig.update_layout(
        title={"text": "Campaign funnel", "font": {"size": 17, "color": INK}},
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        font={"family": "Inter, Segoe UI, sans-serif", "color": INK, "size": 12},
        # Plotly places funnel stage labels outside the polygon; reserve room so
        # the full labels remain visible in the dashboard's half-width column.
        margin={"l": 105, "r": 24, "t": 58, "b": 20},
        hoverlabel={"bgcolor": "#10213D", "font": {"color": "#FFFFFF"}},
    )
    return fig


def monthly_chart(data, metric, title, currency=False):
    fig = px.line(
        data, x="Month", y=metric, color="Channel", markers=True,
        color_discrete_map=COLORS, category_orders={"Channel": list(COLORS)},
    )
    fig.update_traces(line={"width": 3}, marker={"size": 7})
    _polish(fig, title, "INR (₹)" if currency else metric)
    fig.update_layout(legend_title_text="Channel", hovermode="x unified")
    if currency:
        fig.update_yaxes(tickprefix="₹", separatethousands=True)
    return fig


def budget_chart(allocation):
    fig = px.pie(allocation, names="Channel", values="Proposed Budget", hole=0.68,
                 color="Channel", color_discrete_map=COLORS, category_orders={"Channel": list(COLORS)})
    fig.update_traces(textposition="inside", textinfo="percent",
                      hovertemplate="%{label}<br>Proposed: ₹%{value:,.0f}<br>Share: %{percent}<extra></extra>")
    _polish(fig, "Proposed budget distribution")
    fig.update_layout(legend_title_text="Channel", legend={"font": {"color": INK}, "title": {"font": {"color": INK}}})
    return fig


def campaign_metric_chart(data, metric, title, currency=False):
    """Compare one selected campaign measure while retaining its original units."""
    if data.empty or metric not in data.columns:
        return _polish(go.Figure(), title, "INR (₹)" if currency else metric)
    fig = px.bar(
        data, x="Campaign Key", y=metric, color="Channel", text_auto=".2s",
        color_discrete_map=COLORS, barmode="group",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    _polish(fig, title, "INR (₹)" if currency else metric)
    fig.update_layout(legend_title_text="Channel")
    fig.update_xaxes(tickangle=-25)
    if currency:
        fig.update_yaxes(tickprefix="₹", separatethousands=True)
    return fig


def ranking_chart(data, metric, title, currency=False):
    """Compact horizontal ranking chart for the selected campaign metric."""
    if data.empty or metric not in data.columns:
        return _polish(go.Figure(), title, "INR (₹)" if currency else metric)
    ordered = data.sort_values(metric, ascending=True, kind="stable")
    fig = px.bar(
        ordered, x=metric, y="Campaign Key", color="Channel", orientation="h",
        text_auto=".2s", color_discrete_map=COLORS,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    _polish(fig, title, "INR (₹)" if currency else metric)
    fig.update_layout(yaxis={"title": {"text": ""}, "showgrid": False,
                             "linecolor": GRID, "tickfont": {"color": INK}},
                      legend_title_text="Channel")
    if currency:
        fig.update_xaxes(tickprefix="₹", separatethousands=True)
    return fig


def period_comparison_chart(comparison, metric):
    """Show one current-versus-prior total with its native unit."""
    figure = go.Figure()
    current = comparison.get(f"Current {metric}", float("nan"))
    previous = comparison.get(f"Previous {metric}", float("nan"))
    if metric == "ROI (%)":
        y_title, prefix, suffix = "ROI (%)", "", "%"
    elif metric in ("Revenue", "Spend"):
        y_title, prefix, suffix = "INR (₹)", "₹", ""
    else:
        y_title, prefix, suffix = "Campaign count", "", ""
    for label, value, color in [
        ("Previous equivalent period", previous, "#3B82F6"),
        ("Selected period", current, "#10B981"),
    ]:
        if pd.notna(value):
            figure.add_bar(name=label, x=[label], y=[value], marker_color=color,
                           text=[f"{prefix}{value:,.1f}{suffix}"], textposition="outside")
    figure.update_layout(barmode="group", showlegend=False)
    figure = _polish(figure, f"{metric} by period", y_title)
    if prefix:
        figure.update_yaxes(tickprefix=prefix, separatethousands=True)
    if suffix:
        figure.update_yaxes(ticksuffix=suffix)
    return figure
