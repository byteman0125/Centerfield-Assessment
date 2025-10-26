from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.core.models import UserProfile, PhoneVerification
from apps.calls.models import WakeUpCall, CallLog

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role', 'zip_code', 'preferred_contact_method', 'timezone']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'is_phone_verified', 'profile']
        read_only_fields = ['id', 'is_phone_verified']


class PhoneVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=17)
    verification_code = serializers.CharField(max_length=6, required=False)


class WakeUpCallSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(max_length=17, required=False)
    
    class Meta:
        model = WakeUpCall
        fields = [
            'id', 'scheduled_time', 'phone_number', 'contact_method', 
            'zip_code', 'status', 'is_demo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Set phone_number from user if not provided
        if not validated_data.get('phone_number') and 'request' in self.context:
            validated_data['phone_number'] = self.context['request'].user.phone_number
        return super().create(validated_data)
    
    def validate_scheduled_time(self, value):
        """Ensure scheduled time is in the future."""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value
    
    def validate(self, attrs):
        """Validate that user has verified phone number."""
        user = self.context['request'].user
        if not user.is_phone_verified:
            raise serializers.ValidationError("Phone number must be verified before scheduling calls.")
        return attrs


class CallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']
