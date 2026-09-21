from django.urls import path
from . import views

urlpatterns = [
    # Custom form fields
    path('', views.field_list, name='field_list'),
    path('new/', views.field_create, name='field_create'),
    path('<pk:pk>/edit/', views.field_edit, name='field_edit'),
    path('<pk:pk>/delete/', views.field_delete, name='field_delete'),
    path('<pk:pk>/toggle/', views.field_toggle, name='field_toggle'),

    # Process templates
    path('processes/', views.process_template_list, name='process_template_list'),
    path('processes/new/', views.process_template_create, name='process_template_create'),
    path('processes/<pk:pk>/edit/', views.process_template_edit, name='process_template_edit'),
    path('processes/<pk:pk>/delete/', views.process_template_delete, name='process_template_delete'),
    path('processes/<pk:pk>/toggle/', views.process_template_toggle, name='process_template_toggle'),
    path('processes/seed/', views.seed_default_processes, name='seed_default_processes'),

    # Per-project process management
    path('project/<pk:project_pk>/add-process/', views.project_add_process, name='project_add_process'),
    path('project/<pk:project_pk>/delete-process/<pk:process_pk>/', views.project_delete_process, name='project_delete_process'),
]
