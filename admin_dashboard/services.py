# admin_dashboard/services.py
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.db.models import (
    Sum, Count, Avg, Q, F, FloatField, DecimalField,
    ExpressionWrapper, Case, When, Value
)
from django.db.models.functions import TruncDate, TruncMonth, Coalesce
from django.utils import timezone
from django.core.cache import cache

from app.models import (
    Order, OrderItem, Product, ProductVariant, User,
    Payment, Category, Inventory, Cart, Wishlist, Coupon, Review
)


class DashboardAnalyticsService:
    """Service for dashboard analytics and statistics"""
    
    @staticmethod
    def get_dashboard_stats(start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get main dashboard statistics"""
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # Cache key
        cache_key = f'dashboard_stats_{start_date.date()}_{end_date.date()}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Total Revenue
        revenue_data = Order.objects.filter(
            placed_at__range=[start_date, end_date],
            status__in=['paid', 'processing', 'shipped', 'delivered']
        ).aggregate(
            total_revenue=Coalesce(Sum('total'), Decimal('0.00')),
            total_orders=Count('id'),
            avg_order_value=Coalesce(Avg('total'), Decimal('0.00'))
        )
        
        # Previous period comparison
        prev_start = start_date - (end_date - start_date)
        prev_revenue = Order.objects.filter(
            placed_at__range=[prev_start, start_date],
            status__in=['paid', 'processing', 'shipped', 'delivered']
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0.00'))
        )['total']
        
        revenue_change = 0
        if prev_revenue and prev_revenue > 0:
            revenue_change = ((revenue_data['total_revenue'] - prev_revenue) / prev_revenue) * 100
        
        # New Customers
        new_customers = User.objects.filter(
            date_joined__range=[start_date, end_date],
            role='customer'
        ).count()
        
        # Pending Orders
        pending_orders = Order.objects.filter(
            status__in=['pending', 'paid']
        ).count()
        
        # Low Stock Products
        low_stock_count = Inventory.objects.filter(
            quantity__lte=F('low_stock_threshold')
        ).count()
        
        # Top Products
        top_products = OrderItem.objects.filter(
            order__placed_at__range=[start_date, end_date],
            order__status__in=['paid', 'processing', 'shipped', 'delivered']
        ).values(
            'variant__product__name',
            'variant__product__slug'
        ).annotate(
            total_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('-total_sold')[:5]
        
        # Payment Methods Breakdown
        payment_methods = Payment.objects.filter(
            created_at__range=[start_date, end_date],
            status='success'
        ).values('method').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')
        
        result = {
            'total_revenue': float(revenue_data['total_revenue']),
            'total_orders': revenue_data['total_orders'],
            'avg_order_value': float(revenue_data['avg_order_value']),
            'revenue_change': float(revenue_change),
            'new_customers': new_customers,
            'pending_orders': pending_orders,
            'low_stock_count': low_stock_count,
            'top_products': list(top_products),
            'payment_methods': list(payment_methods),
        }
        
        cache.set(cache_key, result, 300)  # Cache for 5 minutes
        return result
    
    @staticmethod
    def get_sales_trend(days: int = 30) -> List[Dict]:
        """Get daily sales trend"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        sales_data = Order.objects.filter(
            placed_at__range=[start_date, end_date],
            status__in=['paid', 'processing', 'shipped', 'delivered']
        ).annotate(
            date=TruncDate('placed_at')
        ).values('date').annotate(
            revenue=Sum('total'),
            orders=Count('id')
        ).order_by('date')
        
        return list(sales_data)
    
    @staticmethod
    def get_revenue_by_category(start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get revenue breakdown by category"""
        category_revenue = OrderItem.objects.filter(
            order__placed_at__range=[start_date, end_date],
            order__status__in=['paid', 'processing', 'shipped', 'delivered']
        ).values(
            'variant__product__category__name'
        ).annotate(
            revenue=Sum(F('quantity') * F('unit_price')),
            items_sold=Sum('quantity')
        ).order_by('-revenue')[:10]
        
        return list(category_revenue)
    
    @staticmethod
    def get_order_status_breakdown() -> Dict:
        """Get order counts by status"""
        status_counts = Order.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {item['status']: item['count'] for item in status_counts}
    
    @staticmethod
    def get_customer_lifetime_value() -> List[Dict]:
        """Get top customers by lifetime value"""
        top_customers = User.objects.filter(
            role='customer'
        ).annotate(
            total_spent=Coalesce(
                Sum('orders__total', filter=Q(orders__status__in=['paid', 'processing', 'shipped', 'delivered'])),
                Decimal('0.00')
            ),
            order_count=Count('orders', filter=Q(orders__status__in=['paid', 'processing', 'shipped', 'delivered']))
        ).filter(
            order_count__gt=0
        ).order_by('-total_spent')[:20]
        
        return [{
            'id': customer.id,
            'username': customer.username,
            'email': customer.email,
            'total_spent': float(customer.total_spent),
            'order_count': customer.order_count,
            'avg_order_value': float(customer.total_spent / customer.order_count) if customer.order_count > 0 else 0
        } for customer in top_customers]


class SalesReportService:
    """Service for detailed sales reports"""
    
    @staticmethod
    def generate_sales_report(start_date: datetime, end_date: datetime, 
                             group_by: str = 'day') -> Dict:
        """Generate comprehensive sales report"""
        
        # Base query
        orders = Order.objects.filter(
            placed_at__range=[start_date, end_date],
            status__in=['paid', 'processing', 'shipped', 'delivered']
        )
        
        # Overall metrics
        overall = orders.aggregate(
            total_revenue=Coalesce(Sum('total'), Decimal('0.00')),
            total_orders=Count('id'),
            avg_order_value=Coalesce(Avg('total'), Decimal('0.00')),
            total_items_sold=Coalesce(Sum('items__quantity'), 0),
            total_discount=Coalesce(Sum('discount_amount'), Decimal('0.00')),
            total_shipping=Coalesce(Sum('shipping_amount'), Decimal('0.00')),
        )
        
        # Group by period
        if group_by == 'day':
            trunc_func = TruncDate('placed_at')
        elif group_by == 'month':
            trunc_func = TruncMonth('placed_at')
        else:
            trunc_func = TruncDate('placed_at')
        
        period_data = orders.annotate(
            period=trunc_func
        ).values('period').annotate(
            revenue=Sum('total'),
            orders=Count('id'),
            items_sold=Sum('items__quantity')
        ).order_by('period')
        
        # Payment method breakdown
        payment_breakdown = Payment.objects.filter(
            order__in=orders,
            status='success'
        ).values('method').annotate(
            count=Count('id'),
            amount=Sum('amount')
        ).order_by('-amount')
        
        # COD vs Online
        cod_orders = orders.filter(payments__method='cod', payments__status='success').distinct()
        online_orders = orders.exclude(payments__method='cod').distinct()
        
        cod_stats = cod_orders.aggregate(
            count=Count('id'),
            revenue=Coalesce(Sum('total'), Decimal('0.00'))
        )
        
        online_stats = online_orders.aggregate(
            count=Count('id'),
            revenue=Coalesce(Sum('total'), Decimal('0.00'))
        )
        
        # Return/Cancellation stats
        cancelled_orders = Order.objects.filter(
            placed_at__range=[start_date, end_date],
            status__in=['cancelled', 'refunded']
        ).aggregate(
            count=Count('id'),
            amount=Coalesce(Sum('total'), Decimal('0.00'))
        )
        
        return {
            'overall': {
                'total_revenue': float(overall['total_revenue']),
                'total_orders': overall['total_orders'],
                'avg_order_value': float(overall['avg_order_value']),
                'total_items_sold': overall['total_items_sold'],
                'total_discount': float(overall['total_discount']),
                'total_shipping': float(overall['total_shipping']),
            },
            'period_data': list(period_data),
            'payment_methods': list(payment_breakdown),
            'cod_vs_online': {
                'cod': {
                    'count': cod_stats['count'],
                    'revenue': float(cod_stats['revenue'])
                },
                'online': {
                    'count': online_stats['count'],
                    'revenue': float(online_stats['revenue'])
                }
            },
            'cancellations': {
                'count': cancelled_orders['count'],
                'amount': float(cancelled_orders['amount'])
            }
        }
    
    @staticmethod
    def get_product_performance_report(start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get detailed product performance metrics"""
        
        products = OrderItem.objects.filter(
            order__placed_at__range=[start_date, end_date],
            order__status__in=['paid', 'processing', 'shipped', 'delivered']
        ).values(
            'variant__product__id',
            'variant__product__name',
            'variant__product__slug',
            'variant__product__category__name'
        ).annotate(
            units_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price')),
            avg_price=Avg('unit_price'),
            order_count=Count('order', distinct=True)
        ).order_by('-revenue')
        
        return list(products)
    
    @staticmethod
    def export_sales_report_csv(start_date: datetime, end_date: datetime) -> str:
        """Generate CSV export of sales report"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Order ID', 'Date', 'Customer', 'Status', 'Items',
            'Subtotal', 'Discount', 'Shipping', 'Tax', 'Total', 'Payment Method'
        ])
        
        # Data
        orders = Order.objects.filter(
            placed_at__range=[start_date, end_date]
        ).select_related('user').prefetch_related('items', 'payments')
        
        for order in orders:
            payment_method = order.payments.first().get_method_display() if order.payments.exists() else 'N/A'
            writer.writerow([
                str(order.id),
                order.placed_at.strftime('%Y-%m-%d %H:%M'),
                order.user.username,
                order.get_status_display(),
                order.items.count(),
                order.subtotal,
                order.discount_amount,
                order.shipping_amount,
                order.tax_amount,
                order.total,
                payment_method
            ])
        
        return output.getvalue()


class OrderManagementService:
    """Service for order management operations"""
    
    @staticmethod
    def update_order_status(order_id: str, new_status: str, notes: str = '') -> Order:
        """Update order status with validation"""
        order = Order.objects.get(id=order_id)
        
        # Validate status transition
        valid_transitions = {
            'pending': ['paid', 'cancelled'],
            'paid': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': ['refunded'],
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            raise ValueError(f"Cannot transition from {order.status} to {new_status}")
        
        order.status = new_status
        if notes:
            order.notes = f"{order.notes}\n{timezone.now()}: {notes}" if order.notes else notes
        order.save()
        
        # Handle inventory if cancelling
        if new_status == 'cancelled':
            for item in order.items.all():
                if hasattr(item.variant, 'inventory'):
                    item.variant.inventory.unreserve(item.quantity)
        
        return order
    
    @staticmethod
    def bulk_update_order_status(order_ids: List[str], new_status: str) -> int:
        """Bulk update order statuses"""
        count = 0
        for order_id in order_ids:
            try:
                OrderManagementService.update_order_status(order_id, new_status)
                count += 1
            except (Order.DoesNotExist, ValueError):
                continue
        return count
    
    @staticmethod
    def generate_invoice_data(order_id: str) -> Dict:
        """Generate invoice data for an order"""
        order = Order.objects.select_related(
            'user', 'address', 'coupon'
        ).prefetch_related(
            'items__variant__product'
        ).get(id=order_id)
        
        return {
            'order': order,
            'items': order.items.all(),
            'invoice_number': f'INV-{str(order.id)[:8].upper()}',
            'invoice_date': timezone.now(),
        }


class CustomerManagementService:
    """Service for customer management"""
    
    @staticmethod
    def get_customer_detailed_info(user_id: int) -> Dict:
        """Get comprehensive customer information"""
        user = User.objects.get(id=user_id)
        
        # Order statistics
        order_stats = user.orders.filter(
            status__in=['paid', 'processing', 'shipped', 'delivered']
        ).aggregate(
            total_orders=Count('id'),
            total_spent=Coalesce(Sum('total'), Decimal('0.00')),
            avg_order_value=Coalesce(Avg('total'), Decimal('0.00'))
        )
        
        # Recent orders
        recent_orders = user.orders.order_by('-placed_at')[:5]
        
        # Cart info
        active_cart = user.carts.filter(is_active=True).first()
        cart_items = []
        cart_total = Decimal('0.00')
        if active_cart:
            cart_items = active_cart.items.select_related('variant__product').all()
            cart_total = active_cart.total()
        
        # Wishlist
        wishlist = user.wishlists.first()
        wishlist_items = []
        if wishlist:
            wishlist_items = wishlist.items.select_related('variant__product').all()
        
        return {
            'user': user,
            'order_stats': order_stats,
            'recent_orders': recent_orders,
            'cart_items': cart_items,
            'cart_total': cart_total,
            'wishlist_items': wishlist_items,
            'wallet_balance': user.wallet_balance,
        }
    
    @staticmethod
    def toggle_customer_block(user_id: int) -> Tuple[bool, str]:
        """Block or unblock customer"""
        user = User.objects.get(id=user_id, role='customer')
        user.is_blocked = not user.is_blocked
        user.save()
        
        status = "blocked" if user.is_blocked else "unblocked"
        return user.is_blocked, f"Customer {status} successfully"
    
    @staticmethod
    def update_customer_wallet(user_id: int, amount: Decimal, reason: str) -> Decimal:
        """Update customer wallet balance"""
        user = User.objects.get(id=user_id)
        user.wallet_balance = F('wallet_balance') + amount
        user.save()
        user.refresh_from_db()
        
        # Log transaction (you can create WalletTransaction model)
        
        return user.wallet_balance


class InventoryManagementService:
    """Service for inventory operations"""
    
    @staticmethod
    def get_low_stock_products(threshold: int = None) -> List[Dict]:
        """Get products with low stock"""
        query = Inventory.objects.select_related('variant__product')
        
        if threshold:
            query = query.filter(quantity__lte=threshold)
        else:
            query = query.filter(quantity__lte=F('low_stock_threshold'))
        
        low_stock = query.annotate(
            product_name=F('variant__product__name'),
            sku=F('variant__sku'),
            size=F('variant__size'),
            color=F('variant__color')
        ).values(
            'id', 'product_name', 'sku', 'size', 'color',
            'quantity', 'low_stock_threshold', 'reserved'
        ).order_by('quantity')
        
        return list(low_stock)
    
    @staticmethod
    def bulk_update_inventory(updates: List[Dict]) -> int:
        """
        Bulk update inventory
        updates: [{'inventory_id': 1, 'quantity': 100, 'threshold': 10}, ...]
        """
        count = 0
        for update in updates:
            try:
                inventory = Inventory.objects.get(id=update['inventory_id'])
                if 'quantity' in update:
                    inventory.quantity = update['quantity']
                if 'threshold' in update:
                    inventory.low_stock_threshold = update['threshold']
                inventory.save()
                count += 1
            except Inventory.DoesNotExist:
                continue
        
        return count
    
    @staticmethod
    def get_inventory_valuation() -> Dict:
        """Calculate total inventory valuation"""
        valuation = Inventory.objects.select_related('variant').aggregate(
            total_units=Coalesce(Sum('quantity'), 0),
            total_value=Coalesce(
                Sum(F('quantity') * F('variant__price')),
                Decimal('0.00')
            )
        )
        
        return {
            'total_units': valuation['total_units'],
            'total_value': float(valuation['total_value'])
        }


class CouponManagementService:
    """Service for coupon management"""
    
    @staticmethod
    def get_coupon_usage_stats(coupon_id: int) -> Dict:
        """Get usage statistics for a coupon"""
        coupon = Coupon.objects.prefetch_related('usages').get(id=coupon_id)
        
        usages = coupon.usages.all()
        total_discount = usages.aggregate(
            total=Coalesce(Sum('order__discount_amount'), Decimal('0.00'))
        )['total']
        
        unique_users = usages.values('user').distinct().count()
        
        return {
            'coupon': coupon,
            'total_uses': usages.count(),
            'unique_users': unique_users,
            'total_discount_given': float(total_discount),
            'remaining_uses': (coupon.max_usage - usages.count()) if coupon.max_usage else None
        }
    
    @staticmethod
    def validate_and_apply_coupon(code: str, user, order_amount: Decimal) -> Tuple[bool, str, Optional[Decimal]]:
        """Validate coupon and return discount amount"""
        try:
            coupon = Coupon.objects.get(code=code, active=True)
            
            if not coupon.is_valid_for_user(user, order_amount):
                return False, "Coupon is not valid for this order", None
            
            discount = coupon.discount_amount(order_amount)
            return True, "Coupon applied successfully", discount
            
        except Coupon.DoesNotExist:
            return False, "Invalid coupon code", None