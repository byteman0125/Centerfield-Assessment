from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
import json
import logging

from .models import WakeUpCall, InboundCall, CallLog
from .services import generate_voice_response, TwilioService, WeatherService

User = get_user_model()

logger = logging.getLogger(__name__)


class VoiceResponseView(View):
    """Handle TwiML voice responses for wake-up calls."""
    
    def get(self, request, wakeup_call_id):
        wakeup_call = get_object_or_404(WakeUpCall, id=wakeup_call_id)
        
        # Get current weather
        weather_service = WeatherService()
        weather_data = weather_service.get_weather_by_zip(wakeup_call.zip_code)
        
        # Generate TwiML response
        twiml = generate_voice_response(weather_data, wakeup_call)
        
        return HttpResponse(twiml, content_type='text/xml')


@csrf_exempt
@require_http_methods(["POST"])
def handle_voice_input(request):
    """Handle DTMF input from voice calls."""
    try:
        digits = request.POST.get('Digits', '')
        call_sid = request.POST.get('CallSid')
        
        # Find the wake-up call based on the call SID
        call_log = CallLog.objects.filter(twilio_sid=call_sid).first()
        if not call_log:
            return HttpResponse("<Response><Say>Call not found</Say></Response>", content_type='text/xml')
        
        wakeup_call = call_log.wakeup_call
        
        if digits == '1':
            # Change next wake-up time
            response = f'<Response><Say>To change your wake-up time, please visit our website or use the mobile app.</Say></Response>'
        elif digits == '2':
            # Cancel all wake-up calls
            wakeup_call.status = 'cancelled'
            wakeup_call.save()
            response = f'<Response><Say>Your wake-up calls have been cancelled.</Say></Response>'
        elif digits == '3':
            # Switch contact method
            new_method = 'sms' if wakeup_call.contact_method == 'call' else 'call'
            wakeup_call.contact_method = new_method
            wakeup_call.save()
            response = f'<Response><Say>Your contact method has been changed to {new_method}.</Say></Response>'
        elif digits == '0':
            response = f'<Response><Say>Thank you for using our service. Have a great day!</Say><Hangup/></Response>'
        else:
            response = f'<Response><Say>Invalid option. Please try again.</Say></Response>'
        
        return HttpResponse(response, content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Error handling voice input: {e}")
        return HttpResponse("<Response><Say>An error occurred. Please try again later.</Say></Response>", content_type='text/xml')


@csrf_exempt
@require_http_methods(["POST"])
def handle_inbound_call(request):
    """Handle inbound calls to the system."""
    try:
        from_number = request.POST.get('From')
        to_number = request.POST.get('To')
        call_sid = request.POST.get('CallSid')
        
        # Create inbound call record
        inbound_call = InboundCall.objects.create(
            twilio_call_sid=call_sid,
            from_number=from_number,
            to_number=to_number,
            status='initiated'
        )
        
        # Try to find user by phone number
        user = User.objects.filter(phone_number=from_number).first()
        
        if user:
            inbound_call.user = user
            
            # Create response for authenticated user
            user_calls = WakeUpCall.objects.filter(user=user, status='scheduled').order_by('scheduled_time')
            next_call = user_calls.first()
            
            if next_call:
                response = f'''<Response>
                    <Say>Hello {user.username}. You have a wake-up call scheduled for {next_call.scheduled_time.strftime('%I:%M %p')}.</Say>
                    <Say>Press 1 to change the time, 2 to cancel, or 3 to switch to text messages.</Say>
                    <Gather numDigits="1" timeout="10" action="/calls/handle-voice-input/">
                    </Gather>
                </Response>'''
            else:
                response = f'<Response><Say>Hello {user.username}. You have no scheduled wake-up calls.</Say></Response>'
        else:
            response = '''<Response>
                <Say>Welcome to Wake-up Call service. This number is for account verification only.</Say>
                <Say>Please visit our website to create an account and schedule wake-up calls.</Say>
            </Response>'''
        
        inbound_call.status = 'active'
        inbound_call.save()
        
        return HttpResponse(response, content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Error handling inbound call: {e}")
        return HttpResponse("<Response><Say>Sorry, an error occurred.</Say></Response>", content_type='text/xml')


@csrf_exempt
@require_http_methods(["POST"])
def handle_sms_webhook(request):
    """Handle SMS replies from users."""
    try:
        from_number = request.POST.get('From')
        message_body = request.POST.get('Body', '').upper().strip()
        
        user = User.objects.filter(phone_number=from_number).first()
        
        if not user:
            return HttpResponse("User not found", status=404)
        
        twilio_service = TwilioService()
        
        if message_body == 'STOP':
            # Cancel all wake-up calls
            WakeUpCall.objects.filter(user=user, status='scheduled').update(status='cancelled')
            response_message = "All your wake-up calls have been cancelled."
        elif message_body == 'CHANGE':
            response_message = "To change your wake-up time, please visit our website or use the mobile app."
        elif message_body == 'METHOD':
            # Switch contact method
            profile = getattr(user, 'profile', None)
            if profile:
                current_method = profile.preferred_contact_method
                new_method = 'sms' if current_method == 'call' else 'call'
                profile.preferred_contact_method = new_method
                profile.save()
                response_message = f"Your contact method has been changed to {new_method}."
            else:
                response_message = "Profile not found."
        else:
            response_message = "Sorry, I didn't understand. Reply STOP to cancel, CHANGE to modify time, or METHOD to switch contact methods."
        
        twilio_service.send_sms(from_number, response_message)
        return HttpResponse("OK")
        
    except Exception as e:
        logger.error(f"Error handling SMS webhook: {e}")
        return HttpResponse("Error", status=500)


def call_status_webhook(request):
    """Handle call status updates from Twilio."""
    try:
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        duration = request.POST.get('CallDuration', '0')
        
        # Update call logs
        CallLog.objects.filter(twilio_sid=call_sid).update(
            status=call_status,
            duration=int(duration) if duration.isdigit() else 0
        )
        
        # Update inbound calls
        InboundCall.objects.filter(twilio_call_sid=call_sid).update(
            status=call_status,
            duration=int(duration) if duration.isdigit() else 0
        )
        
        return HttpResponse("OK")
        
    except Exception as e:
        logger.error(f"Error handling call status webhook: {e}")
        return HttpResponse("Error", status=500)
