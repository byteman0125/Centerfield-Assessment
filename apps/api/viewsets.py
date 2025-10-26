from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import UserProfile, PhoneVerification
from apps.calls.models import WakeUpCall, CallLog
from apps.calls.services import TwilioService, WeatherService
from .serializers import (
    UserSerializer, UserProfileSerializer, PhoneVerificationSerializer,
    WakeUpCallSerializer, CallLogSerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def verify_phone(self, request):
        """Send verification code to phone number."""
        serializer = PhoneVerificationSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            twilio_service = TwilioService()
            
            if twilio_service.send_verification_code(phone_number):
                request.user.phone_number = phone_number
                request.user.save()
                return Response({'message': 'Verification code sent'})
            else:
                return Response(
                    {'error': 'Failed to send verification code'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_code(self, request):
        """Verify phone number with code."""
        serializer = PhoneVerificationSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            code = serializer.validated_data['verification_code']
            
            twilio_service = TwilioService()
            if twilio_service.verify_code(phone_number, code):
                request.user.is_phone_verified = True
                request.user.save()
                return Response({'message': 'Phone number verified successfully'})
            else:
                return Response(
                    {'error': 'Invalid verification code'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WakeUpCallViewSet(viewsets.ModelViewSet):
    serializer_class = WakeUpCallSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return WakeUpCall.objects.all()
        return WakeUpCall.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a wake-up call."""
        wakeup_call = self.get_object()
        wakeup_call.status = 'cancelled'
        wakeup_call.save()
        return Response({'message': 'Wake-up call cancelled'})
    
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule a wake-up call."""
        wakeup_call = self.get_object()
        new_time = request.data.get('scheduled_time')
        
        if not new_time:
            return Response(
                {'error': 'scheduled_time is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            wakeup_call.scheduled_time = timezone.datetime.fromisoformat(new_time.replace('Z', '+00:00'))
            wakeup_call.status = 'scheduled'
            wakeup_call.save()
            return Response({'message': 'Wake-up call rescheduled'})
        except ValueError:
            return Response(
                {'error': 'Invalid datetime format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def change_method(self, request, pk=None):
        """Change contact method (call/sms)."""
        wakeup_call = self.get_object()
        new_method = request.data.get('contact_method')
        
        if new_method not in ['call', 'sms']:
            return Response(
                {'error': 'contact_method must be either "call" or "sms"'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        wakeup_call.contact_method = new_method
        wakeup_call.save()
        return Response({'message': 'Contact method updated'})


class CallLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CallLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            return CallLog.objects.all()
        return CallLog.objects.filter(wakeup_call__user=self.request.user)
