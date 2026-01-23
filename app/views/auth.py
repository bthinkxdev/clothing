from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.views import View
from django.views.generic import TemplateView

from ..models import User
from ..utils import send_otp


class LoginView(TemplateView):
    template_name = "auth/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.GET.get("next", "/")
        return context


class OTPSendView(View):
    def post(self, request):
        phone = request.POST.get("phone")
        if not phone:
            return JsonResponse({"success": False, "error": "Phone number required"})

        otp = send_otp(phone)

        request.session["login_phone"] = phone
        request.session["login_otp"] = otp
        request.session["otp_expiry"] = (
            timezone.now() + timezone.timedelta(minutes=5)
        ).isoformat()

        return JsonResponse({"success": True, "message": "OTP sent successfully"})


class OTPVerifyView(View):
    def post(self, request):
        phone = request.session.get("login_phone")
        otp = request.POST.get("otp")
        stored_otp = request.session.get("login_otp")
        expiry = request.session.get("otp_expiry")

        if not all([phone, otp, stored_otp, expiry]):
            return JsonResponse({"success": False, "error": "Invalid request"})

        if timezone.now() > timezone.datetime.fromisoformat(expiry):
            return JsonResponse({"success": False, "error": "OTP expired"})

        if otp == stored_otp:
            # Get current vendor from request
            current_vendor = self.get_current_vendor(request)
            
            # Create or get user
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "username": phone,
                    "role": "customer",
                    "primary_vendor": current_vendor,
                    "registration_source": "web"
                }
            )
            
            # CHECK IF USER IS BLOCKED
            if user.is_blocked:
                return JsonResponse({
                    "success": False, 
                    "error": "Your account has been blocked. Please contact support."
                })

            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])

            del request.session["login_phone"]
            del request.session["login_otp"]
            del request.session["otp_expiry"]

            next_url = request.POST.get("next", "/")
            return JsonResponse({"success": True, "redirect": next_url})
        return JsonResponse({"success": False, "error": "Invalid OTP"})
    
    def get_current_vendor(self, request):
        """Determine which vendor the user is registering under"""
        from app.models import Vendor
        
        # Get the host from request
        host = request.get_host().split(':')[0]  # Remove port if present
        
        # Try to match vendor by store_domain
        try:
            vendor = Vendor.objects.get(store_domain=host, status='approved')
            return vendor
        except Vendor.DoesNotExist:
            pass
        
        # Try to match by store_slug (subdomain pattern)
        # e.g., vendor1.yourdomain.com -> vendor1
        if '.' in host:
            subdomain = host.split('.')[0]
            try:
                vendor = Vendor.objects.get(store_slug=subdomain, status='approved')
                return vendor
            except Vendor.DoesNotExist:
                pass
        
        # Fallback: Return admin vendor (main platform)
        try:
            admin_user = User.objects.get(username='admin')
            return Vendor.objects.get(user=admin_user)
        except (User.DoesNotExist, Vendor.DoesNotExist):
            return None


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Logged out successfully.")
        return redirect("home")

