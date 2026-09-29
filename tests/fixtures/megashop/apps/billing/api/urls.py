from django.urls import path
from . import controllers as c

urlpatterns = [
    path("billing/invoices/export/", c.InvoiceExportView.as_view()),
    path("billing/charge/", c.ChargeView.as_view()),
    path("billing/revenue/", c.RevenueReportView.as_view()),
    path("billing/refund/", c.RefundView.as_view()),
    path("billing/webhook/", c.PaymentWebhookView.as_view()),
]
