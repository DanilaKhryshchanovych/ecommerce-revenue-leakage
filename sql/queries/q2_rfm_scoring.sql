-- Q2: RFM segmentation of purchasing users
-- Business question: Who are our best customers? Who is at risk of churning?
-- Recency: days since last purchase (lower = more recent = better → score 5)
-- Frequency: distinct sessions with a purchase
-- Monetary: total spend across all purchases

WITH last_date AS (
    SELECT MAX(event_date) AS max_date FROM events
),
purchase_history AS (
    SELECT
        user_id,
        COUNT(DISTINCT user_session)   AS frequency,
        MAX(event_date)                AS last_purchase_date,
        SUM(price)                     AS monetary
    FROM events
    WHERE event_type = 'purchase'
    GROUP BY user_id
),
rfm_raw AS (
    SELECT
        p.user_id,
        DATEDIFF('day', p.last_purchase_date, l.max_date) AS recency_days,
        p.frequency,
        p.monetary
    FROM purchase_history p
    CROSS JOIN last_date l
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM rfm_raw
),
rfm_labeled AS (
    SELECT *,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champion'
            WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customer'
            WHEN r_score >= 4 AND f_score <= 2                  THEN 'New Customer'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'Can''t Lose Them'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost'
            ELSE 'Needs Attention'
        END AS rfm_segment
    FROM rfm_scored
)
SELECT
    rfm_segment,
    COUNT(user_id)                                              AS user_count,
    ROUND(100.0 * COUNT(user_id)
        / SUM(COUNT(user_id)) OVER (), 1)                      AS pct_of_users,
    ROUND(AVG(recency_days), 0)                                AS avg_recency_days,
    ROUND(AVG(frequency), 1)                                   AS avg_orders,
    ROUND(AVG(monetary), 2)                                    AS avg_revenue,
    ROUND(SUM(monetary), 2)                                    AS total_revenue,
    ROUND(100.0 * SUM(monetary)
        / SUM(SUM(monetary)) OVER (), 1)                       AS pct_of_revenue
FROM rfm_labeled
GROUP BY rfm_segment
ORDER BY avg_revenue DESC;
