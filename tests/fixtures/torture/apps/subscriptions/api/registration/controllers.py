"""Registration — writes a Lead then pushes it to the CRM (CRM external + PII egress)."""
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.subscriptions.models import Lead
from apps.subscriptions.crm import CrmService


class RegistrationView(APIView):
    def post(self, request):
        lead = Lead.objects.create(                          # leads:write
            email=request.data["email"], phone=request.data["phone"], name=request.data["name"])
        CrmService.push_lead(lead)                          # -> requests.post CRM + PII (email, phone) egress
        return Response({"id": lead.id})
