"""
Project-level views: the PWA manifest and the custom error pages.

The manifest is rendered here rather than by django-pwa's own view because
that view only passes the settings its app_settings module knows about, so
project-specific keys (the short name, the maskable icon set) would render
as empty values in the JSON.
"""

import mimetypes

from django.conf import settings
from django.http import FileResponse, Http404
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


# -- Uploaded media -----------------------------------------------------------
# Files live in GridFS, not on disk, so nothing serves them by itself: this
# view is the only route to them. It is wired up unconditionally in
# config/urls.py, unlike the old DEBUG-only static() helper, which meant every
# media URL 404'd in production.

# Prefixes holding client work rather than site content. A drawing or an
# invoice must not be readable by anyone who guesses the URL, so these are
# checked against the requesting user; everything else -- machine photos,
# portfolio and service images, profile pictures -- is public, because the
# public website renders it.
PRIVATE_MEDIA_PREFIXES = ('project_files/', 'bills/')


def _may_read_private_file(user, path):
    """True if this user is allowed the project file or invoice at `path`."""
    if not user.is_authenticated:
        return False
    if user.is_admin_user():
        return True

    # A client may read files belonging to their own projects, nobody else's.
    from apps.projects.models import ProjectBill, ProjectFile

    model = ProjectBill if path.startswith('bills/') else ProjectFile
    return model.objects.filter(file=path, project__client=user).exists()


def serve_media(request, path):
    """Stream an uploaded file out of GridFS."""
    from django.core.files.storage import default_storage

    if path.startswith(PRIVATE_MEDIA_PREFIXES) and not _may_read_private_file(
        request.user, path
    ):
        # 404 rather than 403: a client should not learn that another
        # client's drawing exists.
        raise Http404(path)

    try:
        file = default_storage.open(path)
    except Exception as exc:  # gridfs.NoFile, and anything the driver wraps it in
        raise Http404(path) from exc

    content_type, _ = mimetypes.guess_type(path)
    response = FileResponse(file, content_type=content_type or 'application/octet-stream')
    if path.startswith(PRIVATE_MEDIA_PREFIXES):
        response['Cache-Control'] = 'private, max-age=0, no-store'
    else:
        response['Cache-Control'] = 'public, max-age=86400'
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
