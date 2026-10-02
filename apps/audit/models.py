from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('BOOKING_CREATE', 'Booking Created'),
        ('BOOKING_UPDATE', 'Booking Updated'),
        ('BOOKING_SUBMIT', 'Booking Submitted'),
        ('BOOKING_APPROVE', 'Booking Approved'),
        ('BOOKING_REJECT', 'Booking Rejected'),
        ('BOOKING_CANCEL', 'Booking Cancelled'),
        ('HALL_CREATE', 'Hall Created'),
        ('HALL_UPDATE', 'Hall Updated'),
        ('HALL_MAINTENANCE', 'Hall Maintenance Status Changed'),
        ('USER_ROLE_CHANGE', 'User Role Changed'),
        ('SETTINGS_UPDATE', 'System Settings Updated'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    booking_id = models.CharField(max_length=50, blank=True, db_index=True)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    previous_value = models.TextField(blank=True)
    updated_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        username = self.user.username if self.user else 'System'
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {username} - {self.get_action_display()}"


def log_audit(request, action, booking_id='', model_name='', object_id='', previous_value='', updated_value=''):
    """
    Helper utility to record immutable audit log entries.
    """
    user = getattr(request, 'user', None) if request else None
    if user and not user.is_authenticated:
        user = None

    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    return AuditLog.objects.create(
        user=user,
        action=action,
        booking_id=booking_id,
        model_name=model_name,
        object_id=str(object_id),
        previous_value=str(previous_value),
        updated_value=str(updated_value),
        ip_address=ip_address
    )
