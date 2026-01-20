# admin_dashboard/views/other.py
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q, F, Count, Sum, ExpressionWrapper, IntegerField

from .base import (
    BaseAdminListView, BaseAdminDetailView, BaseAdminCreateView,
    BaseAdminUpdateView, BaseAdminDeleteView, BaseAdminAPIView
)
from app.models import (
    Inventory, Coupon, Category, Review, Payment
)
from ..services import InventoryManagementService, CouponManagementService
from ..utils import PermissionHelper
from ..forms import InventoryForm, CouponForm, CategoryForm


# =====================================
# INVENTORY MANAGEMENT
# =====================================

class InventoryListView(BaseAdminListView):
    """List inventory with stock levels"""
    
    model = Inventory
    template_name = 'admin_dashboard/inventory/inventory_list.html'
    context_object_name = 'inventory_items'
    paginate_by = 50
    vendor_field = "vendor"
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Inventory', 'url': '#'},
        ]
    
    def get_queryset(self):
        available_expr = ExpressionWrapper(F('quantity') - F('reserved'), output_field=IntegerField())

        queryset = super().get_queryset().select_related(
            'variant__product', 'variant'
        ).annotate(available=available_expr)
        
        # Filters
        filter_type = self.request.GET.get('filter', 'all')
        
        if filter_type == 'low_stock':
            queryset = queryset.filter(available__gt=0, available__lte=F('low_stock_threshold'))
        elif filter_type == 'out_of_stock':
            queryset = queryset.filter(available__lte=0)
        elif filter_type == 'in_stock':
            queryset = queryset.filter(available__gt=F('low_stock_threshold'))
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(variant__sku__icontains=search) |
                Q(variant__product__name__icontains=search)
            )
        
        # Ordering
        order_by = self.request.GET.get('order_by', '-available')
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Inventory summary
        from django.db.models import Sum
        available_expr = ExpressionWrapper(F('quantity') - F('reserved'), output_field=IntegerField())
        
        all_inventory = self.apply_vendor_scope(
            Inventory.objects.all().annotate(available=available_expr)
        )
        context['total_products'] = all_inventory.count()
        context['low_stock_count'] = all_inventory.filter(available__gt=0, available__lte=F('low_stock_threshold')).count()
        context['out_of_stock_count'] = all_inventory.filter(available__lte=0).count()
        context['total_stock_value'] = InventoryManagementService.get_inventory_valuation(
            vendor=PermissionHelper.get_vendor(self.request.user) if PermissionHelper.is_vendor(self.request.user) else None
        )
        
        return context


class InventoryUpdateView(BaseAdminUpdateView):
    """Update inventory levels"""
    
    model = Inventory
    form_class = InventoryForm
    template_name = 'admin_dashboard/inventory/inventory_form.html'
    success_url = reverse_lazy('admin_dashboard:inventory_list')
    vendor_field = "vendor"
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Inventory', 'url': reverse_lazy('admin_dashboard:inventory_list')},
            {'title': 'Update', 'url': '#'},
        ]


class LowStockReportView(BaseAdminListView):
    """Report of low stock items"""
    
    model = Inventory
    template_name = 'admin_dashboard/inventory/low_stock_report.html'
    context_object_name = 'low_stock_items'
    vendor_field = "vendor"
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Inventory', 'url': reverse_lazy('admin_dashboard:inventory_list')},
            {'title': 'Low Stock Report', 'url': '#'},
        ]
    
    def get_queryset(self):
        available_expr = ExpressionWrapper(F('quantity') - F('reserved'), output_field=IntegerField())
        return self.apply_vendor_scope(
            Inventory.objects.annotate(
            available=available_expr
        ).filter(
            available__gt=0,
            available__lte=F('low_stock_threshold')
        ).select_related('variant__product').order_by('available', 'quantity')
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get structured data
        vendor = PermissionHelper.get_vendor(self.request.user) if PermissionHelper.is_vendor(self.request.user) else None
        context['low_stock_data'] = InventoryManagementService.get_low_stock_products(vendor=vendor)
        
        return context


class InventoryBulkUpdateView(BaseAdminAPIView):
    """Bulk update inventory"""
    
    def post(self, request, *args, **kwargs):
        import json
        
        try:
            data = json.loads(request.body)
            updates = data.get('updates', [])

            vendor = PermissionHelper.get_vendor(request.user) if PermissionHelper.is_vendor(request.user) else None
            count = InventoryManagementService.bulk_update_inventory(updates, vendor=vendor)
            
            return self.success_response(
                message=f'{count} inventory items updated'
            )
            
        except Exception as e:
            return self.error_response(str(e))


# =====================================
# COUPON MANAGEMENT
# =====================================

class CouponListView(BaseAdminListView):
    """List all coupons"""
    
    model = Coupon
    template_name = 'admin_dashboard/coupons/coupon_list.html'
    context_object_name = 'coupons'
    paginate_by = 25
    vendor_field = "vendor"
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Coupons', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('usages')
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(active=True)
        elif status == 'expired':
            from django.utils import timezone
            queryset = queryset.filter(end_date__lt=timezone.now())
        elif status == 'inactive':
            queryset = queryset.filter(active=False)
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        scoped = PermissionHelper.scope_queryset_for_user(Coupon.objects.all(), self.request.user)
        context['total_coupons'] = scoped.count()
        context['active_coupons'] = scoped.filter(active=True).count()
        
        return context


class CouponDetailView(BaseAdminDetailView):
    """View coupon details and usage"""
    
    model = Coupon
    template_name = 'admin_dashboard/coupons/coupon_detail.html'
    context_object_name = 'coupon'
    vendor_field = "vendor"
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Coupons', 'url': reverse_lazy('admin_dashboard:coupon_list')},
            {'title': self.object.code, 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get usage stats
        stats = CouponManagementService.get_coupon_usage_stats(self.object.id)
        context.update(stats)
        
        # Recent usages
        context['recent_usages'] = self.object.usages.select_related(
            'user', 'order'
        ).order_by('-used_at')[:20]
        
        return context


class CouponCreateView(BaseAdminCreateView):
    """Create new coupon"""
    
    model = Coupon
    form_class = CouponForm
    template_name = 'admin_dashboard/coupons/coupon_form.html'
    success_url = reverse_lazy('admin_dashboard:coupon_list')
    vendor_field = "vendor"
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['applicable_products'].queryset = PermissionHelper.scope_queryset_for_user(
            form.fields['applicable_products'].queryset,
            self.request.user,
        )
        form.fields['applicable_categories'].queryset = PermissionHelper.scope_queryset_for_user(
            form.fields['applicable_categories'].queryset,
            self.request.user,
        )
        return form

    def form_valid(self, form):
        if PermissionHelper.is_vendor(self.request.user):
            form.instance.vendor = PermissionHelper.get_vendor(self.request.user)
        return super().form_valid(form)
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Coupons', 'url': reverse_lazy('admin_dashboard:coupon_list')},
            {'title': 'Create Coupon', 'url': '#'},
        ]


class CouponUpdateView(BaseAdminUpdateView):
    """Update coupon"""
    
    model = Coupon
    form_class = CouponForm
    template_name = 'admin_dashboard/coupons/coupon_form.html'
    vendor_field = "vendor"
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Coupons', 'url': reverse_lazy('admin_dashboard:coupon_list')},
            {'title': self.object.code, 'url': reverse_lazy('admin_dashboard:coupon_detail', kwargs={'pk': self.object.pk})},
            {'title': 'Update', 'url': '#'},
        ]
    
    def get_success_url(self):
        return reverse_lazy('admin_dashboard:coupon_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['applicable_products'].queryset = PermissionHelper.scope_queryset_for_user(
            form.fields['applicable_products'].queryset,
            self.request.user,
        )
        form.fields['applicable_categories'].queryset = PermissionHelper.scope_queryset_for_user(
            form.fields['applicable_categories'].queryset,
            self.request.user,
        )
        return form

    def form_valid(self, form):
        if PermissionHelper.is_vendor(self.request.user):
            form.instance.vendor = PermissionHelper.get_vendor(self.request.user)
        return super().form_valid(form)


class CouponDeleteView(BaseAdminDeleteView):
    """Delete coupon"""
    
    model = Coupon
    success_url = reverse_lazy('admin_dashboard:coupon_list')
    vendor_field = "vendor"


class CouponToggleView(BaseAdminAPIView):
    """Toggle coupon active status"""
    
    def post(self, request, pk, *args, **kwargs):
        try:
            coupon = Coupon.objects.get(pk=pk)
            coupon.active = not coupon.active
            coupon.save()
            
            status = "activated" if coupon.active else "deactivated"
            
            return self.success_response(
                data={'active': coupon.active},
                message=f'Coupon {status}'
            )
            
        except Coupon.DoesNotExist:
            return self.error_response('Coupon not found', status=404)


# =====================================
# CATEGORY MANAGEMENT
# =====================================

class CategoryListView(BaseAdminListView):
    """List categories"""
    
    model = Category
    template_name = 'admin_dashboard/categories/category_list.html'
    context_object_name = 'categories'
    vendor_field = "vendor"
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Categories', 'url': '#'},
        ]
    
    def get_queryset(self):
        return self.apply_vendor_scope(
            Category.objects.annotate(
                product_count=Count('products')
            ).order_by('sort_order', 'name')
        )
    
    # method to count active categories
    def get_context_data(self, **kwargs): 
        context = super().get_context_data(**kwargs)
        scoped = PermissionHelper.scope_queryset_for_user(Category.objects.all(), self.request.user)
        context['active_categories_count'] = scoped.filter(is_active=True).count()
        return context

class CategoryCreateView(BaseAdminCreateView):
    """Create category"""
    
    model = Category
    form_class = CategoryForm
    template_name = 'admin_dashboard/categories/category_form.html'
    success_url = reverse_lazy('admin_dashboard:category_list')
    vendor_field = "vendor"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['parent'].queryset = PermissionHelper.scope_queryset_for_user(
            Category.objects.all(),
            self.request.user,
        )
        return form

    def form_valid(self, form):
        if PermissionHelper.is_vendor(self.request.user):
            form.instance.vendor = PermissionHelper.get_vendor(self.request.user)
        return super().form_valid(form)


class CategoryUpdateView(BaseAdminUpdateView):
    """Update category"""
    
    model = Category
    form_class = CategoryForm
    template_name = 'admin_dashboard/categories/category_form.html'
    success_url = reverse_lazy('admin_dashboard:category_list')
    vendor_field = "vendor"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['parent'].queryset = PermissionHelper.scope_queryset_for_user(
            Category.objects.exclude(pk=self.object.pk),
            self.request.user,
        )
        return form

    def form_valid(self, form):
        if PermissionHelper.is_vendor(self.request.user):
            form.instance.vendor = PermissionHelper.get_vendor(self.request.user)
        return super().form_valid(form)


class CategoryDeleteView(BaseAdminDeleteView):
    """Delete category"""
    
    model = Category
    success_url = reverse_lazy('admin_dashboard:category_list')
    vendor_field = "vendor"


# =====================================
# REVIEW MANAGEMENT
# =====================================

class ReviewListView(BaseAdminListView):
    """List reviews"""
    
    model = Review
    template_name = 'admin_dashboard/reviews/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 25
    vendor_field = None
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Reviews', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = Review.objects.select_related('user', 'product')
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(product__vendor=vendor)
        
        # Filter by approval status
        status = self.request.GET.get('status', 'all')  # 'pending' to 'all'
        if status == 'pending':
            queryset = queryset.filter(approved=False)
        elif status == 'approved':
            queryset = queryset.filter(approved=True)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        scoped = self.get_queryset()
        context['pending_count'] = scoped.filter(approved=False).count()
        context['approved_count'] = scoped.filter(approved=True).count()
        
        return context


class ReviewApproveView(BaseAdminAPIView):
    """Approve review"""
    
    def post(self, request, pk, *args, **kwargs):
        try:
            review = Review.objects.get(pk=pk)
            review.approved = True
            review.save()
            
            return self.success_response(message='Review approved')
            
        except Review.DoesNotExist:
            return self.error_response('Review not found', status=404)


class ReviewDeleteView(BaseAdminDeleteView):
    """Delete review"""
    
    model = Review
    success_url = reverse_lazy('admin_dashboard:review_list')


# =====================================
# PAYMENT MANAGEMENT
# =====================================

class PaymentListView(BaseAdminListView):
    """List payments"""
    
    model = Payment
    template_name = 'admin_dashboard/payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 25
    vendor_field = None
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Payments', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = Payment.objects.select_related('order__user')
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                Q(order__vendor=vendor) | Q(order__items__variant__product__vendor=vendor)
            ).distinct()
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by method
        method = self.request.GET.get('method', '')
        if method:
            queryset = queryset.filter(method=method)
        
        return queryset.order_by('-created_at')
    
    def get_filter_options(self):
        return {
            'statuses': Payment.PAYMENT_STATUS,
            'methods': Payment.PAYMENT_METHOD,
        }


class PaymentDetailView(BaseAdminDetailView):
    """View payment details"""
    
    model = Payment
    template_name = 'admin_dashboard/payments/payment_detail.html'
    context_object_name = 'payment'
    vendor_field = None
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Payments', 'url': reverse_lazy('admin_dashboard:payment_list')},
            {'title': f'Payment #{str(self.object.id)[:8]}', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = Payment.objects.select_related('order__user', 'order__address')
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                Q(order__vendor=vendor) | Q(order__items__variant__product__vendor=vendor)
            ).distinct()
        return queryset

