from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('project_update', 'Project Update'),
        ('file_uploaded', 'File Uploaded'),
        ('bill_added', 'Bill Added'),
        ('rating_received', 'Rating Received'),
        ('project_created', 'Project Created'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='project_update')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        # The unread badge runs on every authenticated page render, so the
        # (user, is_read) index is the single most valuable one in the schema.
        indexes = [
            models.Index(fields=['user', 'is_read'], name='notif_user_unread_idx'),
            models.Index(fields=['user', '-created_at'], name='notif_user_date_idx'),
        ]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:60]}"
