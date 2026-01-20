from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.contrib import messages

from .utils import PermissionHelper


class AdminDashboardAccessMiddleware:
    """
    Blocks non-admin/non-vendor users from accessing the admin dashboard URLs.
    Applied early in the pipeline to stop IDOR attempts before view logic.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Only guard the admin dashboard namespace
        if not path.startswith("/dashboard/"):
            return self.get_response(request)

        # Allow unauthenticated users to reach login
        login_url = reverse("admin_dashboard:login")
        logout_url = reverse("admin_dashboard:logout")
        if not request.user.is_authenticated:
            if path.startswith(login_url) or path.startswith(logout_url):
                return self.get_response(request)
            return redirect(f"{login_url}?next={path}")

        # Authenticated: only vendors are allowed
        if PermissionHelper.is_vendor(request.user):
            return self.get_response(request)

        messages.error(request, "Only vendors can access the admin dashboard.")
        return HttpResponseForbidden()

