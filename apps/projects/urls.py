from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/new/', views.project_create, name='project_create'),
    path('projects/<pk:pk>/', views.project_detail, name='project_detail'),
    path('projects/<pk:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<pk:pk>/delete/', views.project_delete, name='project_delete'),
    path('projects/<pk:pk>/update-process/', views.update_process, name='update_process'),
    path('projects/<pk:pk>/upload/', views.upload_file, name='upload_file'),
    path('projects/<pk:pk>/files/<pk:file_pk>/delete/', views.delete_file, name='delete_file'),
    path('projects/<pk:pk>/upload-bill/', views.upload_bill, name='upload_bill'),
    path('projects/<pk:pk>/bills/<pk:bill_pk>/delete/', views.delete_bill, name='delete_bill'),
    path('projects/<pk:pk>/rate/', views.submit_rating, name='submit_rating'),
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('analytics/', views.analytics, name='analytics'),
    path('projects/<pk:pk>/timeline.pdf', views.download_timeline, name='download_timeline'),
    path('projects/<pk:pk>/bills/<pk:bill_pk>/invoice.pdf', views.download_invoice, name='download_invoice'),
]
