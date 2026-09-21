import random
import string
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction

from apps.machines.models import Machine


def generate_project_code(prefix='SGE'):
    """
    Build a project code that is not already taken.

    The original implementation picked six random digits with no uniqueness
    check against a unique column, so a collision surfaced to the user as a
    database error. Check first, and after several attempts widen the random
    space rather than give up.
    """
    for _ in range(10):
        code = prefix + '-' + ''.join(random.choices(string.digits, k=6))
        if not Project.objects.filter(project_code=code).exists():
            return code
    return prefix + '-' + uuid.uuid4().hex[:10].upper()


class Project(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    DEFAULT_PROCESSES = [
        'Material Received',
        'Cutting',
        'Milling',
        'Drilling',
        'Heat Treatment',
        'Finishing',
        'Quality Check',
        'Completed',
    ]

    project_name = models.CharField(max_length=300)
    project_code = models.CharField(max_length=50, unique=True, blank=True)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects',
        limit_choices_to={'role': 'client'}
    )
    machine = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='projects'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_process = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    material = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project_code} - {self.project_name}"

    def save(self, *args, **kwargs):
        # Enforced here as well as in clean(), because the database can no
        # longer do it. Skipped for partial saves, where the fields being
        # written may not include the ones under validation.
        if not kwargs.get('update_fields'):
            self.clean()

        if self.project_code:
            return super().save(*args, **kwargs)

        # Two admins creating a project in the same instant could still pick
        # the same code between the check and the insert, so treat the unique
        # constraint as the real arbiter and retry on conflict.
        error = None
        for _ in range(5):
            self.project_code = generate_project_code()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                error = exc
        raise error

    @property
    def progress_percentage(self):
        """
        Completed share of this project's process stages, as a whole percent.

        Counts in Python off the prefetched relation: the project detail and
        list pages already load the stages, and the previous exists()/count()
        pair issued three extra queries per project on every render.
        """
        processes = list(self.processes.all())
        if not processes:
            return 0
        completed = sum(1 for p in processes if p.status == 'completed')
        return int((completed / len(processes)) * 100)

    @property
    def status_color(self):
        colors = {
            'pending': 'yellow',
            'in_progress': 'blue',
            'on_hold': 'orange',
            'completed': 'green',
            'cancelled': 'red',
        }
        return colors.get(self.status, 'gray')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        indexes = [
            # status alone drives the dashboard counters; the composite serves
            # a client filtering their own projects by status.
            models.Index(fields=['status'], name='project_status_idx'),
            models.Index(fields=['client', 'status'], name='project_client_status_idx'),
            models.Index(fields=['-created_at'], name='project_created_idx'),
            models.Index(fields=['-updated_at'], name='project_updated_idx'),
        ]

    def clean(self):
        """
        Validate the rules that used to be database CHECK constraints.

        MongoDB has no CHECK constraints -- the backend reports
        supports_table_check_constraints = False -- so `quantity >= 1` and
        `expected_delivery >= start_date` can no longer be guaranteed by the
        database. They are enforced here and in save(), so that neither a form
        nor a direct objects.create() can store an invalid row.
        """
        super().clean()
        errors = {}
        if self.quantity is not None and self.quantity < 1:
            errors['quantity'] = 'Quantity must be at least 1.'
        if (
            self.start_date and self.expected_delivery
            and self.expected_delivery < self.start_date
        ):
            errors['expected_delivery'] = (
                'Expected delivery cannot be earlier than the start date.'
            )
        if errors:
            raise ValidationError(errors)


class ProjectProcess(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='processes')
    process_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.project.project_name} - {self.process_name} ({self.status})"

    class Meta:
        ordering = ['order']
        verbose_name = 'Project Process'
        verbose_name_plural = 'Project Processes'
        # Stages are always read as a whole project's ordered list. No unique
        # constraint on (project, order): process templates may share an order
        # value, and copying them must not fail.
        indexes = [
            models.Index(fields=['project', 'order'], name='process_project_order_idx'),
            models.Index(fields=['status'], name='process_status_idx'),
        ]


class ProjectFile(models.Model):
    FILE_TYPES = [
        ('drawing', 'Drawing/Blueprint'),
        ('report', 'Report'),
        ('image', 'Image'),
        ('other', 'Other'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='project_files/%Y/%m/')
    file_name = models.CharField(max_length=300, blank=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.project_name} - {self.file_name}"

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['project', '-uploaded_at'], name='file_project_uploaded_idx'),
        ]


class ProjectActivity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at'], name='activity_project_date_idx'),
            models.Index(fields=['-created_at'], name='activity_created_idx'),
        ]

    def __str__(self):
        return f"{self.project} - {self.action}"


class ProjectBill(models.Model):
    """Invoice/Bill / GST Invoice for a project."""
    GST_RATES = [(0,'0%'),(5,'5%'),(12,'12%'),(18,'18%'),(28,'28%')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bills')
    file = models.FileField(upload_to='bills/%Y/%m/', null=True, blank=True)
    file_name = models.CharField(max_length=300, blank=True)

    # Invoice fields
    invoice_number = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text='Amount before GST (₹)')
    gst_rate = models.IntegerField(choices=GST_RATES, default=18)
    hsn_code = models.CharField(max_length=20, blank=True, help_text='HSN/SAC code')
    description_of_work = models.TextField(blank=True, help_text='Work description on invoice')
    notes = models.CharField(max_length=500, blank=True)

    # Computed
    @property
    def gst_amount(self):
        if self.amount:
            return round(self.amount * self.gst_rate / 100, 2)
        return 0

    @property
    def total_amount(self):
        if self.amount:
            return round(self.amount + self.gst_amount, 2)
        return 0

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['project', '-uploaded_at'], name='bill_project_uploaded_idx'),
        ]

    def __str__(self):
        return f"Bill for {self.project.project_name} — ₹{self.amount or 'N/A'}"

    def clean(self):
        """
        Rules previously held as database CHECK constraints, which MongoDB
        does not support. The GST rate in particular must stay inside the
        five slabs, because gst_amount and total_amount assume it.
        """
        super().clean()
        errors = {}
        if self.amount is not None and self.amount < 0:
            errors['amount'] = 'Amount cannot be negative.'
        if self.gst_rate not in [rate for rate, _ in self.GST_RATES]:
            errors['gst_rate'] = (
                'GST rate must be one of: '
                + ', '.join(f'{rate}%' for rate, _ in self.GST_RATES)
                + '.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not kwargs.get('update_fields'):
            self.clean()
        if not self.file_name and self.file:
            self.file_name = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)


class ProjectRating(models.Model):
    """Client rating after project completion."""
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='rating')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stars = models.IntegerField(choices=RATING_CHOICES)
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.project_name} — {self.stars}★ by {self.client.get_full_name()}"

    def clean(self):
        """Star rating must be 1-5; MongoDB cannot enforce the range."""
        super().clean()
        if self.stars is None or not 1 <= self.stars <= 5:
            raise ValidationError({'stars': 'Rating must be between 1 and 5 stars.'})

    def save(self, *args, **kwargs):
        if not kwargs.get('update_fields'):
            self.clean()
        super().save(*args, **kwargs)
