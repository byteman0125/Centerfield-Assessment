from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class WakeUpCall(models.Model):
    """Model for managing wake-up calls."""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    CONTACT_METHOD_CHOICES = [
        ('call', 'Phone Call'),
        ('sms', 'Text Message'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wakeup_calls')
    scheduled_time = models.DateTimeField()
    phone_number = models.CharField(max_length=17)
    contact_method = models.CharField(max_length=4, choices=CONTACT_METHOD_CHOICES)
    zip_code = models.CharField(max_length=10)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='scheduled')
    is_demo = models.BooleanField(default=False, help_text="Demo calls don't make actual calls/texts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_executed = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['scheduled_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.scheduled_time} ({self.contact_method})"


class CallLog(models.Model):
    """Log all call attempts and interactions."""
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('no_answer', 'No Answer'),
        ('busy', 'Busy'),
    ]
    
    wakeup_call = models.ForeignKey(WakeUpCall, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    twilio_sid = models.CharField(max_length=100, blank=True, null=True)
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")
    error_message = models.TextField(blank=True)
    weather_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wakeup_call.user.username} - {self.status} - {self.created_at}"


class InboundCall(models.Model):
    """Track inbound calls to the system."""
    twilio_call_sid = models.CharField(max_length=100, unique=True)
    from_number = models.CharField(max_length=17)
    to_number = models.CharField(max_length=17)
    status = models.CharField(max_length=20, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    recording_url = models.URLField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.from_number} -> {self.to_number} ({self.status})"
