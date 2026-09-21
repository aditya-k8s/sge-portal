from django.db import models


class ContactEnquiry(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    ]
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=300)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, help_text='Internal notes about this enquiry')

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Contact Enquiry'
        verbose_name_plural = 'Contact Enquiries'
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='enquiry_status_date_idx'),
            models.Index(fields=['-submitted_at'], name='enquiry_submitted_idx'),
        ]

    def __str__(self):
        return f"{self.name} — {self.subject} ({self.submitted_at.strftime('%d %b %Y')})"

    @property
    def is_new(self):
        return self.status == 'new'
