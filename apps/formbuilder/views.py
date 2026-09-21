from django import forms as django_forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required

from .models import ProjectField


class ProjectFieldForm(django_forms.ModelForm):
    INPUT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm'
    SELECT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm bg-white'

    class Meta:
        model = ProjectField
        fields = ['label', 'field_type', 'placeholder', 'options', 'is_required', 'order', 'is_active']
        widgets = {
            'label': django_forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm', 'placeholder': 'e.g. Drawing Number, Part Code'}),
            'field_type': django_forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm bg-white'}),
            'placeholder': django_forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm', 'placeholder': 'Hint text shown inside the field'}),
            'options': django_forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm', 'rows': 4, 'placeholder': 'One option per line:\nSteel\nAluminium\nBrass'}),
            'order': django_forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm'}),
        }


@admin_required
def field_list(request):
    fields = ProjectField.objects.all()
    return render(request, 'formbuilder/field_list.html', {'fields': fields})


@admin_required
def field_create(request):
    if request.method == 'POST':
        form = ProjectFieldForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Custom field added! It will now appear in the project form.')
            return redirect('field_list')
    else:
        form = ProjectFieldForm()
    return render(request, 'formbuilder/field_form.html', {'form': form, 'title': 'Add Custom Field'})


@admin_required
def field_edit(request, pk):
    field = get_object_or_404(ProjectField, pk=pk)
    if request.method == 'POST':
        form = ProjectFieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, 'Field updated!')
            return redirect('field_list')
    else:
        form = ProjectFieldForm(instance=field)
    return render(request, 'formbuilder/field_form.html', {'form': form, 'title': 'Edit Field', 'field': field})


@admin_required
def field_delete(request, pk):
    field = get_object_or_404(ProjectField, pk=pk)
    if request.method == 'POST':
        field.delete()
        messages.success(request, f'Field "{field.label}" deleted.')
        return redirect('field_list')
    return render(request, 'formbuilder/field_confirm_delete.html', {'field': field})


@admin_required
@require_POST
def field_toggle(request, pk):
    """Quick toggle active/inactive without full edit."""
    field = get_object_or_404(ProjectField, pk=pk)
    field.is_active = not field.is_active
    field.save()
    status = 'shown' if field.is_active else 'hidden'
    messages.success(request, f'"{field.label}" is now {status} in the project form.')
    return redirect('field_list')


# ── Process Template Management ───────────────────────────────────────────────

class ProcessTemplateForm(django_forms.ModelForm):
    class Meta:
        from .models import ProcessTemplate
        model = ProcessTemplate
        fields = ['name', 'order', 'is_active']
        widgets = {
            'name': django_forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm',
                'placeholder': 'e.g. Surface Grinding, Anodizing, Inspection'
            }),
            'order': django_forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm'
            }),
        }


@admin_required
def process_template_list(request):
    from .models import ProcessTemplate
    templates = ProcessTemplate.objects.all()
    return render(request, 'formbuilder/process_template_list.html', {'templates': templates})


@admin_required
def process_template_create(request):
    if request.method == 'POST':
        form = ProcessTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Process stage added!')
            return redirect('process_template_list')
    else:
        form = ProcessTemplateForm()
    return render(request, 'formbuilder/process_template_form.html', {'form': form, 'title': 'Add Process Stage'})


@admin_required
def process_template_edit(request, pk):
    from .models import ProcessTemplate
    template = get_object_or_404(ProcessTemplate, pk=pk)
    if request.method == 'POST':
        form = ProcessTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stage updated!')
            return redirect('process_template_list')
    else:
        form = ProcessTemplateForm(instance=template)
    return render(request, 'formbuilder/process_template_form.html', {'form': form, 'title': 'Edit Stage', 'template': template})


@admin_required
def process_template_delete(request, pk):
    from .models import ProcessTemplate
    template = get_object_or_404(ProcessTemplate, pk=pk)
    if request.method == 'POST':
        template.delete()
        messages.success(request, f'Stage "{template.name}" deleted.')
        return redirect('process_template_list')
    return render(request, 'formbuilder/process_template_confirm_delete.html', {'template': template})


@admin_required
@require_POST
def process_template_toggle(request, pk):
    from .models import ProcessTemplate
    template = get_object_or_404(ProcessTemplate, pk=pk)
    template.is_active = not template.is_active
    template.save()
    messages.success(request, f'"{template.name}" is now {"active" if template.is_active else "hidden"}.')
    return redirect('process_template_list')


@admin_required
def seed_default_processes(request):
    """Seed the default 8 process stages if none exist."""
    from .models import ProcessTemplate
    if request.method == 'POST':
        defaults = [
            'Material Received', 'Cutting', 'Milling', 'Drilling',
            'Heat Treatment', 'Finishing', 'Quality Check', 'Completed'
        ]
        ProcessTemplate.objects.all().delete()
        for i, name in enumerate(defaults):
            ProcessTemplate.objects.create(name=name, order=i, is_active=True)
        messages.success(request, 'Default process stages restored!')
        return redirect('process_template_list')
    return redirect('process_template_list')


# ── Per-project process management ───────────────────────────────────────────

@admin_required
def project_add_process(request, project_pk):
    """Add a new process stage to an existing project."""
    from apps.projects.models import Project, ProjectProcess, ProjectActivity
    project = get_object_or_404(Project, pk=project_pk)
    if request.method == 'POST':
        name = request.POST.get('process_name', '').strip()
        if name:
            last_order = project.processes.order_by('-order').values_list('order', flat=True).first() or 0
            ProjectProcess.objects.create(
                project=project, process_name=name,
                order=last_order + 1, status='pending'
            )
            ProjectActivity.objects.create(
                project=project, actor=request.user,
                action=f'Process stage "{name}" added'
            )
            messages.success(request, f'Stage "{name}" added.')
        else:
            messages.error(request, 'Stage name cannot be empty.')
    return redirect('project_detail', pk=project_pk)


@admin_required
def project_delete_process(request, project_pk, process_pk):
    """Delete a process stage from a project."""
    from apps.projects.models import Project, ProjectProcess, ProjectActivity
    project = get_object_or_404(Project, pk=project_pk)
    process = get_object_or_404(ProjectProcess, pk=process_pk, project=project)
    if request.method == 'POST':
        name = process.process_name
        process.delete()
        ProjectActivity.objects.create(
            project=project, actor=request.user,
            action=f'Process stage "{name}" deleted'
        )
        messages.success(request, f'Stage "{name}" deleted.')
    return redirect('project_detail', pk=project_pk)
