from django.conf import settings
from django.db import models

from .order import Order
from .vendor import Vendor

__all__ = ["VendorNotification", "VendorMessage"]


class VendorNotification(models.Model):
    """Notification system for vendors"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="notifications")

    TYPE_CHOICES = (
        ("new_order", "New Order"),
        ("order_cancelled", "Order Cancelled"),
        ("payment_received", "Payment Received"),
        ("payout_processed", "Payout Processed"),
        ("low_stock", "Low Stock Alert"),
        ("new_review", "New Review"),
        ("account_status", "Account Status Change"),
        ("document_required", "Document Required"),
        ("system", "System Notification"),
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=512, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vendor", "is_read"]),
        ]


class VendorMessage(models.Model):
    """Messages between admin/customers and vendors"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="messages")

    SENDER_TYPE_CHOICES = (
        ("admin", "Admin"),
        ("customer", "Customer"),
        ("vendor", "Vendor"),
        ("system", "System"),
    )
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)

    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.vendor.store_name}"

