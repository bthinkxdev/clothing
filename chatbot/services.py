# chatbot/services.py
import re
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db.models import Q, Prefetch
from django.core.exceptions import ValidationError
from app.models import (
    Product, ProductVariant, Order, Category, 
    Inventory, Cart, CartItem
)


class IntentParser:
    """Detect user intent from message"""
    
    INTENT_PATTERNS = {
        'track_order': [
            r'track.*order',
            r'where.*order',
            r'order.*status',
            r'my.*order',
            r'order\s*#?\s*([a-zA-Z0-9\-]+)',
        ],
        'find_product': [
            r'show.*products?',
            r'find.*products?',
            r'looking.*for',
            r'want.*to.*buy',
            r'search.*for',
        ],
        'find_by_size': [
            r'size\s+(xs|s|m|l|xl|xxl|xxxl)',
            r'do.*you.*have.*size',
            r'available.*in.*size',
        ],
        'find_by_color': [
            r'color\s+(\w+)',
            r'available.*in.*(\w+)',
            r'do.*you.*have.*in.*(\w+)',
            r'(\w+)\s+color',
        ],
        'price_check': [
            r'price.*of',
            r'how.*much',
            r'cost.*of',
            r'under.*₹?(\d+)',
            r'below.*₹?(\d+)',
        ],
        'size_recommendation': [
            r'what.*size.*should',
            r'recommend.*size',
            r'size.*recommendation',
            r'which.*size.*fit',
        ],
        'add_to_cart': [
            r'add.*to.*cart',
            r'add.*this',
            r'buy.*this',
        ],
        'cart_help': [
            r'my.*cart',
            r'shopping.*cart',
            r'view.*cart',
        ],
        'shipping_info': [
            r'shipping.*policy',
            r'delivery.*time',
            r'when.*will.*arrive',
            r'shipping.*cost',
        ],
        'return_policy': [
            r'return.*policy',
            r'can.*i.*return',
            r'refund',
        ],
        'payment_help': [
            r'payment.*method',
            r'how.*to.*pay',
            r'cod.*available',
            r'cash.*on.*delivery',
        ],
    }
    
    def parse(self, message: str) -> Tuple[str, Dict]:
        """Returns (intent, extracted_data)"""
        msg_lower = message.lower().strip()
        
        # Check each intent pattern
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    extracted = {}
                    if match.groups():
                        extracted['matched'] = match.groups()
                    return intent, extracted
        
        return 'general', {}


class OrderTrackingHandler:
    """Handle order tracking queries"""
    
    def handle(self, user, message: str, extracted_data: Dict) -> Dict:
        # Extract order ID from message
        order_id_match = re.search(r'[a-f0-9\-]{36}|#?\s*([A-Z0-9\-]+)', message)
        
        if order_id_match:
            order_id = order_id_match.group(0).replace('#', '').strip()
            try:
                # Validate UUID format if full ID provided
                if len(order_id) > 8:
                    try:
                        uuid_obj = uuid.UUID(order_id)
                        order_id = str(uuid_obj)
                    except ValueError:
                        # If not a valid UUID, don't try to query
                        pass

                order = Order.objects.select_related('address').prefetch_related('items__variant__product').get(
                    Q(id=order_id) | Q(id__startswith=order_id[:8])
                )
                
                if user and order.user != user:
                    return self._error_response("Order not found or unauthorized")
                
                return self._format_order_response(order)
            except (Order.DoesNotExist, ValidationError):
                pass
        
        # Show recent orders
        if user and user.is_authenticated:
            recent_orders = Order.objects.filter(user=user).order_by('-placed_at')[:3]
            if recent_orders.exists():
                return {
                    'reply': "Here are your recent orders. Click to view details:",
                    'orders': [self._format_order_summary(o) for o in recent_orders],
                    'suggestions': ['Track another order', 'Browse products']
                }
        
        return {
            'reply': "Please provide your order ID to track. You can find it in your order confirmation email.",
            'suggestions': ['View my orders', 'Browse products']
        }
    
    def _format_order_response(self, order: Order) -> Dict:
        items_summary = []
        for item in order.items.all()[:3]:
            items_summary.append({
                'name': item.variant.product.name,
                'quantity': item.quantity,
                'price': str(item.unit_price)
            })
        
        status_messages = {
            'pending': '⏳ Your order is pending payment confirmation.',
            'paid': '✅ Payment confirmed! We are preparing your order.',
            'processing': '📦 Your order is being processed.',
            'shipped': '🚚 Your order has been shipped!',
            'delivered': '🎉 Your order has been delivered!',
            'cancelled': '❌ This order has been cancelled.',
            'refunded': '💰 This order has been refunded.',
        }
        
        response = {
            'reply': f"**Order #{str(order.id)[:8].upper()}**\n\n{status_messages.get(order.status, 'Order found')}\n\n",
            'order_details': {
                'id': str(order.id),
                'status': order.status,
                'placed_at': order.placed_at.strftime('%B %d, %Y'),
                'total': str(order.total),
                'items': items_summary,
                'tracking_number': order.tracking_number,
                'courier': order.courier,
                'expected_delivery': order.expected_delivery.strftime('%B %d, %Y') if order.expected_delivery else None,
            },
            'suggestions': ['Track another order', 'Contact support', 'Browse products']
        }
        
        if order.tracking_number:
            response['reply'] += f"\n📍 Tracking: {order.tracking_number}"
            if order.courier:
                response['reply'] += f" ({order.courier})"
        
        if order.expected_delivery:
            response['reply'] += f"\n📅 Expected delivery: {order.expected_delivery.strftime('%B %d, %Y')}"
        
        return response
    
    def _format_order_summary(self, order: Order) -> Dict:
        return {
            'id': str(order.id)[:8].upper(),
            'status': order.status,
            'total': str(order.total),
            'date': order.placed_at.strftime('%b %d, %Y')
        }
    
    def _error_response(self, message: str) -> Dict:
        return {
            'reply': message,
            'suggestions': ['View my orders', 'Browse products']
        }


class ProductSearchHandler:
    """Handle product search and filtering"""
    
    def handle(self, message: str, extracted_data: Dict, filters: Dict = None) -> Dict:
        filters = filters or {}
        
        # Build query
        query = Q(is_active=True)
        
        # Extract search terms
        search_terms = self._extract_search_terms(message)
        
        if search_terms:
            # Search in name, description, tags
            for term in search_terms:
                query &= (
                    Q(name__icontains=term) |
                    Q(short_description__icontains=term) |
                    Q(description__icontains=term) |
                    Q(category__name__icontains=term) |
                    Q(brand__icontains=term) |
                    Q(tags__icontains=term)
                )
        
        # Size filter
        if 'size' in filters:
            query &= Q(variants__size__iexact=filters['size'])
        
        # Color filter
        if 'color' in filters:
            query &= Q(variants__color__icontains=filters['color'])
        
        # Price filter
        if 'max_price' in filters:
            query &= Q(variants__price__lte=filters['max_price'])
        
        # Category filter
        if 'category' in filters:
            query &= Q(category__slug=filters['category'])
        
        products = Product.objects.filter(query).select_related('category').prefetch_related(
            Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True).select_related('inventory')),
            'images'
        ).distinct()[:8]
        
        if not products.exists():
            return {
                'reply': "Sorry, I couldn't find any products matching your criteria. Try different keywords or filters.",
                'suggestions': ['View all products', 'Browse categories', 'New arrivals']
            }
        
        return {
            'reply': f"I found {products.count()} product(s) for you:",
            'products': [self._format_product(p) for p in products],
            'suggestions': ['Filter by size', 'Filter by price', 'View cart']
        }
    
    def _extract_search_terms(self, message: str) -> List[str]:
        # Remove common words
        stop_words = {
            'show', 'me', 'find', 'looking', 'for', 'want', 'to', 'buy', 
            'a', 'an', 'the', 'in', 'do', 'you', 'have', 'are', 'is',
            'size', 'color', 'price', 'cost', 'much', 'under', 'below', 'max', 'min'
        }
        words = message.lower().split()
        return [w for w in words if w not in stop_words and len(w) > 2]
    
    def _format_product(self, product: Product) -> Dict:
        variant = product.variants.first()
        image = product.images.first()
        
        price = str(variant.get_price()) if variant else "N/A"
        mrp = str(variant.mrp) if variant and variant.mrp > variant.price else None
        
        stock_status = "In Stock"
        if variant:
            inv = getattr(variant, 'inventory', None)
            if inv:
                if inv.quantity <= 0:
                    stock_status = "Out of Stock"
                elif inv.is_low():
                    stock_status = f"Only {inv.quantity} left!"
        
        return {
            'name': product.name,
            'slug': product.slug,
            'price': price,
            'mrp': mrp,
            'image': image.image.url if image else None,
            'rating': round(product.avg_rating(), 1),
            'stock_status': stock_status,
            'short_description': product.short_description[:100] if product.short_description else ''
        }


class SizeRecommendationHandler:
    """Handle size recommendation based on user measurements"""
    
    def __init__(self):
        self.state = {}
    
    def handle(self, session_id: str, message: str, state: Dict = None) -> Dict:
        state = state or {}
        
        # Extract measurements from message
        height_match = re.search(r'(\d+)\s*(cm|ft|feet|inches?|in|\')', message.lower())
        weight_match = re.search(r'(\d+)\s*(kg|lbs?|pounds?)', message.lower())
        
        if height_match:
            state['height'] = height_match.group(1)
            state['height_unit'] = height_match.group(2)
        
        if weight_match:
            state['weight'] = weight_match.group(1)
            state['weight_unit'] = weight_match.group(2)
        
        # Check for fit preference
        if any(word in message.lower() for word in ['slim', 'tight', 'fitted']):
            state['fit'] = 'slim'
        elif any(word in message.lower() for word in ['regular', 'normal', 'standard']):
            state['fit'] = 'regular'
        elif any(word in message.lower() for word in ['loose', 'relaxed', 'comfort']):
            state['fit'] = 'loose'
        
        # Check if we have enough info
        if 'height' in state and 'weight' in state:
            size = self._calculate_size(state)
            return {
                'reply': f"Based on your measurements, I recommend size **{size}**. This is a general recommendation. Fit may vary by product.",
                'recommended_size': size,
                'state': state,
                'suggestions': [f'Show {size} products', 'Try different size', 'View size chart']
            }
        
        # Ask for missing info
        if 'height' not in state:
            return {
                'reply': "To recommend the right size, I need your height. Please tell me your height (e.g., '170 cm' or '5 ft 7 in').",
                'state': state,
                'suggestions': []
            }
        
        if 'weight' not in state:
            return {
                'reply': "Thanks! Now, what's your weight? (e.g., '70 kg' or '150 lbs')",
                'state': state,
                'suggestions': []
            }
        
        return {
            'reply': "I need a bit more information. What's your height and weight?",
            'state': state,
            'suggestions': []
        }
    
    def _calculate_size(self, state: Dict) -> str:
        """Simple size calculation logic"""
        try:
            height = int(state['height'])
            weight = int(state['weight'])
            
            # Convert to metric if needed
            if state.get('height_unit') in ['ft', 'feet', 'inches', 'in', "'"]:
                height = height * 30.48  # rough conversion
            
            if state.get('weight_unit') in ['lbs', 'pounds']:
                weight = weight * 0.453592
            
            # Simple BMI-based logic
            height_m = height / 100
            bmi = weight / (height_m ** 2)
            
            fit = state.get('fit', 'regular')
            
            # Size mapping
            if bmi < 18.5:
                base_size = 'S'
            elif bmi < 25:
                base_size = 'M'
            elif bmi < 30:
                base_size = 'L'
            else:
                base_size = 'XL'
            
            # Adjust for fit preference
            if fit == 'slim' and base_size != 'S':
                size_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
                idx = size_order.index(base_size)
                return size_order[max(0, idx - 1)]
            elif fit == 'loose' and base_size != 'XXL':
                size_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
                idx = size_order.index(base_size)
                return size_order[min(len(size_order) - 1, idx + 1)]
            
            return base_size
        except:
            return 'M'


class FallbackHandler:
    """Handle unrecognized intents"""
    
    FAQ_RESPONSES = {
        'shipping': "We offer standard shipping (5-7 days) and express shipping (2-3 days). Free shipping on orders above ₹999. Shipping costs are calculated at checkout based on your location.",
        'return': "We accept returns within 30 days of delivery. Items must be unused with original tags. Refunds are processed within 7-10 business days after we receive the returned item.",
        'payment': "We accept Credit/Debit Cards, UPI, Net Banking, and Cash on Delivery. All transactions are secure and encrypted.",
        'cod': "Yes, Cash on Delivery (COD) is available for orders. COD charges may apply depending on your location and order value.",
        'delivery': "Standard delivery takes 5-7 business days. Express delivery takes 2-3 business days. Delivery times may vary based on your location.",
    }
    
    def handle(self, message: str) -> Dict:
        msg_lower = message.lower()
        
        # Check for FAQ keywords
        for key, response in self.FAQ_RESPONSES.items():
            if key in msg_lower:
                return {
                    'reply': response,
                    'suggestions': ['Track order', 'Browse products', 'Talk to human']
                }
        
        return {
            'reply': "I'm here to help! I can assist you with:\n\n• Tracking orders\n• Finding products\n• Size recommendations\n• Shipping & returns\n• And more!\n\nWhat would you like help with?",
            'suggestions': ['Track my order', 'Browse products', 'Find by size', 'Shipping info']
        }


class ChatbotService:
    """Main chatbot orchestrator"""
    
    def __init__(self):
        self.intent_parser = IntentParser()
        self.order_handler = OrderTrackingHandler()
        self.product_handler = ProductSearchHandler()
        self.size_handler = SizeRecommendationHandler()
        self.fallback_handler = FallbackHandler()
    
    def process_message(self, message: str, user=None, session_id: str = None, context: Dict = None) -> Dict:
        """Main entry point for processing messages"""
        context = context or {}
        
        # Parse intent
        intent, extracted_data = self.intent_parser.parse(message)
        
        # Route to appropriate handler
        if intent == 'track_order':
            return self.order_handler.handle(user, message, extracted_data)
        
        elif intent == 'find_product':
            return self.product_handler.handle(message, extracted_data)
        
        elif intent == 'find_by_size':
            size_match = re.search(r'(xs|s|m|l|xl|xxl|xxxl)', message.lower())
            if size_match:
                filters = {'size': size_match.group(1).upper()}
                return self.product_handler.handle(message, extracted_data, filters)
        
        elif intent == 'find_by_color':
            color_match = re.search(r'(black|white|blue|red|green|yellow|pink|purple|orange|gray|brown)', message.lower())
            if color_match:
                filters = {'color': color_match.group(1)}
                return self.product_handler.handle(message, extracted_data, filters)
        
        elif intent == 'price_check':
            price_match = re.search(r'(\d+)', message)
            if price_match:
                filters = {'max_price': Decimal(price_match.group(1))}
                return self.product_handler.handle(message, extracted_data, filters)
        
        elif intent == 'size_recommendation':
            return self.size_handler.handle(session_id, message, context.get('size_state', {}))
        
        elif intent == 'cart_help':
            if user and user.is_authenticated:
                cart = Cart.objects.filter(user=user, is_active=True).first()
                if cart and cart.items.exists():
                    return {
                        'reply': f"You have {cart.item_count()} item(s) in your cart. Total: ₹{cart.total()}",
                        'suggestions': ['View cart', 'Proceed to checkout', 'Continue shopping']
                    }
                return {
                    'reply': "Your cart is empty. Let me help you find some products!",
                    'suggestions': ['Browse products', 'New arrivals', 'Best sellers']
                }
            return {
                'reply': "Please log in to view your cart.",
                'suggestions': ['Log in', 'Browse as guest']
            }
        
        elif intent == 'shipping_info':
            return self.fallback_handler.handle('shipping policy')
        
        elif intent == 'return_policy':
            return self.fallback_handler.handle('return policy')
        
        elif intent == 'payment_help':
            return self.fallback_handler.handle('payment methods')
        
        # Fallback
        return self.fallback_handler.handle(message)