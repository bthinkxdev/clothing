# admin_dashboard/services.py
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.db.models import (
    Sum, Count, Avg, Q, F, FloatField, DecimalField,
    ExpressionWrapper, Case, When, Value, IntegerField
)
from django.db.models.functions import TruncDate, TruncMonth, Coalesce
from django.utils import timezone

from app.models import (
    Order, OrderItem, Product, ProductVariant, User,
    Payment, Category, Inventory, Cart, Wishlist, Coupon, Review
)
import openpyxl
from io import BytesIO

class DashboardAnalyticsService:
    """Service for dashboard analytics and statistics"""
    
    @staticmethod
    def get_dashboard_stats(start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get main dashboard statistics using the requested date range."""
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()

        period_delta = end_date - start_date

        # Current period data
        current_orders = Order.objects.filter(placed_at__range=[start_date, end_date])
        # Count revenue for all non-cancelled orders so pending/processing also show up
        revenue_orders = current_orders.exclude(status__in=['cancelled'])
        revenue_data = revenue_orders.aggregate(
            total_revenue=Coalesce(Sum('total'), Decimal('0.00')),
            total_orders=Count('id')
        )

        # Previous period for comparisons
        prev_start = start_date - period_delta
        prev_end = start_date
        prev_orders = Order.objects.filter(placed_at__range=[prev_start, prev_end])
        prev_revenue_orders = prev_orders.exclude(status__in=['cancelled'])

        prev_revenue_data = prev_revenue_orders.aggregate(
            total=Coalesce(Sum('total'), Decimal('0.00')),
            total_orders=Count('id')
        )

        def _percent_change(current: float, previous: float) -> float:
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return float(((current - previous) / previous) * 100)

        revenue_change = _percent_change(float(revenue_data['total_revenue']), float(prev_revenue_data['total']))
        orders_change = _percent_change(revenue_data['total_orders'], prev_revenue_data['total_orders'])

        new_customers = User.objects.filter(
            date_joined__range=[start_date, end_date],
            role='customer'
        ).count()
        prev_new_customers = User.objects.filter(
            date_joined__range=[prev_start, prev_end],
            role='customer'
        ).count()
        new_customer_change = _percent_change(new_customers, prev_new_customers)

        current_avg_order_value = float(revenue_data['total_revenue']) / revenue_data['total_orders'] if revenue_data['total_orders'] else 0.0
        previous_avg_order_value = float(prev_revenue_data['total']) / prev_revenue_data['total_orders'] if prev_revenue_data['total_orders'] else 0.0
        avg_order_value_change = _percent_change(
            current_avg_order_value,
            previous_avg_order_value
        )
        # Customer Retention Rate (customers who ordered in both periods)
        current_customers = set(current_orders.values_list('user_id', flat=True))
        prev_customers = set(prev_orders.values_list('user_id', flat=True))
        repeat_customers = current_customers.intersection(prev_customers)
        retention_rate = (len(repeat_customers) / len(prev_customers) * 100) if prev_customers else 0
        
        prev_prev_start = prev_start - period_delta
        prev_prev_orders = Order.objects.filter(placed_at__range=[prev_prev_start, prev_start])
        prev_prev_customers = set(prev_prev_orders.values_list('user_id', flat=True))
        prev_repeat = prev_customers.intersection(prev_prev_customers)
        prev_retention_rate = (len(prev_repeat) / len(prev_prev_customers) * 100) if prev_prev_customers else 0
        retention_change = _percent_change(retention_rate, prev_retention_rate)
        
        # Average Response Time (using order processing time as proxy)
        avg_processing_time = current_orders.filter(
            status__in=['processing', 'shipped', 'delivered']
        ).annotate(
            processing_time=F('updated_at') - F('placed_at')
        ).aggregate(avg_time=Avg('processing_time'))['avg_time']
        
        avg_response_hours = (avg_processing_time.total_seconds() / 3600) if avg_processing_time else 0
        
        # Cart Abandonment Rate
        from app.models import Cart
        active_carts = Cart.objects.filter(
            updated_at__range=[start_date, end_date],
            is_active=True
        ).count()
        completed_orders = current_orders.exclude(status__in=['cancelled']).count()
        total_carts = active_carts + completed_orders
        abandonment_rate = (active_carts / total_carts * 100) if total_carts else 0
        
        prev_active_carts = Cart.objects.filter(
            updated_at__range=[prev_start, prev_end],
            is_active=True
        ).count()
        prev_completed = prev_orders.exclude(status__in=['cancelled']).count()
        prev_total_carts = prev_active_carts + prev_completed
        prev_abandonment = (prev_active_carts / prev_total_carts * 100) if prev_total_carts else 0
        abandonment_change = abs(_percent_change(abandonment_rate, prev_abandonment))

        pending_orders = Order.objects.filter(status__in=['pending', 'paid']).count()

        available_expr = ExpressionWrapper(F('quantity') - F('reserved'), output_field=IntegerField())

        low_stock_count = Inventory.objects.annotate(
            available=available_expr
        ).filter(
            available__gt=0,
            available__lte=F('low_stock_threshold')
        ).count()

        top_products = OrderItem.objects.filter(
            order__placed_at__range=[start_date, end_date]
        ).exclude(
            order__status__in=['cancelled']
        ).values(
            'variant__product__name',
            'variant__product__slug'
        ).annotate(
            total_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('-total_sold')[:5]

        # Fallback: if there are no order items but there are orders, show an aggregate bucket
        if not top_products.exists():
            order_agg = Order.objects.filter(
                placed_at__range=[start_date, end_date]
            ).exclude(
                status__in=['cancelled']
            ).aggregate(
                total_orders=Count('id'),
                total_revenue=Coalesce(Sum('total'), Decimal('0.00'))
            )
            if order_agg['total_orders']:
                top_products = [{
                    'variant__product__name': 'All Orders',
                    'variant__product__slug': '',
                    'total_sold': order_agg['total_orders'],
                    'revenue': float(order_agg['total_revenue'] or 0)
                }]

        payment_methods_qs = Payment.objects.filter(
            created_at__range=[start_date, end_date],
            status__in=['success', 'pending']
        ).values('method').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')

        total_payment_amount = sum(item['total'] or Decimal('0.00') for item in payment_methods_qs)
        method_display_map = dict(Payment.PAYMENT_METHOD)
        payment_methods = []
        for item in payment_methods_qs:
            amount = float(item['total'] or Decimal('0.00'))
            percentage = float((item['total'] / total_payment_amount) * 100) if total_payment_amount else 0.0
            payment_methods.append({
                'method': item['method'],
                'display': method_display_map.get(item['method'], item['method'].title()),
                'count': item['count'],
                'total': amount,
                'percentage': percentage
            })

        result = {
            'total_revenue': float(revenue_data['total_revenue']),
            'total_orders': current_orders.count(),
            'avg_order_value': current_avg_order_value,
            'revenue_change': revenue_change,
            'orders_change': orders_change,
            'new_customers': new_customers,
            'new_customers_change': new_customer_change,
            'avg_order_value_change': avg_order_value_change,
            'pending_orders': pending_orders,
            'low_stock_count': low_stock_count,
            'top_products': [
                {
                    **product,
                    'revenue': float(product['revenue']) if product.get('revenue') is not None else 0.0
                } for product in top_products
            ],
            'payment_methods': payment_methods,
            # Coustomer rettention, Avg response time, Abandonment Rate
            'retention_rate': retention_rate,
            'retention_change': retention_change,
            'avg_response_hours': avg_response_hours,
            'cart_abandonment_rate': abandonment_rate,
            'abandonment_change': abandonment_change,
        }

        return result
    
    @staticmethod
    def get_sales_trend(days: int = 30, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get daily sales trend"""
        if not end_date:
            end_date = timezone.now()
        if start_date:
            start_date = start_date
        else:
            start_date = end_date - timedelta(days=days)

        sales_data = Order.objects.filter(
            placed_at__range=[start_date, end_date]
        ).exclude(
            status__in=['cancelled']
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
            order__placed_at__range=[start_date, end_date]
        ).exclude(
            order__status__in=['cancelled']
        ).values(
            'variant__product__category__name'
        ).annotate(
            revenue=Sum(F('quantity') * F('unit_price')),
            items_sold=Sum('quantity')
        ).order_by('-revenue')[:10]

        # Fallback: if there are orders but no order items (e.g., data seeded without line items),
        # show a single aggregate bucket so the chart isn't empty.
        if not category_revenue.exists():
            total_revenue = Order.objects.filter(
                placed_at__range=[start_date, end_date]
            ).exclude(
                status__in=['cancelled']
            ).aggregate(total=Coalesce(Sum('total'), Decimal('0.00')))['total']
            if total_revenue and total_revenue > 0:
                return [{
                    'variant__product__category__name': 'All Orders',
                    'revenue': float(total_revenue),
                    'items_sold': 0
                }]
        
        return list(category_revenue)
    
    @staticmethod
    def get_order_status_breakdown(start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get order counts by status (date-filtered when provided)."""
        orders = Order.objects.all()
        if start_date and end_date:
            orders = orders.filter(placed_at__range=[start_date, end_date])

        status_counts = orders.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        return {item['status']: item['count'] for item in status_counts}

    @staticmethod
    def get_customer_trend(start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get customer registrations per day for the range."""
        customer_data = User.objects.filter(
            role='customer',
            date_joined__range=[start_date, end_date]
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        return list(customer_data)
    
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
    
    @staticmethod
    def get_sales_by_region(start_date, end_date):
        """Get sales grouped by state/region from order addresses"""
        from django.db.models import Sum, Count, Q
        from datetime import timedelta
        from app.models import Order
        
        # Query orders with addresses, group by state
        sales_by_region = Order.objects.filter(
            placed_at__gte=start_date,
            placed_at__lte=end_date,
            address__isnull=False,
            status__in=['paid', 'processing', 'shipped', 'delivered']
        ).values(
            'address__state'
        ).annotate(
            total_revenue=Sum('total'),
            order_count=Count('id')
        ).order_by('-total_revenue')[:10]  # Top 10 states
        
        # Calculate previous period for growth comparison
        period_duration = (end_date - start_date).days
        previous_start = start_date - timedelta(days=period_duration)
        previous_end = start_date
        
        result = []
        max_revenue = float(sales_by_region[0]['total_revenue']) if sales_by_region else 1
        
        for region in sales_by_region:
            state_name = region['address__state']
            if not state_name:
                continue
                
            current_revenue = float(region['total_revenue'])
            
            # Get previous period revenue for this state
            previous_revenue = Order.objects.filter(
                placed_at__gte=previous_start,
                placed_at__lt=previous_end,
                address__state=state_name,
                status__in=['paid', 'processing', 'shipped', 'delivered']
            ).aggregate(total=Sum('total'))['total'] or 0
            
            # Calculate growth percentage
            if previous_revenue > 0:
                growth = ((current_revenue - float(previous_revenue)) / float(previous_revenue)) * 100
            else:
                growth = 100.0 if current_revenue > 0 else 0.0
            
            result.append({
                'state': state_name,
                'revenue': current_revenue,
                'order_count': region['order_count'],
                'percentage': (current_revenue / max_revenue * 100) if max_revenue > 0 else 0,
                'growth': round(growth, 1)
            })
        
        return result


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
    
    @staticmethod
    def export_sales_report_excel(start_date: datetime, end_date: datetime):
        """Generate Excel export of sales report"""
          
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sales Report"
        
        # Headers
        headers = ['Order ID', 'Date', 'Customer', 'Status', 'Items', 'Subtotal', 'Discount', 'Shipping', 'Tax', 'Total', 'Payment Method']
        ws.append(headers)
        
        # Data
        orders = Order.objects.filter(
            placed_at__range=[start_date, end_date]
        ).select_related('user').prefetch_related('items', 'payments')
        
        for order in orders:
            payment_method = order.payments.first().get_method_display() if order.payments.exists() else 'N/A'
            ws.append([
                str(order.id),
                order.placed_at.strftime('%Y-%m-%d %H:%M'),
                order.user.username,
                order.get_status_display(),
                order.items.count(),
                float(order.subtotal),
                float(order.discount_amount),
                float(order.shipping_amount),
                float(order.tax_amount),
                float(order.total),
                payment_method
            ])
        
        # Style headers
        for col in range(1, len(headers) + 1):
            cell = ws.cell(1, col)
            cell.font = openpyxl.styles.Font(bold=True)
        
        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
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
    
    @staticmethod
    def get_order_timeline(order_id: str) -> List[Dict]:
        """Generate timeline events for an order"""
        order = Order.objects.prefetch_related('payments').get(id=order_id)
        
        timeline = [
            {
                'date': order.placed_at,
                'status': 'Order Placed',
                'description': 'Order was placed'
            }
        ]
        
        # Add payment events
        for payment in order.payments.all():
            timeline.append({
                'date': payment.created_at,
                'status': f'Payment {payment.get_status_display()}',
                'description': f'{payment.get_method_display()} payment - ₹{payment.amount}'
            })
        
        # Add current status event if different from placed
        if order.status != 'pending':
            timeline.append({
                'date': order.updated_at,
                'status': order.get_status_display(),
                'description': f'Order status updated to {order.get_status_display()}'
            })
        
        # Sort by date (oldest to newest)
        timeline.sort(key=lambda x: x['date'])
        
        return timeline

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
        available_expr = ExpressionWrapper(F('quantity') - F('reserved'), output_field=IntegerField())

        query = Inventory.objects.select_related('variant__product').annotate(available=available_expr)
        
        if threshold is not None:
            query = query.filter(available__gt=0, available__lte=threshold)
        else:
            query = query.filter(available__gt=0, available__lte=F('low_stock_threshold'))
        
        low_stock = query.annotate(
            product_name=F('variant__product__name'),
            sku=F('variant__sku'),
            size=F('variant__size'),
            color=F('variant__color')
        ).values(
            'id', 'product_name', 'sku', 'size', 'color',
            'quantity', 'low_stock_threshold', 'reserved', 'available'
        ).order_by('available', 'quantity')
        
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
        coupon = Coupon.objects.prefetch_related('usages__order').get(id=coupon_id)
        
        # Filter usages that have orders
        usages = coupon.usages.filter(order__isnull=False)
        
        # Calculate total discount given
        total_discount = usages.aggregate(
            total=Coalesce(Sum('order__discount_amount'), Decimal('0.00'))
        )['total']
        
        # Calculate total revenue from orders with this coupon
        total_revenue = usages.aggregate(
            total=Coalesce(Sum('order__total'), Decimal('0.00'))
        )['total']
        
        unique_users = usages.values('user').distinct().count()
        
        return {
            'coupon': coupon,
            'total_uses': coupon.usages.count(),  # All usages
            'unique_users': unique_users,
            'total_discount_given': float(total_discount),
            'total_revenue': float(total_revenue),
            'remaining_uses': (coupon.max_usage - coupon.usages.count()) if coupon.max_usage else None
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