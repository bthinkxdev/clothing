from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils.text import slugify

from .vendor import Vendor

__all__ = ["Category", "Product", "ProductImage", "ProductVariant", "Inventory"]


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Product is the abstract product. Variants (different sizes/colors) are in ProductVariant.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    sku = models.CharField(max_length=64, blank=True, help_text="Base SKU (optional)")
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    brand = models.CharField(max_length=120, blank=True)

    # MULTI-VENDOR INTEGRATION
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True,
        help_text="Vendor who owns this product"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # meta
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    tags = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    def main_variant(self):
        return self.variants.first()

    def avg_rating(self):
        agg = self.reviews.aggregate(avg=models.Avg("rating"))
        return agg["avg"] or 0

    def primary_image(self):
        """Return primary image preferring featured then order"""
        images_qs = self.images.all()
        if hasattr(self, "_prefetched_objects_cache") and "images" in self._prefetched_objects_cache:
            images_qs = self._prefetched_objects_cache["images"]
        return images_qs.order_by("-is_feature", "order", "id").first()

    def ordered_images(self):
        """Return ordered images without breaking existing prefetch caches"""
        images_qs = self.images.all()
        if hasattr(self, "_prefetched_objects_cache") and "images" in self._prefetched_objects_cache:
            images_qs = self._prefetched_objects_cache["images"]
        return images_qs.order_by("-is_feature", "order", "id")


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_feature = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class ProductVariant(models.Model):
    """
    Represents a specific variant — size + color etc.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    size = models.CharField(max_length=32, blank=True, null=True)
    color = models.CharField(max_length=64, blank=True, null=True)
    material = models.CharField(max_length=120, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    mrp = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    is_active = models.BooleanField(default=True)
    is_preorder = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("product", "size", "color"),)

    def __str__(self):
        return f"{self.product.name} - {self.sku} ({self.size or 'NA'}/{self.color or 'NA'})"

    @property
    def discounted_price(self) -> Decimal:
        if self.discount_percent:
            return (self.price * (Decimal(100) - Decimal(self.discount_percent))) / Decimal(100)
        return self.price

    def get_price(self) -> Decimal:
        return self.discounted_price

    def available_stock(self) -> int:
        inv = getattr(self, "inventory", None)
        if inv:
            return inv.quantity
        return 0


class Inventory(models.Model):
    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.IntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    reserved = models.IntegerField(default=0, help_text="Reserved by unpaid carts / orders in process")

    def __str__(self):
        return f"{self.variant.sku} - {self.quantity} in stock"

    def is_low(self) -> bool:
        return self.quantity - self.reserved <= self.low_stock_threshold

    def reserve(self, qty: int) -> bool:
        if qty <= 0:
            return False
        if (self.quantity - self.reserved) >= qty:
            self.reserved = F("reserved") + qty
            self.save(update_fields=["reserved"])
            self.refresh_from_db()
            return True
        return False

    def unreserve(self, qty: int):
        if qty <= 0:
            return
        self.reserved = F("reserved") - qty
        self.save(update_fields=["reserved"])
        self.refresh_from_db()

    def deduct(self, qty: int):
        if qty <= 0:
            return
        with transaction.atomic():
            self.refresh_from_db()
            if self.quantity >= qty and self.reserved >= qty:
                self.quantity = F("quantity") - qty
                self.reserved = F("reserved") - qty
                self.save(update_fields=["quantity", "reserved"])
            elif self.quantity >= qty:
                self.quantity = F("quantity") - qty
                self.save(update_fields=["quantity"])
            else:
                raise ValueError("Insufficient stock")
        self.refresh_from_db()

