"""Interaction counts — the example metrics.py shape: an ORM filter with an FK-traversal kwarg that
joins a related table (the FK read must be stamped at the kwarg line, not the .filter() line)."""
from apps.ads.models import AdTargetEntity


def counts(kind, window):
    qs = AdTargetEntity.objects.filter(          # ad_target_entity_slice:read
        entity_type=kind,
        ad_target__added_on__gte=window[0],       # FK traversal → AdTarget (ad_target):read
        ad_target__added_on__lte=window[1],
    )
    return qs.values("entity_id").count()
