from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Registration with OTP
    path('register/', views.register_view, name='register'),
    path('register/verify/', views.register_verify, name='register_verify'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),

    # Forgot password with OTP
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-password/verify/', views.forgot_password_verify, name='forgot_password_verify'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),

    # Client management
    path('clients/', views.client_list, name='client_list'),
    path('clients/new/', views.client_create, name='client_create'),
    path('clients/<pk:pk>/', views.client_detail, name='client_detail'),
    path('clients/<pk:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<pk:pk>/set-password/', views.client_set_password, name='client_set_password'),
    path('clients/<pk:pk>/delete/', views.client_delete, name='client_delete'),
]
