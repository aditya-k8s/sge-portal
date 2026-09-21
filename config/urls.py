from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, register_converter

from apps.core import views as core_views
from apps.core.converters import PrimaryKeyConverter
from apps.website import views as views_website

# Registered before any URLconf is imported, so every app can use <pk:...>.
register_converter(PrimaryKeyConverter, 'pk')

admin.site.site_header = f'{settings.COMPANY_NAME} Admin'
admin.site.site_title = 'SGE Admin'
admin.site.index_title = 'Project Management'

urlpatterns = [
    path('admin/', admin.site.urls),

    # Application
    path('', include('apps.website.urls')),
    path('', include('apps.portfolio.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.projects.urls')),
    path('dashboard/machines/', include('apps.machines.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('api/', include('apps.projects.api_urls')),
    path('dashboard/form-fields/', include('apps.formbuilder.urls')),

    # Enquiries
    path('dashboard/enquiries/', views_website.enquiry_list, name='enquiry_list'),
    path('dashboard/enquiries/<pk:pk>/', views_website.enquiry_detail, name='enquiry_detail'),
    path('dashboard/enquiries/<pk:pk>/delete/', views_website.enquiry_delete, name='enquiry_delete'),

    # Progressive Web App.
    # The manifest is served by the project's own view, declared before
    # pwa.urls so it takes precedence over django-pwa's version, which cannot
    # see project-specific manifest keys. django-pwa still provides
    # serviceworker.js and the offline page.
    path('manifest.json', core_views.manifest, name='manifest'),
    path('', include('pwa.urls')),
]

# Error handlers. Only used when DEBUG is off; with DEBUG on Django shows its
# own diagnostic pages instead.
handler400 = 'apps.core.views.bad_request'
handler403 = 'apps.core.views.permission_denied'
handler404 = 'apps.core.views.page_not_found'
handler500 = 'apps.core.views.server_error'

if settings.DEBUG:
    # In production these are served by the web server or WhiteNoise.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
