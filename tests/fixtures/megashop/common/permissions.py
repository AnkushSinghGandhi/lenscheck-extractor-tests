"""Shared auth: a custom API-key permission + a reusable permission-constant list (so
`permission_classes = ORDER_PERMS` resolves to the real classes, not an empty edge)."""
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser


class ApiKeyPermission(permissions.BasePermission):
    """Gate on a shared X-API-KEY header (server-to-server / frontend key)."""
    def has_permission(self, request, view):
        return bool(request.META.get("HTTP_X_API_KEY"))


# a permission CONSTANT — controllers do `permission_classes = ORDER_PERMS`
ORDER_PERMS = [IsAuthenticated, ApiKeyPermission]
STAFF_PERMS = [IsAdminUser]
