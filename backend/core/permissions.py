"""Custom permissions for NexusPay RBAC"""
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Allow access only to Admin or SuperAdmin users"""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("ADMIN", "SUPERADMIN")
        )


class IsSuperAdmin(BasePermission):
    """Allow access only to SuperAdmin users"""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "SUPERADMIN"
        )


class IsVerifiedUser(BasePermission):
    """Allow access only to KYC-verified users"""
    message = "Account verification required. Please complete KYC."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level: allow owner or admin"""

    def has_object_permission(self, request, view, obj):
        if request.user.role in ("ADMIN", "SUPERADMIN"):
            return True
        owner = getattr(obj, "user", getattr(obj, "owner", None))
        return owner == request.user


class IsWalletOwner(BasePermission):
    """Allow access only to the wallet owner"""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
