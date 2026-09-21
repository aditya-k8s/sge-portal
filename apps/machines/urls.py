from django.urls import path
from . import views

urlpatterns = [
    path('', views.machine_list, name='machine_list'),
    path('new/', views.machine_create, name='machine_create'),
    path('<pk:pk>/edit/', views.machine_edit, name='machine_edit'),
    path('<pk:pk>/delete/', views.machine_delete, name='machine_delete'),
]
