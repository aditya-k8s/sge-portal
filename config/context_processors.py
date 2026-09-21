"""Template context shared by every page."""

from django.conf import settings


def company_info(request):
    """
    Expose company details and the app's URL prefix to templates.

    Previously templates and views hardcoded these; reading them from settings
    means they are configured once, in the environment.
    """
    return {
        'COMPANY_NAME': settings.COMPANY_NAME,
        'COMPANY_PHONE': settings.COMPANY_PHONE,
        'COMPANY_EMAIL': settings.COMPANY_EMAIL,
        'COMPANY_ADDRESS': settings.COMPANY_ADDRESS,
        'PWA_APP_SHORT_NAME': settings.PWA_APP_SHORT_NAME,
        'URL_PREFIX': settings.URL_PREFIX,
        'MAX_UPLOAD_SIZE_MB': settings.MAX_UPLOAD_SIZE_MB,
    }
