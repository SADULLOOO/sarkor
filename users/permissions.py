from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission


class IsNotBlocked(BasePermission):
    message = _("Your account is blocked.")

    def has_permission(self, request, view):
        user = request.user
        return not (user.is_authenticated and user.is_blocked)


class IsCustomer(BasePermission):
    message = _("Only customers can do this.")

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_customer


class IsExecutor(BasePermission):
    message = _("Only executors can do this.")

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_executor
