"""Delivery-log revenue export — raw SQL with a CTE (the `recent` alias must NOT be a table)."""
from django.db import connection

from common.raw_sql import _REVENUE_CTE_SQL


def revenue(status):
    with connection.cursor() as cursor:
        cursor.execute(_REVENUE_CTE_SQL, [status])   # raw: ad_campaigns + ad_delivery_logs
        return cursor.fetchall()
