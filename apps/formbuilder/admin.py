from django.contrib import admin
from .models import ProjectField, ProjectFieldValue

@admin.register(ProjectField)
class ProjectFieldAdmin(admin.ModelAdmin):
    list_display = ('label', 'field_type', 'is_required', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('field_type', 'is_active')

@admin.register(ProjectFieldValue)
class ProjectFieldValueAdmin(admin.ModelAdmin):
    list_display = ('project', 'field', 'value')
    list_filter = ('field',)

from .models import ProcessTemplate

@admin.register(ProcessTemplate)
class ProcessTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_editable = ('order', 'is_active')
