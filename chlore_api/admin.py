from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Centre


@admin.register(Centre)
class CentreAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'ville']
    search_fields = ['nom']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['username', 'role', 'centre', 'email', 'is_active']
    list_filter   = ['role', 'centre', 'is_active']
    search_fields = ['username', 'email']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations chlore', {
            'fields': ('role', 'centre', 'telephone')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations chlore', {
            'fields': ('role', 'centre', 'telephone')
        }),
    )