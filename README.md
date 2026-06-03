# E-Commerce Revenue Leakage Analysis

Funnel analysis, RFM segmentation, and loyalty ROI simulation on a real electronics store event log — built to identify and quantify where revenue is lost.

## Live Dashboard

🔗 https://danilakhryshchanovych.github.io/ecommerce-revenue-leakage/

## 📄 Executive Memo
executive_memo.md

## The business problem

Only 4.98% of browsing sessions end in a purchase, with 91.5% of viewers never adding a single item to cart. Revenue is highly concentrated: the top 10% of buyers drive approximately a half of total sales, making retention of high-value customers existentially more important than acquisition. A distinct At Risk cohort — buyers who spent meaningfully but have gone quiet — represents a time-sensitive reactivation opportunity before they slide into the Lost segment.

## Key findings

- **View-to-purchase funnel:** 8.45% view-to-cart → 58.98% cart-to-purchase → **4.98% overall conversion** (490,773 sessions)
- **Revenue concentration:** top 30% of buyers drive **79.6%** of revenue; top 10% alone account for 48.6%
- **At Risk segment:** 1,601 users, **$302,183** in historical spend, avg last purchase 109 days ago
- **Simulated email reactivation:** 19% conversion rate, **73× ROI** vs $0.50/user campaign cost

## Stack

Python · DuckDB · pandas · Plotly Dash

## How to run

```bash
git clone https://github.com/DanilaKhryshchanovych/ecommerce-revenue-leakage
cd ecommerce-revenue-leakage

# Place events.csv (Kaggle download) in the project root
pip install -r dashboard/requirements.txt

# Run SQL queries → sql/results/*.csv
python sql/run_queries.py

# Explore notebooks (cleaning → funnel → RFM + loyalty)
jupyter notebook notebooks/01_cleaning.ipynb

# Launch dashboard
python dashboard/dashboard.py
# → http://localhost:8050

# Or open the pre-built static export directly (no server needed)
# dashboard/dashboard.html
```

## Repository structure

```
├── events.csv                        ← original Kaggle file (gitignored)
├── data/processed/
│   ├── events_clean.parquet
│   └── loyalty_offers.csv
├── sql/
│   ├── schema.sql
│   ├── run_queries.py
│   ├── queries/                      ← q1–q4 SQL files
│   └── results/                      ← q1–q4 CSV outputs
├── notebooks/
│   ├── 01_cleaning.ipynb
│   ├── 02_funnel_analysis.ipynb
│   └── 03_rfm_loyalty.ipynb
├── dashboard/
│   ├── dashboard.py
│   ├── export_html.py
│   ├── dashboard.html               ← static export (no server needed)
│   └── requirements.txt
└── docs/
    └── executive_memo.md
```

## Data source

REES46 eCommerce Events History in Electronics Store  
https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-electronics-store  
Observation window: 24 Sep 2020 – 28 Feb 2021 · 884,474 events · 21,304 purchasing users

## Limitations

- Loyalty ROI simulation is synthetic — calibrated to Klaviyo 2023 benchmarks
- No customer demographic or geographic data available
- Single-store dataset; results may not generalise across retail verticals
