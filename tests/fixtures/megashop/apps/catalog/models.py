"""catalog models."""
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120)

    class Meta:
        db_table = "categories"


class Item(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    products = models.ManyToManyField("orders.Product")
    name = models.CharField(max_length=120)

    class Meta:
        db_table = "catalog_items"
