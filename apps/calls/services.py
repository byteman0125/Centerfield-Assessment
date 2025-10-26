"""
Twilio and weather services for wake-up calls.
"""
import requests
import logging
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class TwilioService:
    """Handle Twilio communication."""
    
    def __init__(self):
        self.client = None
        self.enabled = False
        
        # Only initialize if credentials are available
        if (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and
            settings.TWILIO_ACCOUNT_SID.strip() and settings.TWILIO_AUTH_TOKEN.strip()):
            try:
                self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                self.enabled = True
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.enabled = False
        else:
            logger.warning("Twilio credentials not configured, service disabled")
    
    def send_verification_code(self, phone_number):
        """Send verification code to phone number."""
        if not self.enabled or not self.client:
            logger.warning("Twilio service not enabled, cannot send verification code")
            return False
            
        try:
            verification = self.client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verifications.create(
                to=phone_number,
                channel='sms'
            )
            return verification.status == 'pending'
        except Exception as e:
            logger.error(f"Failed to send verification code: {e}")
            return False
    
    def verify_code(self, phone_number, code):
        """Verify phone number with code."""
        if not self.enabled or not self.client:
            logger.warning("Twilio service not enabled, cannot verify code")
            return False
            
        try:
            verification_check = self.client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verification_checks.create(
                to=phone_number,
                code=code
            )
            return verification_check.status == 'approved'
        except Exception as e:
            logger.error(f"Failed to verify code: {e}")
            return False
    
    def make_call(self, to_number, url, record=False):
        """Make a phone call."""
        if not self.enabled or not self.client:
            logger.warning("Twilio service not enabled, cannot make call")
            return None
            
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=settings.TWILIO_PHONE_NUMBER,
                url=url,
                record=record
            )
            return call.sid
        except Exception as e:
            logger.error(f"Failed to make call: {e}")
            return None
    
    def send_sms(self, to_number, message):
        """Send SMS message."""
        if not self.enabled or not self.client:
            logger.warning("Twilio service not enabled, cannot send SMS")
            return None
            
        try:
            message = self.client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_number
            )
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return None


class WeatherService:
    """Get weather information by zip code."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or settings.WEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    def get_weather_by_zip(self, zip_code):
        """Get current weather by zip code."""
        try:
            params = {
                'zip': f"{zip_code},US",
                'appid': self.api_key,
                'units': 'imperial'
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return {
                'temperature': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'feels_like': data['main']['feels_like'],
                'location': data['name']
            }
        except Exception as e:
            logger.error(f"Failed to get weather: {e}")
            return {
                'temperature': 'N/A',
                'description': 'Weather unavailable',
                'humidity': 'N/A',
                'feels_like': 'N/A',
                'location': 'Unknown'
            }


def generate_voice_response(weather_data, wakeup_call):
    """Generate TwiML response for voice calls."""
    response = VoiceResponse()
    
    # Wake-up message
    response.say(
        f"Good morning! This is your wake-up call scheduled for {wakeup_call.scheduled_time.strftime('%I:%M %p')}.",
        voice='alice'
    )
    
    # Weather announcement
    if weather_data:
        temp = weather_data.get('temperature', 'N/A')
        description = weather_data.get('description', 'weather unavailable')
        location = weather_data.get('location', 'your area')
        
        response.say(
            f"The current temperature in {location} is {temp} degrees with {description}.",
            voice='alice'
        )
    
    # Menu options
    response.say(
        "Press 1 to change your next wake-up time. Press 2 to cancel all wake-up calls. "
        "Press 3 to switch between call and text message. Press 0 to hang up.",
        voice='alice'
    )
    
    # Gather DTMF input
    gather = response.gather(
        num_digits=1,
        timeout=10,
        action='/calls/handle-voice-input/',
        method='POST'
    )
    
    # Fallback if no input
    response.say("Thank you for using our wake-up call service. Have a great day!", voice='alice')
    response.hangup()
    
    return str(response)


def generate_sms_message(weather_data, wakeup_call):
    """Generate SMS message with weather."""
    message = f"Good morning! Your wake-up call at {wakeup_call.scheduled_time.strftime('%I:%M %p')}."
    
    if weather_data:
        temp = weather_data.get('temperature', 'N/A')
        description = weather_data.get('description', 'weather unavailable')
        location = weather_data.get('location', 'your area')
        message += f" Current weather in {location}: {temp}°F, {description}."
    
    message += " Reply STOP to cancel, CHANGE to modify time, or METHOD to switch between call/text."
    
    return message
