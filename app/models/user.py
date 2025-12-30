from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

__all__ = ["User"]


class User(AbstractUser):
    """
    Custom user. Use this as AUTH_USER_MODEL.
    """

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_blocked = models.BooleanField(default=False)
    ROLE_CHOICES = (("customer", "Customer"), ("staff", "Staff"), ("admin", "Admin"), ("vendor", "Vendor"))
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.email})"

