from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserProfile, PhoneVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'phone_display', 'verification_status', 'is_active', 'staff_status', 'date_joined', 'quick_actions')
    list_filter = ('is_phone_verified', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_editable = ('is_active',)
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Phone Verification', {
            'fields': ('phone_number', 'is_phone_verified'),
            'description': 'Users must verify their phone number before scheduling wake-up calls.'
        }),
    )
    
    def phone_display(self, obj):
        if obj.phone_number:
            return format_html(
                '<span style="font-family: monospace;">{}</span>',
                obj.phone_number
            )
        return format_html('<span style="color: #999;">Not provided</span>')
    phone_display.short_description = 'Phone Number'
    
    def verification_status(self, obj):
        if obj.is_phone_verified:
            return format_html(
                '<span style="color: #48bb78; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: #ed8936; font-weight: bold;">⚠ Not Verified</span>'
        )
    verification_status.short_description = 'Verification'
    
    def staff_status(self, obj):
        status = []
        if obj.is_staff:
            status.append('<span style="color: #667eea;">Staff</span>')
        if obj.is_superuser:
            status.append('<span style="color: #9f7aea;">Admin</span>')
        if obj.is_active:
            status.append('<span style="color: #48bb78;">Active</span>')
        else:
            status.append('<span style="color: #e53e3e;">Inactive</span>')
        return format_html(' • '.join(status))
    staff_status.short_description = 'Status'
    
    def quick_actions(self, obj):
        actions = []
        if obj.is_active:
            actions.append(
                f'<a href="{reverse("admin:core_user_changelist")}?is_phone_verified__exact=0" '
                f'style="color: #ed8936; text-decoration: none;" title="View unverified users">'
                f'View Similar</a>'
            )
        
        profile_url = reverse('admin:core_userprofile_changelist') + f'?user__id__exact={obj.id}'
        actions.append(
            f'<a href="{profile_url}" style="color: #667eea; text-decoration: none;" '
            f'title="View user profile">Profile</a>'
        )
        
        return format_html(' | '.join(actions))
    quick_actions.short_description = 'Actions'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_display', 'zip_code', 'contact_method_display', 'preferred_contact_method', 'timezone', 'user_info')
    list_filter = ('role', 'preferred_contact_method', 'timezone')
    search_fields = ('user__username', 'user__email', 'zip_code')
    list_editable = ('zip_code', 'preferred_contact_method')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role'),
            'description': 'Basic user profile information.'
        }),
        ('Preferences', {
            'fields': ('zip_code', 'preferred_contact_method', 'timezone'),
            'description': 'User preferences for wake-up calls and weather updates.'
        }),
    )
    
    def role_display(self, obj):
        colors = {
            'admin': '#9f7aea',
            'user': '#667eea',
        }
        color = colors.get(obj.role, '#718096')
        return format_html(
            '<span style="color: {}; font-weight: bold; text-transform: uppercase;">{}</span>',
            color, obj.role
        )
    role_display.short_description = 'Role'
    
    def contact_method_display(self, obj):
        icons = {
            'call': '📞',
            'sms': '💬',
        }
        icon = icons.get(obj.preferred_contact_method, '❓')
        return format_html(
            '{} {}',
            icon, obj.preferred_contact_method.title()
        )
    contact_method_display.short_description = 'Contact Method'
    
    def user_info(self, obj):
        info = []
        if obj.user.is_phone_verified:
            info.append('<span style="color: #48bb78;">Verified</span>')
        else:
            info.append('<span style="color: #ed8936;">Unverified</span>')
        
        if obj.user.is_active:
            info.append('<span style="color: #48bb78;">Active</span>')
        else:
            info.append('<span style="color: #e53e3e;">Inactive</span>')
            
        return format_html(' • '.join(info))
    user_info.short_description = 'User Status'


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'code_snippet', 'verification_status', 'created_at', 'verified_at')
    list_filter = ('is_verified', 'created_at', 'verified_at')
    search_fields = ('user__username', 'phone_number')
    readonly_fields = ('created_at', 'verified_at', 'verification_code')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Verification Details', {
            'fields': ('user', 'phone_number', 'verification_code', 'is_verified'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'verified_at'),
            'classes': ('collapse',)
        }),
    )
    
    def code_snippet(self, obj):
        if obj.verification_code:
            return format_html(
                '<span style="font-family: monospace; background: #f7fafc; padding: 2px 6px; border-radius: 4px;">{}</span>',
                obj.verification_code[:3] + '***'
            )
        return '-'
    code_snippet.short_description = 'Code'
    
    def verification_status(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="color: #48bb78; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: #ed8936; font-weight: bold;">⏳ Pending</span>'
        )
    verification_status.short_description = 'Status'
