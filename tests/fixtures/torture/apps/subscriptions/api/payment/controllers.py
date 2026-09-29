"""Payment controllers — the subscription-purchase flow: a cache+ORM check view, and a charge
view that reaches Stripe/requests egress + PII through a function-local import."""
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.subscriptions.models import Order, CampaignPage, Product, Lead


class PurchaseCheckView(APIView):
    def get(self, request, lead_id):
        cached = cache.get("purchase:" + str(lead_id))       # cache:read
        if cached:
            return Response(cached)
        data = {
            "order": Order.objects.filter(lead_id=lead_id).exists(),   # orders:read
            "page": CampaignPage.objects.filter(slug="x").first(),     # campaign_pages:read
            "product": Product.objects.filter(price__gt=0).count(),    # products:read
        }
        cache.set("purchase:" + str(lead_id), data)          # cache:write
        return Response(data)


class SubscriptionPurchaseView(APIView):
    def post(self, request):
        from apps.subscriptions.payment import PaymentGateway     # class resolves by name (nested pkgs)
        lead = Lead.objects.get(id=request.data["lead"])      # leads:read (PII source)
        order = Order.objects.get(id=request.data["order"])   # orders:read
        PaymentGateway.charge(order, lead)                    # -> stripe + requests + PII egress + payments:write
        return Response({"paid": True})
