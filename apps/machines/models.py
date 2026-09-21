from django.db import models


class Machine(models.Model):
    MACHINE_TYPES = [
        ('CNC', 'CNC Machine'),
        ('VMC', 'VMC Machine'),
        ('BMC', 'BMC Machine'),
        ('LATHE', 'Lathe Machine'),
        ('MILLING', 'Milling Machine'),
        ('DRILLING', 'Drilling Machine'),
        ('GRINDING', 'Grinding Machine'),
        ('OTHER', 'Other'),
    ]

    machine_name = models.CharField(max_length=200)
    machine_type = models.CharField(max_length=20, choices=MACHINE_TYPES)
    model_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    specifications = models.TextField(blank=True, help_text='Technical specifications')
    image = models.ImageField(upload_to='machines/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.machine_name} ({self.get_machine_type_display()})"

    class Meta:
        ordering = ['machine_name']
        verbose_name = 'Machine'
        verbose_name_plural = 'Machines'
        indexes = [
            models.Index(fields=['is_active', 'machine_name'], name='machine_active_name_idx'),
            models.Index(fields=['machine_type'], name='machine_type_idx'),
        ]
