"""
Run all SQL queries against DuckDB and export results to sql/results/.
Run from project root: python sql/run_queries.py
"""

import os
import duckdb

RESULTS_DIR = "sql/results"
LOYALTY_CSV = "data/processed/loyalty_offers.csv"

os.makedirs(RESULTS_DIR, exist_ok=True)

con = duckdb.connect()

# --- Load events table ---
print("Loading events.csv into DuckDB...")
with open("sql/schema.sql") as f:
    schema_sql = f.read()
# Only execute the events CREATE TABLE; skip the loyalty_offers DDL for now
events_ddl = schema_sql.split("-- Synthetic loyalty")[0].strip()
con.execute(events_ddl)
row_count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
print(f"  {row_count:,} rows loaded.")

# --- Q1: Funnel conversion ---
print("\nRunning Q1: Funnel conversion...")
with open("sql/queries/q1_funnel_conversion.sql") as f:
    sql = f.read()
df = con.execute(sql).df()
out = f"{RESULTS_DIR}/q1_funnel_conversion.csv"
df.to_csv(out, index=False)
print(f"  Saved {out}")
print(df.to_string(index=False))

# --- Q2: RFM scoring ---
print("\nRunning Q2: RFM scoring...")
with open("sql/queries/q2_rfm_scoring.sql") as f:
    sql = f.read()
df = con.execute(sql).df()
out = f"{RESULTS_DIR}/q2_rfm_segments.csv"
df.to_csv(out, index=False)
print(f"  Saved {out}")
print(df.to_string(index=False))

# --- Q3: Revenue concentration ---
print("\nRunning Q3: Revenue concentration...")
with open("sql/queries/q3_revenue_concentration.sql") as f:
    sql = f.read()
df = con.execute(sql).df()
out = f"{RESULTS_DIR}/q3_revenue_concentration.csv"
df.to_csv(out, index=False)
print(f"  Saved {out}")
print(df.to_string(index=False))

# --- Q4: Loyalty ROI (requires loyalty_offers.csv) ---
if os.path.exists(LOYALTY_CSV):
    print("\nRunning Q4: Loyalty ROI...")
    con.execute(f"""
        CREATE TABLE loyalty_offers AS
        SELECT * FROM read_csv_auto('{LOYALTY_CSV}', header=true)
    """)
    with open("sql/queries/q4_loyalty_roi.sql") as f:
        sql = f.read()
    df = con.execute(sql).df()
    out = f"{RESULTS_DIR}/q4_loyalty_roi.csv"
    df.to_csv(out, index=False)
    print(f"  Saved {out}")
    print(df.to_string(index=False))
else:
    print(f"\nSkipping Q4: {LOYALTY_CSV} not found.")
    print("  Generate it by running notebook 03_rfm_loyalty.ipynb first.")

con.close()
print("\nDone.")
