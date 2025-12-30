from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .catalog import ProductVariant
from .vendor import Vendor

__all__ = ["Wishlist", "WishlistItem"]


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlists")
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="wishlists",
        null=True,
        blank=True,
        help_text="Vendor this wishlist belongs to"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist {self.user}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("wishlist", "variant"),)

    def clean(self):
        vendor = getattr(self.wishlist, "vendor", None)
        variant_vendor = getattr(self.variant.product, "vendor", None)
        if vendor and variant_vendor and vendor != variant_vendor:
            raise ValidationError("Wishlist and item vendor mismatch.")
        if vendor and not variant_vendor:
            raise ValidationError("Wishlist and item vendor mismatch.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

