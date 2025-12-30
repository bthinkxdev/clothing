from decimal import Decimal

from django.db import models
from django.utils import timezone

from .vendor import Vendor

__all__ = ["VendorSubscriptionPlan", "VendorSubscription", "VendorSubscriptionInvoice"]


class VendorSubscriptionPlan(models.Model):
    """Subscription plans for vendors"""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    max_products = models.PositiveIntegerField(default=100)
    max_images_per_product = models.PositiveIntegerField(default=10)
    commission_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    custom_domain_allowed = models.BooleanField(default=False)
    advanced_analytics = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)
    bulk_upload = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "price_monthly"]

    def __str__(self):
        return f"{self.name} - ${self.price_monthly}/month"


class VendorSubscription(models.Model):
    """Active subscription for a vendor"""

    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(VendorSubscriptionPlan, on_delete=models.PROTECT)

    BILLING_CYCLE_CHOICES = (
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default="monthly")

    STATUS_CHOICES = (
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
        ("suspended", "Suspended"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    start_date = models.DateField()
    current_period_start = models.DateField()
    current_period_end = models.DateField()
    cancelled_at = models.DateTimeField(null=True, blank=True)

    auto_renew = models.BooleanField(default=True)
    payment_method = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vendor.store_name} - {self.plan.name}"

    def is_active(self):
        return self.status == "active" and self.current_period_end >= timezone.now().date()


class VendorSubscriptionInvoice(models.Model):
    """Invoices for vendor subscriptions"""

    subscription = models.ForeignKey(VendorSubscription, on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=50, unique=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    period_start = models.DateField()
    period_end = models.DateField()

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    payment_reference = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

