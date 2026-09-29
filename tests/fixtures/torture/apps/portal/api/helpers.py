"""portal helpers — a get_object_or_404 read and the dynamic-model helper (param-binding test)."""
from django.shortcuts import get_object_or_404

from apps.portal.models import User


def load_user(pk):
    return get_object_or_404(User, pk=pk)          # users:read (shortcut)


def fetch_all(model):
    # dynamic model: `model` is bound to a real class at the call site — must resolve, not invent "model"
    return list(model.objects.all())
