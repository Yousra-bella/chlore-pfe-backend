from rest_framework.permissions import BasePermission


def get_role(user):
    """Retourne le rôle de l'utilisateur ou None."""
    try:
        return user.profile.role
    except Exception:
        return None


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) == 'admin'


class IsAdminOrSuperviseur(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) in ('admin', 'superviseur')


class IsAnyRole(BasePermission):
    """Tout utilisateur authentifié avec un profil peut accéder."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) is not None