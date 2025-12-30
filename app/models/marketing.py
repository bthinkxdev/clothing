from django.conf import settings
from django.db import models

from .vendor import Vendor

__all__ = ["Banner", "NewsletterSubscriber", "Referral", "VendorBanner"]


class Banner(models.Model):
    title = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="banners/%Y/%m/")
    url = models.CharField(max_length=512, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)


class Referral(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals")
    code = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    usage_count = models.PositiveIntegerField(default=0)


class VendorBanner(models.Model):
    """Vendor-specific banners for their store"""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="banners")
    title = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="vendors/banners/%Y/%m/")
    url = models.CharField(max_length=512, blank=True, help_text="Link destination")

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["vendor", "order"]

    def __str__(self):
        return f"{self.vendor.store_name} - {self.title or 'Banner'}"

