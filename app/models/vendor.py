from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import F, Sum, Avg
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .address import ShippingZone

__all__ = [
    "VendorStatus",
    "BusinessType",
    "ShippingResponsibility",
    "CommissionType",
    "PayoutFrequency",
    "Vendor",
    "VendorBankVerification",
    "VendorDocument",
    "VendorShippingRate",
    "VendorApprovalLog",
]


class VendorStatus(models.TextChoices):
    PENDING = "pending", _("Pending Approval")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    SUSPENDED = "suspended", _("Suspended")
    INACTIVE = "inactive", _("Inactive")


class BusinessType(models.TextChoices):
    INDIVIDUAL = "individual", _("Individual")
    PROPRIETORSHIP = "proprietorship", _("Proprietorship")
    PARTNERSHIP = "partnership", _("Partnership")
    PRIVATE_LIMITED = "pvt_ltd", _("Private Limited / LLP")


class ShippingResponsibility(models.TextChoices):
    VENDOR = "vendor", _("Vendor Ships")
    PLATFORM = "platform", _("Platform Ships")
    HYBRID = "hybrid", _("Hybrid")


class CommissionType(models.TextChoices):
    PERCENTAGE = "percentage", _("Percentage")
    FIXED = "fixed", _("Fixed per Order")
    TIERED = "tiered", _("Tiered")
    PRODUCT_BASED = "product_based", _("Product Based")


class PayoutFrequency(models.TextChoices):
    WEEKLY = "weekly", _("Weekly")
    BIWEEKLY = "biweekly", _("Bi-Weekly")
    MONTHLY = "monthly", _("Monthly")
    ON_DEMAND = "on_demand", _("On Demand")


class Vendor(models.Model):
    """
    Core Vendor Model - Central hub for all vendor operations
    """

    # A. Basic Business Identity
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor_profile",
        help_text="Linked user account (vendor owner)",
    )
    store_name = models.CharField(max_length=255, unique=True)
    store_slug = models.SlugField(max_length=280, unique=True, db_index=True)
    store_logo = models.ImageField(upload_to="vendors/logos/%Y/%m/", blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True, help_text="Short brand tagline")
    about = models.TextField(blank=True, help_text="Brand story/description")

    # Brand category
    BRAND_CATEGORY_CHOICES = (
        ("men", "Men"),
        ("women", "Women"),
        ("kids", "Kids"),
        ("all", "All Categories"),
        ("unisex", "Unisex"),
    )
    brand_category = models.CharField(max_length=20, choices=BRAND_CATEGORY_CHOICES, default="all")
    year_established = models.PositiveIntegerField(null=True, blank=True)

    # B. Vendor Account & Ownership
    owner_full_name = models.CharField(max_length=255)
    owner_email = models.EmailField()
    owner_phone = models.CharField(max_length=20)

    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("manager", "Manager"),
        ("authorized_signatory", "Authorized Signatory"),
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="owner")
    status = models.CharField(
        max_length=20,
        choices=VendorStatus.choices,
        default=VendorStatus.PENDING,
        db_index=True,
    )

    # C. Business & Legal Details
    business_type = models.CharField(
        max_length=20,
        choices=BusinessType.choices,
        default=BusinessType.INDIVIDUAL,
    )
    gst_number = models.CharField(max_length=15, blank=True, help_text="GST Number (India)")
    pan_number = models.CharField(max_length=10, blank=True, help_text="PAN Number")

    # Business Address
    business_address_line1 = models.CharField(max_length=255)
    business_address_line2 = models.CharField(max_length=255, blank=True)
    business_city = models.CharField(max_length=100)
    business_state = models.CharField(max_length=100)
    business_postal_code = models.CharField(max_length=20)
    business_country = models.CharField(max_length=100, default="India")

    # Documents
    business_registration_doc = models.FileField(
        upload_to="vendors/documents/%Y/%m/",
        blank=True,
        null=True,
        help_text="Business registration certificate",
    )
    gst_certificate = models.FileField(upload_to="vendors/documents/%Y/%m/", blank=True, null=True)
    pan_card = models.FileField(upload_to="vendors/documents/%Y/%m/", blank=True, null=True)

    # D. Bank & Payout Details
    bank_account_holder_name = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=255, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_ifsc_code = models.CharField(max_length=11, blank=True, help_text="IFSC Code")
    upi_id = models.CharField(max_length=100, blank=True, help_text="Optional UPI ID")

    payout_frequency = models.CharField(
        max_length=20,
        choices=PayoutFrequency.choices,
        default=PayoutFrequency.MONTHLY,
    )

    # E. Vendor Storefront Settings
    store_domain = models.CharField(
        max_length=255,
        blank=True,
        unique=True,
        null=True,
        help_text="Custom domain or subdomain for store",
    )
    theme = models.ForeignKey(
        "SiteTheme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_stores",
    )
    primary_brand_color = models.CharField(max_length=7, default="#FF6B6B")
    store_banner = models.ImageField(upload_to="vendors/banners/%Y/%m/", blank=True, null=True)

    # Social Links
    instagram_url = models.URLField(blank=True, max_length=500)
    facebook_url = models.URLField(blank=True, max_length=500)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)

    # F. Operational & Fulfilment Settings
    shipping_responsibility = models.CharField(
        max_length=20,
        choices=ShippingResponsibility.choices,
        default=ShippingResponsibility.VENDOR,
    )
    default_processing_time = models.PositiveIntegerField(
        default=2,
        help_text="Processing time in days",
    )
    return_policy = models.TextField(blank=True)
    exchange_policy = models.TextField(blank=True)
    cod_enabled = models.BooleanField(default=True)
    max_cod_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("5000.00"),
    )

    # G. Commission & Pricing Control (Admin Controlled)
    commission_type = models.CharField(
        max_length=20,
        choices=CommissionType.choices,
        default=CommissionType.PERCENTAGE,
    )
    commission_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text="Percentage or fixed amount",
    )
    vendor_tax_responsibility = models.BooleanField(
        default=True,
        help_text="True if vendor handles tax, False if platform handles",
    )
    settlement_delay_days = models.PositiveIntegerField(
        default=7,
        help_text="Days after delivery before payout (T+7, T+14 etc)",
    )

    # H. Vendor Analytics (System Generated)
    total_products_count = models.PositiveIntegerField(default=0, editable=False)
    total_orders_count = models.PositiveIntegerField(default=0, editable=False)
    total_sales_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    platform_earnings_from_vendor = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    vendor_payout_due = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Feature flags
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False, help_text="Platform verified badge")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "is_featured"]),
            models.Index(fields=["store_slug"]),
        ]

    def __str__(self):
        return f"{self.store_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.store_slug:
            self.store_slug = slugify(self.store_name)

        if not self.store_domain and self.store_slug:
            self.store_domain = f"{self.store_slug}.yourdomain.com"

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("vendor_store", kwargs={"slug": self.store_slug})

    def approve(self):
        """Approve vendor application"""
        self.status = VendorStatus.APPROVED
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_at"])

    def reject(self, reason=""):
        """Reject vendor application"""
        self.status = VendorStatus.REJECTED
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save(update_fields=["status", "rejected_at", "rejection_reason"])

    def suspend(self):
        """Suspend vendor"""
        self.status = VendorStatus.SUSPENDED
        self.save(update_fields=["status"])

    def calculate_commission(self, order_amount: Decimal) -> Decimal:
        """Calculate commission for an order"""
        if self.commission_type == CommissionType.PERCENTAGE:
            return (order_amount * self.commission_value / Decimal("100")).quantize(Decimal("0.01"))
        if self.commission_type == CommissionType.FIXED:
            return self.commission_value
        return Decimal("0.00")

    def update_analytics(self):
        """Update cached analytics fields"""
        from .order import Order, OrderItem  # local import to avoid circular

        self.total_products_count = self.products.filter(is_active=True).count()

        vendor_orders = Order.objects.filter(
            items__variant__product__vendor=self,
            status__in=["paid", "processing", "shipped", "delivered"],
        ).distinct()

        self.total_orders_count = vendor_orders.count()

        order_items = OrderItem.objects.filter(
            order__in=vendor_orders,
            variant__product__vendor=self,
        )
        sales_data = order_items.aggregate(total=Sum(F("unit_price") * F("quantity")))
        self.total_sales_amount = sales_data["total"] or Decimal("0.00")

        self.platform_earnings_from_vendor = sum(
            self.calculate_commission(item.unit_price * item.quantity)
            for item in order_items
        )

        payouts = self.payouts.filter(status="pending")
        self.vendor_payout_due = payouts.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        avg_rating = self.reviews.aggregate(avg=Avg("rating"))
        self.average_rating = avg_rating["avg"] or Decimal("0.00")

        self.save(
            update_fields=[
                "total_products_count",
                "total_orders_count",
                "total_sales_amount",
                "platform_earnings_from_vendor",
                "vendor_payout_due",
                "average_rating",
            ]
        )


class VendorBankVerification(models.Model):
    """Track bank verification status"""

    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name="bank_verification")

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("failed", "Failed"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_response = models.JSONField(blank=True, null=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class VendorDocument(models.Model):
    """Additional vendor documents"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="documents")

    DOCUMENT_TYPE_CHOICES = (
        ("identity", "Identity Proof"),
        ("address", "Address Proof"),
        ("business", "Business Document"),
        ("tax", "Tax Document"),
        ("bank", "Bank Document"),
        ("other", "Other"),
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="vendors/documents/%Y/%m/")

    STATUS_CHOICES = (
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_vendor_documents",
    )


class VendorShippingRate(models.Model):
    """Custom shipping rates for vendors"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="shipping_rates")

    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name="vendor_rates")
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    rate = models.DecimalField(max_digits=8, decimal_places=2)
    free_shipping_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    estimated_days_min = models.PositiveIntegerField(default=2)
    estimated_days_max = models.PositiveIntegerField(default=7)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [["vendor", "zone", "min_order_value"]]
        ordering = ["vendor", "zone", "min_order_value"]

    def __str__(self):
        return f"{self.vendor.store_name} - {self.zone.name} - ${self.rate}"


class VendorApprovalLog(models.Model):
    """Log all vendor approval/rejection actions"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="approval_logs")

    ACTION_CHOICES = (
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("suspended", "Suspended"),
        ("reactivated", "Reactivated"),
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendor_actions",
    )
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self):
        return f"{self.vendor.store_name} - {self.action} - {self.performed_at}"

