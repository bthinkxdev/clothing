from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from ..models import Cart, CartItem, Coupon, ProductVariant
from ..utils import calculate_shipping, calculate_tax
from .base import CommonContextMixin


class CartView(CommonContextMixin, TemplateView):
    template_name = "cart/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=self.request.user, is_active=True)
            cart_items = cart.items.select_related(
                "variant__product", "variant__inventory"
            ).all()

            stock_issues = []
            for item in cart_items:
                available = item.variant.available_stock()
                if available < item.quantity:
                    stock_issues.append(
                        {"item": item, "available": available, "requested": item.quantity}
                    )

            context["cart"] = cart
            context["cart_items"] = cart_items
            context["subtotal"] = cart.total()
            context["shipping"] = calculate_shipping(cart)
            context["tax"] = calculate_tax(cart)
            context["total"] = context["subtotal"] + context["shipping"] + context["tax"]
            context["stock_issues"] = stock_issues

            context["available_coupons"] = Coupon.objects.filter(
                active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now()
            )
        else:
            context["cart"] = None
            context["cart_items"] = []
            context["subtotal"] = Decimal("0.00")

        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Cart", "url": ""},
        ]

        return context


class CartAddView(LoginRequiredMixin, View):
    def post(self, request):
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))

        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)

        available = variant.available_stock()
        if available < quantity:
            messages.error(request, f"Only {available} items available in stock.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant, defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity = F("quantity") + quantity
            cart_item.save()
            cart_item.refresh_from_db()

            if cart_item.quantity > available:
                cart_item.quantity = available
                cart_item.save()
                messages.warning(request, f"Only {available} items added to cart.")

        messages.success(request, "Item added to cart!")
        return redirect("cart")


class CartUpdateView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get("quantity", 1))

        if quantity <= 0:
            cart_item.delete()
            messages.success(request, "Item removed from cart.")
        else:
            available = cart_item.variant.available_stock()
            if quantity > available:
                messages.error(request, f"Only {available} items available.")
                quantity = available

            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated.")

        return redirect("cart")


class CartRemoveView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        messages.success(request, "Item removed from cart.")
        return redirect("cart")


class CartClearView(LoginRequiredMixin, View):
    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user, is_active=True)
        cart.items.all().delete()
        messages.success(request, "Cart cleared.")
        return redirect("cart")

