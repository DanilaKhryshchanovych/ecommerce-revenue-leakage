-- Load raw CSV into DuckDB
-- DuckDB auto-parses event_time (TIMESTAMPTZ due to ' UTC' suffix); cast to plain TIMESTAMP
CREATE TABLE events AS
    SELECT
        event_time::TIMESTAMP                                       AS event_time,
        event_type,
        product_id::INTEGER                                         AS product_id,
        category_id::BIGINT                                         AS category_id,
        SPLIT_PART(category_code, '.', 1)                          AS category_l1,
        SPLIT_PART(category_code, '.', 2)                          AS category_l2,
        brand,
        price::FLOAT                                                AS price,
        user_id::BIGINT                                             AS user_id,
        user_session,
        event_time::DATE                                            AS event_date,
        DATE_TRUNC('month', event_time::TIMESTAMP)::DATE           AS event_month
    FROM read_csv_auto('events.csv', header=true);

-- Synthetic loyalty offers companion table
-- Populated after notebook 03 runs (see data/processed/loyalty_offers.csv)
CREATE TABLE loyalty_offers (
    user_id       BIGINT,
    rfm_segment   VARCHAR,
    offer_type    VARCHAR,
    offer_date    DATE,
    discount_pct  INTEGER,
    converted     BOOLEAN,
    order_value   FLOAT
);
