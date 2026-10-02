from django.db import models

class SystemConfiguration(models.Model):
    DATA_TYPES = [
        ('boolean', 'Boolean'),
        ('string', 'String'),
        ('integer', 'Integer'),
        ('text', 'Text'),
    ]

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField(blank=True, default='')
    description = models.CharField(max_length=255, blank=True)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default='string')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_bool(cls, key, default=False):
        try:
            config = cls.objects.get(key=key)
            return config.value.strip().lower() in ('true', '1', 'yes')
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_str(cls, key, default=''):
        try:
            config = cls.objects.get(key=key)
            return config.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, key, value, description='', data_type='string'):
        obj, created = cls.objects.get_or_create(
            key=key,
            defaults={'value': str(value), 'description': description, 'data_type': data_type}
        )
        if not created:
            obj.value = str(value)
            if description:
                obj.description = description
            obj.save()
        return obj
