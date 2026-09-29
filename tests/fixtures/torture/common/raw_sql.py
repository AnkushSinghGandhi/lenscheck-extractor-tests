"""Shared raw-SQL constants, imported across apps (resolved via the repo-wide global_consts table)."""

# The example interactions.py shape: a multi-table JOIN export, read.
_INTERACTIONS_SQL = """
    SELECT c.uid, u.email, c.action, c.created
    FROM ad_target_entity_slice e
    JOIN ad_target_slice c ON c.id = e.ad_target_id
    LEFT JOIN users u   ON u.uid = c.uid
    LEFT JOIN cities ci ON ci.id = u.city_id
    WHERE e.entity_type = %s AND c.created BETWEEN %s AND %s
    ORDER BY c.created DESC
"""

# a revenue report using a CTE — `recent` is a query-local alias, NOT a table
_REVENUE_CTE_SQL = """
    WITH recent AS (SELECT id FROM ad_campaigns WHERE status = %s)
    SELECT r.id, SUM(l.amount)
    FROM recent r
    JOIN ad_delivery_logs l ON l.campaign_id = r.id
    GROUP BY r.id
"""

_PURGE_SQL = "DELETE FROM ad_audit_log WHERE created < %s"
