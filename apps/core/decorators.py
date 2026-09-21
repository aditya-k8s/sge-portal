"""
Shared view decorators.

Before this module every admin-only view opened with the same three lines:

    if not request.user.is_admin_user():
        return redirect('dashboard')

which meant the rule lived in twenty-five places, some of which forgot to tell
the user why nothing happened, and one of which needed to answer JSON instead
of a redirect.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect


def _wants_json(request):
    """True when the caller expects JSON rather than a rendered page."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return True
    return 'application/json' in request.headers.get('accept', '')


def admin_required(view_func):
    """
    Allow staff, superusers and users with role 'admin'.

    Everyone else is sent back to their dashboard with an explanation, which
    preserves the behaviour the app already had while making the refusal
    visible instead of silent. JSON callers get a 403 with a message body.
    """

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.is_admin_user():
            return view_func(request, *args, **kwargs)
        if _wants_json(request):
            return JsonResponse(
                {'detail': 'This action is restricted to administrators.'},
                status=403,
            )
        messages.error(
            request, 'That page is only available to administrators.'
        )
        return redirect('dashboard')

    return _wrapped


def client_required(view_func):
    """Mirror of admin_required for the client-only pages."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.is_client_user():
            return view_func(request, *args, **kwargs)
        return redirect('dashboard')

    return _wrapped
