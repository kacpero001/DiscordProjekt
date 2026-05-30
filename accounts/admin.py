from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'status', 'is_blocked', 'date_joined']
    list_filter = ['role', 'status', 'is_blocked', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Profil', {'fields': ('avatar', 'bio', 'role', 'status', 'is_blocked', 'blocked_users')}),
    )
    search_fields = ['username', 'email']