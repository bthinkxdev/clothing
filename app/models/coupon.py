from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .catalog import Product, Category
from .vendor import Vendor

__all__ = ["Coupon", "CouponUsage", "GiftCard", "LoyaltyPoint"]


class Coupon(models.Model):
    CODE_TYPE = (("fixed", "Fixed"), ("percent", "Percentage"))
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="coupons",
        null=True,
        blank=True,
        help_text="Vendor that owns this coupon"
    )
    code = models.CharField(max_length=64, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    coupon_type = models.CharField(max_length=16, choices=CODE_TYPE, default="percent")
    value = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_usage = models.PositiveIntegerField(null=True, blank=True, help_text="Global usage limit")
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    applicable_products = models.ManyToManyField(Product, blank=True)
    applicable_categories = models.ManyToManyField(Category, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["vendor", "code"], name="unique_coupon_code_per_vendor")
        ]

    def __str__(self):
        return f"{self.code} ({self.coupon_type} {self.value})"

    def is_valid_for_user(self, user: settings.AUTH_USER_MODEL, order_amount: Decimal, vendor=None) -> bool:
        now = timezone.now()
        if self.vendor:
            if not vendor:
                return False
            if self.vendor_id != getattr(vendor, "id", None):
                return False
        if not self.active or not (self.start_date <= now <= self.end_date):
            return False
        if order_amount < self.min_purchase_amount:
            return False
        if self.max_usage is not None:
            used = self.usages.count()
            if used >= self.max_usage:
                return False
        if self.per_user_limit is not None:
            used_by_user = self.usages.filter(user=user).count()
            if used_by_user >= self.per_user_limit:
                return False
        return True

    def discount_amount(self, order_amount: Decimal) -> Decimal:
        if self.coupon_type == "fixed":
            return min(self.value, order_amount)
        else:
            return (order_amount * (self.value / Decimal("100.00"))).quantize(Decimal("0.01"))


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="coupon_usages",
        null=True,
        blank=True,
        help_text="Vendor this usage belongs to"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey("Order", on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)


class GiftCard(models.Model):
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="giftcards",
        null=True,
        blank=True,
        help_text="Vendor that issued this gift card"
    )
    code = models.CharField(max_length=64, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def redeem(self, amount: Decimal):
        if amount <= 0:
            raise ValueError("Invalid amount")
        if not self.active:
            raise ValueError("Inactive gift card")
        if self.expires_at and timezone.now() > self.expires_at:
            raise ValueError("Expired gift card")
        if amount > self.balance:
            raise ValueError("Insufficient gift card balance")
        self.balance = models.F("balance") - amount
        self.save(update_fields=["balance"])
        self.refresh_from_db()


class LoyaltyPoint(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty")
    points = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

