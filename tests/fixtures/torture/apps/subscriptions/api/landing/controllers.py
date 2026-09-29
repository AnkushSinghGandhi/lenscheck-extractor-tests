from rest_framework.views import APIView
from rest_framework.response import Response

from .helpers.subscription_helpers import SubscriptionHelper
from apps.subscriptions.service import SubscriptionService


class SubscriptionLandingView(APIView):
    def get(self, request):
        return Response(SubscriptionHelper.landing_data())      # -> repo -> products:read + cache


class SubscriptionSummaryView(APIView):
    def get(self, request, lead_id):
        return Response({"n": SubscriptionService().summary(lead_id)})   # Service().method() → products + orders
