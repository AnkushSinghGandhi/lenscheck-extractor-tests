"""Streaming CSV export — the exact example interactions.py shape: a module-constant raw SQL run through
a chain of pass-through generators. The endpoint reaches this only via a *function-local* import."""
from django.db import connection

from common.raw_sql import _INTERACTIONS_SQL

CHUNK = 2000


def _source_rows(kind, entity_id, window):
    with connection.cursor() as cursor:
        cursor.execute(_INTERACTIONS_SQL, [kind, window[0], window[1]])   # raw: cta_slice, entities_slice, users, cities
        while True:
            batch = cursor.fetchmany(CHUNK)
            if not batch:
                return
            for row in batch:
                yield row


def _stream(kind, entity_id, window):
    for row in _source_rows(kind, entity_id, window):
        yield row


def build_response(kind, entity_id, window):
    return list(_stream(kind, entity_id, window))
