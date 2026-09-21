from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required
from apps.core.validators import validate_image_upload

from .models import Machine


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ['machine_name', 'machine_type', 'model_number', 'manufacturer',
                  'description', 'specifications', 'image', 'is_active']
        widgets = {
            'machine_name': forms.TextInput(attrs={'class': 'form-input'}),
            'machine_type': forms.Select(attrs={'class': 'form-input'}),
            'model_number': forms.TextInput(attrs={'class': 'form-input'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'specifications': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
        }

    def clean_image(self):
        return validate_image_upload(self.cleaned_data.get('image'))


@admin_required
def machine_list(request):
    machines = Machine.objects.all().order_by('machine_name')
    search = request.GET.get('search', '').strip()
    if search:
        machines = machines.filter(machine_name__icontains=search)
    return render(request, 'machines/machine_list.html', {
        'machines': machines,
        'search': search,
    })


@admin_required
def machine_create(request):
    if request.method == 'POST':
        form = MachineForm(request.POST, request.FILES)
        if form.is_valid():
            machine = form.save()
            messages.success(request, f'Machine "{machine.machine_name}" added successfully.')
            return redirect('machine_list')
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = MachineForm()
    return render(request, 'machines/machine_form.html', {'form': form, 'title': 'Add Machine'})


@admin_required
def machine_edit(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    if request.method == 'POST':
        form = MachineForm(request.POST, request.FILES, instance=machine)
        if form.is_valid():
            form.save()
            messages.success(request, 'Machine updated successfully.')
            return redirect('machine_list')
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = MachineForm(instance=machine)
    return render(request, 'machines/machine_form.html', {
        'form': form, 'title': 'Edit Machine', 'machine': machine,
    })


@admin_required
def machine_delete(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    if request.method == 'POST':
        name = machine.machine_name
        # Projects reference the machine with SET_NULL, so deleting it leaves
        # their history intact; tell the admin how many are affected.
        machine.delete()
        messages.success(request, f'Machine "{name}" deleted.')
        return redirect('machine_list')
    return render(request, 'machines/machine_confirm_delete.html', {
        'machine': machine,
        'project_count': machine.projects.count(),
    })
