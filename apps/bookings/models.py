import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.departments.models import Department
from apps.halls.models import Hall

class Booking(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_HOD_APPROVED = 'HOD_APPROVED'
    STATUS_COORDINATOR_APPROVED = 'COORDINATOR_APPROVED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Pending HOD Approval'),
        (STATUS_HOD_APPROVED, 'Pending Coordinator Review'),
        (STATUS_COORDINATOR_APPROVED, 'Pending Principal Approval'),
        (STATUS_APPROVED, 'Approved / Confirmed'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    STAGE_DRAFT = 'DRAFT'
    STAGE_HOD = 'HOD'
    STAGE_COORDINATOR = 'COORDINATOR'
    STAGE_PRINCIPAL = 'PRINCIPAL'
    STAGE_COMPLETED = 'COMPLETED'
    STAGE_REJECTED = 'REJECTED'
    STAGE_CANCELLED = 'CANCELLED'

    STAGE_CHOICES = [
        (STAGE_DRAFT, 'Draft'),
        (STAGE_HOD, 'HOD Verification'),
        (STAGE_COORDINATOR, 'Coordinator Verification'),
        (STAGE_PRINCIPAL, 'Principal Final Approval'),
        (STAGE_COMPLETED, 'Completed / Confirmed'),
        (STAGE_REJECTED, 'Rejected'),
        (STAGE_CANCELLED, 'Cancelled'),
    ]

    EVENT_TYPES = [
        ('Seminar', 'Seminar'),
        ('Workshop', 'Workshop'),
        ('Guest Lecture', 'Guest Lecture'),
        ('Faculty Development Programme', 'Faculty Development Programme (FDP)'),
        ('Meeting', 'Meeting'),
        ('Examination', 'Examination'),
        ('Cultural Event', 'Cultural Event'),
        ('Other', 'Other'),
    ]

    booking_id = models.CharField(max_length=30, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='bookings')

    event_name = models.CharField(max_length=200)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='Seminar')
    expected_participants = models.PositiveIntegerField(default=50)

    event_date = models.DateField(db_index=True)
    start_time = models.TimeField(db_index=True)
    end_time = models.TimeField(db_index=True)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)

    preferred_hall = models.ForeignKey(Hall, on_delete=models.PROTECT, related_name='preferred_bookings')
    alternative_hall = models.ForeignKey(Hall, on_delete=models.SET_NULL, null=True, blank=True, related_name='alternative_bookings')
    allocated_hall = models.ForeignKey(Hall, on_delete=models.PROTECT, null=True, blank=True, related_name='allocated_bookings')

    # Facilities Checkboxes
    req_projector = models.BooleanField(default=False, verbose_name='Projector')
    req_audio = models.BooleanField(default=False, verbose_name='Audio System')
    req_microphone = models.BooleanField(default=False, verbose_name='Microphone')
    req_wifi = models.BooleanField(default=False, verbose_name='Wi-Fi')
    req_video_conferencing = models.BooleanField(default=False, verbose_name='Video Conferencing')
    req_ac = models.BooleanField(default=False, verbose_name='Air Conditioning')
    req_stage = models.BooleanField(default=False, verbose_name='Stage')
    req_recording = models.BooleanField(default=False, verbose_name='Recording Facility')

    # Additional Information
    chief_guest = models.CharField(max_length=255, blank=True)
    event_description = models.TextField(blank=True)
    special_requirements = models.TextField(blank=True)

    # Workflow & State
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    current_approval_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default=STAGE_DRAFT)

    rejection_reason = models.TextField(blank=True)
    rejected_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='rejected_bookings')

    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_bookings')
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event_date', '-start_time']
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'

    def __str__(self):
        return f"{self.booking_id} - {self.event_name} ({self.get_active_hall().name})"

    def save(self, *args, **kwargs):
        if not self.booking_id:
            # Generate unique booking ID: BK-YEAR-SEQUENCE
            year = self.event_date.year if self.event_date else timezone.now().year
            last_booking = Booking.objects.filter(booking_id__startswith=f'BK-{year}-').order_by('-id').first()
            if last_booking:
                try:
                    last_num = int(last_booking.booking_id.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = Booking.objects.count() + 1
            else:
                new_num = 1
            self.booking_id = f"BK-{year}-{new_num:03d}"

        # Calculate duration
        if self.start_time and self.end_time:
            t1 = datetime.datetime.combine(datetime.date.today(), self.start_time)
            t2 = datetime.datetime.combine(datetime.date.today(), self.end_time)
            if t2 > t1:
                diff = (t2 - t1).total_seconds() / 3600.0
                self.duration_hours = round(diff, 2)

        # Set default allocated hall if not assigned
        if not self.allocated_hall and self.preferred_hall:
            self.allocated_hall = self.preferred_hall

        super().save(*args, **kwargs)

    def get_active_hall(self):
        return self.allocated_hall or self.preferred_hall

    @property
    def requested_facilities(self):
        facilities = []
        if self.req_projector: facilities.append('Projector')
        if self.req_audio: facilities.append('Audio System')
        if self.req_microphone: facilities.append('Microphone')
        if self.req_wifi: facilities.append('Wi-Fi')
        if self.req_video_conferencing: facilities.append('Video Conferencing')
        if self.req_ac: facilities.append('Air Conditioning')
        if self.req_stage: facilities.append('Stage')
        if self.req_recording: facilities.append('Recording Facility')
        return facilities

    @property
    def is_editable(self):
        return self.status in [self.STATUS_DRAFT, self.STATUS_SUBMITTED]

    @property
    def is_cancellable(self):
        return self.status not in [self.STATUS_CANCELLED, self.STATUS_REJECTED]

    @property
    def status_badge_class(self):
        if self.status == self.STATUS_APPROVED:
            return 'badge-success'
        elif self.status in [self.STATUS_SUBMITTED, self.STATUS_HOD_APPROVED, self.STATUS_COORDINATOR_APPROVED]:
            return 'badge-warning'
        elif self.status == self.STATUS_REJECTED:
            return 'badge-danger'
        elif self.status == self.STATUS_CANCELLED:
            return 'badge-neutral'
        return 'badge-secondary'


class BookingAttachment(models.Model):
    TYPE_SCHEDULE = 'schedule'
    TYPE_APPROVAL_DOC = 'approval_doc'
    TYPE_OTHER = 'other'

    TYPE_CHOICES = [
        (TYPE_SCHEDULE, 'Programme Schedule'),
        (TYPE_APPROVAL_DOC, 'Approval Document'),
        (TYPE_OTHER, 'Other Document'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='booking_docs/%Y/%m/')
    title = models.CharField(max_length=150)
    file_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default=TYPE_SCHEDULE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.booking_id} - {self.title}"
