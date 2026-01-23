from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, FormView

from ..forms import OrderTrackingForm
from ..models import Order
from ..utils import send_order_confirmation_email
from .base import CommonContextMixin


class OrderSuccessView(LoginRequiredMixin, CommonContextMixin, DetailView):
    model = Order
    template_name = "orders/success.html"
    context_object_name = "order"
    pk_url_kwarg = "id"

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_items"] = self.object.items.select_related("variant__product").all()
        context["payment"] = self.object.payments.filter(status="success").first()

        # send_order_confirmation_email(self.object)

        return context


class OrderFailureView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "orders/failure.html"
    context_object_name = "order"
    pk_url_kwarg = "id"

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class MyOrdersView(LoginRequiredMixin, CommonContextMixin, ListView):
    template_name = "account/orders.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).prefetch_related(
            "items__variant__product"
        )

        status_filter = self.request.GET.get("status")
        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by("-placed_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "all")
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "My Orders", "url": ""},
        ]
        return context


class OrderDetailView(LoginRequiredMixin, CommonContextMixin, DetailView):
    model = Order
    template_name = "orders/detail.html"
    context_object_name = "order"
    pk_url_kwarg = "id"

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_items"] = self.object.items.select_related("variant__product").all()
        context["payment"] = self.object.payments.filter(status="success").first()
        context["tracking_timeline"] = self.get_tracking_timeline()
        context["can_cancel"] = self.object.status in ["pending", "processing"]
        context["can_return"] = self.object.status == "delivered"

        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "My Orders", "url": reverse("my_orders")},
            {"name": str(self.object.id), "url": ""},
        ]
        return context

    def get_tracking_timeline(self):
        order = self.object
        return [
            {"status": "placed", "label": "Order Placed", "completed": True, "date": order.placed_at},
            {
                "status": "paid",
                "label": "Payment Confirmed",
                "completed": order.status != "pending",
            },
            {
                "status": "processing",
                "label": "Processing",
                "completed": order.status in ["processing", "shipped", "delivered"],
            },
            {
                "status": "shipped",
                "label": "Shipped",
                "completed": order.status in ["shipped", "delivered"],
            },
            {"status": "delivered", "label": "Delivered", "completed": order.status == "delivered"},
        ]


class OrderCancelView(LoginRequiredMixin, View):
    def post(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)

        if order.status not in ["pending", "processing"]:
            messages.error(request, "This order cannot be cancelled.")
            return redirect("order_detail", id=id)

        with transaction.atomic():
            for item in order.items.select_related("variant__inventory").all():
                item.variant.inventory.unreserve(item.quantity)

            order.status = "cancelled"
            order.save()

        messages.success(request, "Order cancelled successfully.")
        return redirect("order_detail", id=id)


class GuestOrderTrackingView(FormView):
    template_name = "orders/track.html"
    form_class = OrderTrackingForm

    def form_valid(self, form):
        order_id = form.cleaned_data["order_id"]
        email = form.cleaned_data["email"]

        try:
            order = Order.objects.get(id=order_id, user__email=email)
            return render(
                self.request,
                self.template_name,
                {"form": form, "order": order, "order_items": order.items.all()},
            )
        except Order.DoesNotExist:
            messages.error(self.request, "Order not found.")
            return self.form_invalid(form)

