"""catalog controllers — cache lens (get/set/delete + caches['x']), .raw(), Service() instance-call."""
from django.core.cache import cache, caches
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.catalog.models import Item
from .service import CatalogService


class CatalogListView(APIView):
    def get(self, request):
        hit = cache.get("catalog:list")                   # cache:read
        if hit:
            return Response(hit)
        rows = list(Item.objects.raw("SELECT * FROM catalog_items WHERE name IS NOT NULL"))   # catalog_items:read (raw)
        cache.set("catalog:list", [r.id for r in rows])   # cache:write
        return Response([r.id for r in rows])


class CategorySummaryView(APIView):
    def get(self, request):
        return Response({"n": CatalogService().summary()})   # Service().method() → categories + catalog_items


class CacheClearView(APIView):
    def post(self, request):
        cache.delete("catalog:list")                      # cache:write (delete) — NOT a DB write
        caches["default"].clear()                         # cache:write (clear) — NOT a DB write
        return Response({"cleared": True})                # db must be empty (trap)
