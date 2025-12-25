# app/models.py
import uuid
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


# -----------------------
# User
# -----------------------
class User(AbstractUser):
    """
    Custom user. Use this as AUTH_USER_MODEL.
    """
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_blocked = models.BooleanField(default=False)
    ROLE_CHOICES = (("customer", "Customer"), ("staff", "Staff"), ("admin", "Admin"))
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.email})"


# -----------------------
# Address & Shipping
# -----------------------
class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=64, blank=True, help_text="Home / Office / Parent's")
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.full_name}, {self.line1}, {self.city}"


# -----------------------
# Catalog: Category & Product
# -----------------------
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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # meta
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    # tags for filtering and searching
    tags = models.JSONField(default=list, blank=True)  # e.g. ["new", "best-seller"]

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
        """Return primary image preferring featured then order, using prefetched cache when available."""
        images_qs = self.images.all()
        if hasattr(self, "_prefetched_objects_cache") and "images" in self._prefetched_objects_cache:
            images_qs = self._prefetched_objects_cache["images"]
        return images_qs.order_by("-is_feature", "order", "id").first()

    def ordered_images(self):
        """Return ordered images without breaking existing prefetch caches."""
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


# -----------------------
# Product Variant & Inventory
# -----------------------
class ProductVariant(models.Model):
    """
    Represents a specific variant — size + color etc.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    size = models.CharField(max_length=32, blank=True, null=True)    # S, M, L, XL
    color = models.CharField(max_length=64, blank=True, null=True)
    material = models.CharField(max_length=120, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    mrp = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    # Example: control if variant is available for preorder
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
        """
        Reserve stock (for example when user reaches checkout). Returns True if successful.
        """
        if qty <= 0:
            return False
        if (self.quantity - self.reserved) >= qty:
            self.reserved = F("reserved") + qty
            self.save(update_fields=["reserved"])
            # refresh from db
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
        """
        Deduct stock permanently (when order confirmed).
        """
        if qty <= 0:
            return
        # use transaction to avoid races in concurrent orders
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


# -----------------------
# Cart & Wishlist
# -----------------------
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  # keep old carts for analytics
    # For guest carts you could add session_id field

    def __str__(self):
        return f"Cart #{self.pk} - {self.user}"

    def total(self) -> Decimal:
        items = self.items.select_related("variant")
        total = Decimal("0.00")
        for it in items:
            total += it.line_total()
        return total

    def item_count(self) -> int:
        # Return number of distinct line items, not total quantity
        return self.items.count()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("cart", "variant"),)

    def line_total(self):
        return self.variant.get_price() * Decimal(self.quantity)

    def __str__(self):
        return f"{self.variant} x {self.quantity}"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlists")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist {self.user}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("wishlist", "variant"),)


# -----------------------
# Coupons & Giftcards & Loyalty
# -----------------------
class Coupon(models.Model):
    CODE_TYPE = (("fixed", "Fixed"), ("percent", "Percentage"))
    code = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=255, blank=True)
    coupon_type = models.CharField(max_length=16, choices=CODE_TYPE, default="percent")
    value = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_usage = models.PositiveIntegerField(null=True, blank=True, help_text="Global usage limit")
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    applicable_products = models.ManyToManyField(Product, blank=True)
    applicable_categories = models.ManyToManyField(Category, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.coupon_type} {self.value})"

    def is_valid_for_user(self, user: settings.AUTH_USER_MODEL, order_amount: Decimal) -> bool:
        now = timezone.now()
        if not self.active or not (self.start_date <= now <= self.end_date):
            return False
        if order_amount < self.min_purchase_amount:
            return False
        # check global usage
        if self.max_usage is not None:
            used = self.usages.count()
            if used >= self.max_usage:
                return False
        # check per user usage
        if self.per_user_limit is not None:
            used_by_user = self.usages.filter(user=user).count()
            if used_by_user >= self.per_user_limit:
                return False
        return True

    def discount_amount(self, order_amount: Decimal) -> Decimal:
        if self.coupon_type == "fixed":
            return min(self.value, order_amount)
        else:
            return (order_amount * (self.value / Decimal("100.00"))).quantize(Decimal("0.01"))


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey("Order", on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)


class GiftCard(models.Model):
    code = models.CharField(max_length=64, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def redeem(self, amount: Decimal):
        if amount <= 0:
            raise ValueError("Invalid amount")
        if not self.active:
            raise ValueError("Inactive gift card")
        if self.expires_at and timezone.now() > self.expires_at:
            raise ValueError("Expired gift card")
        if amount > self.balance:
            raise ValueError("Insufficient gift card balance")
        self.balance = F("balance") - amount
        self.save(update_fields=["balance"])
        self.refresh_from_db()


class LoyaltyPoint(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty")
    points = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


# -----------------------
# Orders & Payments
# -----------------------
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
        # one place to compute tax, shipping and total - override in business logic
        self.total = (self.subtotal + self.shipping_amount + self.tax_amount - self.discount_amount).quantize(Decimal("0.01"))
        self.save(update_fields=["subtotal", "total", "updated_at"])

    def apply_coupon(self, coupon: Coupon):
        if coupon and coupon.is_valid_for_user(self.user, self.subtotal):
            self.coupon = coupon
            self.discount_amount = coupon.discount_amount(self.subtotal)
            # create usage record
            CouponUsage.objects.create(coupon=coupon, user=self.user, order=self)
            self.recalc_totals()
        else:
            raise ValueError("Coupon invalid")

    def mark_paid(self, payment):
        self.status = "paid"
        self.updated_at = timezone.now()
        self.save(update_fields=["status", "updated_at"])
        # call finalize: deduct stock
        self.finalize_order()

    def finalize_order(self):
        """
        Deduct inventory for each item (assumes items have been reserved earlier or stock is available)
        """
        for item in self.items.select_related("variant__inventory"):
            inv = getattr(item.variant, "inventory", None)
            if not inv:
                raise ValueError(f"No inventory for {item.variant}")
            inv.deduct(item.quantity)
        # other business logic: send email, reduce reserved, etc.


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("order", "variant"),)

    def line_total(self):
        return self.unit_price * Decimal(self.quantity)


class Payment(models.Model):
    """
    A record of payment attempt; supports multiple processors
    """
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
    reference = models.CharField(max_length=255, blank=True)  # external tx id
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_success(self, processor_response: dict = None):
        self.status = "success"
        if processor_response:
            self.processor_response = processor_response
        self.save(update_fields=["status", "processor_response", "updated_at"])
        # mark order paid if fully paid
        if self.order and Decimal(self.order.total) <= self.order.payments.filter(status="success").aggregate(total=models.Sum("amount"))["total"] or Decimal(self.amount) >= self.order.total:
            self.order.mark_paid(self)


# -----------------------
# Reviews & QnA
# -----------------------
class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# -----------------------
# Marketing Models
# -----------------------
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


# -----------------------
# Analytics & Admin helpers
# -----------------------
class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AbandonedCartSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="abandoned_carts")
    cart_snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)


# -----------------------
# Shipping Rates (simple)
# -----------------------
class ShippingZone(models.Model):
    name = models.CharField(max_length=120)
    countries = models.JSONField(default=list, blank=True)  # list of country codes or states
    base_rate = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return self.name


# -----------------------
# Misc helpers & signals (optional)
# -----------------------
# You can add django signals (in signals.py) to:
# - create Inventory when ProductVariant created
# - reserve inventory when cart goes to checkout
# - unreserve on cart abandonment / order cancel
#
# Example helper for automatic inventory creation (run in app.apps.py ready()):
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=ProductVariant)
def create_inventory_for_variant(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.create(variant=instance)


@receiver(post_save, sender=OrderItem)
def ensure_unit_price(sender, instance, created, **kwargs):
    # set unit price from variant if not set
    if created and (not instance.unit_price or instance.unit_price == 0):
        instance.unit_price = instance.variant.get_price()
        instance.save(update_fields=["unit_price"])

class DesignPattern(models.Model):
    """Model to store design pattern configurations"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Radius Scale (in pixels)
    radius_xxs = models.IntegerField(default=2, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_xs = models.IntegerField(default=4, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_sm = models.IntegerField(default=6, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_md = models.IntegerField(default=10, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_lg = models.IntegerField(default=14, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_xl = models.IntegerField(default=18, validators=[MinValueValidator(0), MaxValueValidator(50)])
    
    # Shadow configurations (stored as CSS values)
    shadow_sm = models.CharField(max_length=200, default='0 2px 6px rgba(0, 0, 0, 0.06)')
    shadow_md = models.CharField(max_length=200, default='0 6px 18px rgba(0, 0, 0, 0.08)')
    shadow_lg = models.CharField(max_length=200, default='0 10px 30px rgba(0, 0, 0, 0.12)')
    shadow_floating = models.CharField(max_length=200, default='0 20px 50px rgba(0, 0, 0, 0.12)')
    
    # Backdrop blur (in pixels)
    backdrop_blur = models.IntegerField(default=12, validators=[MinValueValidator(0), MaxValueValidator(50)])
    
    # Border configurations
    border_width = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(10)])
    border_opacity = models.FloatField(default=0.06, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    class Meta:
        ordering = ['-is_active', '-is_default', '-created_at']
        verbose_name = 'Design Pattern'
        verbose_name_plural = 'Design Patterns'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Ensure only one pattern is active at a time
        if self.is_active:
            DesignPattern.objects.filter(is_active=True).update(is_active=False)
        
        # Ensure only one pattern is default
        if self.is_default:
            DesignPattern.objects.filter(is_default=True).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def generate_css(self):
        """Generate CSS variables from the pattern"""
        return f"""
/* Design Pattern: {self.name} */
:root {{
    /* Radius scale */
    --radius-xxs: {self.radius_xxs}px;
    --radius-xs: {self.radius_xs}px;
    --radius-sm: {self.radius_sm}px;
    --radius-md: {self.radius_md}px;
    --radius-lg: {self.radius_lg}px;
    --radius-xl: {self.radius_xl}px;

    /* Shadows */
    --shadow-sm: {self.shadow_sm};
    --shadow-md: {self.shadow_md};
    --shadow-lg: {self.shadow_lg};
    --shadow-card: var(--shadow-md);
    --shadow-btn: var(--shadow-sm);
    --shadow-floating: {self.shadow_floating};

    /* Blur / glass */
    --backdrop-blur: {self.backdrop_blur}px;

    /* Borders */
    --border-soft: {self.border_width}px solid rgba(0, 0, 0, {self.border_opacity});
}}
"""

    @classmethod
    def get_active_pattern(cls):
        """Get the currently active design pattern"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            # Return default pattern or create one
            return cls.objects.filter(is_default=True).first() or cls.create_default_pattern()
    
    @classmethod
    def create_default_pattern(cls):
        """Create a default design pattern"""
        return cls.objects.create(
            name='Default Pattern',
            description='Default design pattern with standard values',
            is_default=True,
            is_active=True
        )
        

class SiteTheme(models.Model):
    """
    Store site-wide theme configuration
    """
    name = models.CharField(max_length=100, default="Default Theme")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    design_pattern = models.ForeignKey(DesignPattern, on_delete=models.SET_NULL, null=True, blank=True)
    # Brand Colors
    primary_color = models.CharField(max_length=7, default="#FF6B6B", help_text="Hex color code")
    primary_dark = models.CharField(max_length=7, default="#E85555")
    secondary_color = models.CharField(max_length=7, default="#FFA07A")
    accent_color = models.CharField(max_length=7, default="#FFD93D")
    
    # Text & Surfaces
    text_dark = models.CharField(max_length=7, default="#2D3142")
    text_light = models.CharField(max_length=7, default="#6C757D")
    bg_cream = models.CharField(max_length=7, default="#FFFFFF")
    border_color = models.CharField(max_length=7, default="#E8E8E8")
    
    # State Colors
    error_color = models.CharField(max_length=7, default="#FF5252")
    success_color = models.CharField(max_length=7, default="#4CAF50")
    warning_color = models.CharField(max_length=7, default="#FFB300")
    info_color = models.CharField(max_length=7, default="#00BCD4")
    
    # Additional Settings
    border_radius = models.CharField(max_length=10, default="8px")
    font_family = models.CharField(max_length=200, default="'Inter', sans-serif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-is_active", "-updated_at"]
    
    def __str__(self):
        return f"{self.name} {'(Active)' if self.is_active else ''}"
    
    def save(self, *args, **kwargs):
        # Ensure only one active theme
        if self.is_active:
            SiteTheme.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_theme(cls):
        """Get the currently active theme or create default"""
        theme = cls.objects.filter(is_active=True).first()
        if not theme:
            theme = cls.objects.create(name="Default Theme", is_active=True)
        return theme
    
    def to_css_vars(self):
        """Convert theme to CSS variables dictionary"""
        return {
            '--primary-color': self.primary_color,
            '--primary-dark': self.primary_dark,
            '--secondary-color': self.secondary_color,
            '--accent-color': self.accent_color,
            '--text-dark': self.text_dark,
            '--text-light': self.text_light,
            '--bg-cream': self.bg_cream,
            '--border-color': self.border_color,
            '--error-color': self.error_color,
            '--success-color': self.success_color,
            '--warning-color': self.warning_color,
            '--info-color': self.info_color,
        }