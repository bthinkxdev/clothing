import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

from .address import Address
from .catalog import ProductVariant
from .coupon import Coupon, CouponUsage
from .vendor import Vendor

__all__ = ["Order", "OrderItem", "Payment"]


class Order(models.Model):
    ORDER_STATUS = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)

    # MULTI-VENDOR INTEGRATION
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_orders",
        help_text="Primary vendor for this order (if single vendor)"
    )
    is_multi_vendor = models.BooleanField(
        default=False,
        help_text="True if order contains items from multiple vendors"
    )

    status = models.CharField(max_length=20, choices=ORDER_STATUS, default="pending")
    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    # shipping/tracking
    courier = models.CharField(max_length=120, blank=True)
    tracking_number = models.CharField(max_length=255, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-placed_at"]

    def __str__(self):
        return f"Order {self.id} by {self.user}"

    def recalc_totals(self):
        items = self.items.select_related("variant")
        subtotal = Decimal("0.00")
        for it in items:
            subtotal += it.unit_price * it.quantity
        self.subtotal = subtotal
        self.total = (self.subtotal + self.shipping_amount + self.tax_amount - self.discount_amount).quantize(Decimal("0.01"))
        self.save(update_fields=["subtotal", "total", "updated_at"])

    def apply_coupon(self, coupon: Coupon):
        if not coupon:
            raise ValueError("Coupon invalid")
        if coupon.vendor and coupon.vendor != self.vendor:
            raise ValueError("Coupon not applicable for this vendor")
        if coupon.is_valid_for_user(self.user, self.subtotal, vendor=self.vendor):
            self.coupon = coupon
            self.discount_amount = coupon.discount_amount(self.subtotal)
            CouponUsage.objects.create(coupon=coupon, vendor=coupon.vendor, user=self.user, order=self)
            self.recalc_totals()
        else:
            raise ValueError("Coupon invalid")

    def mark_paid(self, payment):
        self.status = "paid"
        self.updated_at = timezone.now()
        self.save(update_fields=["status", "updated_at"])
        self.finalize_order()

    def finalize_order(self):
        """Deduct inventory for each item"""
        for item in self.items.select_related("variant__inventory"):
            inv = getattr(item.variant, "inventory", None)
            if not inv:
                raise ValueError(f"No inventory for {item.variant}")
            inv.deduct(item.quantity)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("order", "variant"),)

    def clean(self):
        from django.core.exceptions import ValidationError

        variant_vendor = getattr(self.variant.product, "vendor", None)
        order_vendor = getattr(self.order, "vendor", None)
        if not self.order.is_multi_vendor:
            if order_vendor and variant_vendor and order_vendor != variant_vendor:
                raise ValidationError("Order and item vendor mismatch.")
            if order_vendor and not variant_vendor:
                raise ValidationError("Order and item vendor mismatch.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def line_total(self):
        return self.unit_price * Decimal(self.quantity)


class Payment(models.Model):
    """A record of payment attempt; supports multiple processors"""

    PAYMENT_METHOD = (
        ("razorpay", "Razorpay"),
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("cod", "Cash On Delivery"),
        ("wallet", "Wallet"),
    )

    PAYMENT_STATUS = (
        ("initiated", "Initiated"),
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=32, choices=PAYMENT_METHOD)
    status = models.CharField(max_length=32, choices=PAYMENT_STATUS, default="initiated")
    processor_response = models.JSONField(blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_success(self, processor_response: dict = None):
        self.status = "success"
        if processor_response:
            self.processor_response = processor_response
        self.save(update_fields=["status", "processor_response", "updated_at"])
        if self.order and Decimal(self.order.total) <= self.order.payments.filter(status="success").aggregate(total=models.Sum("amount"))["total"] or Decimal(self.amount) >= self.order.total:
            self.order.mark_paid(self)

