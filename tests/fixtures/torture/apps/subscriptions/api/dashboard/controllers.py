from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import helpers


class SubscriptionDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        return Response(helpers.dashboard_data(lead_id))     # -> repo -> orders + order_items
