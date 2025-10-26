from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import WakeUpCall, CallLog, InboundCall


@admin.register(WakeUpCall)
class WakeUpCallAdmin(admin.ModelAdmin):
    list_display = ('call_info', 'scheduled_time_display', 'contact_method_display', 'status', 'status_display', 'user_info', 'demo_status', 'quick_actions')
    list_filter = ('status', 'contact_method', 'is_demo', 'scheduled_time', 'created_at')
    search_fields = ('user__username', 'phone_number', 'zip_code')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_executed', 'next_execution')
    list_editable = ('status',)
    date_hierarchy = 'scheduled_time'
    ordering = ('-scheduled_time',)
    
    fieldsets = (
        ('Call Details', {
            'fields': ('user', 'scheduled_time', 'phone_number', 'contact_method', 'zip_code'),
            'description': 'Basic information about the wake-up call.'
        }),
        ('Status & Settings', {
            'fields': ('status', 'is_demo'),
            'description': 'Call status and whether this is a demo call.'
        }),
        ('Execution History', {
            'fields': ('last_executed', 'next_execution'),
            'classes': ('collapse',),
            'description': 'Information about when the call was last executed and when it will be executed next.'
        }),
        ('System Info', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System-generated information.'
        }),
    )
    
    def call_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">{}</small>',
            obj.user.username,
            obj.phone_number
        )
    call_info.short_description = 'Call Details'
    
    def scheduled_time_display(self, obj):
        now = timezone.now()
        if obj.scheduled_time > now:
            color = '#667eea'  # Future - blue
        else:
            color = '#718096'  # Past - gray
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br><small>{}</small>',
            color,
            obj.scheduled_time.strftime('%m/%d/%Y'),
            obj.scheduled_time.strftime('%I:%M %p')
        )
    scheduled_time_display.short_description = 'Scheduled Time'
    scheduled_time_display.admin_order_field = 'scheduled_time'
    
    def contact_method_display(self, obj):
        icons = {
            'call': '📞',
            'sms': '💬',
        }
        colors = {
            'call': '#667eea',
            'sms': '#48bb78',
        }
        icon = icons.get(obj.contact_method, '❓')
        color = colors.get(obj.contact_method, '#718096')
        
        return format_html(
            '<span style="color: {}; font-size: 1.2em;">{}</span><br><small>{}</small>',
            color, icon, obj.contact_method.title()
        )
    contact_method_display.short_description = 'Method'
    contact_method_display.admin_order_field = 'contact_method'
    
    def status_display(self, obj):
        colors = {
            'scheduled': '#667eea',
            'completed': '#48bb78',
            'cancelled': '#e53e3e',
            'failed': '#ed8936',
        }
        color = colors.get(obj.status, '#718096')
        
        icons = {
            'scheduled': '⏰',
            'completed': '✅',
            'cancelled': '❌',
            'failed': '⚠️',
        }
        icon = icons.get(obj.status, '❓')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.status.title()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def user_info(self, obj):
        info = []
        if obj.user.is_phone_verified:
            info.append('<span style="color: #48bb78;">Verified</span>')
        else:
            info.append('<span style="color: #ed8936;">Unverified</span>')
            
        if obj.zip_code:
            info.append(f'<span style="color: #667eea;">{obj.zip_code}</span>')
            
        return format_html(' • '.join(info))
    user_info.short_description = 'User Status'
    
    def demo_status(self, obj):
        if obj.is_demo:
            return format_html(
                '<span style="background: #fffbeb; color: #92400e; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">DEMO</span>'
            )
        return format_html('<span style="color: #48bb78;">Live</span>')
    demo_status.short_description = 'Type'
    
    def quick_actions(self, obj):
        actions = []
        
        # View call logs
        logs_url = reverse('admin:calls_calllog_changelist') + f'?wakeup_call__id__exact={obj.id}'
        actions.append(
            f'<a href="{logs_url}" style="color: #667eea; text-decoration: none;" title="View call logs">Logs</a>'
        )
        
        return format_html(' | '.join(actions))
    quick_actions.short_description = 'Actions'


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ('call_info', 'status_display', 'twilio_sid_display', 'duration_display', 'created_at')
    list_filter = ('status', 'created_at', 'wakeup_call__contact_method')
    search_fields = ('wakeup_call__user__username', 'twilio_sid', 'wakeup_call__phone_number')
    readonly_fields = ('created_at', 'twilio_sid', 'duration', 'status')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('wakeup_call__user')
    
    fieldsets = (
        ('Call Information', {
            'fields': ('wakeup_call', 'twilio_sid', 'status'),
            'description': 'Basic information about the call attempt.'
        }),
        ('Call Details', {
            'fields': ('duration', 'error_message'),
            'description': 'Details about the call execution and any errors.'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def call_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small><br><small style="color: #666;">{}</small>',
            obj.wakeup_call.user.username,
            obj.wakeup_call.phone_number,
            obj.wakeup_call.contact_method.title()
        )
    call_info.short_description = 'Call Info'
    
    def status_display(self, obj):
        colors = {
            'completed': '#48bb78',
            'failed': '#e53e3e',
            'busy': '#ed8936',
            'no-answer': '#718096',
        }
        color = colors.get(obj.status, '#667eea')
        
        icons = {
            'completed': '✅',
            'failed': '❌',
            'busy': '📞',
            'no-answer': '⏰',
        }
        icon = icons.get(obj.status, '📋')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.status.title() if obj.status else 'Unknown'
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def twilio_sid_display(self, obj):
        if obj.twilio_sid:
            return format_html(
                '<span style="font-family: monospace; background: #f7fafc; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">{}</span>',
                obj.twilio_sid[:20] + '...' if len(obj.twilio_sid) > 20 else obj.twilio_sid
            )
        return format_html('<span style="color: #999;">No SID</span>')
    twilio_sid_display.short_description = 'Twilio SID'
    
    def duration_display(self, obj):
        if obj.duration:
            return format_html(
                '<span style="font-weight: bold; color: #667eea;">{}s</span>',
                obj.duration
            )
        return format_html('<span style="color: #999;">-</span>')
    duration_display.short_description = 'Duration'


@admin.register(InboundCall)
class InboundCallAdmin(admin.ModelAdmin):
    list_display = ('call_participants', 'status_display', 'duration_display', 'user_info', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_number', 'to_number', 'user__username')
    readonly_fields = ('created_at', 'duration')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Call Information', {
            'fields': ('from_number', 'to_number', 'user', 'status'),
            'description': 'Information about the inbound call.'
        }),
        ('Call Details', {
            'fields': ('duration', 'twilio_sid', 'recording_url'),
            'description': 'Details about the call execution.'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def call_participants(self, obj):
        return format_html(
            '<strong>From:</strong> <span style="font-family: monospace;">{}</span><br>'
            '<strong>To:</strong> <span style="font-family: monospace;">{}</span>',
            obj.from_number, obj.to_number
        )
    call_participants.short_description = 'Call Participants'
    
    def status_display(self, obj):
        colors = {
            'completed': '#48bb78',
            'failed': '#e53e3e',
            'busy': '#ed8936',
            'no-answer': '#718096',
        }
        color = colors.get(obj.status, '#667eea')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.status.title() if obj.status else 'Unknown'
        )
    status_display.short_description = 'Status'
    
    def duration_display(self, obj):
        if obj.duration:
            return format_html(
                '<span style="font-weight: bold; color: #667eea;">{}s</span>',
                obj.duration
            )
        return format_html('<span style="color: #999;">-</span>')
    duration_display.short_description = 'Duration'
    
    def user_info(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.user.username,
                obj.user.email or 'No email'
            )
        return format_html('<span style="color: #999;">Anonymous</span>')
    user_info.short_description = 'User'
