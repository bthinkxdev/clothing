import random
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone

from .order import Order, OrderItem
from .vendor import Vendor

__all__ = [
    "VendorOrderTransaction",
    "VendorPayout",
    "VendorPayoutAdjustment",
    "VendorSettlementBatch",
]


class VendorOrderTransaction(models.Model):
    """Track each order line item for commission calculation"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="transactions")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="vendor_transactions")
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="vendor_transaction")

    # Financial breakdown
    item_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Rate at time of order")
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    vendor_earning = models.DecimalField(max_digits=12, decimal_places=2)

    # Tax handling
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_responsibility = models.CharField(max_length=20, default="vendor")

    # Status tracking
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Payout tracking
    is_paid_out = models.BooleanField(default=False)
    payout = models.ForeignKey(
        "VendorPayout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vendor", "status", "is_paid_out"]),
            models.Index(fields=["order", "vendor"]),
        ]

    def __str__(self):
        return f"Transaction {self.id} - {self.vendor.store_name} - Order {self.order.id}"

    def save(self, *args, **kwargs):
        from .vendor import Vendor  # local import to avoid circular in type checkers

        if not self.item_subtotal:
            self.item_subtotal = self.order_item.line_total()

        if not self.commission_rate:
            self.commission_rate = self.vendor.commission_value

        if not self.commission_amount:
            self.commission_amount = self.vendor.calculate_commission(self.item_subtotal)

        if not self.vendor_earning:
            self.vendor_earning = self.item_subtotal - self.commission_amount

        super().save(*args, **kwargs)


class VendorPayout(models.Model):
    """Vendor payout records - generated for settlement periods"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="payouts")

    # Payout period
    period_start = models.DateField()
    period_end = models.DateField()

    # Financial details
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    total_commission = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    adjustments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Manual adjustments (refunds, bonuses, penalties)"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Final payout amount to vendor")

    # Status
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Payment details
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_reference = models.CharField(max_length=255, blank=True)
    payment_proof = models.FileField(upload_to="vendor_payouts/%Y/%m/", blank=True, null=True)

    # Metadata
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_payouts"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["period_start", "period_end"]),
        ]

    def __str__(self):
        return f"Payout {self.invoice_number} - {self.vendor.store_name} - ${self.amount}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    def generate_invoice_number(self):
        """Generate unique invoice number"""
        date_str = timezone.now().strftime("%Y%m%d")
        random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"VP-{date_str}-{random_str}"

    def mark_paid(self, transaction_ref="", payment_method="", proof=None):
        """Mark payout as paid"""
        self.status = "paid"
        self.paid_at = timezone.now()
        self.transaction_reference = transaction_ref
        self.payment_method = payment_method
        if proof:
            self.payment_proof = proof
        self.save()
        self.transactions.update(is_paid_out=True)


class VendorPayoutAdjustment(models.Model):
    """Track adjustments to vendor payouts"""

    payout = models.ForeignKey(VendorPayout, on_delete=models.CASCADE, related_name="adjustment_records")

    TYPE_CHOICES = (
        ("refund", "Refund"),
        ("return", "Return"),
        ("bonus", "Bonus"),
        ("penalty", "Penalty"),
        ("correction", "Correction"),
        ("other", "Other"),
    )
    adjustment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    reference = models.CharField(max_length=255, blank=True, help_text="Order ID or reference")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class VendorSettlementBatch(models.Model):
    """Batch processing for multiple vendor payouts"""

    batch_number = models.CharField(max_length=50, unique=True)

    period_start = models.DateField()
    period_end = models.DateField()

    total_vendors = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch {self.batch_number} - {self.total_vendors} vendors - ${self.total_amount}"

    def generate_payouts(self):
        """Generate individual payouts for all eligible vendors"""
        vendors_with_sales = VendorOrderTransaction.objects.filter(
            is_paid_out=False,
            status="completed",
            order__status__in=["delivered"],
            created_at__date__range=[self.period_start, self.period_end]
        ).values("vendor").annotate(
            total_sales=Sum("item_subtotal"),
            total_commission=Sum("commission_amount"),
            order_count=Count("order", distinct=True)
        )

        payouts_created = 0
        for vendor_data in vendors_with_sales:
            vendor = Vendor.objects.get(pk=vendor_data["vendor"])
            payout_amount = vendor_data["total_sales"] - vendor_data["total_commission"]

            if payout_amount > 0:
                payout = VendorPayout.objects.create(
                    vendor=vendor,
                    period_start=self.period_start,
                    period_end=self.period_end,
                    total_sales=vendor_data["total_sales"],
                    total_commission=vendor_data["total_commission"],
                    amount=payout_amount,
                    status="pending",
                    created_by=self.created_by
                )

                transactions = VendorOrderTransaction.objects.filter(
                    vendor=vendor,
                    is_paid_out=False,
                    status="completed",
                    created_at__date__range=[self.period_start, self.period_end]
                )
                transactions.update(payout=payout)

                payouts_created += 1

        self.total_vendors = payouts_created
        self.status = "processing"
        self.save()

        return payouts_created

