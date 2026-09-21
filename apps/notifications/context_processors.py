from .models import Notification


def unread_notifications(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(user=request.user).select_related('project')[:5]
        # New enquiry count for admin
        new_enquiry_count = 0
        if hasattr(request.user, 'is_admin_user') and request.user.is_admin_user():
            try:
                from apps.website.models import ContactEnquiry
                new_enquiry_count = ContactEnquiry.objects.filter(status='new').count()
            except Exception:
                pass
        return {
            'unread_notification_count': count,
            'recent_notifications': recent,
            'new_enquiry_count': new_enquiry_count,
        }
    return {
        'unread_notification_count': 0,
        'recent_notifications': [],
        'new_enquiry_count': 0,
    }
