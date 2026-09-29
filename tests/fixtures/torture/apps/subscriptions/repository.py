"""Class-based repository (repository pattern) — ORM reads fronted by a cache."""
from django.core.cache import cache
from .models import Product, Order, OrderedItems


class ProductRepository:
    @staticmethod
    def catalog():
        hit = cache.get("catalog")                       # cache:read
        if hit:
            return hit
        rows = list(Product.objects.all().values("id", "name"))   # products:read
        cache.set("catalog", rows)                       # cache:write
        return rows

    @staticmethod
    def orders_for(lead_id):
        order = Order.objects.filter(lead_id=lead_id).first()     # orders:read
        return OrderedItems.objects.filter(order=order)           # order_items:read
