from django.contrib import admin
from .models import Machine


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('machine_name', 'machine_type', 'model_number', 'manufacturer', 'is_active')
    list_filter = ('machine_type', 'is_active')
    search_fields = ('machine_name', 'model_number', 'manufacturer')
    list_editable = ('is_active',)
