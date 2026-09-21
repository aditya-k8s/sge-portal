from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'company_name', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'company_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Company Info', {'fields': ('role', 'company_name', 'phone', 'address', 'profile_image')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Company Info', {'fields': ('role', 'company_name', 'phone', 'address')}),
    )
