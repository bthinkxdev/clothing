from django.db import models

from .vendor import Vendor

__all__ = ["VendorStorePage"]


class VendorStorePage(models.Model):
    """Custom pages for vendor stores"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="store_pages")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280)
    content = models.TextField()

    is_active = models.BooleanField(default=True)
    show_in_menu = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["vendor", "slug"]]
        ordering = ["vendor", "order"]

