from decimal import Decimal
from django.db import models

from .catalog import Product
from .vendor import Vendor

__all__ = ["VendorAnalyticsSnapshot", "VendorProductPerformance"]


class VendorAnalyticsSnapshot(models.Model):
    """Daily/Weekly/Monthly analytics snapshots"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="analytics_snapshots")

    PERIOD_TYPE_CHOICES = (
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    )
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES)
    period_date = models.DateField(db_index=True)

    orders_count = models.PositiveIntegerField(default=0)
    sales_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))

    products_sold = models.PositiveIntegerField(default=0)
    products_views = models.PositiveIntegerField(default=0)

    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)

    average_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["vendor", "period_type", "period_date"]]
        ordering = ["-period_date"]
        indexes = [
            models.Index(fields=["vendor", "period_type", "period_date"]),
        ]

    def __str__(self):
        return f"{self.vendor.store_name} - {self.period_type} - {self.period_date}"


class VendorProductPerformance(models.Model):
    """Track performance metrics for vendor products"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="product_performance")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="performance_metrics")

    period_start = models.DateField()
    period_end = models.DateField()

    views = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    add_to_cart = models.PositiveIntegerField(default=0)
    purchases = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    return_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["vendor", "product", "period_start", "period_end"]]
        ordering = ["-period_start", "-revenue"]

