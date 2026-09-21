from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'projects', api_views.ProjectViewSet, basename='api-project')

urlpatterns = [
    path('', include(router.urls)),
]
