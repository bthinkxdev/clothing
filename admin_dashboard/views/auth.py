from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

from ..utils import PermissionHelper


class AdminLoginView(LoginView):
    """Login page for the admin dashboard"""

    template_name = "admin_dashboard/auth/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Allow only users with admin permission"""
        response = super().form_valid(form)
        user = self.request.user
        if not PermissionHelper.check_admin_permission(user):
            messages.error(self.request, "You do not have permission to access the admin dashboard.")
            logout(self.request)
            return redirect("admin_dashboard:login")
        return response

    def get_success_url(self):
        return reverse_lazy("admin_dashboard:home")


class AdminLogoutView(LogoutView):
    """Logout and redirect to login"""

    next_page = reverse_lazy("admin_dashboard:login")

