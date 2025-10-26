from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
import uuid


class User(AbstractUser):
    """Custom user model with phone verification."""
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """Extended user profile with zip code and preferences."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    
    CONTACT_METHOD_CHOICES = [
        ('call', 'Phone Call'),
        ('sms', 'Text Message'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    zip_code = models.CharField(max_length=10, blank=True)
    preferred_contact_method = models.CharField(
        max_length=4, 
        choices=CONTACT_METHOD_CHOICES, 
        default='call'
    )
    timezone = models.CharField(max_length=50, default='America/New_York')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"


class PhoneVerification(models.Model):
    """Track phone number verification codes."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=17)
    verification_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number}"
