import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.core.decorators import admin_required

from .emails import send_login_alert, send_otp_email
from .forms import ClientCreateForm, ClientRegisterForm, LoginForm, ProfileUpdateForm
from .models import OTPCode, User

logger = logging.getLogger(__name__)

# How many codes one address may request in ten minutes before being asked to
# wait. Without this the OTP endpoints can be used to mail an address
# repeatedly, and to grind guesses at a six-digit code.
OTP_REQUEST_LIMIT = 5


def _safe_redirect_target(request, fallback='dashboard'):
    """
    Resolve ?next= only when it points back at this site.

    Passing the raw parameter to redirect() made the login page an open
    redirect: /accounts/login/?next=https://example.invalid would send the
    user off-site immediately after authenticating.
    """
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(
        url=target,
        allowed_hosts={request.get_host(), *settings.ALLOWED_HOSTS},
        require_https=request.is_secure(),
    ):
        return target
    return fallback


# -- Auth ---------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.email:
                try:
                    send_login_alert(user, request)
                except Exception:
                    # A failed courtesy email must never block a valid login.
                    logger.warning('Could not send login alert', exc_info=True)
            messages.success(
                request, f'Welcome back, {user.get_full_name() or user.username}.'
            )
            return redirect(_safe_redirect_target(request))
        messages.error(request, 'Those details did not match an account. Please try again.')
    else:
        form = LoginForm(request)
    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# -- Registration with OTP ----------------------------------------------------

def register_view(request):
    """Step 1 -- collect the details and send a verification code."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ClientRegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            email = data['email'].strip().lower()

            if OTPCode.recent_attempt_count(email, 'registration') >= OTP_REQUEST_LIMIT:
                messages.error(
                    request,
                    'Too many verification codes have been requested for that '
                    'address. Please wait ten minutes and try again.',
                )
                return render(request, 'accounts/register.html', {'form': form})

            # The password sits in the session only until the code is
            # confirmed, because the account does not exist yet.
            request.session['pending_registration'] = {
                'username': data['username'],
                'email': email,
                'password': data['password1'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'company_name': data['company_name'],
                'phone': data.get('phone', ''),
            }
            otp = OTPCode.generate(email, 'registration')
            if send_otp_email(email, otp.code, 'registration', data['first_name']):
                messages.success(request, f'A 6-digit verification code has been sent to {email}.')
            else:
                messages.warning(
                    request,
                    'The code was generated but the email could not be sent. '
                    'Check your inbox shortly, or request a new code.',
                )
            return redirect('register_verify')
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = ClientRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def register_verify(request):
    """Step 2 -- verify the code and create the account."""
    pending = request.session.get('pending_registration')
    if not pending:
        return redirect('register')

    email = pending['email']
    if request.method == 'POST':
        entered = request.POST.get('otp_code', '').strip()

        otp = OTPCode.objects.filter(
            email=email, purpose='registration', is_used=False
        ).order_by('-created_at').first()

        if not otp:
            messages.error(request, 'No code was found for that address. Please register again.')
            return redirect('register')

        if not otp.is_valid():
            messages.error(request, 'That code has expired. Please register again.')
            request.session.pop('pending_registration', None)
            return redirect('register')

        if otp.code != entered:
            messages.error(request, 'That code is not correct. Please check and try again.')
            return render(request, 'accounts/register_verify.html', {'email': email})

        # Guard against the address or username being taken while the code was
        # in flight.
        if User.objects.filter(username=pending['username']).exists():
            messages.error(request, 'That username has just been taken. Please register again.')
            request.session.pop('pending_registration', None)
            return redirect('register')

        with transaction.atomic():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            user = User.objects.create_user(
                username=pending['username'],
                email=email,
                password=pending['password'],
                first_name=pending['first_name'],
                last_name=pending['last_name'],
                company_name=pending['company_name'],
                phone=pending.get('phone', ''),
                role='client',
                is_email_verified=True,
            )
        request.session.pop('pending_registration', None)
        login(request, user)
        messages.success(
            request,
            f'Welcome to {settings.COMPANY_NAME}, {user.get_full_name()}. '
            f'Your account is verified.',
        )
        return redirect('dashboard')

    return render(request, 'accounts/register_verify.html', {'email': email})


def resend_otp(request):
    """Issue a fresh code for registration or password reset."""
    purpose = request.GET.get('purpose', 'registration')

    if purpose == 'password_reset':
        pending = request.session.get('pending_reset')
        redirect_to, verify_page = 'forgot_password', 'forgot_password_verify'
    else:
        purpose = 'registration'
        pending = request.session.get('pending_registration')
        redirect_to, verify_page = 'register', 'register_verify'

    if not pending:
        return redirect(redirect_to)

    email = pending['email']
    if OTPCode.recent_attempt_count(email, purpose) >= OTP_REQUEST_LIMIT:
        messages.error(
            request,
            'Too many codes have been requested for that address. '
            'Please wait ten minutes and try again.',
        )
        return redirect(verify_page)

    otp = OTPCode.generate(email, purpose)
    send_otp_email(email, otp.code, purpose, pending.get('first_name', ''))
    messages.success(request, f'A new code has been sent to {email}.')
    return redirect(verify_page)


# -- Forgot password with OTP -------------------------------------------------

def forgot_password(request):
    """Step 1 -- take the address and send a reset code."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        user = User.objects.filter(email__iexact=email).order_by('pk').first()

        if user and OTPCode.recent_attempt_count(email, 'password_reset') >= OTP_REQUEST_LIMIT:
            messages.error(
                request,
                'Too many reset codes have been requested for that address. '
                'Please wait ten minutes and try again.',
            )
            return redirect('forgot_password_verify')

        if user:
            otp = OTPCode.generate(email, 'password_reset')
            send_otp_email(email, otp.code, 'password_reset', user.get_full_name())

        # The same response either way, so the page cannot be used to discover
        # which addresses have accounts.
        request.session['pending_reset'] = {'email': email}
        messages.success(
            request, f'If an account exists for {email}, a reset code has been sent.'
        )
        return redirect('forgot_password_verify')
    return render(request, 'accounts/forgot_password.html')


def forgot_password_verify(request):
    """Step 2 -- verify the code and set the new password."""
    pending = request.session.get('pending_reset')
    if not pending:
        return redirect('forgot_password')

    email = pending['email']
    if request.method == 'POST':
        entered = request.POST.get('otp_code', '').strip()
        new_password = request.POST.get('new_password1', '')
        confirm_password = request.POST.get('new_password2', '')

        otp = OTPCode.objects.filter(
            email=email, purpose='password_reset', is_used=False
        ).order_by('-created_at').first()

        if not otp or not otp.is_valid():
            messages.error(request, 'That code has expired or is not valid. Please request a new one.')
            request.session.pop('pending_reset', None)
            return redirect('forgot_password')

        if otp.code != entered:
            messages.error(request, 'That code is not correct. Please check and try again.')
            return render(request, 'accounts/forgot_password_verify.html', {'email': email})

        if len(new_password) < 8:
            messages.error(request, 'The new password must be at least 8 characters.')
            return render(request, 'accounts/forgot_password_verify.html', {'email': email})

        if new_password != confirm_password:
            messages.error(request, 'The two passwords do not match.')
            return render(request, 'accounts/forgot_password_verify.html', {'email': email})

        # order_by('pk').first() rather than get(): email is not unique, and
        # get() raised MultipleObjectsReturned -- a 500 on the reset page --
        # as soon as two accounts shared an address.
        user = User.objects.filter(email__iexact=email).order_by('pk').first()
        if not user:
            messages.error(request, 'No account was found for that address.')
            request.session.pop('pending_reset', None)
            return redirect('forgot_password')

        with transaction.atomic():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            user.set_password(new_password)
            user.save(update_fields=['password'])
        request.session.pop('pending_reset', None)
        messages.success(request, 'Password updated. Please log in with your new password.')
        return redirect('login')

    return render(request, 'accounts/forgot_password_verify.html', {'email': email})


# -- Profile and password -----------------------------------------------------

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-input'})
    return render(request, 'accounts/change_password.html', {'form': form})


# -- Client management (admin) ------------------------------------------------

class AdminSetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        min_length=8,
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password1') and cleaned.get('new_password2'):
            if cleaned['new_password1'] != cleaned['new_password2']:
                raise forms.ValidationError('The two passwords do not match.')
        return cleaned


@admin_required
def client_list(request):
    clients = User.objects.filter(role='client').order_by('-created_at')
    search = request.GET.get('search', '').strip()
    if search:
        clients = clients.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(company_name__icontains=search)
            | Q(email__icontains=search)
            | Q(username__icontains=search)
        )
    # Project counts in the same query, rather than one per row in the template.
    clients = clients.annotate(project_total=Count('projects'))
    page = Paginator(clients, getattr(settings, 'PAGE_SIZE', 20)).get_page(
        request.GET.get('page')
    )
    return render(request, 'accounts/client_list.html', {
        'clients': page,
        'page_obj': page,
        'search': search,
        'total_count': page.paginator.count,
    })


@admin_required
def client_create(request):
    if request.method == 'POST':
        form = ClientCreateForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(
                request, f'Client {client.get_full_name()} created successfully.'
            )
            return redirect('client_detail', pk=client.pk)
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = ClientCreateForm()
    return render(request, 'accounts/client_form.html', {
        'form': form, 'title': 'Add New Client',
    })


@admin_required
def client_edit(request, pk):
    client = get_object_or_404(User, pk=pk, role='client')
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client updated successfully.')
            return redirect('client_detail', pk=client.pk)
        messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = ProfileUpdateForm(instance=client)
    return render(request, 'accounts/client_form.html', {
        'form': form, 'title': 'Edit Client', 'client': client,
    })


@admin_required
def client_detail(request, pk):
    client = get_object_or_404(User, pk=pk, role='client')
    projects = (
        client.projects.select_related('machine')
        .prefetch_related('processes')
        .order_by('-created_at')
    )
    return render(request, 'accounts/client_detail.html', {
        'client': client, 'projects': projects,
    })


@admin_required
def client_set_password(request, pk):
    client = get_object_or_404(User, pk=pk, role='client')
    if request.method == 'POST':
        form = AdminSetPasswordForm(request.POST)
        if form.is_valid():
            client.set_password(form.cleaned_data['new_password1'])
            client.save(update_fields=['password'])
            messages.success(
                request,
                f'The password for {client.get_full_name() or client.username} has been reset.',
            )
            return redirect('client_detail', pk=client.pk)
    else:
        form = AdminSetPasswordForm()
    return render(request, 'accounts/client_set_password.html', {
        'form': form, 'client': client,
    })


@admin_required
def client_delete(request, pk):
    client = get_object_or_404(User, pk=pk, role='client')
    if request.method == 'POST':
        name = client.get_full_name() or client.username
        client.delete()
        messages.success(request, f'Client "{name}" deleted successfully.')
        return redirect('client_list')
    return render(request, 'accounts/client_confirm_delete.html', {
        'client': client,
        'project_count': client.projects.count(),
    })
