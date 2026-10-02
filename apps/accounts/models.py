from django.db import models
from django.contrib.auth.models import User
from apps.departments.models import Department

class UserProfile(models.Model):
    ROLE_STUDENT = 'STUDENT'
    ROLE_FACULTY = 'FACULTY'
    ROLE_HOD = 'HOD'
    ROLE_COORDINATOR = 'COORDINATOR'
    ROLE_PRINCIPAL = 'PRINCIPAL'
    ROLE_ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_FACULTY, 'Faculty / Staff'),
        (ROLE_HOD, 'Head of Department (HOD)'),
        (ROLE_COORDINATOR, 'Seminar Hall Coordinator'),
        (ROLE_PRINCIPAL, 'Principal / Authorized Approver'),
        (ROLE_ADMIN, 'System Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_FACULTY)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    employee_roll_no = models.CharField(max_length=50, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    auth_provider = models.CharField(max_length=50, default='local') # 'microsoft' or 'local'
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        dept_str = f" - {self.department.code}" if self.department else ""
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()}{dept_str})"

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    @property
    def is_faculty(self):
        return self.role in [self.ROLE_FACULTY, self.ROLE_HOD, self.ROLE_COORDINATOR, self.ROLE_PRINCIPAL, self.ROLE_ADMIN]

    @property
    def is_hod(self):
        return self.role == self.ROLE_HOD

    @property
    def is_coordinator(self):
        return self.role == self.ROLE_COORDINATOR

    @property
    def is_principal(self):
        return self.role == self.ROLE_PRINCIPAL

    @property
    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN or self.user.is_superuser

    @property
    def can_create_booking(self):
        # Faculty, HOD, Coordinator, Principal, Admin can create bookings
        return self.role != self.ROLE_STUDENT

    @property
    def can_view_approvals(self):
        return self.role in [self.ROLE_HOD, self.ROLE_COORDINATOR, self.ROLE_PRINCIPAL, self.ROLE_ADMIN]
