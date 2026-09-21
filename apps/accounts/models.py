from django.contrib.auth.models import AbstractUser
from django.db import models
import random, string
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('client', 'Client'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    company_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    profile_image = models.FileField(upload_to='profiles/', null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_admin_user(self):
        return self.role == 'admin' or self.is_staff or self.is_superuser

    def is_client_user(self):
        return self.role == 'client'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        # role is filtered on nearly every admin page; email is looked up on
        # every password-reset request. Note that email is deliberately NOT
        # unique at database level: AbstractUser allows it to be blank, and
        # MySQL treats two empty strings as a collision. Uniqueness is enforced
        # in the forms instead, where a useful message can be shown.
        indexes = [
            models.Index(fields=['role'], name='user_role_idx'),
            models.Index(fields=['email'], name='user_email_idx'),
            models.Index(fields=['-created_at'], name='user_created_idx'),
        ]


class OTPCode(models.Model):
    PURPOSE_CHOICES = [
        ('registration', 'Registration Verification'),
        ('password_reset', 'Password Reset'),
    ]
    email = models.EmailField()
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Matches the exact filter used when verifying a code.
            models.Index(fields=['email', 'purpose', 'is_used'], name='otp_lookup_idx'),
            models.Index(fields=['expires_at'], name='otp_expires_idx'),
        ]

    def __str__(self):
        # The code itself is a single-use secret, so keep it out of logs,
        # admin listings and error pages.
        return f"OTP for {self.email} ({self.purpose})"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def generate(cls, email, purpose):
        # Invalidate any existing unused OTPs for this email+purpose
        cls.objects.filter(email=email, purpose=purpose, is_used=False).update(is_used=True)
        # Spent codes have no value after they expire and the table would
        # otherwise grow without limit.
        cls.objects.filter(expires_at__lt=timezone.now() - timedelta(days=1)).delete()
        code = ''.join(random.choices(string.digits, k=6))
        otp = cls.objects.create(
            email=email,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        return otp

    @classmethod
    def recent_attempt_count(cls, email, purpose, within_minutes=10):
        """
        How many codes were issued for this address recently. Used to rate
        limit OTP requests so the endpoint cannot be used to send mail
        repeatedly to an address that did not ask for it.
        """
        since = timezone.now() - timedelta(minutes=within_minutes)
        return cls.objects.filter(
            email=email, purpose=purpose, created_at__gte=since
        ).count()
