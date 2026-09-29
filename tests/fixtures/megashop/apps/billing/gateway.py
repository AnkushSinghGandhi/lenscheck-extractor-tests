"""Payment gateway — Stripe SDK + a settings-host POST carrying PII (off-platform egress)."""
import requests
import stripe
from django.conf import settings
from .models import Payment


class PaymentGateway:
    @staticmethod
    def charge(order, customer):
        stripe.Charge.create(amount=order.total, currency="usd")     # external: stripe (SDK verb)
        # PII off-platform: the customer's email leaves in the outbound POST body
        requests.post(settings.PAYMENT_URL, json={"email": customer.email, "amount": order.total})
        return Payment.objects.create(order=order, amount=order.total)   # billing_payments:write
