from django.db import models
from django.contrib.auth.models import User
from apps.bookings.models import Booking

class ApprovalHistory(models.Model):
    ACTION_SUBMITTED = 'SUBMITTED'
    ACTION_HOD_APPROVED = 'HOD_APPROVED'
    ACTION_HOD_REJECTED = 'HOD_REJECTED'
    ACTION_COORDINATOR_APPROVED = 'COORDINATOR_APPROVED'
    ACTION_COORDINATOR_REJECTED = 'COORDINATOR_REJECTED'
    ACTION_PRINCIPAL_APPROVED = 'PRINCIPAL_APPROVED'
    ACTION_PRINCIPAL_REJECTED = 'PRINCIPAL_REJECTED'
    ACTION_MODIFICATION_REQUESTED = 'MODIFICATION_REQUESTED'
    ACTION_CANCELLED = 'CANCELLED'

    ACTION_CHOICES = [
        (ACTION_SUBMITTED, 'Booking Submitted'),
        (ACTION_HOD_APPROVED, 'HOD Approved'),
        (ACTION_HOD_REJECTED, 'HOD Rejected'),
        (ACTION_COORDINATOR_APPROVED, 'Coordinator Approved'),
        (ACTION_COORDINATOR_REJECTED, 'Coordinator Rejected'),
        (ACTION_PRINCIPAL_APPROVED, 'Principal Approved (Confirmed)'),
        (ACTION_PRINCIPAL_REJECTED, 'Principal Rejected'),
        (ACTION_MODIFICATION_REQUESTED, 'Modification Requested'),
        (ACTION_CANCELLED, 'Cancelled'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='approval_history')
    stage = models.CharField(max_length=50) # 'HOD Verification', 'Coordinator Review', 'Principal Approval', 'System Admin'
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_actions')
    previous_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Approval History'
        verbose_name_plural = 'Approval Histories'

    def __str__(self):
        return f"{self.booking.booking_id} - {self.get_action_display()} by {self.user}"
