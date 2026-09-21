from django.db import models
from django.conf import settings


class WorkSample(models.Model):
    """Our Work / Portfolio items — uploaded by admin."""
    CATEGORY_CHOICES = [
        ('cnc', 'CNC Machining'),
        ('vmc', 'VMC Machining'),
        ('lathe', 'Lathe / Turning'),
        ('milling', 'Milling'),
        ('drilling', 'Drilling'),
        ('finishing', 'Finishing'),
        ('other', 'Other'),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='cnc')
    description = models.TextField(blank=True)
    image = models.FileField(upload_to='portfolio/%Y/%m/', null=True, blank=True)
    material = models.CharField(max_length=100, blank=True, help_text='e.g. EN24 Steel, SS304')
    machine_used = models.CharField(max_length=100, blank=True, help_text='e.g. Fanuc CNC')
    is_featured = models.BooleanField(default=False, help_text='Show on home page')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = 'Work Sample'
        verbose_name_plural = 'Work Samples'
        # Matches the public home page query: active and featured, newest first.
        indexes = [
            models.Index(fields=['is_active', '-is_featured', '-created_at'],
                         name='work_active_feat_idx'),
            models.Index(fields=['category'], name='work_category_idx'),
        ]

    def __str__(self):
        return self.title


class Service(models.Model):
    """Services section — fully managed by admin."""
    title = models.CharField(max_length=200)
    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    icon_label = models.CharField(max_length=10, default='⚙', help_text='Emoji or short text for icon')
    image = models.FileField(upload_to='services/', null=True, blank=True)
    features = models.TextField(
        blank=True,
        help_text='One feature per line — these appear as bullet points'
    )
    order = models.PositiveIntegerField(default=0, help_text='Display order (lower = first)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        indexes = [
            models.Index(fields=['is_active', 'order'], name='service_active_order_idx'),
        ]

    def __str__(self):
        return self.title

    def features_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]
