"""Use-case layer — an instance-var helper the controller stores then calls (h = UseCase(); h.run())."""
from .services import OrderService


class OrderUseCase:
    def __init__(self, request):
        self.request = request

    def create(self, customer_id, items):
        return OrderService.create(customer_id, items)         # -> service -> repo -> dao (deep chain)
