from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

from ..utils import PermissionHelper
from ..forms import AdminAuthenticationForm
from app.models import VendorStatus


class AdminLoginView(LoginView):
    """Login page for the admin dashboard"""

    template_name = "admin_dashboard/auth/login.html"
    redirect_authenticated_user = True
    form_class = AdminAuthenticationForm

    def form_valid(self, form):
        """Allow only users with admin permission"""
        response = super().form_valid(form)
        user = self.request.user
        if PermissionHelper.is_vendor(user):
            vendor_profile = PermissionHelper.get_vendor(user)
            if not vendor_profile or vendor_profile.status != VendorStatus.APPROVED:
                messages.error(self.request, "Vendor account is not approved yet.")
                logout(self.request)
                return redirect("admin_dashboard:login")
            return response

        if not PermissionHelper.check_dashboard_permission(user):
            messages.error(self.request, "You do not have permission to access the admin dashboard.")
            logout(self.request)
            return redirect("admin_dashboard:login")
        return response

    def get_success_url(self):
        # Vendors and admins land on the same dashboard, but data is scoped.
        return reverse_lazy("admin_dashboard:home")


class AdminLogoutView(LogoutView):
    """Logout and redirect to login"""

    next_page = reverse_lazy("admin_dashboard:login")

