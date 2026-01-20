# app/utils.py
import random
import razorpay
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db.models import F
from django.template.loader import render_to_string
from .models import Cart, Wishlist


def send_otp(phone_number):
    """
    Generate and send OTP to phone number.
    In production, integrate with SMS gateway like Twilio, MSG91, etc.
    """
    otp = str(random.randint(100000, 999999))
    otp = '123456'
    # TODO: Send via SMS gateway
    print(f"OTP for {phone_number}: {otp}")  # For development
    
    return otp


def verify_otp(phone_number, otp):
    """
    Verify OTP - in production, check against SMS gateway or database
    """
    # This is handled in the view using session
    pass


def get_cart_or_create(request):
    """
    Get or create cart for authenticated user
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True
        )
        return cart
    return None


def get_wishlist_or_create(request):
    """
    Get or create wishlist for authenticated user
    """
    if request.user.is_authenticated:
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        return wishlist
    return None


def calculate_shipping(cart, address=None):
    """
    Calculate shipping charges based on cart value and address
    """
    subtotal = cart.total()
    
    # Free shipping above 1000
    if subtotal >= Decimal('1000.00'):
        return Decimal('0.00')
    
    # Base shipping
    return Decimal('50.00')


def calculate_tax(cart):
    """
    Calculate tax (GST) - 18% for example
    """
    subtotal = cart.total()
    tax_rate = Decimal('0.18')  # 18%
    return (subtotal * tax_rate).quantize(Decimal('0.01'))


def check_pincode_serviceability(pincode, service_type='standard'):
    """
    Check if delivery is available for pincode.
    Returns True/False.
    """
    # TODO: Integrate with courier API
    # For now, assume all pincodes are serviceable except where explicitly restricted
    serviceable_pincodes = getattr(settings, "SERVICEABLE_PINCODES", [])

    if service_type == "cod":
        cod_pincodes = getattr(settings, "COD_SERVICEABLE_PINCODES", [])
        if not cod_pincodes:
            return True
        return pincode in cod_pincodes

    if not serviceable_pincodes:
        return True

    return pincode in serviceable_pincodes


def is_razorpay_configured():
    """
    Return True if Razorpay credentials are not the default placeholders.
    """
    key = getattr(settings, "RAZORPAY_KEY_ID", "")
    secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    invalid_placeholders = {"", None, "your_key_id", "your_key_secret"}
    return key not in invalid_placeholders and secret not in invalid_placeholders


def get_razorpay_client():
    """
    Initialize and return Razorpay client
    """
    if not is_razorpay_configured():
        raise ImproperlyConfigured("Razorpay API credentials are missing or still use placeholders.")
    client = razorpay.Client(auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    ))
    return client


def generate_order_id():
    """
    Generate unique order ID
    """
    import uuid
    return str(uuid.uuid4())


def send_order_confirmation_email(order):
    """
    Send order confirmation email to customer
    """
    subject = f'Order Confirmation - {order.id}'
    context = {
        'order': order,
        'order_items': order.items.select_related('variant__product').all(),
        'user': order.user,
    }
    
    html_message = render_to_string('emails/order_confirmation.html', context)
    plain_message = render_to_string('emails/order_confirmation.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_order_shipped_email(order):
    """
    Send shipping notification email
    """
    subject = f'Your Order {order.id} has been shipped'
    context = {
        'order': order,
        'tracking_number': order.tracking_number,
        'courier': order.courier,
    }
    
    html_message = render_to_string('emails/order_shipped.html', context)
    
    send_mail(
        subject=subject,
        message=f'Your order has been shipped. Tracking: {order.tracking_number}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_abandoned_cart_email(user, cart):
    """
    Send abandoned cart reminder email
    """
    subject = 'Complete your purchase'
    context = {
        'user': user,
        'cart': cart,
        'cart_items': cart.items.select_related('variant__product')[:5],
    }
    
    html_message = render_to_string('emails/abandoned_cart.html', context)
    
    send_mail(
        subject=subject,
        message='You have items in your cart waiting for you!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True,
    )


def get_similar_products(product, limit=8):
    """
    Get similar products based on category and tags
    """
    from .models import Product
    
    similar = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)
    
    # Boost products with similar tags
    if product.tags:
        similar = similar.filter(tags__overlap=product.tags)
    
    return similar.prefetch_related('variants', 'images')[:limit]


def get_recommended_products(user=None, limit=12):
    """
    Get personalized product recommendations
    """
    from .models import Product, ProductViewLog, OrderItem
    
    if user and user.is_authenticated:
        # Get user's order history
        purchased_products = OrderItem.objects.filter(
            order__user=user
        ).values_list('variant__product_id', flat=True).distinct()
        
        # Get viewed products
        viewed_products = ProductViewLog.objects.filter(
            user=user
        ).values_list('product_id', flat=True).distinct()[:20]
        
        # Recommend similar products
        recommendations = Product.objects.filter(
            is_active=True
        ).exclude(id__in=purchased_products)
        
        if viewed_products:
            # Get categories from viewed products
            viewed_categories = Product.objects.filter(
                id__in=viewed_products
            ).values_list('category_id', flat=True).distinct()
            
            recommendations = recommendations.filter(
                category_id__in=viewed_categories
            )
        
        return recommendations.prefetch_related('variants', 'images')[:limit]
    
    # Default: Return trending/popular products
    return Product.objects.filter(
        is_active=True,
        tags__contains=['trending']
    ).prefetch_related('variants', 'images')[:limit]


def merge_guest_cart_to_user(session_cart_data, user):
    """
    Merge guest cart items to user cart after login
    """
    user_cart, _ = Cart.objects.get_or_create(user=user, is_active=True)
    
    # Logic to merge session cart items into user cart
    # Implementation depends on how guest cart is stored
    pass


def check_low_stock_alerts():
    """
    Check for low stock items and send alerts to admin
    Intended to be run as a periodic task (Celery)
    """
    from .models import Inventory
    
    low_stock_items = Inventory.objects.filter(
        quantity__lte=F('low_stock_threshold')
    ).select_related('variant__product')
    
    if low_stock_items.exists():
        # Send email to admin
        subject = 'Low Stock Alert'
        message = f'{low_stock_items.count()} items are running low on stock'
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )


def process_abandoned_carts():
    """
    Find abandoned carts and send reminder emails
    Intended to be run as a periodic task (Celery)
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Cart, AbandonedCartSnapshot
    
    # Find carts inactive for 24 hours
    threshold = timezone.now() - timedelta(hours=24)
    
    abandoned_carts = Cart.objects.filter(
        is_active=True,
        updated_at__lte=threshold,
        items__isnull=False
    ).distinct()
    
    for cart in abandoned_carts:
        # Check if already notified
        already_notified = AbandonedCartSnapshot.objects.filter(
            user=cart.user,
            created_at__gte=threshold,
            notified=True
        ).exists()
        
        if not already_notified:
            # Send email
            send_abandoned_cart_email(cart.user, cart)
            
            # Create snapshot
            AbandonedCartSnapshot.objects.create(
                user=cart.user,
                cart_snapshot={'items': list(cart.items.values())},
                notified=True
            )