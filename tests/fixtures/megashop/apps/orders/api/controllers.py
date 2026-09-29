"""orders controllers — exercise E1 (routes), E2 (constant + IsAdminUser + default), E3 (deep chain,
manager, FK, serializer), E5 (celery + thread), E7 (cache)."""
import threading

from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.orders.models import Order
from common.permissions import ORDER_PERMS
from common.tasks import sync_to_crm
from .serializers import OrderSerializer
from .usecases import OrderUseCase
from .services import OrderService


class OrderListView(APIView):
    permission_classes = ORDER_PERMS          # a permission CONSTANT → [IsAuthenticated, ApiKeyPermission]

    def get(self, request):
        from .repositories import OrderRepository
        return Response(OrderRepository.list_active())        # orders:read + cache


class OrderCreateView(APIView):               # no permission_classes → DRF default (IsAuthenticated)
    def post(self, request):
        uc = OrderUseCase(request)            # instance-var use-case helper
        order = uc.create(request.data["customer"], request.data["items"])   # deep chain: orders+order_items write
        sync_to_crm.delay(request.data["customer"])           # async: celery
        threading.Thread(target=_reindex, args=(order.id,)).start()          # async: threading
        return Response({"id": order.id})


def _reindex(order_id):
    return order_id


class OrderDetailView(APIView):
    permission_classes = ORDER_PERMS

    def get(self, request, order_id):
        return Response(list(OrderService.detail(order_id).values("id")))    # orders + order_items + customers (FK)


class OrderImportView(APIView):
    permission_classes = [IsAdminUser]        # explicit admin-only

    def post(self, request):
        Order.objects.bulk_import(request.data["rows"])       # custom manager → orders:write + audit_log:write
        return Response({"ok": True})


class OrderCreateFormView(APIView):
    def post(self, request):
        s = OrderSerializer(data=request.data)
        s.is_valid()
        s.save()                              # orders:write (Meta.model)
        return Response(s.data)
