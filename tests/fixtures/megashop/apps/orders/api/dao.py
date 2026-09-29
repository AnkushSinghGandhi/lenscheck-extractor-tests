"""DAO — deepest layer of the create chain: the actual OrderItem write."""
from apps.orders.models import OrderItem


def write_items(order, items):
    for it in items:
        OrderItem.objects.create(order=order, product_id=it["p"], qty=it["q"])   # order_items:write
