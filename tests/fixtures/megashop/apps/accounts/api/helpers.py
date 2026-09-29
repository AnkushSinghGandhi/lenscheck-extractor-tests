"""accounts helpers — get_object_or_404, the dynamic-model helper, and an instance-var update flow."""
from django.shortcuts import get_object_or_404
from apps.accounts.models import Account


def load_account(pk):
    return get_object_or_404(Account, pk=pk)          # accounts:read (shortcut)


def fetch_all(model):
    return list(model.objects.all())                  # dynamic model → bound at the call site


class UpdateFlow:
    def __init__(self, request):
        self.request = request

    def run(self, pk):
        Account.objects.filter(id=pk).update(name=self.request.data["name"])   # accounts:write
