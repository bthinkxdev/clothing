from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages


def block_check_required(view_func):
    """
    Decorator to check if user is blocked before allowing access.
    Use this on views that perform write operations.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, 'is_blocked', False):
            # For AJAX/API requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Your account has been blocked.',
                    'blocked': True
                }, status=403)
            
            # For regular requests
            messages.error(request, 'Your account has been blocked. Please contact support.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

