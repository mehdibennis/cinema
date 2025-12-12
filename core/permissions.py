"""Permissions personnalisées réutilisables."""

from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only for all, write for admin only.

    - GET, HEAD, OPTIONS: allowed for all (including anonymous)
    - POST, PUT, PATCH, DELETE: reserved for administrators (is_staff)
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
