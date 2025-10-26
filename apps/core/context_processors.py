from django.contrib.auth import get_user_model
from apps.calls.models import WakeUpCall, CallLog

User = get_user_model()


def user_context(request):
    """Add user context to all templates."""
    context = {}
    if request.user.is_authenticated:
        try:
            context['is_admin_user'] = (
                hasattr(request.user, 'profile') and 
                request.user.profile.role == 'admin'
            )
        except Exception:
            # If profile doesn't exist, treat as regular user
            context['is_admin_user'] = False
    return context


def admin_stats(request):
    """Add statistics to admin context for dashboard widgets."""
    if request.path.startswith('/admin/'):
        try:
            total_users = User.objects.count()
            verified_users = User.objects.filter(is_phone_verified=True).count()
            unverified_users = total_users - verified_users
            verified_percentage = round((verified_users / total_users * 100) if total_users > 0 else 0)
            
            total_calls = WakeUpCall.objects.count()
            scheduled_calls = WakeUpCall.objects.filter(status='scheduled').count()
            completed_calls = WakeUpCall.objects.filter(status='completed').count()
            failed_calls = WakeUpCall.objects.filter(status='failed').count()
            total_logs = CallLog.objects.count()
            successful_calls = CallLog.objects.filter(status='completed').count()
            failed_logs = CallLog.objects.filter(status='failed').count()
            no_answer_logs = CallLog.objects.filter(status='no_answer').count()
            
            return {
                'total_users': total_users,
                'verified_users': verified_users,
                'unverified_users': unverified_users,
                'verified_percentage': verified_percentage,
                'total_calls': total_calls,
                'scheduled_calls': scheduled_calls,
                'completed_calls': completed_calls,
                'failed_calls': failed_calls,
                'total_logs': total_logs,
                'successful_calls': successful_calls,
                'failed_logs': failed_logs,
                'no_answer_logs': no_answer_logs,
            }
        except Exception:
            # Return empty stats if database is not ready
            return {
                'total_users': 0,
                'verified_users': 0,
                'unverified_users': 0,
                'verified_percentage': 0,
                'total_calls': 0,
                'scheduled_calls': 0,
                'completed_calls': 0,
                'failed_calls': 0,
                'total_logs': 0,
                'successful_calls': 0,
                'failed_logs': 0,
                'no_answer_logs': 0,
            }
    return {}
