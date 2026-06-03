-- Q1: Session-level funnel conversion rates
-- Business question: At what rate do users move view → cart → purchase?
-- Unit: one row per (user_id, user_session); a session "did" a step if any event of that type exists

WITH funnel_steps AS (
    SELECT
        user_id,
        user_session,
        MAX(CASE WHEN event_type = 'view'     THEN 1 ELSE 0 END) AS did_view,
        MAX(CASE WHEN event_type = 'cart'     THEN 1 ELSE 0 END) AS did_cart,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS did_purchase
    FROM events
    GROUP BY user_id, user_session
)
SELECT
    COUNT(*)                                                           AS total_sessions,
    SUM(did_view)                                                      AS sessions_with_view,
    SUM(did_cart)                                                      AS sessions_with_cart,
    SUM(did_purchase)                                                  AS sessions_with_purchase,
    ROUND(100.0 * SUM(did_cart)     / NULLIF(SUM(did_view), 0), 2)   AS view_to_cart_pct,
    ROUND(100.0 * SUM(did_purchase) / NULLIF(SUM(did_cart), 0), 2)   AS cart_to_purchase_pct,
    ROUND(100.0 * SUM(did_purchase) / NULLIF(SUM(did_view), 0), 2)   AS overall_conversion_pct
FROM funnel_steps;
