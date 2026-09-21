import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import EmailMessage, send_mail
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.core.decorators import admin_required

from .models import ContactEnquiry

logger = logging.getLogger(__name__)

# One address or IP may submit the contact form this many times per hour.
CONTACT_RATE_LIMIT = 5
CONTACT_RATE_WINDOW_SECONDS = 60 * 60


class ContactForm(forms.Form):
    name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
        'placeholder': 'Your Name'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
        'placeholder': 'Your Email'
    }))
    phone = forms.CharField(required=False, max_length=20, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
        'placeholder': 'Phone Number'
    }))
    subject = forms.CharField(max_length=300, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
        'placeholder': 'Subject'
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
        'placeholder': 'Your message...',
        'rows': 5
    }))


def home(request):
    from apps.portfolio.models import WorkSample, Service
    featured_work = WorkSample.objects.filter(is_active=True, is_featured=True)[:6]
    services = Service.objects.filter(is_active=True)[:4]
    return render(request, 'website/home.html', {
        'featured_work': featured_work,
        'services': services,
    })


def about(request):
    return render(request, 'website/about.html')


def industries(request):
    return render(request, 'website/industries.html')


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            ip = _client_ip(request)

            # The form is public and sends two emails per submission, so it is
            # worth rate limiting before it can be used to flood the inbox.
            cache_key = f'contact-rate:{ip}'
            attempts = cache.get(cache_key, 0)
            if attempts >= CONTACT_RATE_LIMIT:
                messages.error(
                    request,
                    'Several messages have already been sent from this connection. '
                    'Please try again later, or call us directly.',
                )
                return render(request, 'website/contact.html', {'form': form})
            cache.set(cache_key, attempts + 1, CONTACT_RATE_WINDOW_SECONDS)

            # Save to database
            enquiry = ContactEnquiry.objects.create(
                name=data['name'],
                email=data['email'],
                phone=data.get('phone', ''),
                subject=data['subject'],
                message=data['message'],
                ip_address=ip,
                status='new',
            )

            # Send email to admin
            to_email = settings.COMPANY_EMAIL or settings.EMAIL_HOST_USER
            if not to_email:
                # Without a recipient the notification is dropped by the mail
                # backend and nobody ever learns the enquiry arrived. The
                # enquiry itself is safely in the database and visible in the
                # dashboard, so say so loudly in the log.
                logger.error(
                    'Contact enquiry %s saved but not emailed: neither '
                    'COMPANY_EMAIL nor EMAIL_HOST_USER is configured.',
                    enquiry.pk,
                )

            # Built from SITE_URL rather than a hardcoded 127.0.0.1 address,
            # which made the link in every production email unusable.
            dashboard_link = settings.SITE_URL.rstrip('/') + reverse(
                'enquiry_detail', args=[enquiry.pk]
            )
            body = f"""New contact form enquiry — {settings.COMPANY_NAME}

Name:    {data['name']}
Email:   {data['email']}
Phone:   {data.get('phone') or 'Not provided'}
Subject: {data['subject']}

Message:
{data['message']}

---
View in dashboard: {dashboard_link}
Reply to: {data['email']}
"""
            auto_reply = f"""Hello {data['name']},

Thank you for contacting {settings.COMPANY_NAME}.

We have received your enquiry regarding "{data['subject']}" and will get back
to you within 24 hours.

If this is urgent, please call us directly.

Best regards,
{settings.COMPANY_NAME} Team
"""
            try:
                if to_email:
                    EmailMessage(
                        subject=f'[SGE Enquiry] {data["subject"]}',
                        body=body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[to_email],
                        reply_to=[data['email']],
                    ).send(fail_silently=False)

                send_mail(
                    subject=f'Thank you for contacting {settings.COMPANY_NAME}',
                    message=auto_reply,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[data['email']],
                    fail_silently=True,
                )
            except Exception:
                # The enquiry is already saved, so the visitor is told it
                # worked; the delivery failure goes to the log, not to stdout.
                logger.error('Contact enquiry %s saved but email failed', enquiry.pk,
                             exc_info=True)

            messages.success(
                request,
                'Thank you. Your message has been sent and we will contact you shortly.',
            )
            return redirect('contact')
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = ContactForm()
    return render(request, 'website/contact.html', {'form': form})


# ── Admin Enquiry Management ──────────────────────────────────────────────────

@admin_required
def enquiry_list(request):
    status_filter = request.GET.get('status', '')
    enquiries = ContactEnquiry.objects.all()
    valid_statuses = {value for value, _ in ContactEnquiry.STATUS_CHOICES}
    if status_filter in valid_statuses:
        enquiries = enquiries.filter(status=status_filter)
    else:
        status_filter = ''
    new_count = ContactEnquiry.objects.filter(status='new').count()
    filter_tabs = [
        ('', 'All', ''),
        ('new', 'New', 'orange'),
        ('read', 'Read', 'blue'),
        ('replied', 'Replied', 'green'),
        ('closed', 'Closed', 'gray'),
    ]
    page = Paginator(enquiries, getattr(settings, 'PAGE_SIZE', 20)).get_page(
        request.GET.get('page')
    )
    return render(request, 'website/enquiry_list.html', {
        'enquiries': page,
        'page_obj': page,
        'new_count': new_count,
        'status_filter': status_filter,
        'total': ContactEnquiry.objects.count(),
        'filter_tabs': filter_tabs,
    })


@admin_required
def enquiry_detail(request, pk):
    enquiry = get_object_or_404(ContactEnquiry, pk=pk)
    # Mark as read
    if enquiry.status == 'new':
        enquiry.status = 'read'
        enquiry.read_at = timezone.now()
        enquiry.save()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in ['new', 'read', 'replied', 'closed']:
                enquiry.status = new_status
                enquiry.save()
                messages.success(request, 'Status updated.')
        elif action == 'save_notes':
            enquiry.admin_notes = request.POST.get('admin_notes', '')
            enquiry.save()
            messages.success(request, 'Notes saved.')
        elif action == 'send_reply':
            reply_text = request.POST.get('reply_text', '').strip()
            if reply_text:
                try:
                    send_mail(
                        subject=f'Re: {enquiry.subject}',
                        message=f'Hello {enquiry.name},\n\n{reply_text}\n\nBest regards,\nShri Gouri Engineers',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[enquiry.email],
                        fail_silently=False,
                    )
                    enquiry.status = 'replied'
                    enquiry.save(update_fields=['status'])
                    messages.success(request, f'Reply sent to {enquiry.email}')
                except Exception:
                    # Show a usable message; keep the SMTP detail in the log
                    # rather than on the page.
                    logger.error('Failed to send reply for enquiry %s', enquiry.pk,
                                 exc_info=True)
                    messages.error(
                        request,
                        'The reply could not be sent. Please check the email '
                        'settings and try again.',
                    )
            else:
                messages.error(request, 'Please write a reply before sending.')
        return redirect('enquiry_detail', pk=pk)
    return render(request, 'website/enquiry_detail.html', {'enquiry': enquiry})


@admin_required
def enquiry_delete(request, pk):
    enquiry = get_object_or_404(ContactEnquiry, pk=pk)
    if request.method == 'POST':
        enquiry.delete()
        messages.success(request, 'Enquiry deleted.')
        return redirect('enquiry_list')
    return render(request, 'website/enquiry_confirm_delete.html', {'enquiry': enquiry})
