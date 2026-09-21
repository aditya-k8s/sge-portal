import logging

from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .models import Project, ProjectProcess

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """
    Return a consistent JSON error shape, and never leak a traceback.

    DRF renders its own exceptions but hands anything else to Django, which
    returns an HTML error page to a client that asked for JSON. Unexpected
    errors are logged here with the full traceback and answered with a plain
    message.
    """
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        if isinstance(detail, dict) and 'detail' in detail:
            response.data = {'error': str(detail['detail']), 'status': response.status_code}
        else:
            response.data = {'error': detail, 'status': response.status_code}
        return response

    logger.exception(
        'Unhandled API error in %s', context.get('view').__class__.__name__
        if context.get('view') else 'unknown view'
    )
    return None  # Let Django's handler produce the 500 after logging.


class ProjectProcessSerializer(serializers.ModelSerializer):
    # ModelSerializer maps an auto primary key to IntegerField, which raises
    # TypeError on an ObjectId. The key is a 24-character hex string in JSON.
    id = serializers.CharField(read_only=True)

    class Meta:
        model = ProjectProcess
        fields = ['id', 'process_name', 'status', 'order', 'notes', 'updated_at', 'completed_at']


class ProjectSerializer(serializers.ModelSerializer):
    # See ProjectProcessSerializer.id.
    id = serializers.CharField(read_only=True)
    processes = ProjectProcessSerializer(many=True, read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    client_name = serializers.SerializerMethodField()
    machine_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'project_code', 'project_name', 'client_name', 'machine_name',
            'status', 'status_display', 'current_process', 'description',
            'quantity', 'material', 'start_date', 'expected_delivery',
            'completed_date', 'progress_percentage', 'processes',
            'created_at', 'updated_at'
        ]

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username

    def get_machine_name(self, obj):
        return obj.machine.machine_name if obj.machine else None

    def get_status_display(self, obj):
        return obj.get_status_display()


class IsAdminOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user():
            return True
        return obj.client == request.user


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        qs = Project.objects.select_related('client', 'machine').prefetch_related('processes')
        if not user.is_admin_user():
            qs = qs.filter(client=user)
        status_filter = self.request.query_params.get('status')
        # Ignore an unknown status rather than returning an empty list that
        # looks like "you have no projects".
        if status_filter in {value for value, _ in Project.STATUS_CHOICES}:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def processes(self, request, pk=None):
        project = self.get_object()
        serializer = ProjectProcessSerializer(project.processes.all(), many=True)
        return Response(serializer.data)
