from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required

from .forms import ServiceForm, WorkSampleForm
from .models import Service, WorkSample


# ── Public views ──────────────────────────────────────────────────────────────

def our_work(request):
    category = request.GET.get('category', '')
    samples = WorkSample.objects.filter(is_active=True)
    if category:
        samples = samples.filter(category=category)
    categories = WorkSample.CATEGORY_CHOICES
    return render(request, 'portfolio/our_work.html', {
        'samples': samples,
        'categories': categories,
        'active_category': category,
    })


def services_public(request):
    services = Service.objects.filter(is_active=True)
    default_services = [
        {
            'icon': '⚙', 'title': 'CNC Machining',
            'desc': 'Computer-controlled precision for complex geometries at consistent quality.',
            'features': ['3-axis and 4-axis CNC turning and milling', 'Tolerances down to ±0.01mm', 'Complex profile machining', 'Prototype to production volumes'],
        },
        {
            'icon': '🏭', 'title': 'VMC Machining',
            'desc': 'Vertical machining centre for high-accuracy flat and prismatic components.',
            'features': ['Milling, boring, tapping operations', 'High surface finish requirements', 'Large component handling', 'Multi-feature machining in one setup'],
        },
        {
            'icon': '🔩', 'title': 'Precision Engineering',
            'desc': 'Close-tolerance components for critical applications.',
            'features': ['Gear shafts, bushings, flanges', 'Hydraulic and pneumatic components', 'Assembly-ready finished parts', 'Full inspection reports on request'],
        },
        {
            'icon': '🛠', 'title': 'Custom Fabrication',
            'desc': 'From your drawing to a finished part — any geometry, any material.',
            'features': ['Steel, stainless steel, aluminium, brass', 'One-off prototypes to batch production', 'Heat treatment and surface finish options', 'Drawing review and DFM feedback'],
        },
    ]
    return render(request, 'portfolio/services_public.html', {
        'services': services,
        'default_services': default_services,
    })


# ── Admin: Work Samples ───────────────────────────────────────────────────────

@admin_required
def work_sample_list(request):
    samples = WorkSample.objects.all()
    return render(request, 'portfolio/work_sample_list.html', {'samples': samples})


@admin_required
def work_sample_create(request):
    if request.method == 'POST':
        form = WorkSampleForm(request.POST, request.FILES)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.created_by = request.user
            sample.save()
            messages.success(request, 'Work sample added!')
            return redirect('work_sample_list')
    else:
        form = WorkSampleForm()
    return render(request, 'portfolio/work_sample_form.html', {'form': form, 'title': 'Add Work Sample'})


@admin_required
def work_sample_edit(request, pk):
    sample = get_object_or_404(WorkSample, pk=pk)
    if request.method == 'POST':
        form = WorkSampleForm(request.POST, request.FILES, instance=sample)
        if form.is_valid():
            form.save()
            messages.success(request, 'Work sample updated!')
            return redirect('work_sample_list')
    else:
        form = WorkSampleForm(instance=sample)
    return render(request, 'portfolio/work_sample_form.html', {
        'form': form, 'title': 'Edit Work Sample', 'sample': sample
    })


@admin_required
def work_sample_delete(request, pk):
    sample = get_object_or_404(WorkSample, pk=pk)
    if request.method == 'POST':
        sample.delete()
        messages.success(request, 'Work sample deleted.')
        return redirect('work_sample_list')
    return render(request, 'portfolio/work_sample_confirm_delete.html', {'sample': sample})


# ── Admin: Services ───────────────────────────────────────────────────────────

@admin_required
def service_list(request):
    services = Service.objects.all()
    return render(request, 'portfolio/service_list.html', {'services': services})


@admin_required
def service_create(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service added!')
            return redirect('service_list')
    else:
        form = ServiceForm()
    return render(request, 'portfolio/service_form.html', {'form': form, 'title': 'Add Service'})


@admin_required
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated!')
            return redirect('service_list')
    else:
        form = ServiceForm(instance=service)
    return render(request, 'portfolio/service_form.html', {
        'form': form, 'title': 'Edit Service', 'service': service
    })


@admin_required
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        service.delete()
        messages.success(request, 'Service deleted.')
        return redirect('service_list')
    return render(request, 'portfolio/service_confirm_delete.html', {'service': service})
