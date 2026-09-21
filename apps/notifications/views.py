from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications = (
        Notification.objects.filter(user=request.user).select_related('project')
    )
    page = Paginator(notifications, getattr(settings, 'PAGE_SIZE', 20)).get_page(
        request.GET.get('page')
    )

    # Read the rows before marking them read. Querysets are lazy, so the
    # previous order -- update() first, then let the template iterate --
    # meant every notification rendered as already-read and the unread
    # styling was never visible.
    items = list(page.object_list)
    unread_ids = [n.pk for n in items if not n.is_read]
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids).update(is_read=True)

    return render(request, 'notifications/notification_list.html', {
        'notifications': items,
        'page_obj': page,
    })


@login_required
@require_POST
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_read(request):
    updated = Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({'success': True, 'updated': updated})


@login_required
def unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    response = JsonResponse({'count': count})
    # Live data: the service worker and the browser must not serve a stale
    # badge count from cache.
    response['Cache-Control'] = 'no-store'
    return response
