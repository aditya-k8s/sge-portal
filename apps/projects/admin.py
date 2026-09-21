from django.contrib import admin
from .models import Project, ProjectProcess, ProjectFile, ProjectActivity


class ProjectProcessInline(admin.TabularInline):
    model = ProjectProcess
    extra = 0
    fields = ('process_name', 'status', 'order', 'notes', 'completed_at')
    readonly_fields = ('completed_at',)


class ProjectFileInline(admin.TabularInline):
    model = ProjectFile
    extra = 0
    fields = ('file', 'file_name', 'file_type', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_code', 'project_name', 'client', 'machine', 'status', 'current_process', 'expected_delivery', 'progress_percentage')
    list_filter = ('status', 'machine')
    search_fields = ('project_name', 'project_code', 'client__first_name', 'client__company_name')
    readonly_fields = ('project_code', 'created_at', 'updated_at')
    inlines = [ProjectProcessInline, ProjectFileInline]
    date_hierarchy = 'created_at'

    def progress_percentage(self, obj):
        return f"{obj.progress_percentage}%"
    progress_percentage.short_description = 'Progress'


@admin.register(ProjectProcess)
class ProjectProcessAdmin(admin.ModelAdmin):
    list_display = ('project', 'process_name', 'status', 'order', 'updated_at')
    list_filter = ('status',)
    search_fields = ('project__project_name', 'process_name')


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ('project', 'file_name', 'file_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('file_type',)


@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):
    list_display = ('project', 'actor', 'action', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
