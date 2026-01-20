# admin_dashboard/views/customers.py
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count, Avg

from .base import (
    BaseAdminListView, BaseAdminDetailView, BaseAdminAPIView, BaseAdminTemplateView
)
from app.models import User, Order, Cart, Wishlist
from ..services import CustomerManagementService
from ..utils import FilterHelper, PermissionHelper


class CustomerListView(BaseAdminListView):
    """List all customers"""
    
    model = User
    template_name = 'admin_dashboard/customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Customers', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = User.objects.filter(role='customer').annotate(
            total_orders=Count('orders'),
            total_spent=Sum('orders__total', filter=Q(orders__status__in=['paid', 'processing', 'shipped', 'delivered'])),
            avg_order_value=Avg('orders__total', filter=Q(orders__status__in=['paid', 'processing', 'shipped', 'delivered']))
        )
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                orders__in=vendor.vendor_orders.all()
            ).distinct()
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(is_active=True, is_blocked=False)
        elif status == 'blocked':
            queryset = queryset.filter(is_blocked=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Ordering
        order_by = self.request.GET.get('order_by', '-date_joined')
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_filter_options(self):
        return {
            'status_options': [
                ('', 'All'),
                ('active', 'Active'),
                ('blocked', 'Blocked'),
                ('inactive', 'Inactive'),
            ]
        }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Summary stats
        queryset = User.objects.filter(role='customer')
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(orders__in=vendor.vendor_orders.all()).distinct()
        context['total_customers'] = queryset.count()
        context['active_customers'] = queryset.filter(is_active=True, is_blocked=False).count()
        context['blocked_customers'] = queryset.filter(is_blocked=True).count()
        # Ensure template has expected filter_options alias
        context['filter_options'] = self.get_filter_options()
        
        return context


class CustomerDetailView(BaseAdminDetailView):
    """View customer details"""
    
    model = User
    template_name = 'admin_dashboard/customers/customer_detail.html'
    context_object_name = 'customer'
    
    def get_breadcrumbs(self):
        # for proper working of bred-crumbs from payments, orders, dashboard
        referer = self.request.META.get('HTTP_REFERER', '')
        
        if '/payments/' in referer or 'payment' in referer:
            return [
                {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
                {'title': 'Payments', 'url': reverse_lazy('admin_dashboard:payment_list')},
                {'title': self.object.username, 'url': '#'},
            ]
        elif '/orders/' in referer:
            return [
                {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
                {'title': 'Orders', 'url': reverse_lazy('admin_dashboard:order_list')},
                {'title': self.object.username, 'url': '#'},
            ]
        else:
            return [
                {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
                {'title': 'Customers', 'url': reverse_lazy('admin_dashboard:customer_list')},
                {'title': self.object.username, 'url': '#'},
            ]
    
    def get_queryset(self):
        queryset = User.objects.filter(role='customer')
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(orders__in=vendor.vendor_orders.all()).distinct()
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get comprehensive customer info
        vendor = PermissionHelper.get_vendor(self.request.user) if PermissionHelper.is_vendor(self.request.user) else None
        customer_info = CustomerManagementService.get_customer_detailed_info(self.object.id, vendor=vendor)
        context.update(customer_info)
        
        return context


class CustomerOrdersView(BaseAdminListView):
    """View customer's orders"""
    
    model = Order
    template_name = 'admin_dashboard/customers/customer_orders.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_breadcrumbs(self):
        customer = get_object_or_404(User, pk=self.kwargs['pk'])
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Customers', 'url': reverse_lazy('admin_dashboard:customer_list')},
            {'title': customer.username, 'url': reverse_lazy('admin_dashboard:customer_detail', kwargs={'pk': customer.pk})},
            {'title': 'Orders', 'url': '#'},
        ]
    
    def get_queryset(self):
        customer_id = self.kwargs['pk']
        queryset = Order.objects.filter(user_id=customer_id).select_related(
            'address', 'coupon'
        ).prefetch_related('items', 'payments').order_by('-placed_at')
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                Q(vendor=vendor) | Q(items__variant__product__vendor=vendor)
            ).distinct()
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        customer = get_object_or_404(User, pk=self.kwargs['pk'])
        context['customer'] = customer
        
        # Order statistics
        orders = self.get_queryset()
        context['total_orders'] = orders.count()
        context['total_spent'] = sum(order.total for order in orders.filter(status__in=['paid', 'processing', 'shipped', 'delivered']))
        
        return context


class CustomerCartView(BaseAdminDetailView):
    """View customer's cart"""
    
    model = User
    template_name = 'admin_dashboard/customers/customer_cart.html'
    context_object_name = 'customer'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Customers', 'url': reverse_lazy('admin_dashboard:customer_list')},
            {'title': self.object.username, 'url': reverse_lazy('admin_dashboard:customer_detail', kwargs={'pk': self.object.pk})},
            {'title': 'Cart', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active cart
        cart = self.object.carts.filter(is_active=True).first()
        
        if cart:
            cart_items_qs = cart.items.select_related(
                'variant__product', 'variant__inventory'
            )
            if PermissionHelper.is_vendor(self.request.user):
                vendor = PermissionHelper.get_vendor(self.request.user)
                cart_items_qs = cart_items_qs.filter(variant__product__vendor=vendor)
            cart_items = list(cart_items_qs)
            cart_total = sum(item.variant.price * item.quantity for item in cart_items)
        else:
            cart_items = []
            cart_total = Decimal('0.00')
        
        context['cart'] = cart
        context['cart_items'] = cart_items
        context['cart_total'] = cart_total
        context['item_count'] = len(cart_items)
        
        return context


class CustomerWishlistView(BaseAdminDetailView):
    """View customer's wishlist"""
    
    model = User
    template_name = 'admin_dashboard/customers/customer_wishlist.html'
    context_object_name = 'customer'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Customers', 'url': reverse_lazy('admin_dashboard:customer_list')},
            {'title': self.object.username, 'url': reverse_lazy('admin_dashboard:customer_detail', kwargs={'pk': self.object.pk})},
            {'title': 'Wishlist', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get wishlist
        wishlist = self.object.wishlists.first()
        
        if wishlist:
            wishlist_items_qs = wishlist.items.select_related(
                'variant__product', 'variant'
            ).prefetch_related(
                'variant__product__images'
            )
            if PermissionHelper.is_vendor(self.request.user):
                vendor = PermissionHelper.get_vendor(self.request.user)
                wishlist_items_qs = wishlist_items_qs.filter(variant__product__vendor=vendor)
            wishlist_items = list(wishlist_items_qs)
        else:
            wishlist_items = []
        
        context['wishlist'] = wishlist
        context['wishlist_items'] = wishlist_items
        context['item_count'] = len(wishlist_items)
        
        return context


class CustomerBlockView(BaseAdminAPIView):
    """Block/unblock customer"""
    
    def post(self, request, pk, *args, **kwargs):
        try:
            is_blocked, message = CustomerManagementService.toggle_customer_block(pk)
            
            return self.success_response(
                data={'is_blocked': is_blocked},
                message=message
            )
            
        except User.DoesNotExist:
            return self.error_response('Customer not found', status=404)
        except Exception as e:
            return self.error_response(str(e))


class CustomerWalletView(BaseAdminAPIView):
    """Manage customer wallet"""
    
    def get(self, request, pk, *args, **kwargs):
        """Get wallet balance"""
        try:
            user = User.objects.get(pk=pk, role='customer')
            return self.success_response(data={
                'balance': float(user.wallet_balance)
            })
        except User.DoesNotExist:
            return self.error_response('Customer not found', status=404)
    
    def post(self, request, pk, *args, **kwargs):
        """Update wallet balance"""
        import json
        
        try:
            data = json.loads(request.body)
            amount = Decimal(str(data.get('amount', 0)))
            reason = data.get('reason', 'Manual adjustment by admin')
            
            if amount == 0:
                return self.error_response('Amount cannot be zero')
            
            new_balance = CustomerManagementService.update_customer_wallet(
                pk, amount, reason
            )
            
            return self.success_response(
                data={'new_balance': float(new_balance)},
                message=f'Wallet updated successfully'
            )
            
        except User.DoesNotExist:
            return self.error_response('Customer not found', status=404)
        except (ValueError, json.JSONDecodeError):
            return self.error_response('Invalid data')
        except Exception as e:
            return self.error_response(str(e))
