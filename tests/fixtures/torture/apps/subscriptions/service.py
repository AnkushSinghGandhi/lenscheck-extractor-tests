"""A service invoked as `SubscriptionService().summary()` (instance-call pattern). Includes a Django
m2m `.add()` — which must NOT be mistaken for a DB write (only SQLAlchemy session.add is a write)."""
from .models import Product, Order


class SubscriptionService:
    def summary(self, lead_id):
        products = Product.objects.filter(price__gt=0)      # products:read
        order = Order.objects.get(lead_id=lead_id)          # orders:read
        order.products.add(products.first())                # m2m add — NOT a table write (trap)
        return products.count()
