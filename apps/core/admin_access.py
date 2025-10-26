from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseForbidden


class AdminAccessMiddleware:
    """Middleware to prevent regular users from accessing admin URLs."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is trying to access admin URLs
        if request.path.startswith('/admin/'):
            # Allow access if user is not authenticated (will be redirected to login)
            if not request.user.is_authenticated:
                pass  # Let Django handle the authentication redirect
            else:
                # User is authenticated, check if they're admin
                try:
                    is_admin = (hasattr(request.user, 'profile') and 
                               request.user.profile.role == 'admin')
                except Exception:
                    # If profile doesn't exist, treat as regular user
                    is_admin = False
                
                if not is_admin:
                    # Regular user trying to access admin - redirect to home with error message
                    messages.error(request, 'Access denied. Admin privileges required.')
                    return redirect('home')
        
        response = self.get_response(request)
        return response
