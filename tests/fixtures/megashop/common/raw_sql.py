"""Shared raw-SQL constants (resolved repo-wide via global_consts). Includes a PII column, a CTE,
a multi-table JOIN, and write statements — the hard cases for the raw-SQL lens."""

# streaming invoice export — selects a PII column (u.email); the rows are yielded to the client
_INVOICE_SQL = """
    SELECT i.id, u.email, u.phone, i.amount, i.created
    FROM billing_invoices i
    JOIN orders o ON o.id = i.order_id
    JOIN customers u ON u.id = o.customer_id
    WHERE i.status = %s
    ORDER BY i.created DESC
"""

# revenue report using a CTE — `recent` is a query-local alias, NOT a table
_REVENUE_CTE_SQL = """
    WITH recent AS (SELECT id FROM orders WHERE created > %s)
    SELECT r.id, SUM(p.amount)
    FROM recent r
    JOIN billing_payments p ON p.order_id = r.id
    GROUP BY r.id
"""

_PURGE_AUDIT_SQL = "DELETE FROM audit_log WHERE created < %s"
