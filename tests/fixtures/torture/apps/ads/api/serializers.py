from rest_framework import serializers
from apps.ads.models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign               # a .save() on this writes ad_campaigns, not "CampaignSerializer"
        fields = "__all__"
