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
            user, _ = User.objects.get_or_create(
                phone=phone, defaults={"username": phone, "role": "customer"}
            )

            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])

            del request.session["login_phone"]
            del request.session["login_otp"]
            del request.session["otp_expiry"]

            next_url = request.POST.get("next", "/")
            return JsonResponse({"success": True, "redirect": next_url})
        return JsonResponse({"success": False, "error": "Invalid OTP"})


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Logged out successfully.")
        return redirect("home")

