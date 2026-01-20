from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from .base import BaseAdminUpdateView
from app.models import Vendor, VendorSettings
from ..forms import VendorSettingsForm
from ..utils import PermissionHelper


class VendorSettingsUpdateView(BaseAdminUpdateView):
    """Allow vendors/admins to edit vendor settings."""

    model = VendorSettings
    form_class = VendorSettingsForm
    template_name = "admin_dashboard/vendors/settings_form.html"
    vendor_field = "vendor"

    def get_queryset(self):
        queryset = VendorSettings.objects.select_related("vendor")
        return self.apply_vendor_scope(queryset)

    def get_object(self, queryset=None):
        user = self.request.user
        vendor = None

        if PermissionHelper.is_vendor(user):
            vendor = PermissionHelper.get_vendor(user)
            if not vendor:
                raise PermissionDenied("Vendor not found for current user.")
        elif PermissionHelper.is_admin(user):
            vendor_id = self.kwargs.get("vendor_id")
            if vendor_id:
                vendor = get_object_or_404(Vendor, pk=vendor_id)
        else:
            raise PermissionDenied("You do not have permission to view these settings.")

        if vendor:
            settings_obj, _ = VendorSettings.objects.get_or_create(vendor=vendor)
            return settings_obj

        # Fallback to default behavior if somehow reached without vendor (should not happen)
        return super().get_object(queryset)

    def form_valid(self, form):
        # Ensure vendor is enforced
        if PermissionHelper.is_vendor(self.request.user):
            form.instance.vendor = PermissionHelper.get_vendor(self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        vendor = self.object.vendor
        if PermissionHelper.is_admin(self.request.user) and not PermissionHelper.is_vendor(self.request.user):
            return reverse_lazy("admin_dashboard:vendor_settings_admin", kwargs={"vendor_id": vendor.id})
        return reverse_lazy("admin_dashboard:vendor_settings")

    def get_breadcrumbs(self):
        crumbs = [
            {"title": "Dashboard", "url": reverse_lazy("admin_dashboard:home")},
            {"title": "Vendor Settings", "url": "#"},
        ]
        return crumbs

