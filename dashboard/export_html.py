"""Export the Revenue Leakage dashboard as a single self-contained HTML file."""

from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent.parent
Q1     = BASE / "sql/results/q1_funnel_conversion.csv"
Q2     = BASE / "sql/results/q2_rfm_segments.csv"
Q3     = BASE / "sql/results/q3_revenue_concentration.csv"
Q4     = BASE / "sql/results/q4_loyalty_roi.csv"
EVENTS = BASE / "data/processed/events_clean.parquet"
OUT    = BASE / "dashboard/dashboard.html"

# ── Colours ────────────────────────────────────────────────────────────────────
TEAL  = "#1D9E75"
AMBER = "#EF9F27"
CORAL = "#D85A30"
SEG_COLORS = [TEAL, "#2DB88A", AMBER, "#5BC8C8", "#E07B2A", CORAL]

# ── Load data ──────────────────────────────────────────────────────────────────
q1 = pd.read_csv(Q1)
q2 = pd.read_csv(Q2)
q4 = pd.read_csv(Q4)

events = pd.read_parquet(EVENTS, columns=["event_month", "event_type", "user_session"])
_total = events.groupby("event_month")["user_session"].nunique().reset_index(name="total_sessions")
_purch = (events[events["event_type"] == "purchase"]
          .groupby("event_month")["user_session"].nunique().reset_index(name="purchase_sessions"))
monthly = _total.merge(_purch, on="event_month")
monthly["conv_pct"] = (monthly["purchase_sessions"] / monthly["total_sessions"] * 100).round(2)
monthly["event_month"] = pd.to_datetime(monthly["event_month"])

# RFM scores
q2_scored = q2.copy()
q2_scored["r_score"] = (
    q2_scored["avg_recency_days"].rank(ascending=False, method="min", pct=True) * 4 + 1
).clip(1, 5).round(1)
q2_scored["f_score"] = (
    q2_scored["avg_orders"].rank(ascending=True, method="min", pct=True) * 4 + 1
).clip(1, 5).round(1)
rev_min, rev_max = q2_scored["avg_revenue"].min(), q2_scored["avg_revenue"].max()
q2_scored["bubble"] = (20 + (q2_scored["avg_revenue"] - rev_min) / (rev_max - rev_min) * 60).round(1)

r1  = q1.iloc[0]
v2c = round(float(r1["view_to_cart_pct"]), 2)
c2p = round(float(r1["cart_to_purchase_pct"]), 2)
ovr = round(float(r1["overall_conversion_pct"]), 2)

at_risk = q2[q2["rfm_segment"] == "At Risk"].iloc[0]

# ── Figures ────────────────────────────────────────────────────────────────────
def _base():
    return dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=13))

# Funnel
f_labels = ["Total Sessions", "With View", "With Cart Add", "With Purchase"]
f_values = [int(r1["total_sessions"]), int(r1["sessions_with_view"]),
            int(r1["sessions_with_cart"]), int(r1["sessions_with_purchase"])]
f_pcts   = [100.0] + [round(v / f_values[0] * 100, 1) for v in f_values[1:]]
fig_funnel = go.Figure(go.Funnel(
    y=f_labels, x=f_values,
    text=[f"{v:,}  ({p}%)" for v, p in zip(f_values, f_pcts)],
    textinfo="text",
    marker=dict(color=[TEAL, TEAL, AMBER, CORAL]),
    connector=dict(line=dict(color="white", width=2)),
))
fig_funnel.update_layout(title="Session Conversion Funnel",
                         margin=dict(l=10, r=10, t=50, b=10), **_base())

# Monthly line
fig_monthly = go.Figure(go.Scatter(
    x=monthly["event_month"], y=monthly["conv_pct"],
    mode="lines+markers+text",
    text=monthly["conv_pct"].apply(lambda v: f"{v}%"),
    textposition="top center",
    line=dict(color=TEAL, width=2.5),
    marker=dict(size=9, color=TEAL),
    fill="tozeroy", fillcolor="rgba(29,158,117,0.10)",
))
fig_monthly.update_layout(
    title="Monthly View-to-Purchase Conversion %",
    xaxis_title="Month", yaxis_title="Conversion %",
    margin=dict(l=50, r=20, t=50, b=50),
    yaxis=dict(gridcolor="#e9ecef"), xaxis=dict(gridcolor="#e9ecef"), **_base(),
)

# RFM scatter
_TEXT_POS = {
    "Champion":        "middle right",
    "Lost":            "middle right",
    "Needs Attention": "bottom center",
}

fig_rfm = go.Figure()
for i, row in q2_scored.iterrows():
    fig_rfm.add_trace(go.Scatter(
        x=[row["r_score"]], y=[row["f_score"]],
        mode="markers+text", name=row["rfm_segment"],
        text=[row["rfm_segment"]],
        textposition=_TEXT_POS.get(row["rfm_segment"], "top center"),
        marker=dict(size=row["bubble"], color=SEG_COLORS[i % len(SEG_COLORS)],
                    opacity=0.85, line=dict(width=1.5, color="white")),
        hovertemplate=(f"<b>{row['rfm_segment']}</b><br>"
                       f"Recency score: {row['r_score']}<br>"
                       f"Frequency score: {row['f_score']}<br>"
                       f"Avg revenue: ${row['avg_revenue']:,.0f}<br>"
                       f"Users: {row['user_count']:,}<extra></extra>"),
    ))
fig_rfm.update_layout(
    title=dict(text="RFM Segment Map  (bubble size = avg. revenue per customer)", pad=dict(b=20)),
    xaxis=dict(title="Recency Score (1 = low → 5 = high)", range=[0.5, 5.8], dtick=1, gridcolor="#e9ecef"),
    yaxis=dict(title="Frequency Score (1 = low → 5 = high)", range=[0.5, 5.8], dtick=1, gridcolor="#e9ecef"),
    showlegend=False, margin=dict(l=50, r=20, t=80, b=60), **_base(),
)

# Segment bar — sorted by % of Users descending (ascending in df = top of chart = largest)
q2_bar = q2.sort_values("pct_of_users", ascending=True)
fig_seg_bar = go.Figure()
fig_seg_bar.add_trace(go.Bar(y=q2_bar["rfm_segment"], x=q2_bar["pct_of_users"], name="% of Users",
                             orientation="h", marker_color=TEAL,
                             text=q2_bar["pct_of_users"].apply(lambda v: f"{v}%"), textposition="outside"))
fig_seg_bar.add_trace(go.Bar(y=q2_bar["rfm_segment"], x=q2_bar["pct_of_revenue"], name="% of Revenue",
                             orientation="h", marker_color=AMBER,
                             text=q2_bar["pct_of_revenue"].apply(lambda v: f"{v}%"), textposition="outside"))
fig_seg_bar.update_layout(
    barmode="group", title=dict(text="User Share vs Revenue Share by Segment", pad=dict(b=20)),
    xaxis_title="%", margin=dict(l=20, r=60, t=80, b=50),
    xaxis=dict(gridcolor="#e9ecef", range=[0, 32]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), **_base(),
)

# Loyalty bar
OFFER_COLORS = {"email_discount": TEAL, "push_cashback": AMBER, "control": CORAL}
q4_plot = q4[q4["rfm_segment"] == "At Risk"]
_n_campaign = int(q4_plot["users_targeted"].sum())
fig_loyalty = go.Figure(go.Bar(
    x=q4_plot["offer_type"], y=q4_plot["total_revenue"],
    text=[f"Conv: {r}%<br>ROI: {ri}×" for r, ri in zip(q4_plot["conversion_rate_pct"], q4_plot["roi_ratio"])],
    textposition="outside",
    marker_color=[OFFER_COLORS.get(o, "#6C757D") for o in q4_plot["offer_type"]],
    hovertemplate=("<b>%{x}</b><br>Total revenue: $%{y:,.0f}<br>"
                   "Users targeted: %{customdata[0]:,}<br>"
                   "Conversions: %{customdata[1]:,}<extra></extra>"),
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
    xaxis_title="Offer Type", yaxis_title="Revenue ($)",
    margin=dict(l=50, r=20, t=110, b=50),
    yaxis=dict(gridcolor="#e9ecef", range=[0, _loyalty_ymax * 1.35]),
    uniformtext=dict(minsize=11, mode="show"), **_base(),
)

# ── Serialize figures to HTML fragments ───────────────────────────────────────
def fig_html(fig, div_id, height="440px"):
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
        config={"responsive": True},
        default_height=height,
    )

h_funnel  = fig_html(fig_funnel,   "fig-funnel")
h_monthly = fig_html(fig_monthly,  "fig-monthly", "440px")
h_rfm     = fig_html(fig_rfm,      "fig-rfm",     "500px")
h_segbar  = fig_html(fig_seg_bar,  "fig-segbar",  "500px")
h_loyalty = fig_html(fig_loyalty,  "fig-loyalty", "500px")

# ── HTML template ─────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Revenue Leakage Dashboard</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
        crossorigin="anonymous"/>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js" charset="utf-8"></script>
  <style>
    body {{ background: #f8f9fa; }}
    .kpi-card {{ border: none; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
    .kpi-label {{ font-size: .8rem; color: #6c757d; margin-bottom: .15rem; }}
    .kpi-value {{ font-size: 1.7rem; font-weight: 700; margin: 0; }}
    .tab-content {{ background: white; border: 1px solid #dee2e6;
                    border-top: none; border-radius: 0 0 .375rem .375rem;
                    padding: 1rem; }}
    .nav-tabs .nav-link.active {{ font-weight: 600; color: #2C3E50; }}
  </style>
</head>
<body>
<div class="container-fluid py-3">

  <h2 class="fw-bold mb-3" style="color:#2C3E50">E-Commerce Revenue Leakage Dashboard</h2>

  <!-- Tabs nav -->
  <ul class="nav nav-tabs" id="mainTabs" role="tablist">
    <li class="nav-item" role="presentation">
      <button class="nav-link active" id="tab-funnel-btn"
              data-bs-toggle="tab" data-bs-target="#tab-funnel"
              type="button" role="tab">Funnel &amp; Conversion</button>
    </li>
    <li class="nav-item" role="presentation">
      <button class="nav-link" id="tab-segments-btn"
              data-bs-toggle="tab" data-bs-target="#tab-segments"
              type="button" role="tab">Customer Segments</button>
    </li>
    <li class="nav-item" role="presentation">
      <button class="nav-link" id="tab-loyalty-btn"
              data-bs-toggle="tab" data-bs-target="#tab-loyalty"
              type="button" role="tab">Loyalty ROI</button>
    </li>
  </ul>

  <div class="tab-content" id="mainTabsContent">

    <!-- ── Tab 1: Funnel & Conversion ───────────────────────────────────── -->
    <div class="tab-pane fade show active" id="tab-funnel" role="tabpanel">
      <div class="row mt-3 g-3">
        <div class="col-md-4">
          <div class="card kpi-card h-100">
            <div class="card-body">
              <p class="kpi-label">View-to-Cart %</p>
              <p class="kpi-value" style="color:{AMBER}">{v2c}%</p>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card kpi-card h-100">
            <div class="card-body">
              <p class="kpi-label">Cart-to-Purchase %</p>
              <p class="kpi-value" style="color:{TEAL}">{c2p}%</p>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card kpi-card h-100">
            <div class="card-body">
              <p class="kpi-label">Overall Conversion %</p>
              <p class="kpi-value" style="color:{CORAL}">{ovr}%</p>
            </div>
          </div>
        </div>
      </div>
      <div class="row mt-4 g-3">
        <div class="col-md-5">{h_funnel}</div>
        <div class="col-md-7">{h_monthly}</div>
      </div>
    </div>

    <!-- ── Tab 2: Customer Segments ─────────────────────────────────────── -->
    <div class="tab-pane fade" id="tab-segments" role="tabpanel">
      <div class="row mt-3 g-3">
        <div class="col-md-6">{h_rfm}</div>
        <div class="col-md-6">{h_segbar}</div>
      </div>
    </div>

    <!-- ── Tab 3: Loyalty ROI ────────────────────────────────────────────── -->
    <div class="tab-pane fade" id="tab-loyalty" role="tabpanel">
      <div class="row mt-3 g-3">
        <div class="col-md-8">{h_loyalty}</div>
        <div class="col-md-4">
          <h5 class="fw-semibold mt-2 mb-1">Segment Profile</h5>
          <p class="text-muted small mb-3" style="line-height:1.4">Full At Risk segment — all {int(at_risk['user_count']):,} customers · historical data</p>

          <div class="card kpi-card mb-3">
            <div class="card-body">
              <p class="kpi-label">Total Users at Risk</p>
              <p class="kpi-value" style="color:{CORAL}">{int(at_risk['user_count']):,}</p>
            </div>
          </div>

          <div class="card kpi-card mb-3">
            <div class="card-body">
              <p class="kpi-label">Historical Revenue</p>
              <p class="kpi-value" style="color:{AMBER}">${at_risk['total_revenue']:,.0f}</p>
            </div>
          </div>

          <div class="card kpi-card">
            <div class="card-body">
              <p class="kpi-label">Share of Total Users</p>
              <h4 style="color:{AMBER};font-weight:700">{at_risk['pct_of_users']}%</h4>
              <hr class="my-2"/>
              <p class="kpi-label">Share of Total Revenue</p>
              <h4 style="color:{CORAL};font-weight:700">{at_risk['pct_of_revenue']}%</h4>
            </div>
          </div>
          <p class="text-muted mt-3" style="font-size:0.75rem;line-height:1.4">* Segment-level analysis suggests revenue patterns from a campaign on the At Risk segment baseline cohort.</p>
        </div>
      </div>
    </div>

  </div><!-- /tab-content -->
</div><!-- /container-fluid -->

<script>
  // Vanilla tab switching — no Bootstrap JS needed; Bootstrap CSS handles styling
  document.querySelectorAll('[data-bs-toggle="tab"]').forEach(function(btn) {{
    btn.addEventListener('click', function(e) {{
      e.preventDefault();
      document.querySelectorAll('.nav-link').forEach(function(el) {{ el.classList.remove('active'); }});
      document.querySelectorAll('.tab-pane').forEach(function(el) {{ el.classList.remove('show', 'active'); }});
      this.classList.add('active');
      document.querySelector(this.getAttribute('data-bs-target')).classList.add('show', 'active');
      document.querySelectorAll('.js-plotly-plot').forEach(function(el) {{ Plotly.Plots.resize(el); }});
    }});
  }});
</script>
</body>
</html>"""

OUT.write_text(html, encoding="utf-8")
print(f"Saved: {OUT}")
