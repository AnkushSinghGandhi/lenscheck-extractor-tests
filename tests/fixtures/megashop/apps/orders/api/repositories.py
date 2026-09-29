"""Repository — cache-fronted reads + a hop deeper into the DAO for the create path."""
from django.core.cache import cache
from apps.orders.models import Order, OrderItem
from . import dao


class OrderRepository:
    @staticmethod
    def list_active():
        hit = cache.get("orders:active")                 # cache:read
        if hit:
            return hit
        rows = list(Order.objects.filter(status="active").values("id"))   # orders:read
        cache.set("orders:active", rows)                 # cache:write
        return rows

    @staticmethod
    def items_for(order_id):
        return OrderItem.objects.filter(order_id=order_id)   # order_items:read

    @staticmethod
    def persist_items(order, items):
        dao.write_items(order, items)                    # -> order_items:write (deeper)
