from django.db import models
from django.utils import timezone

class Hall(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    building = models.CharField(max_length=100)
    floor = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=100)
    location = models.CharField(max_length=255, blank=True)
    responsible_person = models.CharField(max_length=150, blank=True)
    responsible_contact = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_under_maintenance = models.BooleanField(default=False)
    maintenance_reason = models.TextField(blank=True)
    maintenance_start = models.DateTimeField(null=True, blank=True)
    maintenance_end = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(upload_to='halls/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Seminar Hall'
        verbose_name_plural = 'Seminar Halls'

    def __str__(self):
        return f"{self.name} ({self.code}) - Cap: {self.capacity}"

    @property
    def is_currently_under_maintenance(self):
        if not self.is_under_maintenance:
            return False
        now = timezone.now()
        if self.maintenance_start and self.maintenance_end:
            return self.maintenance_start <= now <= self.maintenance_end
        return self.is_under_maintenance

    @property
    def available_facilities_list(self):
        return [f.name for f in self.facilities.filter(is_available=True)]


class HallFacility(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='facilities')
    name = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)
    details = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Hall Facility'
        verbose_name_plural = 'Hall Facilities'
        unique_together = ['hall', 'name']

    def __str__(self):
        return f"{self.hall.name} - {self.name} ({'Available' if self.is_available else 'Unavailable'})"
