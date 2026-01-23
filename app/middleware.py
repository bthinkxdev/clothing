from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect


class BlockedUserMiddleware:
    """
    Middleware to check if authenticated user is blocked.
    Logs them out immediately if blocked.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only check authenticated users
        if request.user.is_authenticated:
            # Check if user is blocked
            if getattr(request.user, 'is_blocked', False):
                # Logout the user
                logout(request)
                
                # Return appropriate response based on request type
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                   request.path.startswith('/api/'):
                    # For AJAX/API requests
                    return JsonResponse({
                        'error': 'Your account has been blocked. Please contact support.',
                        'blocked': True
                    }, status=403)
                else:
                    # For regular requests, redirect to login with message
                    from django.contrib import messages
                    messages.error(request, 'Your account has been blocked. Please contact support.')
                    return redirect('login')
        
        response = self.get_response(request)
        return response
    
class NoCacheMiddleware:
    """
    Middleware to prevent caching for authenticated users.
    Fixes back button showing cached pages after logout.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add no-cache headers for authenticated users
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response