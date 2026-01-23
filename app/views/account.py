from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    TemplateView,
    UpdateView,
    CreateView,
    ListView,
    DeleteView,
)

from ..forms import ProfileForm, AddressForm
from ..models import User, Address, LoyaltyPoint, Order, Wishlist
from .base import CommonContextMixin

from django.utils.decorators import method_decorator
from ..decorators import block_check_required


class AccountDashboardView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = "account/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Account", "url": ""},
        ]
        context["recent_orders"] = Order.objects.filter(user=self.request.user)[:5]
        context["total_orders"] = Order.objects.filter(user=self.request.user).count()
        context["wallet_balance"] = self.request.user.wallet_balance
        context["wishlist_count"] = Wishlist.objects.filter(user=self.request.user).aggregate(
            total=Count("items")
        ).get("total") or 0

        loyalty = LoyaltyPoint.objects.filter(user=self.request.user).first()
        context["loyalty_points"] = loyalty.points if loyalty else 0
        context["saved_addresses"] = self.request.user.addresses.count()

        return context

@method_decorator(block_check_required, name='dispatch')
class ProfileEditView(LoginRequiredMixin, CommonContextMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "account/profile_edit.html"
    success_url = reverse_lazy("account_dashboard")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Account", "url": reverse("account_dashboard")},
            {"name": "Edit Profile", "url": ""},
        ]
        return context


class AddressListView(LoginRequiredMixin, CommonContextMixin, ListView):
    template_name = "account/addresses.html"
    context_object_name = "addresses"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Addresses", "url": ""},
        ]
        return context

@method_decorator(block_check_required, name='dispatch')
class AddressCreateView(LoginRequiredMixin, CommonContextMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = "account/address_form.html"
    success_url = reverse_lazy("address_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Address added successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Addresses", "url": reverse("address_list")},
            {"name": "Add", "url": ""},
        ]
        return context


class AddressUpdateView(LoginRequiredMixin, CommonContextMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = "account/address_form.html"
    success_url = reverse_lazy("address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Addresses", "url": reverse("address_list")},
            {"name": "Edit", "url": ""},
        ]
        return context

@method_decorator(block_check_required, name='dispatch')
class AddressDeleteView(LoginRequiredMixin, CommonContextMixin, DeleteView):
    model = Address
    success_url = reverse_lazy("address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Addresses", "url": reverse("address_list")},
            {"name": "Delete", "url": ""},
        ]
        return context


class WalletView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = "account/wallet.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wallet_balance"] = getattr(self.request.user, "wallet_balance", 0)
        transactions = getattr(self.request.user, "wallet_transactions", None)
        context["transactions"] = transactions.all() if transactions else []
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Wallet", "url": ""},
        ]
        return context


class MyCouponsView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = "account/coupons.html"

    def get_context_data(self, **kwargs):
        from django.utils import timezone
        from ..models import Coupon

        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context["coupons"] = Coupon.objects.filter(active=True, end_date__gte=now)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Coupons", "url": ""},
        ]
        return context

