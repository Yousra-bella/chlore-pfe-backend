from rest_framework.permissions import BasePermission


class EstAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class EstChefCentre(BasePermission):
    """Admin + Chef de centre."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['admin', 'chef_centre']
        )


class EstAgent(BasePermission):
    """Tous les rôles authentifiés sauf consultation en écriture."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['admin', 'chef_centre', 'agent', 'consultation']
        )


class LectureSeule(BasePermission):
    """Consultation — lecture seule, aucune modification"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        # Lecture seule : GET, HEAD, OPTIONS uniquement
        return request.method in ['GET', 'HEAD', 'OPTIONS']