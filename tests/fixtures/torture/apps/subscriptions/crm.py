"""CrmService CRM push (CRM integration) — external egress carrying PII. Class-based."""
import requests
from django.conf import settings


class CrmService:
    @staticmethod
    def push_lead(lead):
        # PII EGRESS: email + phone leave in an outbound POST to the CRM
        requests.post(settings.CRM_URL, json={"email": lead.email, "phone": lead.phone})
