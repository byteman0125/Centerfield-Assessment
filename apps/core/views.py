from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .models import UserProfile, User
from apps.calls.models import WakeUpCall
from apps.calls.services import TwilioService


class CustomLoginView(LoginView):
    """Custom login view that redirects based on user role."""
    template_name = 'registration/login.html'
    redirect_authenticated_user = False
    
    def form_valid(self, form):
        """Override form_valid to redirect based on user role after login."""
        # Perform the login first
        auth_login(self.request, form.get_user())
        
        # Now check the user's role and redirect accordingly
        user = form.get_user()
        
        # Check if user has admin role with proper error handling
        try:
            # Try to get the profile and check if user is admin
            if hasattr(user, 'profile'):
                profile = getattr(user, 'profile', None)
                is_admin = profile and profile.role == 'admin'
            else:
                is_admin = False
        except Exception:
            # If any error occurs, treat as regular user
            is_admin = False
        
        if is_admin:
            return HttpResponseRedirect(reverse('admin:index'))
        else:
            # Regular users go to home page - this should be the case for demo_user_1
            return HttpResponseRedirect(reverse('home'))


def home(request):
    """Home page with role-based access."""
    context = {}
    if request.user.is_authenticated:
        # Check if user has profile and what role they have
        is_admin = (hasattr(request.user, 'profile') and 
                   request.user.profile.role == 'admin')
        
        if is_admin:
            # Admins can see all scheduled calls
            wakeup_calls = WakeUpCall.objects.filter(status='scheduled').order_by('scheduled_time')[:10]
        else:
            # Regular users see only their calls
            wakeup_calls = WakeUpCall.objects.filter(user=request.user, status='scheduled').order_by('scheduled_time')
        context['wakeup_calls'] = wakeup_calls
        context['is_admin'] = is_admin
    return render(request, 'core/home.html', context)


@login_required
def dashboard(request):
    """User dashboard - only for regular users."""
    # Redirect admin users to admin dashboard
    if (hasattr(request.user, 'profile') and 
        request.user.profile.role == 'admin'):
        return redirect('admin:index')
    
    user_wakeup_calls = WakeUpCall.objects.filter(user=request.user).order_by('-created_at')[:10]
    context = {
        'wakeup_calls': user_wakeup_calls,
        'user_profile': getattr(request.user, 'profile', None),
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    """Update user profile."""
    try:
        data = json.loads(request.body)
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if 'zip_code' in data:
            profile.zip_code = data['zip_code']
        if 'preferred_contact_method' in data:
            profile.preferred_contact_method = data['preferred_contact_method']
        if 'timezone' in data:
            profile.timezone = data['timezone']
        
        profile.save()
        
        return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
