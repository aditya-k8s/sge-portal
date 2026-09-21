"""
Project-level views: the PWA manifest and the custom error pages.

The manifest is rendered here rather than by django-pwa's own view because
that view only passes the settings its app_settings module knows about, so
project-specific keys (the short name, the maskable icon set) would render
as empty values in the JSON.
"""

from django.conf import settings
from django.shortcuts import render


def manifest(request):
    """Serve the web app manifest, built from the PWA_* settings."""
    context = {
        name: getattr(settings, name)
        for name in dir(settings)
        if name.startswith('PWA_')
    }
    response = render(
        request, 'manifest.json', context, content_type='application/manifest+json'
    )
    # The manifest changes only on deploy, but Chrome re-reads it when
    # deciding installability, so keep it fresh rather than long-lived.
    response['Cache-Control'] = 'public, max-age=3600'
    return response


# -- Error handlers -----------------------------------------------------------
# Registered in config/urls.py. Each renders a branded page instead of
# Django's bare default, and returns the correct status code.

def bad_request(request, exception=None):
    return render(request, 'errors/400.html', status=400)


def permission_denied(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def page_not_found(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def server_error(request):
    # Deliberately renders without any context: whatever broke may be the
    # database or a context processor, and the error page must not depend on
    # the thing that failed.
    return render(request, 'errors/500.html', status=500)
