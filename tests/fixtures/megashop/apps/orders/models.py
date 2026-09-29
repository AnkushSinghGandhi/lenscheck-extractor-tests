"""orders models — Customer carries PII; Order uses the custom OrderManager."""
from django.db import models
from common.managers import OrderManager


class Customer(models.Model):
    email = models.EmailField()          # PII
    phone = models.CharField(max_length=20)   # PII
    name = models.CharField(max_length=120)

    class Meta:
        db_table = "customers"


class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.IntegerField()

    class Meta:
        db_table = "products"


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    total = models.IntegerField()
    status = models.CharField(max_length=20)
    objects = OrderManager()

    class Meta:
        db_table = "orders"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.IntegerField()

    class Meta:
        db_table = "order_items"


class AuditLog(models.Model):
    action = models.CharField(max_length=120)

    class Meta:
        db_table = "audit_log"
