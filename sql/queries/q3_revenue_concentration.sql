-- Q3: Revenue concentration by customer decile (Pareto analysis)
-- Business question: Do 20% of customers drive 80% of revenue?
-- Each decile = 10% of customers ranked by total spend (decile 1 = highest spenders)

WITH user_revenue AS (
    SELECT
        user_id,
        SUM(price) AS total_spent
    FROM events
    WHERE event_type = 'purchase'
    GROUP BY user_id
),
ranked AS (
    SELECT *,
        NTILE(10) OVER (ORDER BY total_spent DESC) AS decile
    FROM user_revenue
)
SELECT
    decile,
    COUNT(user_id)                                                          AS users,
    ROUND(SUM(total_spent), 2)                                             AS decile_revenue,
    ROUND(100.0 * SUM(total_spent) / SUM(SUM(total_spent)) OVER (), 1)    AS pct_of_revenue,
    ROUND(
        100.0 * SUM(SUM(total_spent)) OVER (ORDER BY decile ROWS UNBOUNDED PRECEDING)
        / SUM(SUM(total_spent)) OVER (), 1
    )                                                                       AS cumulative_pct
FROM ranked
GROUP BY decile
ORDER BY decile;
