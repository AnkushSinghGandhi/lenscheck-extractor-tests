"""A custom manager whose method hides writes — followed via `Order.objects.bulk_import(...)`."""
from django.db import models


class OrderManager(models.Manager):
    def bulk_import(self, rows):
        for r in rows:
            self.create(**r)                       # write to the managed model (Order)
        from apps.orders.models import AuditLog
        AuditLog.objects.create(action="order_import")   # audit_log:write hidden in the manager
