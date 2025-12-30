from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models

from .catalog import ProductVariant
from .vendor import Vendor

__all__ = ["Cart", "CartItem", "AbandonedCartSnapshot"]


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carts")
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="carts",
        null=True,
        blank=True,
        help_text="Vendor this cart belongs to"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Cart #{self.pk} - {self.user}"

    def total(self) -> Decimal:
        items = self.items.select_related("variant")
        total = Decimal("0.00")
        for it in items:
            total += it.line_total()
        return total

    def item_count(self) -> int:
        return self.items.count()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("cart", "variant"),)

    def clean(self):
        vendor = getattr(self.cart, "vendor", None)
        variant_vendor = getattr(self.variant.product, "vendor", None)
        if vendor and variant_vendor and vendor != variant_vendor:
            raise ValidationError("Cart and item vendor mismatch.")
        if vendor and not variant_vendor:
            raise ValidationError("Cart and item vendor mismatch.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def line_total(self):
        return self.variant.get_price() * Decimal(self.quantity)

    def __str__(self):
        return f"{self.variant} x {self.quantity}"


class AbandonedCartSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="abandoned_carts")
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="abandoned_cart_snapshots",
        null=True,
        blank=True,
        help_text="Vendor for which the cart was abandoned",
    )
    cart_snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

