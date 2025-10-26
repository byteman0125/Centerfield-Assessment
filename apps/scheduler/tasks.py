"""
Celery tasks for handling wake-up calls.
"""
from celery import shared_task
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
import logging

from apps.calls.models import WakeUpCall, CallLog
from apps.calls.services import TwilioService, WeatherService, generate_voice_response, generate_sms_message

logger = logging.getLogger(__name__)


@shared_task
def execute_wakeup_call(wakeup_call_id):
    """Execute a wake-up call task."""
    try:
        wakeup_call = WakeUpCall.objects.get(id=wakeup_call_id)
    except WakeUpCall.DoesNotExist:
        logger.error(f"WakeUpCall {wakeup_call_id} not found")
        return False
    
    # Check if call is still scheduled and not cancelled
    if wakeup_call.status not in ['scheduled', 'active']:
        logger.info(f"WakeUpCall {wakeup_call_id} is no longer active")
        return False
    
    # Get weather data
    weather_service = WeatherService()
    weather_data = weather_service.get_weather_by_zip(wakeup_call.zip_code)
    
    # Create call log entry
    call_log = CallLog.objects.create(
        wakeup_call=wakeup_call,
        status='initiated',
        weather_data=weather_data
    )
    
    try:
        if wakeup_call.is_demo:
            # Demo mode - just log
            logger.info(f"Demo wake-up call for {wakeup_call.user.username}")
            call_log.status = 'completed'
            call_log.save()
        else:
            # Real call/SMS
            twilio_service = TwilioService()
            
            if wakeup_call.contact_method == 'call':
                # Generate voice URL
                voice_url = f"{settings.BASE_URL}{reverse('calls:voice_response', args=[wakeup_call.id])}"
                twilio_sid = twilio_service.make_call(wakeup_call.phone_number, voice_url)
                
                if twilio_sid:
                    call_log.twilio_sid = twilio_sid
                    call_log.status = 'completed'
                    wakeup_call.status = 'completed'
                else:
                    call_log.status = 'failed'
                    call_log.error_message = "Failed to initiate call"
                    wakeup_call.status = 'failed'
            
            elif wakeup_call.contact_method == 'sms':
                message = generate_sms_message(weather_data, wakeup_call)
                twilio_sid = twilio_service.send_sms(wakeup_call.phone_number, message)
                
                if twilio_sid:
                    call_log.twilio_sid = twilio_sid
                    call_log.status = 'completed'
                    wakeup_call.status = 'completed'
                else:
                    call_log.status = 'failed'
                    call_log.error_message = "Failed to send SMS"
                    wakeup_call.status = 'failed'
            
            call_log.save()
        
        wakeup_call.last_executed = timezone.now()
        wakeup_call.save()
        
        return True
        
    except Exception as e:
        logger.error(f"Error executing wakeup call {wakeup_call_id}: {e}")
        call_log.status = 'failed'
        call_log.error_message = str(e)
        call_log.save()
        
        wakeup_call.status = 'failed'
        wakeup_call.save()
        
        return False


@shared_task
def schedule_recurring_wakeup_calls():
    """Schedule all pending wake-up calls."""
    current_time = timezone.now()
    
    # Find calls that should be executed now or in the next minute
    pending_calls = WakeUpCall.objects.filter(
        status__in=['scheduled', 'active'],
        scheduled_time__lte=current_time + timezone.timedelta(minutes=1),
        scheduled_time__gte=current_time - timezone.timedelta(minutes=1)
    )
    
    for wakeup_call in pending_calls:
        execute_wakeup_call.delay(str(wakeup_call.id))
    
    logger.info(f"Scheduled {pending_calls.count()} wake-up calls")
