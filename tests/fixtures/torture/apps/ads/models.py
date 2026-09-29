"""ads models — explicit db_table names + the real example `ad_target` db_table collision
(two models sharing `ad_target_entity_slice`) + a custom manager on Campaign."""
from django.db import models
from common.managers import CampaignManager


class Campaign(models.Model):
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=20)
    objects = CampaignManager()

    class Meta:
        db_table = "ad_campaigns"


class LeadDeliveryLog(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    amount = models.IntegerField()

    class Meta:
        db_table = "ad_delivery_logs"


class AuditLog(models.Model):
    action = models.CharField(max_length=120)

    class Meta:
        db_table = "ad_audit_log"


class Entity(models.Model):
    kind = models.CharField(max_length=20)
    name = models.CharField(max_length=120)

    class Meta:
        db_table = "ad_entity"


class AdTarget(models.Model):
    uid = models.IntegerField()
    action = models.CharField(max_length=120)
    added_on = models.DateTimeField(db_column="created", auto_now_add=True)

    class Meta:
        db_table = "ad_target"


class AdTargetEntity(models.Model):
    ad_target = models.ForeignKey(AdTarget, on_delete=models.DO_NOTHING)
    entity_id = models.IntegerField()
    entity_type = models.CharField(max_length=120)

    class Meta:
        db_table = "ad_target_entity_slice"     # real example collision: two models, one table
