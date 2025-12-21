# chatbot/advanced_features.py
# Optional advanced features for the chatbot

from django.core.cache import cache
from django.db.models import Q
from app.models import Cart, CartItem, ProductVariant
from decimal import Decimal


class CartAssistantHandler:
    """Handle cart operations through chatbot"""
    
    def add_to_cart(self, user, product_slug: str, size: str = None, color: str = None, quantity: int = 1):
        """Add product to cart via chatbot"""
        if not user or not user.is_authenticated:
            return {
                'reply': "Please log in to add items to your cart.",
                'suggestions': ['Log in', 'Browse products']
            }
        
        try:
            # Find variant
            query = Q(product__slug=product_slug, is_active=True)
            if size:
                query &= Q(size__iexact=size)
            if color:
                query &= Q(color__icontains=color)
            
            variant = ProductVariant.objects.select_related('product', 'inventory').filter(query).first()
            
            if not variant:
                return {
                    'reply': f"Sorry, I couldn't find that product variant. Please check the size or color.",
                    'suggestions': ['View product page', 'Try different size']
                }
            
            # Check stock
            inv = getattr(variant, 'inventory', None)
            if inv and inv.quantity < quantity:
                return {
                    'reply': f"Sorry, only {inv.quantity} items available in stock.",
                    'suggestions': ['Notify when available', 'View similar products']
                }
            
            # Get or create cart
            cart, created = Cart.objects.get_or_create(user=user, is_active=True)
            
            # Add or update cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            return {
                'reply': f"✅ Added {variant.product.name} ({variant.size}/{variant.color}) to your cart!\n\nCart total: ₹{cart.total()}",
                'suggestions': ['View cart', 'Proceed to checkout', 'Continue shopping']
            }
            
        except Exception as e:
            return {
                'reply': "Sorry, I couldn't add that to your cart. Please try again.",
                'suggestions': ['View cart', 'Browse products']
            }
    
    def view_cart(self, user):
        """Show cart contents"""
        if not user or not user.is_authenticated:
            return {
                'reply': "Please log in to view your cart.",
                'suggestions': ['Log in', 'Browse products']
            }
        
        cart = Cart.objects.filter(user=user, is_active=True).first()
        
        if not cart or not cart.items.exists():
            return {
                'reply': "Your cart is empty. Let me help you find some products!",
                'suggestions': ['Browse products', 'New arrivals', 'Best sellers']
            }
        
        items = cart.items.select_related('variant__product').all()
        
        reply = f"🛒 **Your Cart** ({cart.item_count()} items)\n\n"
        
        for item in items:
            reply += f"• {item.variant.product.name} ({item.variant.size}/{item.variant.color})\n"
            reply += f"  Qty: {item.quantity} × ₹{item.variant.get_price()} = ₹{item.line_total()}\n\n"
        
        reply += f"**Total: ₹{cart.total()}**"
        
        return {
            'reply': reply,
            'suggestions': ['Proceed to checkout', 'Continue shopping', 'Clear cart']
        }


class SmartSearchHandler:
    """Enhanced semantic search with caching"""
    
    def search(self, query: str, filters: dict = None):
        """Cached smart search"""
        cache_key = f"chatbot_search:{query}:{str(filters)}"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        # Perform search (reuse ProductSearchHandler logic)
        from .services import ProductSearchHandler
        handler = ProductSearchHandler()
        result = handler.handle(query, {}, filters)
        
        # Cache for 5 minutes
        cache.set(cache_key, result, 300)
        
        return result


class RateLimitMiddleware:
    """Rate limit chatbot requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path.startswith('/chatbot/'):
            # Get client IP
            ip = self.get_client_ip(request)
            
            # Rate limit: 30 requests per minute
            cache_key = f"chatbot_ratelimit:{ip}"
            requests = cache.get(cache_key, 0)
            
            if requests >= 30:
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'Too many requests. Please wait a moment.'
                }, status=429)
            
            cache.set(cache_key, requests + 1, 60)
        
        return self.get_response(request)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AnalyticsTracker:
    """Track chatbot usage for analytics"""
    
    @staticmethod
    def track_intent(session_id: str, intent: str, success: bool):
        """Track intent success rate"""
        cache_key = f"chatbot_analytics:intent:{intent}"
        stats = cache.get(cache_key, {'total': 0, 'success': 0})
        
        stats['total'] += 1
        if success:
            stats['success'] += 1
        
        cache.set(cache_key, stats, 3600 * 24)  # 24 hours
    
    @staticmethod
    def get_popular_queries():
        """Get most common queries"""
        from .models import ChatMessage
        from django.db.models import Count
        
        return ChatMessage.objects.filter(
            message_type='user'
        ).values('intent').annotate(
            count=Count('id')
        ).order_by('-count')[:10]


class NotificationHandler:
    """Handle chatbot notifications"""
    
    @staticmethod
    def send_order_update(user, order_id: str, status: str):
        """Send order update notification via chatbot"""
        # This would integrate with your notification system
        # For now, we'll increment unread badge
        pass
    
    @staticmethod
    def send_stock_alert(user, product_name: str):
        """Notify when product back in stock"""
        pass


# WebSocket support for real-time chat (optional)
class ChatbotConsumer:
    """
    WebSocket consumer for real-time chat
    Requires channels library
    
    Install: pip install channels channels-redis
    
    # routing.py
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from django.urls import path
    
    application = ProtocolTypeRouter({
        'websocket': AuthMiddlewareStack(
            URLRouter([
                path('ws/chatbot/', ChatbotConsumer.as_asgi()),
            ])
        ),
    })
    """
    
    async def connect(self):
        await self.accept()
    
    async def receive(self, text_data):
        # Process message through ChatbotService
        # Send response back
        pass
    
    async def disconnect(self, close_code):
        pass