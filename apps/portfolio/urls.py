from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('our-work/', views.our_work, name='our_work'),
    path('services/', views.services_public, name='services'),

    # Admin — Work Samples
    path('dashboard/work-samples/', views.work_sample_list, name='work_sample_list'),
    path('dashboard/work-samples/new/', views.work_sample_create, name='work_sample_create'),
    path('dashboard/work-samples/<pk:pk>/edit/', views.work_sample_edit, name='work_sample_edit'),
    path('dashboard/work-samples/<pk:pk>/delete/', views.work_sample_delete, name='work_sample_delete'),

    # Admin — Services
    path('dashboard/services/', views.service_list, name='service_list'),
    path('dashboard/services/new/', views.service_create, name='service_create'),
    path('dashboard/services/<pk:pk>/edit/', views.service_edit, name='service_edit'),
    path('dashboard/services/<pk:pk>/delete/', views.service_delete, name='service_delete'),
]
