"""A custom manager whose method hides writes — must be followed to surface them."""
from django.db import models


class CampaignManager(models.Manager):
    def import_batch(self, rows):
        for r in rows:
            self.create(**r)                # write on the manager's own model (Campaign)
        from apps.ads.models import AuditLog
        AuditLog.objects.create(action="import")   # audit_log:write hidden in the manager
