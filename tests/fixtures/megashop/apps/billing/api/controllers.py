"""billing controllers — E2 base-class inheritance + open-webhook, E3 raw SQL (streaming + CTE + write),
E4 stripe/razorpay/requests, E5 celery apply_async, E6 off-platform + to-client PII."""
import requests
from django.conf import settings
from django.db import connection
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.billing.models import Refund, Payment
from apps.billing.gateway import PaymentGateway
from apps.orders.models import Order, Customer
from common.raw_sql import _REVENUE_CTE_SQL
from common.tasks import send_receipt


class BaseBillingView(APIView):
    permission_classes = [IsAdminUser]            # inherited by subclasses that set nothing


class InvoiceExportView(BaseBillingView):         # → auth inherited = IsAdminUser
    def get(self, request):
        from . import export_stream
        return Response(export_stream.build(request.GET.get("status", "paid")))   # PII to-client (email streamed)


class ChargeView(BaseBillingView):
    def post(self, request):
        order = Order.objects.get(id=request.data["order"])      # orders:read
        customer = Customer.objects.get(id=request.data["customer"])   # customers:read (PII source)
        PaymentGateway.charge(order, customer)                   # stripe + requests + PII off-platform + payment write
        send_receipt.apply_async(args=[customer.email])          # async: celery
        return Response({"charged": True})


class RevenueReportView(BaseBillingView):
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute(_REVENUE_CTE_SQL, [request.GET.get("since", "2020-01-01")])   # orders + billing_payments (CTE)
            return Response(cur.fetchall())


class RefundView(BaseBillingView):
    def post(self, request):
        # razorpay egress (a settings host) — no PII in the body here
        requests.post(settings.RAZORPAY_URL, json={"payment_id": request.data["pid"]})   # external
        return Response({"id": Refund.objects.create(payment_id=request.data["pid"], amount=request.data["amt"]).id})


class PaymentWebhookView(APIView):
    permission_classes = []                       # OPEN on purpose (external payment provider callback)

    def post(self, request):
        Payment.objects.filter(id=request.data["pid"]).update(amount=request.data["amt"])   # billing_payments:write
        return Response({"ok": True})
