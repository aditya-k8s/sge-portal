from django.db import models


class ProjectField(models.Model):
    """Admin-defined custom fields that appear in the project creation form."""
    FIELD_TYPES = [
        ('text', 'Text (single line)'),
        ('textarea', 'Text Area (multi-line)'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('select', 'Dropdown / Select'),
        ('checkbox', 'Checkbox (Yes/No)'),
    ]

    label = models.CharField(max_length=200, help_text='Field label shown to user (e.g. "Drawing Number")')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    placeholder = models.CharField(max_length=200, blank=True, help_text='Hint text inside the field')
    options = models.TextField(
        blank=True,
        help_text='For Dropdown only — one option per line'
    )
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text='Display order (lower = first)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Project Field'
        verbose_name_plural = 'Project Fields'
        indexes = [
            models.Index(fields=['is_active', 'order'], name='field_active_order_idx'),
        ]

    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()})"

    def get_options_list(self):
        return [o.strip() for o in self.options.splitlines() if o.strip()]


class ProjectFieldValue(models.Model):
    """Stores the values entered in custom fields for each project."""
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='custom_field_values'
    )
    field = models.ForeignKey(
        ProjectField,
        on_delete=models.CASCADE,
        related_name='values'
    )
    value = models.TextField(blank=True)

    class Meta:
        # One value per field per project, enforced in the database.
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'field'], name='fieldvalue_unique_per_project'
            ),
        ]
        # No index on project alone: the ForeignKey already creates one, and
        # MongoDB rejects a second index over the same key with a different
        # name (IndexOptionsConflict).

    def __str__(self):
        return f"{self.project} — {self.field.label}: {self.value}"


class ProcessTemplate(models.Model):
    """Admin-managed default process stages used when creating new projects."""
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Process Template'
        verbose_name_plural = 'Process Templates'
        indexes = [
            models.Index(fields=['is_active', 'order'], name='template_active_order_idx'),
        ]

    def __str__(self):
        return self.name
