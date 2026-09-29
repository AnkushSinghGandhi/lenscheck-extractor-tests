"""Payment egress — Stripe SDK (non-standard verb) + a settings-host POST carrying PII. Class-based
so it resolves by name across the nested api/ packages (this fixture is class-heavy)."""
import requests
import stripe
from django.conf import settings
from .models import Payment


class PaymentGateway:
    @staticmethod
    def charge(order, lead):
        stripe.Charge.create(amount=order.total, currency="usd")     # external (SDK verb)
        requests.post(settings.PAYMENT_URL, json={"email": lead.email, "amount": order.total})  # external + PII
        return Payment.objects.create(order=order, amount=order.total)   # payments:write
