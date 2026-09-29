"""ads controllers (cms-style APIViews). Delegates to helper/interactions/metrics/delivery_logs;
one endpoint reaches the raw-SQL export only through a FUNCTION-LOCAL import (the real example dodge)."""
from django.db import connection
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.ads.models import Campaign
from .serializers import CampaignSerializer
from . import metrics, delivery_logs
from common.raw_sql import _PURGE_SQL


class CampaignListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(list(Campaign.objects.filter(status="active").values("id")))   # ad_campaigns:read


class CampaignExportView(APIView):
    def get(self, request):
        return Response(delivery_logs.revenue(request.GET.get("status", "active")))     # CTE raw SQL


class CampaignImportView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        Campaign.objects.import_batch(request.data["rows"])          # custom manager → campaigns + audit_log
        return Response({"ok": True})


class CampaignCreateView(APIView):
    def post(self, request):
        s = CampaignSerializer(data=request.data)
        s.is_valid()
        s.save()                                                     # ad_campaigns:write (Meta.model)
        return Response(s.data)


class EntityInteractionsExportView(APIView):
    def get(self, request, kind, pk):
        from . import interactions                                   # FUNCTION-LOCAL import
        window = (request.GET.get("start"), request.GET.get("end"))
        return Response(interactions.build_response(kind, pk, window))   # raw SQL: cta tables + users + cities


class EntityMetricsView(APIView):
    def get(self, request, kind):
        window = (request.GET.get("start"), request.GET.get("end"))
        return Response({"n": metrics.counts(kind, window)})         # FK traversal


class CampaignRawView(APIView):
    def get(self, request):
        rows = Campaign.objects.raw("SELECT * FROM ad_campaigns WHERE status = %s", ["active"])
        return Response([r.id for r in rows])            # ad_campaigns:read (via .raw)


class AuditPurgeView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        with connection.cursor() as cur:
            cur.execute(_PURGE_SQL, [request.data["before"]])        # raw DELETE → ad_audit_log:write
        return Response({"ok": True})
