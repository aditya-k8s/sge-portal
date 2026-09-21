from django.contrib import admin
from .models import WorkSample, Service


@admin.register(WorkSample)
class WorkSampleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'material', 'is_featured', 'is_active', 'created_at')
    list_filter = ('category', 'is_featured', 'is_active')
    search_fields = ('title', 'description', 'material')
    list_editable = ('is_featured', 'is_active')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'description')
