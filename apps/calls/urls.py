from django.urls import path
from . import views

app_name = 'calls'

urlpatterns = [
    path('voice-response/<uuid:wakeup_call_id>/', views.VoiceResponseView.as_view(), name='voice_response'),
    path('handle-voice-input/', views.handle_voice_input, name='handle_voice_input'),
    path('inbound-call/', views.handle_inbound_call, name='inbound_call'),
    path('sms-webhook/', views.handle_sms_webhook, name='sms_webhook'),
    path('call-status/', views.call_status_webhook, name='call_status'),
]
