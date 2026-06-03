from pathlib import Path

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
Q1   = BASE / "sql/results/q1_funnel_conversion.csv"
Q2   = BASE / "sql/results/q2_rfm_segments.csv"
Q3   = BASE / "sql/results/q3_revenue_concentration.csv"
Q4   = BASE / "sql/results/q4_loyalty_roi.csv"
EVENTS = BASE / "data/processed/events_clean.parquet"

# ── Colours ───────────────────────────────────────────────────────────────────
TEAL  = "#1D9E75"
AMBER = "#EF9F27"
CORAL = "#D85A30"

SEG_COLORS = [TEAL, "#2DB88A", AMBER, "#5BC8C8", "#E07B2A", CORAL]

# ── Load data ─────────────────────────────────────────────────────────────────
q1 = pd.read_csv(Q1)
q2 = pd.read_csv(Q2)
q4 = pd.read_csv(Q4)

events = pd.read_parquet(EVENTS, columns=["event_month", "event_type", "user_session"])
_total = (events.groupby("event_month")["user_session"]
          .nunique().reset_index(name="total_sessions"))
_purch = (events[events["event_type"] == "purchase"]
          .groupby("event_month")["user_session"]
          .nunique().reset_index(name="purchase_sessions"))
monthly = _total.merge(_purch, on="event_month")
monthly["conv_pct"] = (
    monthly["purchase_sessions"] / monthly["total_sessions"] * 100
).round(2)
monthly["event_month"] = pd.to_datetime(monthly["event_month"])

# RFM scores derived from segment rank (not raw days/orders)
q2_scored = q2.copy()
q2_scored["r_score"] = (
    q2_scored["avg_recency_days"]
    .rank(ascending=False, method="min", pct=True) * 4 + 1
).clip(1, 5).round(1)
q2_scored["f_score"] = (
    q2_scored["avg_orders"]
    .rank(ascending=True, method="min", pct=True) * 4 + 1
).clip(1, 5).round(1)

# Normalise avg_revenue to bubble size 20–80 px
rev_min = q2_scored["avg_revenue"].min()
rev_max = q2_scored["avg_revenue"].max()
q2_scored["bubble"] = (
    20 + (q2_scored["avg_revenue"] - rev_min) / (rev_max - rev_min) * 60
).round(1)

# ── Convenience row ───────────────────────────────────────────────────────────
r1 = q1.iloc[0]
v2c = round(float(r1["view_to_cart_pct"]), 2)
c2p = round(float(r1["cart_to_purchase_pct"]), 2)
ovr = round(float(r1["overall_conversion_pct"]), 2)

# ── Figure: Funnel ────────────────────────────────────────────────────────────
f_labels = ["Total Sessions", "With View", "With Cart Add", "With Purchase"]
f_values = [
    int(r1["total_sessions"]),
    int(r1["sessions_with_view"]),
    int(r1["sessions_with_cart"]),
    int(r1["sessions_with_purchase"]),
]
f_pcts   = [100.0] + [round(v / f_values[0] * 100, 1) for v in f_values[1:]]
f_text   = [f"{v:,}  ({p}%)" for v, p in zip(f_values, f_pcts)]

fig_funnel = go.Figure(go.Funnel(
    y=f_labels,
    x=f_values,
    text=f_text,
    textinfo="text",
    marker=dict(color=[TEAL, TEAL, AMBER, CORAL]),
    connector=dict(line=dict(color="white", width=2)),
))
fig_funnel.update_layout(
    title="Session Conversion Funnel",
    margin=dict(l=10, r=10, t=50, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=13),
)

# ── Figure: Monthly conversion line ──────────────────────────────────────────
fig_monthly = go.Figure(go.Scatter(
    x=monthly["event_month"],
    y=monthly["conv_pct"],
    mode="lines+markers+text",
    text=monthly["conv_pct"].apply(lambda v: f"{v}%"),
    textposition="top center",
    line=dict(color=TEAL, width=2.5),
    marker=dict(size=9, color=TEAL),
    fill="tozeroy",
    fillcolor="rgba(29,158,117,0.10)",
))
fig_monthly.update_layout(
    title="Monthly View-to-Purchase Conversion %",
    xaxis_title="Month",
    yaxis_title="Conversion %",
    margin=dict(l=50, r=20, t=50, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(gridcolor="#e9ecef"),
    xaxis=dict(gridcolor="#e9ecef"),
)

# ── Figure: RFM scatter ───────────────────────────────────────────────────────
fig_rfm = go.Figure()
_TEXT_POS = {
    "Champion":        "middle right",
    "Lost":            "middle right",
    "Needs Attention": "bottom center",
}

for i, row in q2_scored.iterrows():
    fig_rfm.add_trace(go.Scatter(
        x=[row["r_score"]],
        y=[row["f_score"]],
        mode="markers+text",
        name=row["rfm_segment"],
        text=[row["rfm_segment"]],
        textposition=_TEXT_POS.get(row["rfm_segment"], "top center"),
        marker=dict(
            size=row["bubble"],
            color=SEG_COLORS[i % len(SEG_COLORS)],
            opacity=0.85,
            line=dict(width=1.5, color="white"),
        ),
        hovertemplate=(
            f"<b>{row['rfm_segment']}</b><br>"
            f"Recency score: {row['r_score']}<br>"
            f"Frequency score: {row['f_score']}<br>"
            f"Avg revenue: ${row['avg_revenue']:,.0f}<br>"
            f"Users: {row['user_count']:,}<extra></extra>"
        ),
    ))
fig_rfm.update_layout(
    title=dict(text="RFM Segment Map  (bubble size = avg. revenue per customer)", pad=dict(b=20)),
    xaxis=dict(title="Recency Score (1 = low → 5 = high)", range=[0.5, 5.8], dtick=1,
               gridcolor="#e9ecef"),
    yaxis=dict(title="Frequency Score (1 = low → 5 = high)", range=[0.5, 5.8], dtick=1,
               gridcolor="#e9ecef"),
    showlegend=False,
    margin=dict(l=50, r=20, t=80, b=60),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# ── Figure: Grouped horizontal bar  users vs revenue ─────────────────────────
q2_bar = q2.sort_values("pct_of_users", ascending=True)
fig_seg_bar = go.Figure()
fig_seg_bar.add_trace(go.Bar(
    y=q2_bar["rfm_segment"],
    x=q2_bar["pct_of_users"],
    name="% of Users",
    orientation="h",
    marker_color=TEAL,
    text=q2_bar["pct_of_users"].apply(lambda v: f"{v}%"),
    textposition="outside",
))
fig_seg_bar.add_trace(go.Bar(
    y=q2_bar["rfm_segment"],
    x=q2_bar["pct_of_revenue"],
    name="% of Revenue",
    orientation="h",
    marker_color=AMBER,
    text=q2_bar["pct_of_revenue"].apply(lambda v: f"{v}%"),
    textposition="outside",
))
fig_seg_bar.update_layout(
    barmode="group",
    title=dict(text="User Share vs Revenue Share by Segment", pad=dict(b=20)),
    xaxis_title="%",
    margin=dict(l=20, r=60, t=80, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor="#e9ecef", range=[0, 32]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

# ── Figure: Loyalty ROI bar ───────────────────────────────────────────────────
OFFER_COLORS = {"email_discount": TEAL, "push_cashback": AMBER, "control": CORAL}
q4_plot = q4[q4["rfm_segment"] == "At Risk"]
_n_campaign = int(q4_plot["users_targeted"].sum())
bar_colors = [OFFER_COLORS.get(o, "#6C757D") for o in q4_plot["offer_type"]]

fig_loyalty = go.Figure(go.Bar(
    x=q4_plot["offer_type"],
    y=q4_plot["total_revenue"],
    text=[f"Conv: {r}%<br>ROI: {ri}×"
          for r, ri in zip(q4_plot["conversion_rate_pct"], q4_plot["roi_ratio"])],
    textposition="outside",
    marker_color=bar_colors,
    hovertemplate=(
        "<b>%{x}</b><br>"
        "Total revenue: $%{y:,.0f}<br>"
        "Users targeted: %{customdata[0]:,}<br>"
        "Conversions: %{customdata[1]:,}<extra></extra>"
    ),
    customdata=list(zip(q4_plot["users_targeted"], q4_plot["conversions"])),
))
_loyalty_ymax = q4_plot["total_revenue"].max()
fig_loyalty.update_layout(
    title=dict(
        text=(
            "Campaign Revenue by Offer Type — At Risk Segment"
            f"<br><sup>Segment analysis · n = {_n_campaign} users · figures reflect segment participants only</sup>"
        ),
        font=dict(size=14),
    ),
    xaxis_title="Offer Type",
    yaxis_title="Revenue ($)",
    margin=dict(l=50, r=20, t=110, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(gridcolor="#e9ecef", range=[0, _loyalty_ymax * 1.35]),
    uniformtext=dict(minsize=11, mode="show"),
)

# ── Layout helpers ────────────────────────────────────────────────────────────
def kpi_card(label, value, color=TEAL):
    return dbc.Card(
        dbc.CardBody([
            html.P(label, className="text-muted small mb-1"),
            html.H3(value, style={"color": color, "fontWeight": "700", "margin": 0}),
        ]),
        className="shadow-sm h-100",
    )


at_risk = q2[q2["rfm_segment"] == "At Risk"].iloc[0]

# ── App ───────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Revenue Leakage Dashboard"

app.layout = dbc.Container(
    [
        dbc.Row(dbc.Col(
            html.H2(
                "E-Commerce Revenue Leakage Dashboard",
                className="my-3 fw-bold",
                style={"color": "#2C3E50"},
            ),
            width=12,
        )),

        dbc.Tabs(
            [
                dbc.Tab(label="Funnel & Conversion", tab_id="tab-funnel"),
                dbc.Tab(label="Customer Segments",   tab_id="tab-segments"),
                dbc.Tab(label="Loyalty ROI",         tab_id="tab-loyalty"),
            ],
            id="main-tabs",
            active_tab="tab-funnel",
            className="mt-2",
        ),
        html.Div(id="tab-content"),
    ],
    fluid=True,
)


@app.callback(Output("tab-content", "children"), Input("main-tabs", "active_tab"))
def render_tab(active_tab):
    if active_tab == "tab-funnel":
        return [
            dbc.Row(
                [
                    dbc.Col(kpi_card("View-to-Cart %",       f"{v2c}%", AMBER), md=4, className="mt-3"),
                    dbc.Col(kpi_card("Cart-to-Purchase %",   f"{c2p}%", TEAL),  md=4, className="mt-3"),
                    dbc.Col(kpi_card("Overall Conversion %", f"{ovr}%", CORAL), md=4, className="mt-3"),
                ],
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=fig_funnel,  style={"height": "440px"}), md=5, className="mt-4"),
                    dbc.Col(dcc.Graph(figure=fig_monthly, style={"height": "440px"}), md=7, className="mt-4"),
                ],
            ),
        ]
    if active_tab == "tab-segments":
        return dbc.Row(
            [
                dbc.Col(dcc.Graph(figure=fig_rfm,     style={"height": "480px"}), md=6, className="mt-4"),
                dbc.Col(dcc.Graph(figure=fig_seg_bar, style={"height": "480px"}), md=6, className="mt-4"),
            ],
        )
    if active_tab == "tab-loyalty":
        return dbc.Row(
            [
                dbc.Col(dcc.Graph(figure=fig_loyalty, style={"height": "480px"}), md=8, className="mt-4"),
                dbc.Col(
                    [
                        html.H5("Segment Profile", className="mt-4 mb-1 fw-semibold"),
                        html.P(
                            f"Full At Risk segment — all {int(at_risk['user_count']):,} customers · historical data",
                            className="text-muted small mb-3",
                            style={"lineHeight": "1.4"},
                        ),
                        kpi_card("Total Users at Risk", f"{int(at_risk['user_count']):,}", CORAL),
                        html.Div(className="mt-3"),
                        kpi_card("Historical Revenue",  f"${at_risk['total_revenue']:,.0f}", AMBER),
                        html.Div(className="mt-3"),
                        dbc.Card(
                            dbc.CardBody([
                                html.P("Share of Total Users",   className="text-muted small mb-1"),
                                html.H4(f"{at_risk['pct_of_users']}%",    style={"color": AMBER, "fontWeight": "700"}),
                                html.Hr(className="my-2"),
                                html.P("Share of Total Revenue", className="text-muted small mb-1"),
                                html.H4(f"{at_risk['pct_of_revenue']}%",  style={"color": CORAL, "fontWeight": "700"}),
                            ]),
                            className="shadow-sm",
                        ),
                        html.P(
                            "* Segment-level analysis suggests revenue patterns from a campaign on the At Risk segment baseline cohort.",
                            className="text-muted mt-3",
                            style={"fontSize": "0.75rem", "lineHeight": "1.4"},
                        ),
                    ],
                    md=4,
                ),
            ],
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
