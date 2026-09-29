"""catalog service — invoked as `CatalogService().summary()` (instance-call); includes an m2m `.add()`
that must NOT be counted as a DB write (only SQLAlchemy session.add is a write)."""
from apps.catalog.models import Category, Item


class CatalogService:
    def summary(self):
        cats = Category.objects.filter(name__isnull=False)   # categories:read
        item = Item.objects.first()                          # catalog_items:read
        item.products.add(1)                                 # m2m add — NOT a table write (trap)
        return cats.count()
