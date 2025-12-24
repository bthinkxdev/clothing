from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from ..models import Wishlist, WishlistItem, Cart, CartItem, ProductVariant
from .base import CommonContextMixin


class WishlistView(LoginRequiredMixin, CommonContextMixin, ListView):
    template_name = "wishlist/wishlist.html"
    context_object_name = "wishlist_items"

    def get_queryset(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist.items.select_related("variant__product", "variant__inventory").all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_items"] = self.get_queryset().count()
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Wishlist", "url": ""},
        ]

        total_value = Decimal("0.00")
        for item in self.get_queryset():
            total_value += item.variant.get_price()
        context["total_value"] = total_value

        return context


class WishlistAddView(LoginRequiredMixin, View):
    def post(self, request):
        variant_id = request.POST.get("variant_id")
        variant = get_object_or_404(ProductVariant, id=variant_id)

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        WishlistItem.objects.get_or_create(wishlist=wishlist, variant=variant)

        messages.success(request, "Added to wishlist!")
        return redirect(request.META.get("HTTP_REFERER", "/"))


class WishlistRemoveView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        wishlist_item = get_object_or_404(
            WishlistItem, id=item_id, wishlist__user=request.user
        )
        wishlist_item.delete()
        messages.success(request, "Removed from wishlist.")
        return redirect("wishlist")


class WishlistMoveToCartView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        wishlist_item = get_object_or_404(
            WishlistItem, id=item_id, wishlist__user=request.user
        )

        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
        CartItem.objects.get_or_create(
            cart=cart, variant=wishlist_item.variant, defaults={"quantity": 1}
        )

        wishlist_item.delete()

        messages.success(request, "Moved to cart!")
        return redirect("wishlist")

