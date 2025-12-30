from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .catalog import ProductVariant, Inventory
from .order import OrderItem, Order
from .review import Review
from .vendor import Vendor
from .payouts import VendorOrderTransaction
from .notifications import VendorNotification


@receiver(post_save, sender=ProductVariant)
def create_inventory_for_variant(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.create(variant=instance)


@receiver(post_save, sender=OrderItem)
def ensure_unit_price(sender, instance, created, **kwargs):
    if created and (not instance.unit_price or instance.unit_price == 0):
        instance.unit_price = instance.variant.get_price()
        instance.save(update_fields=["unit_price"])


@receiver(post_save, sender=Vendor)
def create_vendor_resources(sender, instance, created, **kwargs):
    """Create related resources when vendor is created"""
    if created and instance.user.role != "vendor":
        instance.user.role = "vendor"
        instance.user.save(update_fields=["role"])


@receiver(post_save, sender=Order)
def create_vendor_transactions(sender, instance, created, **kwargs):
    """Create vendor transactions when order is placed"""
    if instance.status in ["paid", "processing"]:
        for item in instance.items.select_related("variant__product__vendor").all():
            vendor = item.variant.product.vendor
            if vendor and not hasattr(item, "vendor_transaction"):
                VendorOrderTransaction.objects.get_or_create(
                    vendor=vendor,
                    order=instance,
                    order_item=item,
                    defaults={
                        "item_subtotal": item.line_total(),
                        "commission_rate": vendor.commission_value,
                        "status": "processing",
                    },
                )


@receiver(post_save, sender=OrderItem)
def notify_vendor_new_order(sender, instance, created, **kwargs):
    """Notify vendor when they receive a new order"""
    if created and instance.variant.product.vendor:
        vendor = instance.variant.product.vendor
        VendorNotification.objects.create(
            vendor=vendor,
            notification_type="new_order",
            title=f"New Order #{instance.order.id}",
            message=f"You have received a new order for {instance.variant.product.name}",
            link=f"/vendor/orders/{instance.order.id}/",
        )


@receiver(post_save, sender=Review)
def update_vendor_rating(sender, instance, created, **kwargs):
    """Update vendor average rating when product review is added"""
    if created and hasattr(instance.product, "vendor") and instance.product.vendor:
        vendor = instance.product.vendor
        vendor.update_analytics()

        VendorNotification.objects.create(
            vendor=vendor,
            notification_type="new_review",
            title="New Product Review",
            message=f'Your product "{instance.product.name}" received a {instance.rating}-star review',
            link="/vendor/reviews/",
        )


@receiver(post_save, sender=Inventory)
def check_low_stock_alert(sender, instance, **kwargs):
    """Alert vendor when stock is low"""
    if instance.is_low() and hasattr(instance.variant.product, "vendor"):
        vendor = instance.variant.product.vendor
        if vendor:
            recent_alert = VendorNotification.objects.filter(
                vendor=vendor,
                notification_type="low_stock",
                created_at__gte=timezone.now() - timezone.timedelta(days=1),
                message__contains=instance.variant.sku,
            ).exists()

            if not recent_alert:
                VendorNotification.objects.create(
                    vendor=vendor,
                    notification_type="low_stock",
                    title="Low Stock Alert",
                    message=f"Stock is low for {instance.variant.product.name} ({instance.variant.sku}). Current: {instance.quantity}",
                    link="/vendor/inventory/",
                )

