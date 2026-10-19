from rest_framework.permissions import BasePermission


class EsSuperadministrador(BasePermission):
    message = "No tienes permiso para acceder a la plataforma."

    def has_permission(self, request, view) -> bool:
        return bool(request.user.is_authenticated and request.user.is_active
                    and request.user.is_superuser)
