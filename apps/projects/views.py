import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.core.decorators import admin_required
from apps.notifications.models import Notification

from .forms import BillForm, ProjectFileForm, ProjectForm
from .models import (
    Project,
    ProjectActivity,
    ProjectBill,
    ProjectFile,
    ProjectProcess,
    ProjectRating,
)
from .pdf_utils import generate_invoice_pdf, generate_timeline_pdf

logger = logging.getLogger(__name__)


# -- Helpers ------------------------------------------------------------------

def _admin_users():
    """Every user who counts as an administrator, in one query."""
    return User.objects.filter(Q(is_staff=True) | Q(role='admin')).distinct()


def _email_client(project, message):
    """
    Email a project update to its client.

    Failures are logged rather than swallowed. Delivery problems used to
    disappear into a bare `except Exception: pass`, so a misconfigured SMTP
    host looked exactly like a working one.
    """
    if not project.client.email:
        return
    try:
        send_mail(
            subject=f'Project Update: {project.project_name}',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[project.client.email],
            fail_silently=False,
        )
    except Exception:
        logger.warning(
            'Could not email project update for %s to the client',
            project.project_code, exc_info=True,
        )


def send_project_notification(project, message, notify_type='project_update',
                              also_notify_admins=False):
    """Notify the client about a change, and optionally the admins too."""
    recipients = [project.client]
    if also_notify_admins:
        recipients += [a for a in _admin_users() if a.pk != project.client_id]

    # One INSERT for the whole fan-out instead of one per recipient.
    Notification.objects.bulk_create([
        Notification(user=user, project=project, message=message,
                     notification_type=notify_type)
        for user in recipients
    ])
    _email_client(project, message)


def notify_admins(project, message, notify_type='file_uploaded'):
    """Notify only the admins, e.g. when a client uploads something."""
    Notification.objects.bulk_create([
        Notification(user=admin, project=project, message=message,
                     notification_type=notify_type)
        for admin in _admin_users()
    ])


def _visible_projects(user):
    """
    The projects a user is allowed to see.

    Centralised so no view can accidentally omit the client filter and leak
    another company's work.
    """
    queryset = Project.objects.select_related('client', 'machine')
    if user.is_admin_user():
        return queryset
    return queryset.filter(client=user)


def _paginate(request, queryset, per_page=None):
    per_page = per_page or getattr(settings, 'PAGE_SIZE', 20)
    paginator = Paginator(queryset, per_page)
    # get_page never raises: a junk or out-of-range ?page= lands on a real
    # page instead of a 404 or a traceback.
    return paginator.get_page(request.GET.get('page'))


# -- Dashboards ---------------------------------------------------------------

@login_required
def dashboard(request):
    user = request.user
    if user.is_admin_user():
        # One grouped query for all five counters, instead of five COUNT(*)
        # round trips over the whole table.
        counts = dict(
            Project.objects.values_list('status')
            .annotate(total=Count('id'))
            .values_list('status', 'total')
        )
        recent_projects = (
            Project.objects.select_related('client', 'machine')
            .prefetch_related('processes')
            .order_by('-updated_at')[:8]
        )
        context = {
            'total_clients': User.objects.filter(role='client').count(),
            'total_projects': sum(counts.values()),
            'in_progress': counts.get('in_progress', 0),
            'completed': counts.get('completed', 0),
            'pending': counts.get('pending', 0),
            'recent_projects': recent_projects,
            'recent_activities': (
                ProjectActivity.objects.select_related('project', 'actor')
                .order_by('-created_at')[:10]
            ),
            'is_admin': True,
        }
    else:
        projects = Project.objects.filter(client=user).select_related('machine')
        counts = dict(
            projects.values_list('status')
            .annotate(total=Count('id'))
            .values_list('status', 'total')
        )
        context = {
            'projects': projects,
            'in_progress': counts.get('in_progress', 0),
            'completed': counts.get('completed', 0),
            'recent_projects': (
                projects.prefetch_related('processes').order_by('-updated_at')[:6]
            ),
            'unread_notifications': Notification.objects.filter(
                user=user, is_read=False
            ).count(),
            'is_admin': False,
        }
    return render(request, 'projects/dashboard.html', context)


@login_required
def client_dashboard(request):
    """Dedicated dashboard for client users."""
    if request.user.is_admin_user():
        return redirect('dashboard')

    projects = (
        Project.objects.filter(client=request.user)
        .select_related('machine')
        .prefetch_related('processes')
        .order_by('-created_at')
    )
    bills = ProjectBill.objects.filter(project__client=request.user)
    counts = dict(
        projects.values_list('status').annotate(total=Count('id'))
        .values_list('status', 'total')
    )
    context = {
        'projects': projects[:8],
        'recent_bills': bills.select_related('project').order_by('-uploaded_at')[:5],
        'recent_notifications': (
            Notification.objects.filter(user=request.user)
            .select_related('project').order_by('-created_at')[:8]
        ),
        'total_projects': sum(counts.values()),
        'in_progress': counts.get('in_progress', 0),
        'completed': counts.get('completed', 0),
        # Counted on the full queryset. This previously counted a queryset
        # already sliced to five rows, so the figure could never exceed 5.
        'pending_bills': bills.count(),
    }
    return render(request, 'projects/client_dashboard.html', context)


# -- Projects -----------------------------------------------------------------

@login_required
def project_list(request):
    projects = _visible_projects(request.user).prefetch_related('processes')

    search = request.GET.get('search', '').strip()
    if search:
        projects = projects.filter(
            Q(project_name__icontains=search)
            | Q(project_code__icontains=search)
            | Q(client__first_name__icontains=search)
            | Q(client__last_name__icontains=search)
            | Q(client__company_name__icontains=search)
        )

    status_filter = request.GET.get('status', '')
    valid_statuses = {value for value, _ in Project.STATUS_CHOICES}
    if status_filter in valid_statuses:
        projects = projects.filter(status=status_filter)
    else:
        # Ignore an unrecognised ?status= rather than returning nothing.
        status_filter = ''

    page = _paginate(request, projects.order_by('-created_at'))
    return render(request, 'projects/project_list.html', {
        'projects': page,
        'page_obj': page,
        'search': search,
        'status_filter': status_filter,
        'status_choices': Project.STATUS_CHOICES,
        'total_count': page.paginator.count,
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(
        _visible_projects(request.user).prefetch_related(
            'processes', 'bills', 'files',
        ).select_related('rating', 'rating__client'),
        pk=pk,
    )
    context = {
        'project': project,
        'processes': project.processes.all(),
        'files': project.files.all(),
        'activities': project.activities.select_related('actor')[:15],
        'file_form': ProjectFileForm(),
        'bill_form': BillForm(),
    }
    return render(request, 'projects/project_detail.html', context)


def _save_custom_field_values(project, post_data, update=False):
    """Persist the admin-defined custom fields attached to the project form."""
    from apps.formbuilder.models import ProjectField, ProjectFieldValue

    for field in ProjectField.objects.filter(is_active=True):
        value = post_data.get(f'custom_{field.pk}', '')
        if update:
            ProjectFieldValue.objects.update_or_create(
                project=project, field=field, defaults={'value': value}
            )
        elif value:
            ProjectFieldValue.objects.create(
                project=project, field=field, value=value
            )


def _create_process_stages(project):
    """
    Give a new project its process stages, from the admin-managed templates
    or the model's defaults when none are configured.
    """
    from apps.formbuilder.models import ProcessTemplate

    templates = list(ProcessTemplate.objects.filter(is_active=True))
    if templates:
        stages = [
            ProjectProcess(project=project, process_name=t.name,
                           order=t.order, status='pending')
            for t in templates
        ]
    else:
        stages = [
            ProjectProcess(project=project, process_name=name,
                           order=index, status='pending')
            for index, name in enumerate(Project.DEFAULT_PROCESSES)
        ]
    ProjectProcess.objects.bulk_create(stages)


@admin_required
def project_create(request):
    from apps.formbuilder.models import ProjectField

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            # All of it or none of it. Without this a failure partway through
            # left a project with no process stages, which renders as a
            # permanently 0% project that cannot be advanced.
            with transaction.atomic():
                project = form.save()
                _save_custom_field_values(project, request.POST)
                _create_process_stages(project)
                ProjectActivity.objects.create(
                    project=project,
                    actor=request.user,
                    action=f'Project created by {request.user.get_full_name() or request.user.username}',
                )
            send_project_notification(
                project,
                f'Your new project "{project.project_name}" '
                f'(#{project.project_code}) has been created and is now pending.',
                notify_type='project_created',
            )
            messages.success(request, f'Project {project.project_name} created successfully.')
            return redirect('project_detail', pk=project.pk)
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {
        'form': form,
        'title': 'Create New Project',
        'custom_fields': ProjectField.objects.filter(is_active=True),
    })


@admin_required
def project_edit(request, pk):
    from apps.formbuilder.models import ProjectField

    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        old_status = project.status
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            with transaction.atomic():
                project = form.save()
                _save_custom_field_values(project, request.POST, update=True)
                if old_status != project.status:
                    ProjectActivity.objects.create(
                        project=project, actor=request.user,
                        action=f'Status changed from {old_status} to {project.status}',
                    )
            if old_status != project.status:
                send_project_notification(
                    project,
                    f'Your project "{project.project_name}" status changed to '
                    f'{project.get_status_display()}.',
                )
            messages.success(request, 'Project updated successfully.')
            return redirect('project_detail', pk=project.pk)
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {
        'form': form,
        'title': 'Edit Project',
        'project': project,
        'custom_fields': ProjectField.objects.filter(is_active=True),
        'existing_values': {
            value.field_id: value.value
            for value in project.custom_field_values.all()
        },
    })


@admin_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        name = project.project_name
        project.delete()
        messages.success(request, f'Project "{name}" deleted successfully.')
        return redirect('project_list')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})


# -- Process stages -----------------------------------------------------------

@admin_required
@require_POST
def update_process(request, pk):
    project = get_object_or_404(Project, pk=pk)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        # Previously this raised, producing a 500 for a malformed request.
        return JsonResponse({'error': 'Malformed request body.'}, status=400)

    new_status = data.get('status')
    valid_statuses = {value for value, _ in ProjectProcess.STATUS_CHOICES}
    if new_status not in valid_statuses:
        return JsonResponse(
            {'error': f'Unknown status. Expected one of: '
                      f'{", ".join(sorted(valid_statuses))}.'},
            status=400,
        )

    try:
        process = ProjectProcess.objects.get(pk=data.get('process_id'), project=project)
    except (ProjectProcess.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'error': 'That stage is not part of this project.'}, status=404)

    old_status = process.status

    with transaction.atomic():
        process.status = new_status
        process.completed_at = timezone.now() if new_status == 'completed' else None
        if 'notes' in data:
            process.notes = str(data.get('notes') or '')
        process.save(update_fields=['status', 'completed_at', 'notes', 'updated_at'])

        project_changed = False
        if new_status == 'in_progress':
            project.current_process = process.process_name
            if project.status == 'pending':
                project.status = 'in_progress'
            project_changed = True

        all_done = not project.processes.exclude(
            status__in=['completed', 'skipped']
        ).exists()
        if all_done:
            project.status = 'completed'
            project.completed_date = timezone.now().date()
            project_changed = True

        if project_changed:
            project.save(update_fields=['current_process', 'status', 'completed_date', 'updated_at'])

        if old_status != new_status:
            ProjectActivity.objects.create(
                project=project, actor=request.user,
                action=f'Process "{process.process_name}" updated to {new_status}',
            )

    if old_status != new_status:
        if all_done:
            message = f'Great news! Your project "{project.project_name}" has been completed.'
        else:
            message = (f'Your project "{project.project_name}" is now in the '
                       f'{process.process_name} stage.')
        send_project_notification(project, message)

    return JsonResponse({
        'success': True,
        'progress': project.progress_percentage,
        'project_status': project.status,
        'project_status_display': project.get_status_display(),
        'process_status': process.status,
    })


# -- Files --------------------------------------------------------------------

@login_required
@require_POST
def upload_file(request, pk):
    project = get_object_or_404(_visible_projects(request.user), pk=pk)

    form = ProjectFileForm(request.POST, request.FILES)
    if not form.is_valid():
        # Show the actual reason (too large, wrong type) instead of a generic
        # "upload failed".
        for error in form.errors.get('file', []) or ['Please choose a file to upload.']:
            messages.error(request, error)
        return redirect('project_detail', pk=pk)

    with transaction.atomic():
        project_file = form.save(commit=False)
        project_file.project = project
        project_file.uploaded_by = request.user
        project_file.save()
        ProjectActivity.objects.create(
            project=project, actor=request.user,
            action=f'File "{project_file.file_name}" uploaded',
        )

    if not request.user.is_admin_user():
        notify_admins(
            project,
            f'Client {request.user.get_full_name() or request.user.username} '
            f'uploaded a file "{project_file.file_name}" on project '
            f'"{project.project_name}".',
            notify_type='file_uploaded',
        )
    messages.success(request, 'File uploaded successfully.')
    return redirect('project_detail', pk=pk)


@admin_required
@require_POST
def delete_file(request, pk, file_pk):
    project = get_object_or_404(Project, pk=pk)
    project_file = get_object_or_404(ProjectFile, pk=file_pk, project=project)
    project_file.file.delete(save=False)
    project_file.delete()
    messages.success(request, 'File deleted.')
    return redirect('project_detail', pk=pk)


# -- Bills and invoices -------------------------------------------------------

@admin_required
@require_POST
def upload_bill(request, pk):
    project = get_object_or_404(Project, pk=pk)

    form = BillForm(request.POST, request.FILES)
    if not form.is_valid():
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect('project_detail', pk=pk)

    with transaction.atomic():
        bill = form.save(commit=False)
        bill.project = project
        bill.uploaded_by = request.user
        bill.save()
        amount_note = f' (₹{bill.amount})' if bill.amount else ''
        ProjectActivity.objects.create(
            project=project, actor=request.user,
            action=f'Bill uploaded: {bill.file_name}{amount_note}',
        )

    send_project_notification(
        project,
        f'A bill/invoice has been uploaded for your project '
        f'"{project.project_name}".'
        + (f' Amount: ₹{bill.amount}' if bill.amount else ''),
        notify_type='bill_added',
    )
    messages.success(request, 'Bill uploaded successfully.')
    return redirect('project_detail', pk=pk)


@admin_required
@require_POST
def delete_bill(request, pk, bill_pk):
    project = get_object_or_404(Project, pk=pk)
    bill = get_object_or_404(ProjectBill, pk=bill_pk, project=project)
    if bill.file:
        bill.file.delete(save=False)
    bill.delete()
    messages.success(request, 'Bill deleted.')
    return redirect('project_detail', pk=pk)


@login_required
def download_invoice(request, pk, bill_pk):
    project = get_object_or_404(_visible_projects(request.user), pk=pk)
    bill = get_object_or_404(ProjectBill, pk=bill_pk, project=project)
    company = {
        'gstin': settings.COMPANY_GSTIN,
        'address': settings.COMPANY_ADDRESS,
        'phone': settings.COMPANY_PHONE,
        'email': settings.COMPANY_EMAIL,
    }
    invoice_number = bill.invoice_number or f'INV-{bill.pk:04d}'
    response = HttpResponse(
        generate_invoice_pdf(bill, company), content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice_number}.pdf"'
    return response


@login_required
def download_timeline(request, pk):
    project = get_object_or_404(
        _visible_projects(request.user).prefetch_related('processes'), pk=pk
    )
    response = HttpResponse(
        generate_timeline_pdf(project), content_type='application/pdf'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="Timeline_{project.project_code}.pdf"'
    )
    return response


# -- Ratings ------------------------------------------------------------------

@login_required
@require_POST
def submit_rating(request, pk):
    """Client submits a star rating once their project is complete."""
    project = get_object_or_404(Project, pk=pk, client=request.user)
    if project.status != 'completed':
        messages.error(request, 'You can only rate completed projects.')
        return redirect('project_detail', pk=pk)

    stars = request.POST.get('stars', '')
    if not stars.isdigit() or not 1 <= int(stars) <= 5:
        messages.error(request, 'Please choose a rating between 1 and 5 stars.')
        return redirect('project_detail', pk=pk)

    review = request.POST.get('review', '').strip()[:2000]
    with transaction.atomic():
        ProjectRating.objects.update_or_create(
            project=project,
            defaults={'client': request.user, 'stars': int(stars), 'review': review},
        )
        ProjectActivity.objects.create(
            project=project, actor=request.user,
            action=f'Project rated {stars} stars by '
                   f'{request.user.get_full_name() or request.user.username}',
        )
    notify_admins(
        project,
        f'{request.user.get_full_name() or request.user.username} rated project '
        f'"{project.project_name}" {stars} stars.',
        notify_type='rating_received',
    )
    messages.success(request, 'Thank you for your feedback.')
    return redirect('project_detail', pk=pk)


# -- Analytics ----------------------------------------------------------------

@admin_required
def analytics(request):
    import datetime

    status_counts = dict(
        Project.objects.values_list('status').annotate(total=Count('id'))
        .values_list('status', 'total')
    )
    total_projects = sum(status_counts.values())
    completed = status_counts.get('completed', 0)

    # Monthly project counts for the last six calendar months. This reads the
    # window in one query and buckets the rows in Python rather than using
    # TruncMonth: on MySQL, date truncation with USE_TZ enabled needs the
    # server's time zone tables loaded, and returns NULL silently when they
    # are not. Six months of rows is small enough that this is cheaper than
    # depending on that.
    today = timezone.now().date()
    first_of_this_month = today.replace(day=1)
    months = []
    cursor = first_of_this_month
    for _ in range(6):
        months.append(cursor)
        cursor = (cursor - datetime.timedelta(days=1)).replace(day=1)
    months.reverse()

    # Compared as an aware datetime: filtering a DateTimeField against a bare
    # date makes Django warn about a naive value and compare in UTC, which
    # silently drops or adds rows near a month boundary.
    window_start = timezone.make_aware(
        datetime.datetime.combine(months[0], datetime.time.min)
    )
    created_per_month = {}
    for row in (
        Project.objects.filter(created_at__gte=window_start)
        .values_list('created_at')
    ):
        created = timezone.localtime(row[0]).date() if timezone.is_aware(row[0]) else row[0].date()
        key = created.replace(day=1)
        created_per_month[key] = created_per_month.get(key, 0) + 1

    monthly_projects = [
        {'label': month.strftime('%b'), 'count': created_per_month.get(month, 0)}
        for month in months
    ]
    max_monthly = max([m['count'] for m in monthly_projects] + [1])

    status_breakdown = [
        {
            'label': label,
            'count': status_counts.get(value, 0),
            'pct': round(status_counts.get(value, 0) / total_projects * 100) if total_projects else 0,
            'color': color,
        }
        for value, label, color in [
            ('pending', 'Pending', '#3B82F6'),
            ('in_progress', 'In Progress', '#E85D04'),
            ('completed', 'Completed', '#16A34A'),
            ('on_hold', 'On Hold', '#9CA3AF'),
        ]
    ]

    # Both totals come back with the clients in a single query. The previous
    # version ran an extra COUNT for every client in the list.
    top_clients = [
        {
            'name': client.get_full_name() or client.username,
            'company': client.company_name or '—',
            'total': client.total,
            'completed': client.completed_total,
        }
        for client in User.objects.filter(role='client').annotate(
            total=Count('projects', distinct=True),
            completed_total=Count(
                'projects', filter=Q(projects__status='completed'), distinct=True
            ),
        ).order_by('-total')[:8]
    ]

    rating_summary = ProjectRating.objects.aggregate(
        average=Avg('stars'), total=Count('id')
    )
    average_rating = rating_summary['average']

    return render(request, 'projects/analytics.html', {
        'stats': {
            'total_projects': total_projects,
            'completed': completed,
            'total_clients': User.objects.filter(role='client').count(),
            'total_revenue': ProjectBill.objects.aggregate(s=Sum('amount'))['s'] or 0,
            'completion_rate': round(completed / total_projects * 100) if total_projects else 0,
        },
        'monthly_projects': monthly_projects,
        'max_monthly': max_monthly,
        'status_breakdown': status_breakdown,
        'top_clients': top_clients,
        'avg_rating': round(average_rating, 1) if average_rating else None,
        'avg_rating_int': round(average_rating) if average_rating else 0,
        'total_ratings': rating_summary['total'],
        'recent_ratings': (
            ProjectRating.objects.select_related('client', 'project')
            .order_by('-created_at')[:5]
        ),
    })
