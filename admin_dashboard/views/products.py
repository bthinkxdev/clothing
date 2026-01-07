# admin_dashboard/views/products.py
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.contrib import messages

from .base import (
    BaseAdminListView, BaseAdminDetailView, BaseAdminCreateView,
    BaseAdminUpdateView, BaseAdminDeleteView, BaseAdminAPIView
)
from app.models import Product, ProductVariant, ProductImage, Category, Inventory
from ..utils import FilterHelper
from ..forms import ProductForm, ProductVariantFormSet, ProductImageFormSet


class ProductListView(BaseAdminListView):
    """List all products"""
    
    model = Product
    template_name = 'admin_dashboard/products/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Products', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('category').prefetch_related('variants', 'images')
        
        # Apply filters
        filters = FilterHelper.build_product_filters(self.request)
        
        # Handle search
        search = filters.pop('_search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(brand__icontains=search) |
                Q(description__icontains=search)
            )
        
        queryset = queryset.filter(**filters)
        
        # Annotate with sales data
        queryset = queryset.annotate(
            total_sold=Count('variants__orderitem'),
            total_stock=Sum('variants__inventory__quantity')
        )
        
        # Ordering
        order_by = self.request.GET.get('order_by', '-created_at')
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_filter_options(self):
        categories = Category.objects.filter(is_active=True)
        brands = Product.objects.values_list('brand', flat=True).distinct().exclude(brand='')
        
        return {
            'categories': categories,
            'brands': brands,
        }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        queryset = self.get_queryset()
        context['total_products'] = queryset.count()
        context['active_products'] = queryset.filter(is_active=True).count()
        context['filter_options'] = self.get_filter_options() 
        
        return context


class ProductDetailView(BaseAdminDetailView):
    """View product details"""
    
    model = Product
    template_name = 'admin_dashboard/products/product_detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    context_object_name = 'product'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Products', 'url': reverse_lazy('admin_dashboard:product_list')},
            {'title': self.object.name, 'url': '#'},
        ]
    
    def get_queryset(self):
        return super().get_queryset().select_related('category').prefetch_related(
            'variants__inventory',
            'images',
            'reviews'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        product = self.object
        
        # Sales statistics
        from django.db.models import Sum
        from app.models import OrderItem
        
        sales_data = OrderItem.objects.filter(
            variant__product=product,
            order__status__in=['paid', 'processing', 'shipped', 'delivered']
        ).aggregate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('unit_price')
        )
        
        context['total_sold'] = sales_data['total_sold'] or 0
        context['total_revenue'] = sales_data['total_revenue'] or 0
        
        # Stock summary
        context['total_stock'] = sum(v.available_stock() for v in product.variants.all())
        context['variants_count'] = product.variants.count()
        
        # Reviews
        context['avg_rating'] = product.avg_rating()
        context['total_reviews'] = product.reviews.count()
        
        return context


class ProductCreateView(BaseAdminCreateView):
    """Create new product"""
    
    model = Product
    form_class = ProductForm
    template_name = 'admin_dashboard/products/product_form.html'
    success_url = reverse_lazy('admin_dashboard:product_list')
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Products', 'url': reverse_lazy('admin_dashboard:product_list')},
            {'title': 'Create Product', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['variant_formset'] = ProductVariantFormSet(self.request.POST)
            context['image_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES)
        else:
            context['variant_formset'] = ProductVariantFormSet()
            context['image_formset'] = ProductImageFormSet()
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        variant_formset = context['variant_formset']
        image_formset = context['image_formset']

        # Save the product FIRST to get an ID
        self.object = form.save()
        
        # Now set the product instance for formsets
        variant_formset.instance = self.object
        image_formset.instance = self.object
        
        if variant_formset.is_valid() and image_formset.is_valid():
            self.object = form.save()
            
            # Save variants
            variants = variant_formset.save(commit=False)
            for variant in variants:
                variant.product = self.object
                variant.save()
            
            # Save images
            images = image_formset.save(commit=False)
            for image in images:
                image.product = self.object
                image.save()
            
            messages.success(self.request, 'Product created successfully!')
            return redirect(self.get_success_url())  # pyright: ignore[reportUndefinedVariable]
        else:
            return self.form_invalid(form)


class ProductUpdateView(BaseAdminUpdateView):
    """Update product"""
    
    model = Product
    form_class = ProductForm
    template_name = 'admin_dashboard/products/product_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['variant_formset'] = ProductVariantFormSet(self.request.POST, instance=self.object)
            context['image_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['variant_formset'] = ProductVariantFormSet(instance=self.object)
            context['image_formset'] = ProductImageFormSet(instance=self.object)
        return context
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Products', 'url': reverse_lazy('admin_dashboard:product_list')},
            {'title': self.object.name, 'url': reverse_lazy('admin_dashboard:product_detail', kwargs={'slug': self.object.slug})},
            {'title': 'Update', 'url': '#'},
        ]
    
    def get_success_url(self):
        return reverse_lazy('admin_dashboard:product_detail', kwargs={'slug': self.object.slug})

    def form_valid(self, form):
        context = self.get_context_data()
        variant_formset = context['variant_formset']
        image_formset = context['image_formset']
        
        if variant_formset.is_valid() and image_formset.is_valid():
            self.object = form.save()
            
            variants = variant_formset.save(commit=False)
            for variant in variants:
                variant.product = self.object
                variant.save()
            for variant in variant_formset.deleted_objects:
                variant.delete()
            
            images = image_formset.save(commit=False)
            for image in images:
                image.product = self.object
                image.save()
            for image in image_formset.deleted_objects:
                image.delete()
            
            messages.success(self.request, 'Product updated successfully!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class ProductDeleteView(BaseAdminDeleteView):
    """Delete product"""
    
    model = Product
    success_url = reverse_lazy('admin_dashboard:product_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def delete(self, request, *args, **kwargs):
        # Soft delete - just set is_active to False
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        
        messages.success(request, 'Product deactivated successfully!')
        return redirect(self.success_url)


class ProductVariantManageView(BaseAdminDetailView):
    """Manage product variants"""
    
    model = Product
    template_name = 'admin_dashboard/products/product_variants.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Products', 'url': reverse_lazy('admin_dashboard:product_list')},
            {'title': self.object.name, 'url': reverse_lazy('admin_dashboard:product_detail', kwargs={'slug': self.object.slug})},
            {'title': 'Manage Variants', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['variant_formset'] = ProductVariantFormSet(
                self.request.POST,
                instance=self.object
            )
        else:
            context['variant_formset'] = ProductVariantFormSet(instance=self.object)
        
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        variant_formset = context['variant_formset']
        
        if variant_formset.is_valid():
            variant_formset.save()
            messages.success(request, 'Variants updated successfully!')
            return redirect('admin_dashboard:product_detail', slug=self.object.slug)
        
        return self.render_to_response(context)


class ProductBulkUpdateView(BaseAdminAPIView):
    """Bulk update products"""
    
    def post(self, request, *args, **kwargs):
        import json
        
        try:
            data = json.loads(request.body)
            product_ids = data.get('product_ids', [])
            action = data.get('action')
            
            if not product_ids:
                return self.error_response('No products selected')
            
            products = Product.objects.filter(id__in=product_ids)
            
            if action == 'activate':
                products.update(is_active=True)
                return self.success_response(message='Products activated')
            elif action == 'deactivate':
                products.update(is_active=False)
                return self.success_response(message='Products deactivated')
            elif action == 'delete':
                products.delete()
                return self.success_response(message='Products deleted')
            
            return self.error_response('Invalid action')
            
        except Exception as e:
            return self.error_response(str(e))

