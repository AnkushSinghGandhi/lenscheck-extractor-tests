"""Dashboard helpers — a deeper chain into the repository (orders + order_items)."""
from apps.subscriptions.repository import ProductRepository


def dashboard_data(lead_id):
    items = ProductRepository.orders_for(lead_id)     # -> orders:read + order_items:read
    return {"count": len(list(items))}
