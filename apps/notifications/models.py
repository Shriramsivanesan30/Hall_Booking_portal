from django.db import models
from django.contrib.auth.models import User
from apps.bookings.models import Booking

class Notification(models.Model):
    TYPE_SUBMITTED = 'SUBMITTED'
    TYPE_HOD_APPROVAL = 'HOD_APPROVAL'
    TYPE_COORDINATOR_APPROVAL = 'COORDINATOR_APPROVAL'
    TYPE_FINAL_APPROVAL = 'FINAL_APPROVAL'
    TYPE_REJECTION = 'REJECTION'
    TYPE_CANCELLATION = 'CANCELLATION'
    TYPE_REMINDER = 'REMINDER'
    TYPE_SYSTEM = 'SYSTEM'

    TYPE_CHOICES = [
        (TYPE_SUBMITTED, 'Booking Submitted'),
        (TYPE_HOD_APPROVAL, 'HOD Approved'),
        (TYPE_COORDINATOR_APPROVAL, 'Coordinator Approved'),
        (TYPE_FINAL_APPROVAL, 'Final Confirmation'),
        (TYPE_REJECTION, 'Booking Rejected'),
        (TYPE_CANCELLATION, 'Booking Cancelled'),
        (TYPE_REMINDER, 'Event Reminder'),
        (TYPE_SYSTEM, 'System Notification'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default=TYPE_SYSTEM)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.recipient.username} - {self.title} ({'Read' if self.is_read else 'Unread'})"
