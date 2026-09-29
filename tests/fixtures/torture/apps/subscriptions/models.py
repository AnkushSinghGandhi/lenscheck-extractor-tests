"""subscriptions models (commerce-style). Lead carries PII (email/phone)."""
from django.db import models


class Lead(models.Model):
    email = models.EmailField()          # PII
    phone = models.CharField(max_length=20)   # PII
    name = models.CharField(max_length=120)

    class Meta:
        db_table = "leads"


class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.IntegerField()

    class Meta:
        db_table = "products"


class Order(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    total = models.IntegerField()
    status = models.CharField(max_length=20)

    class Meta:
        db_table = "orders"


class OrderedItems(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.IntegerField()

    class Meta:
        db_table = "order_items"


class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.IntegerField()

    class Meta:
        db_table = "payments"


class CampaignPage(models.Model):
    slug = models.CharField(max_length=120)

    class Meta:
        db_table = "campaign_pages"
