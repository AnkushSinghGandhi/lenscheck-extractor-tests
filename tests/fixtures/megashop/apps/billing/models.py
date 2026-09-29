"""billing models."""
from django.db import models


class Invoice(models.Model):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE)
    amount = models.IntegerField()
    status = models.CharField(max_length=20)

    class Meta:
        db_table = "billing_invoices"


class Payment(models.Model):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE)
    amount = models.IntegerField()

    class Meta:
        db_table = "billing_payments"


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    amount = models.IntegerField()

    class Meta:
        db_table = "billing_refunds"
