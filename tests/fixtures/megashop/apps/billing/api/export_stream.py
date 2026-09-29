"""Streaming invoice export — raw SQL selecting a PII column, streamed to the client (the interactions
shape): cursor tainted → fetched rows → `yield` → email reaches the client (PII to-client)."""
from django.db import connection
from common.raw_sql import _INVOICE_SQL


def _rows(status):
    with connection.cursor() as cur:
        cur.execute(_INVOICE_SQL, [status])          # raw: billing_invoices, orders, customers + PII(email,phone)
        while True:
            batch = cur.fetchmany(500)
            if not batch:
                return
            for row in batch:
                yield row                            # email streamed to the client


def build(status):
    return list(_rows(status))
