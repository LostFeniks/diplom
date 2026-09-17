from rest_framework.permissions import BasePermission


class IsAuthenticatedStorageUser(BasePermission):
    message = "Требуется аутентификация."

    def has_permission(self, request, view):
        return bool(request.session.get("user_id"))


class IsAdminStorageUser(BasePermission):
    message = "Требуются права администратора."

    def has_permission(self, request, view):
        user = getattr(request, "storage_user", None)
        return bool(user and user.is_admin)
