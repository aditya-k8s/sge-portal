"""
Email sending helpers for Shri Gouri Engineers.
Uses Django's send_mail — configure SMTP in settings.py for real delivery.
"""
from django.core.mail import send_mail
from django.conf import settings

COMPANY = "Shri Gouri Engineers"


def send_otp_email(email, otp_code, purpose, name=""):
    """Send OTP verification email."""
    if purpose == 'registration':
        subject = f"Verify your email — {COMPANY}"
        body = f"""Hello {name or 'there'},

Welcome to {COMPANY}!

Your email verification code is:

    {otp_code}

This code is valid for 10 minutes.

If you did not create an account with us, please ignore this email.

— {COMPANY} Team
"""
    else:
        subject = f"Reset your password — {COMPANY}"
        body = f"""Hello {name or 'there'},

We received a request to reset your password for your {COMPANY} account.

Your password reset code is:

    {otp_code}

This code is valid for 10 minutes.

If you did not request a password reset, please ignore this email.

— {COMPANY} Team
"""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send OTP to {email}: {e}")
        return False


def send_login_alert(user, request=None):
    """Send login notification email to the user."""
    import datetime
    from django.utils import timezone

    now = timezone.now()
    try:
        ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now_ist = now.astimezone(ist_offset)
        time_str = now_ist.strftime("%d %b %Y at %I:%M %p IST")
    except Exception:
        time_str = now.strftime("%d %b %Y at %H:%M")

    ip = "Unknown"
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR', 'Unknown')

    name = user.get_full_name() or user.username
    subject = f"New login to your {COMPANY} account"
    body = f"""Hello {name},

A new login was detected on your {COMPANY} account.

  Time:       {time_str}
  IP Address: {ip}
  Username:   {user.username}

If this was you, no action is needed.

If you did NOT log in, please reset your password immediately:
http://127.0.0.1:8000/accounts/forgot-password/

— {COMPANY} Team
"""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"[EMAIL ERROR] Login alert failed for {user.email}: {e}")
