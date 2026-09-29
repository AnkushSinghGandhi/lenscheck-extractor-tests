"""Service layer — orchestrates the repository; holds the FK-traversal read and the create hop."""
from apps.orders.models import Order, Customer
from .repositories import OrderRepository


class OrderService:
    @staticmethod
    def detail(order_id):
        order = Order.objects.get(id=order_id)                 # orders:read
        # FK traversal: `customer__email` joins the Customer table (customers:read)
        Order.objects.filter(customer__email="x@y.com").exists()
        return OrderRepository.items_for(order_id)             # -> order_items:read

    @staticmethod
    def create(customer_id, items):
        order = Order.objects.create(customer_id=customer_id, total=0, status="new")   # orders:write
        OrderRepository.persist_items(order, items)            # -> dao -> order_items:write
        return order
