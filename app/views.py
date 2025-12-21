# app/views.py
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum, F, Prefetch, Min, Max
from django.db import connection
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.conf import settings
from django.views import View
from django.views.generic import (
    TemplateView, ListView, DetailView, 
    CreateView, UpdateView, DeleteView, FormView
)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction

from .models import (
    User, Product, ProductVariant, ProductImage, Category,
    Cart, CartItem, Wishlist, WishlistItem, Order, OrderItem,
    Payment, Address, Coupon, CouponUsage, GiftCard, Review,
    LoyaltyPoint, Referral, Banner, ProductView as ProductViewLog,
    Inventory, NewsletterSubscriber, ShippingZone
)
from .forms import (
    AddressForm, ReviewForm, ContactForm, OTPLoginForm,
    NewsletterForm, QuestionForm, ProfileForm, OrderTrackingForm
)
from .utils import (
    send_otp, verify_otp, generate_order_id, 
    calculate_shipping, calculate_tax, get_cart_or_create,
    get_wishlist_or_create, check_pincode_serviceability,
    get_razorpay_client, send_order_confirmation_email
)


class CartMixin:
    """Mixin to add cart context to views"""
    def get_cart_context(self):
        if self.request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=self.request.user, is_active=True)
            cart_count = cart.item_count()
        else:
            # Handle guest carts using session
            cart = None
            cart_count = 0
        return {'cart': cart, 'cart_count': cart_count}


class WishlistMixin:
    """Mixin to add wishlist context"""
    def get_wishlist_context(self):
        if self.request.user.is_authenticated:
            wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
            wishlist_count = wishlist.items.count()
        else:
            wishlist = None
            wishlist_count = 0
        return {'wishlist': wishlist, 'wishlist_count': wishlist_count}


class CommonContextMixin(CartMixin, WishlistMixin):
    """Combines common context data for all views"""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_cart_context())
        context.update(self.get_wishlist_context())
        context['categories'] = Category.objects.filter(is_active=True, parent=None)
        return context


# ========================
# HOME & LANDING
# ========================

class HomeView(CommonContextMixin, TemplateView):
    template_name = 'home.html'

    def _filter_by_tag(self, queryset, tag):
        """Filter products by tag in a database-agnostic way"""
        db_backend = connection.vendor
        if db_backend == 'sqlite':
            # For SQLite, filter in Python
            products = list(queryset)
            return [p for p in products if isinstance(p.tags, list) and tag in p.tags]
        else:
            # For PostgreSQL and others, use contains lookup
            return queryset.filter(tags__contains=[tag])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        
        # Active banners
        context['banners'] = Banner.objects.filter(
            active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('order')
        
        # Featured products - database-agnostic tag filtering
        base_queryset = Product.objects.filter(
            is_active=True
        ).prefetch_related('variants', 'images')
        
        new_arrivals = self._filter_by_tag(base_queryset, 'new')[:12]
        best_sellers = self._filter_by_tag(base_queryset, 'best-seller')[:12]
        
        context['new_arrivals'] = new_arrivals
        context['best_sellers'] = best_sellers
        
        context['sale_products'] = Product.objects.filter(
            is_active=True,
            variants__discount_percent__gt=0
        ).distinct().prefetch_related('variants', 'images')[:12]
        
        # Categories
        context['featured_categories'] = Category.objects.filter(
            is_active=True,
            parent=None
        )[:8]
        
        return context


# ========================
# CATALOG & PRODUCTS
# ========================

class ProductListView(CommonContextMixin, ListView):
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = 24

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).prefetch_related(
            'variants__inventory', 'images'
        ).select_related('category')
        
        # Category filter
        category_slug = self.kwargs.get('category_slug')
        subcategory_slug = self.kwargs.get('subcategory_slug')
        
        if subcategory_slug:
            category = get_object_or_404(Category, slug=subcategory_slug, is_active=True)
            queryset = queryset.filter(category=category)
        elif category_slug:
            category = get_object_or_404(Category, slug=category_slug, is_active=True)
            # Include subcategories
            category_ids = [category.id] + list(category.children.values_list('id', flat=True))
            queryset = queryset.filter(category_id__in=category_ids)
        
        # Size filter
        sizes = self.request.GET.getlist('size')
        if sizes:
            queryset = queryset.filter(variants__size__in=sizes).distinct()
        
        # Color filter
        colors = self.request.GET.getlist('color')
        if colors:
            queryset = queryset.filter(variants__color__in=colors).distinct()
        
        # Brand filter
        brands = self.request.GET.getlist('brand')
        if brands:
            queryset = queryset.filter(brand__in=brands)
        
        # Price range filter
        price_min = self.request.GET.get('price_min')
        price_max = self.request.GET.get('price_max')
        if price_min:
            queryset = queryset.filter(variants__price__gte=price_min).distinct()
        if price_max:
            queryset = queryset.filter(variants__price__lte=price_max).distinct()
        
        # Discount filter
        discount = self.request.GET.get('discount')
        if discount:
            queryset = queryset.filter(variants__discount_percent__gte=discount).distinct()
        
        # Availability filter
        availability = self.request.GET.get('availability')
        if availability == 'in_stock':
            queryset = queryset.filter(variants__inventory__quantity__gt=0).distinct()
        elif availability == 'out_of_stock':
            queryset = queryset.filter(variants__inventory__quantity=0).distinct()
        elif availability == 'preorder':
            queryset = queryset.filter(variants__is_preorder=True).distinct()
        
        # Rating filter
        rating = self.request.GET.get('rating')
        if rating:
            queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).filter(avg_rating__gte=rating)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'popularity')
        if sort_by == 'price_low':
            queryset = queryset.order_by('variants__price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-variants__price')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'discount':
            queryset = queryset.order_by('-variants__discount_percent')
        elif sort_by == 'rating':
            queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
        elif sort_by == 'popularity':
            queryset = queryset.annotate(view_count=Count('views')).order_by('-view_count')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current category
        category_slug = self.kwargs.get('category_slug')
        subcategory_slug = self.kwargs.get('subcategory_slug')
        
        if subcategory_slug:
            context['current_category'] = get_object_or_404(Category, slug=subcategory_slug)
        elif category_slug:
            context['current_category'] = get_object_or_404(Category, slug=category_slug)
        else:
            context['current_category'] = None
        
        # Breadcrumbs
        breadcrumbs = [{'name': 'Home', 'url': '/'}]
        if context['current_category']:
            if context['current_category'].parent:
                breadcrumbs.append({
                    'name': context['current_category'].parent.name,
                    'url': reverse('product_list_category', kwargs={'category_slug': context['current_category'].parent.slug})
                })
            breadcrumbs.append({'name': context['current_category'].name, 'url': ''})
        context['breadcrumbs'] = breadcrumbs
        
        # Filter options
        context['available_sizes'] = ProductVariant.objects.filter(
            product__is_active=True
        ).values_list('size', flat=True).distinct().exclude(size__isnull=True)
        
        context['available_colors'] = ProductVariant.objects.filter(
            product__is_active=True
        ).values_list('color', flat=True).distinct().exclude(color__isnull=True)
        
        context['available_brands'] = Product.objects.filter(
            is_active=True
        ).values_list('brand', flat=True).distinct().exclude(brand='')
        
        # Price range
        price_range = ProductVariant.objects.filter(
            product__is_active=True
        ).aggregate(min_price=Min('price'), max_price=Max('price'))
        context['price_range'] = price_range
        
        # Applied filters
        context['applied_filters'] = {
            'sizes': self.request.GET.getlist('size'),
            'colors': self.request.GET.getlist('color'),
            'brands': self.request.GET.getlist('brand'),
            'price_min': self.request.GET.get('price_min'),
            'price_max': self.request.GET.get('price_max'),
            'discount': self.request.GET.get('discount'),
            'availability': self.request.GET.get('availability'),
            'rating': self.request.GET.get('rating'),
        }
        
        context['sort_by'] = self.request.GET.get('sort', 'popularity')
        context['per_page'] = int(self.request.GET.get('per_page', 24))
        context['total_count'] = self.get_queryset().count()
        
        return context


class ProductDetailView(CommonContextMixin, DetailView):
    model = Product
    template_name = 'products/detail.html'
    context_object_name = 'product'
    slug_field = 'slug'

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True).prefetch_related(
            'variants__inventory', 'images', 'reviews'
        ).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Log product view
        if self.request.user.is_authenticated:
            ProductViewLog.objects.create(
                product=product,
                user=self.request.user
            )
        else:
            session_id = self.request.session.session_key
            if session_id:
                ProductViewLog.objects.create(
                    product=product,
                    session_id=session_id
                )
        
        # Variants
        context['variants'] = product.variants.filter(is_active=True).select_related('inventory')
        context['default_variant'] = product.main_variant()
        
        # Images
        context['images'] = product.images.all()
        
        # Reviews
        reviews = product.reviews.filter(approved=True)
        context['reviews'] = reviews[:10]
        context['total_reviews'] = reviews.count()
        context['avg_rating'] = product.avg_rating()
        
        # Rating breakdown
        rating_breakdown = {}
        for i in range(1, 6):
            count = reviews.filter(rating=i).count()
            percentage = (count / context['total_reviews'] * 100) if context['total_reviews'] > 0 else 0
            rating_breakdown[i] = {'count': count, 'percentage': percentage}
        context['rating_breakdown'] = rating_breakdown
        
        # Check if user can review
        if self.request.user.is_authenticated:
            has_purchased = OrderItem.objects.filter(
                order__user=self.request.user,
                order__status='delivered',
                variant__product=product
            ).exists()
            context['can_review'] = has_purchased
            context['user_review'] = Review.objects.filter(
                user=self.request.user,
                product=product
            ).first()
        else:
            context['can_review'] = False
            context['user_review'] = None
        
        # Similar products
        context['similar_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(id=product.id).prefetch_related('variants', 'images')[:8]
        
        # Recently viewed (from session)
        recently_viewed_ids = self.request.session.get('recently_viewed', [])
        context['recently_viewed'] = Product.objects.filter(
            id__in=recently_viewed_ids,
            is_active=True
        ).exclude(id=product.id).prefetch_related('variants', 'images')[:8]
        
        # Add current product to recently viewed
        if product.id not in recently_viewed_ids:
            recently_viewed_ids.insert(0, product.id)
            self.request.session['recently_viewed'] = recently_viewed_ids[:20]
        
        # Breadcrumbs
        breadcrumbs = [{'name': 'Home', 'url': '/'}]
        if product.category:
            if product.category.parent:
                breadcrumbs.append({
                    'name': product.category.parent.name,
                    'url': reverse('product_list_category', kwargs={'category_slug': product.category.parent.slug})
                })
            breadcrumbs.append({
                'name': product.category.name,
                'url': reverse('product_list_category', kwargs={'category_slug': product.category.slug})
            })
        breadcrumbs.append({'name': product.name, 'url': ''})
        context['breadcrumbs'] = breadcrumbs
        
        return context


class ProductQuickView(CommonContextMixin, DetailView):
    model = Product
    template_name = 'products/quick_view.html'
    context_object_name = 'product'
    slug_field = 'slug'

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True).prefetch_related(
            'variants__inventory', 'images', 'reviews'
        ).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context['images'] = product.images.all()
        context['variants'] = product.variants.filter(is_active=True).select_related('inventory')
        context['default_variant'] = product.main_variant()
        context['avg_rating'] = product.avg_rating()
        context['total_reviews'] = product.reviews.filter(approved=True).count()
        return context


class ProductSearchView(CommonContextMixin, ListView):
    model = Product
    template_name = 'products/search.html'
    context_object_name = 'products'
    paginate_by = 24

    def _filter_by_tag(self, term):
        """Database-agnostic tag filtering (SQLite fallback)."""
        if connection.vendor == 'sqlite':
            products = Product.objects.filter(is_active=True)
            term_lower = term.lower()
            ids = []
            for p in products:
                if isinstance(p.tags, list) and any(term_lower in str(t).lower() for t in p.tags):
                    ids.append(p.id)
            return Product.objects.filter(id__in=ids)
        else:
            return Product.objects.filter(is_active=True, tags__contains=[term])

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return Product.objects.none()
        
        base = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(brand__icontains=query) |
            Q(category__name__icontains=query)
        ).filter(is_active=True).prefetch_related('variants', 'images')

        tag_qs = self._filter_by_tag(query)

        queryset = (base | tag_qs).distinct()
        
        # Apply same filters as ProductListView
        # ... (reuse filter logic)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        context['query'] = query
        context['total_results'] = self.get_queryset().count()
        
        # Search suggestions (popular searches if no results)
        if context['total_results'] == 0:
            context['popular_searches'] = ['T-shirts', 'Jeans', 'Dresses', 'Shoes', 'Jackets']
            # DB-agnostic trending fetch
            if connection.vendor == 'sqlite':
                trending_ids = []
                for p in Product.objects.filter(is_active=True):
                    if isinstance(p.tags, list) and 'trending' in p.tags:
                        trending_ids.append(p.id)
                context['trending_products'] = Product.objects.filter(id__in=trending_ids)[:8]
            else:
                context['trending_products'] = Product.objects.filter(
                    is_active=True,
                    tags__contains=['trending']
                )[:8]
        
        return context


# ========================
# CART MANAGEMENT
# ========================

class CartView(CommonContextMixin, TemplateView):
    template_name = 'cart/cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=self.request.user, is_active=True)
            cart_items = cart.items.select_related('variant__product', 'variant__inventory').all()
            
            # Check stock issues
            stock_issues = []
            for item in cart_items:
                available = item.variant.available_stock()
                if available < item.quantity:
                    stock_issues.append({
                        'item': item,
                        'available': available,
                        'requested': item.quantity
                    })
            
            context['cart'] = cart
            context['cart_items'] = cart_items
            context['subtotal'] = cart.total()
            context['shipping'] = calculate_shipping(cart)
            context['tax'] = calculate_tax(cart)
            context['total'] = context['subtotal'] + context['shipping'] + context['tax']
            context['stock_issues'] = stock_issues
            
            # Available coupons
            context['available_coupons'] = Coupon.objects.filter(
                active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
        else:
            context['cart'] = None
            context['cart_items'] = []
            context['subtotal'] = Decimal('0.00')

        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Cart', 'url': ''},
        ]
        
        return context


class CartAddView(LoginRequiredMixin, View):
    def post(self, request):
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))
        
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        
        # Check stock
        available = variant.available_stock()
        if available < quantity:
            messages.error(request, f'Only {available} items available in stock.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity = F('quantity') + quantity
            cart_item.save()
            cart_item.refresh_from_db()
            
            # Recheck stock
            if cart_item.quantity > available:
                cart_item.quantity = available
                cart_item.save()
                messages.warning(request, f'Only {available} items added to cart.')
        
        messages.success(request, 'Item added to cart!')
        return redirect('cart')


class CartUpdateView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, 'Item removed from cart.')
        else:
            available = cart_item.variant.available_stock()
            if quantity > available:
                messages.error(request, f'Only {available} items available.')
                quantity = available
            
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated.')
        
        return redirect('cart')


class CartRemoveView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        messages.success(request, 'Item removed from cart.')
        return redirect('cart')


class CartClearView(LoginRequiredMixin, View):
    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user, is_active=True)
        cart.items.all().delete()
        messages.success(request, 'Cart cleared.')
        return redirect('cart')


# ========================
# WISHLIST MANAGEMENT
# ========================

class WishlistView(LoginRequiredMixin, CommonContextMixin, ListView):
    template_name = 'wishlist/wishlist.html'
    context_object_name = 'wishlist_items'

    def get_queryset(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist.items.select_related('variant__product', 'variant__inventory').all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_items'] = self.get_queryset().count()
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Wishlist', 'url': ''},
        ]
        
        # Calculate total value
        total_value = Decimal('0.00')
        for item in self.get_queryset():
            total_value += item.variant.get_price()
        context['total_value'] = total_value
        
        return context


class WishlistAddView(LoginRequiredMixin, View):
    def post(self, request):
        variant_id = request.POST.get('variant_id')
        variant = get_object_or_404(ProductVariant, id=variant_id)
        
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        WishlistItem.objects.get_or_create(wishlist=wishlist, variant=variant)
        
        messages.success(request, 'Added to wishlist!')
        return redirect(request.META.get('HTTP_REFERER', '/'))


class WishlistRemoveView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
        wishlist_item.delete()
        messages.success(request, 'Removed from wishlist.')
        return redirect('wishlist')


class WishlistMoveToCartView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
        
        # Add to cart
        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
        CartItem.objects.get_or_create(
            cart=cart,
            variant=wishlist_item.variant,
            defaults={'quantity': 1}
        )
        
        # Remove from wishlist
        wishlist_item.delete()
        
        messages.success(request, 'Moved to cart!')
        return redirect('wishlist')


# ========================
# AUTHENTICATION
# ========================

class LoginView(TemplateView):
    template_name = 'auth/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '/')
        return context


class OTPSendView(View):
    def post(self, request):
        phone = request.POST.get('phone')
        if not phone:
            return JsonResponse({'success': False, 'error': 'Phone number required'})
        
        # Generate and send OTP
        otp = send_otp(phone)
        
        # Store in session
        request.session['login_phone'] = phone
        request.session['login_otp'] = otp
        request.session['otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).isoformat()
        
        return JsonResponse({'success': True, 'message': 'OTP sent successfully'})


class OTPVerifyView(View):
    def post(self, request):
        phone = request.session.get('login_phone')
        otp = request.POST.get('otp')
        stored_otp = request.session.get('login_otp')
        expiry = request.session.get('otp_expiry')
        
        if not all([phone, otp, stored_otp, expiry]):
            return JsonResponse({'success': False, 'error': 'Invalid request'})
        
        # Check expiry
        if timezone.now() > timezone.datetime.fromisoformat(expiry):
            return JsonResponse({'success': False, 'error': 'OTP expired'})
        
        # Verify OTP
        if otp == stored_otp:
            # Get or create user
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={'username': phone, 'role': 'customer'}
            )
            
            # Login user
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
            
            # Clear session
            del request.session['login_phone']
            del request.session['login_otp']
            del request.session['otp_expiry']
            
            next_url = request.POST.get('next', '/')
            return JsonResponse({'success': True, 'redirect': next_url})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid OTP'})


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, 'Logged out successfully.')
        return redirect('home')


# ========================
# CHECKOUT FLOW
# ========================

class CheckoutAddressView(LoginRequiredMixin, CommonContextMixin, FormView):
    template_name = 'checkout/address.html'
    form_class = AddressForm
    success_url = reverse_lazy('checkout_shipping')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['addresses'] = self.request.user.addresses.all()
        context['default_address'] = self.request.user.addresses.filter(is_default=True).first()
        context['selected_address_id'] = self.request.session.get('checkout_address_id')
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Checkout', 'url': ''},
            {'name': 'Address', 'url': ''},
        ]
        
        # Cart summary
        cart = get_object_or_404(Cart, user=self.request.user, is_active=True)
        context['cart'] = cart
        context['cart_items'] = cart.items.select_related('variant__product').all()
        context['subtotal'] = cart.total()
        
        return context

    def form_valid(self, form):
        address = form.save(commit=False)
        address.user = self.request.user
        address.save()
        self.request.session['checkout_address_id'] = address.id
        messages.success(self.request, 'Address added successfully.')
        return super().form_valid(form)


class CheckoutAddressSelectView(LoginRequiredMixin, View):
    def post(self, request, address_id):
        address = get_object_or_404(Address, id=address_id, user=request.user)
        request.session['checkout_address_id'] = address.id
        return redirect('checkout_shipping')


class CheckoutShippingView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = 'checkout/shipping.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Checkout', 'url': ''},
            {'name': 'Shipping', 'url': ''},
        ]
        
        # Get selected address
        address_id = self.request.session.get('checkout_address_id')
        if not address_id:
            return redirect('checkout_address')
        
        address = get_object_or_404(Address, id=address_id, user=self.request.user)
        context['selected_address'] = address
        
        # Get shipping options
        cart = get_object_or_404(Cart, user=self.request.user, is_active=True)
        context['cart'] = cart
        context['shipping_options'] = self.get_shipping_options(address, cart)
        context['subtotal'] = cart.total()
        
        return context

    def get_shipping_options(self, address, cart):
        # Mock shipping options based on zone/cart value
        options = [
            {
                'id': 'standard',
                'name': 'Standard Shipping',
                'description': '5-7 business days',
                'cost': Decimal('50.00'),
                'estimated_days': 7
            },
            {
                'id': 'express',
                'name': 'Express Shipping',
                'description': '2-3 business days',
                'cost': Decimal('150.00'),
                'estimated_days': 3
            },
        ]
        
        # Free shipping for orders above 1000
        if cart.total() >= Decimal('1000.00'):
            options[0]['cost'] = Decimal('0.00')
            options[0]['name'] = 'Free Standard Shipping'
        
        return options

    def post(self, request):
        shipping_id = request.POST.get('shipping_option')
        request.session['checkout_shipping_id'] = shipping_id
        return redirect('checkout_payment')


class CheckoutPaymentView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = 'checkout/payment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Checkout', 'url': ''},
            {'name': 'Payment', 'url': ''},
        ]
        
        # Verify previous steps
        if not self.request.session.get('checkout_address_id'):
            return redirect('checkout_address')
        if not self.request.session.get('checkout_shipping_id'):
            return redirect('checkout_shipping')
        
        # Get data
        address = get_object_or_404(Address, id=self.request.session['checkout_address_id'])
        cart = get_object_or_404(Cart, user=self.request.user, is_active=True)
        
        context['selected_address'] = address
        context['cart'] = cart
        context['cart_items'] = cart.items.select_related('variant__product').all()
        
        # Calculate totals
        subtotal = cart.total()
        shipping_cost = self.get_shipping_cost()
        tax = calculate_tax(cart)
        discount = Decimal('0.00')
        
        # Apply coupon if any
        coupon_code = self.request.session.get('applied_coupon')
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, active=True).first()
            if coupon and coupon.is_valid_for_user(self.request.user, subtotal):
                discount = coupon.discount_amount(subtotal)
                context['applied_coupon'] = coupon
        
        context['subtotal'] = subtotal
        context['shipping'] = shipping_cost
        context['tax'] = tax
        context['discount'] = discount
        context['total'] = subtotal + shipping_cost + tax - discount
        
        # Payment methods
        context['payment_methods'] = self.get_payment_methods(address, cart)
        context['wallet_balance'] = self.request.user.wallet_balance
        
        return context

    def get_shipping_cost(self):
        shipping_id = self.request.session.get('checkout_shipping_id')
        if shipping_id == 'express':
            return Decimal('150.00')
        return Decimal('50.00')

    def get_payment_methods(self, address, cart):
        methods = [
            {'id': 'razorpay', 'name': 'Razorpay (Card/UPI/Net Banking)', 'icon': 'razorpay'},
            {'id': 'wallet', 'name': 'Wallet', 'icon': 'wallet'},
        ]
        
        # COD available for certain pincodes
        if check_pincode_serviceability(address.postal_code, 'cod'):
            methods.append({
                'id': 'cod',
                'name': 'Cash on Delivery',
                'icon': 'cod',
                'extra_charge': Decimal('40.00')
            })
        
        return methods


class ApplyCouponView(LoginRequiredMixin, View):
    def post(self, request):
        coupon_code = request.POST.get('coupon_code')
        cart = get_object_or_404(Cart, user=request.user, is_active=True)
        
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            if coupon.is_valid_for_user(request.user, cart.total()):
                request.session['applied_coupon'] = coupon_code
                messages.success(request, f'Coupon {coupon_code} applied successfully!')
            else:
                messages.error(request, 'This coupon is not valid for your order.')
        except Coupon.DoesNotExist:
            messages.error(request, 'Invalid coupon code.')
        
        return redirect('checkout_payment')


class RemoveCouponView(LoginRequiredMixin, View):
    def post(self, request):
        if 'applied_coupon' in request.session:
            del request.session['applied_coupon']
            messages.success(request, 'Coupon removed.')
        return redirect('checkout_payment')


class OrderCreateView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request):
        # Get checkout data
        address_id = request.session.get('checkout_address_id')
        shipping_id = request.session.get('checkout_shipping_id')
        payment_method = request.POST.get('payment_method')
        
        if not all([address_id, shipping_id, payment_method]):
            messages.error(request, 'Please complete all checkout steps.')
            return redirect('checkout_address')
        
        # Get cart and address
        cart = get_object_or_404(Cart, user=request.user, is_active=True)
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Verify stock for all items
        for item in cart.items.select_related('variant__inventory').all():
            if item.variant.available_stock() < item.quantity:
                messages.error(request, f'Insufficient stock for {item.variant.product.name}')
                return redirect('cart')
        
        # Calculate totals
        subtotal = cart.total()
        shipping_cost = Decimal('50.00') if shipping_id == 'standard' else Decimal('150.00')
        tax = calculate_tax(cart)
        discount = Decimal('0.00')
        
        # Apply coupon
        coupon = None
        coupon_code = request.session.get('applied_coupon')
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, active=True).first()
            if coupon:
                discount = coupon.discount_amount(subtotal)
        
        total = subtotal + shipping_cost + tax - discount
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            address=address,
            status='pending',
            subtotal=subtotal,
            shipping_amount=shipping_cost,
            tax_amount=tax,
            discount_amount=discount,
            total=total,
            coupon=coupon
        )
        
        # Create order items
        for cart_item in cart.items.select_related('variant').all():
            OrderItem.objects.create(
                order=order,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                unit_price=cart_item.variant.get_price()
            )
        
        # Reserve inventory
        for item in order.items.select_related('variant__inventory').all():
            item.variant.inventory.reserve(item.quantity)
        
        # Create coupon usage if applicable
        if coupon:
            CouponUsage.objects.create(
                coupon=coupon,
                user=request.user,
                order=order
            )
        
        # Initialize payment
        if payment_method == 'razorpay':
            # Create Razorpay payment
            payment = Payment.objects.create(
                order=order,
                amount=total,
                method='razorpay',
                status='initiated'
            )
            
            # Get Razorpay order
            client = get_razorpay_client()
            razorpay_order = client.order.create({
                'amount': int(total * 100),  # paise
                'currency': 'INR',
                'receipt': str(order.id),
            })
            
            payment.reference = razorpay_order['id']
            payment.save()
            
            # Store in session for verification
            request.session['pending_order_id'] = str(order.id)
            request.session['razorpay_order_id'] = razorpay_order['id']
            
            return JsonResponse({
                'success': True,
                'razorpay_order_id': razorpay_order['id'],
                'amount': int(total * 100),
                'currency': 'INR',
                'name': 'Your Store',
                'order_id': str(order.id)
            })
        
        elif payment_method == 'wallet':
            if request.user.wallet_balance >= total:
                # Deduct from wallet
                request.user.wallet_balance = F('wallet_balance') - total
                request.user.save()
                request.user.refresh_from_db()
                
                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    amount=total,
                    method='wallet',
                    status='success'
                )
                
                # Mark order as paid
                order.mark_paid(payment)
                
                # Clear cart and session
                cart.items.all().delete()
                self.clear_checkout_session(request)
                
                return redirect('order_success', id=order.id)
            else:
                messages.error(request, 'Insufficient wallet balance.')
                order.delete()
                return redirect('checkout_payment')
        
        elif payment_method == 'cod':
            # Create COD payment
            payment = Payment.objects.create(
                order=order,
                amount=total,
                method='cod',
                status='pending'
            )
            
            order.status = 'processing'
            order.save()
            
            # Clear cart and session
            cart.items.all().delete()
            self.clear_checkout_session(request)
            
            return redirect('order_success', id=order.id)
    
    def clear_checkout_session(self, request):
        keys_to_clear = ['checkout_address_id', 'checkout_shipping_id', 'applied_coupon', 'pending_order_id']
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayVerifyView(View):
    def post(self, request):
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        # Verify signature
        client = get_razorpay_client()
        try:
            client.utility.verify_payment_signature({
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': razorpay_signature
            })
            
            # Get payment
            payment = Payment.objects.get(reference=razorpay_order_id)
            payment.mark_success({
                'payment_id': razorpay_payment_id,
                'signature': razorpay_signature
            })
            
            # Clear cart
            cart = Cart.objects.get(user=payment.order.user, is_active=True)
            cart.items.all().delete()
            
            return JsonResponse({'success': True, 'order_id': str(payment.order.id)})
        
        except Exception as e:
            # Mark payment as failed
            payment = Payment.objects.filter(reference=razorpay_order_id).first()
            if payment:
                payment.status = 'failed'
                payment.save()
            
            return JsonResponse({'success': False, 'error': str(e)})


class OrderSuccessView(LoginRequiredMixin, CommonContextMixin, DetailView):
    model = Order
    template_name = 'orders/success.html'
    context_object_name = 'order'
    pk_url_kwarg = 'id'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_items'] = self.object.items.select_related('variant__product').all()
        context['payment'] = self.object.payments.filter(status='success').first()
        
        # Send confirmation email
        send_order_confirmation_email(self.object)
        
        return context


class OrderFailureView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/failure.html'
    context_object_name = 'order'
    pk_url_kwarg = 'id'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


# ========================
# ORDER MANAGEMENT
# ========================

class MyOrdersView(LoginRequiredMixin, CommonContextMixin, ListView):
    template_name = 'account/orders.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).prefetch_related('items__variant__product')
        
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-placed_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'My Orders', 'url': ''},
        ]
        return context


class OrderDetailView(LoginRequiredMixin, CommonContextMixin, DetailView):
    model = Order
    template_name = 'orders/detail.html'
    context_object_name = 'order'
    pk_url_kwarg = 'id'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_items'] = self.object.items.select_related('variant__product').all()
        context['payment'] = self.object.payments.filter(status='success').first()
        
        # Tracking timeline
        context['tracking_timeline'] = self.get_tracking_timeline()
        context['can_cancel'] = self.object.status in ['pending', 'processing']
        context['can_return'] = self.object.status == 'delivered'  # Add date logic
        
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'My Orders', 'url': reverse('my_orders')},
            {'name': str(self.object.id), 'url': ''},
        ]
        return context

    def get_tracking_timeline(self):
        order = self.object
        timeline = [
            {'status': 'placed', 'label': 'Order Placed', 'completed': True, 'date': order.placed_at},
            {'status': 'paid', 'label': 'Payment Confirmed', 'completed': order.status != 'pending'},
            {'status': 'processing', 'label': 'Processing', 'completed': order.status in ['processing', 'shipped', 'delivered']},
            {'status': 'shipped', 'label': 'Shipped', 'completed': order.status in ['shipped', 'delivered']},
            {'status': 'delivered', 'label': 'Delivered', 'completed': order.status == 'delivered'},
        ]
        return timeline


class OrderCancelView(LoginRequiredMixin, View):
    def post(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)
        
        if order.status not in ['pending', 'processing']:
            messages.error(request, 'This order cannot be cancelled.')
            return redirect('order_detail', id=id)
        
        with transaction.atomic():
            # Unreserve/restore inventory
            for item in order.items.select_related('variant__inventory').all():
                item.variant.inventory.unreserve(item.quantity)
            
            order.status = 'cancelled'
            order.save()
        
        messages.success(request, 'Order cancelled successfully.')
        return redirect('order_detail', id=id)


# ========================
# ACCOUNT MANAGEMENT
# ========================

class AccountDashboardView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = 'account/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Account', 'url': ''},
        ]
        context['recent_orders'] = Order.objects.filter(user=self.request.user)[:5]
        context['total_orders'] = Order.objects.filter(user=self.request.user).count()
        context['wallet_balance'] = self.request.user.wallet_balance
        
        loyalty = LoyaltyPoint.objects.filter(user=self.request.user).first()
        context['loyalty_points'] = loyalty.points if loyalty else 0
        
        context['saved_addresses'] = self.request.user.addresses.count()
        
        return context


class ProfileEditView(LoginRequiredMixin, CommonContextMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'account/profile_edit.html'
    success_url = reverse_lazy('account_dashboard')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Account', 'url': reverse('account_dashboard')},
            {'name': 'Edit Profile', 'url': ''},
        ]
        return context


class AddressListView(LoginRequiredMixin, CommonContextMixin, ListView):
    template_name = 'account/addresses.html'
    context_object_name = 'addresses'

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Addresses', 'url': ''},
        ]
        return context


class AddressCreateView(LoginRequiredMixin, CommonContextMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = 'account/address_form.html'
    success_url = reverse_lazy('address_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Address added successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Addresses', 'url': reverse('address_list')},
            {'name': 'Add', 'url': ''},
        ]
        return context


class AddressUpdateView(LoginRequiredMixin, CommonContextMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'account/address_form.html'
    success_url = reverse_lazy('address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Addresses', 'url': reverse('address_list')},
            {'name': 'Edit', 'url': ''},
        ]
        return context


class AddressDeleteView(LoginRequiredMixin, CommonContextMixin, DeleteView):
    model = Address
    success_url = reverse_lazy('address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Addresses', 'url': reverse('address_list')},
            {'name': 'Delete', 'url': ''},
        ]
        return context


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'reviews/form.html'
    success_url = reverse_lazy('my_reviews')

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, slug=kwargs['slug'])
        
        # Check if user has purchased
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status='delivered',
            variant__product=self.product
        ).exists()
        
        if not has_purchased:
            messages.error(request, 'You can only review products you have purchased.')
            return redirect('product_detail', slug=self.product.slug)
        
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.product = self.product
        messages.success(self.request, 'Review submitted successfully.')
        return super().form_valid(form)


class MyReviewsView(LoginRequiredMixin, CommonContextMixin, ListView):
    template_name = 'account/reviews.html'
    context_object_name = 'my_reviews'

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user).select_related('product')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Reviews', 'url': ''},
        ]
        return context


class WalletView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = 'account/wallet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wallet_balance'] = getattr(self.request.user, 'wallet_balance', 0)
        transactions = getattr(self.request.user, 'wallet_transactions', None)
        context['transactions'] = transactions.all() if transactions else []
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Wallet', 'url': ''},
        ]
        return context


class MyCouponsView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = 'account/coupons.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context['coupons'] = Coupon.objects.filter(active=True, end_date__gte=now)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Coupons', 'url': ''},
        ]
        return context


# ========================
# MISC VIEWS
# ========================

class NewsletterSubscribeView(FormView):
    form_class = NewsletterForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        NewsletterSubscriber.objects.get_or_create(email=email)
        messages.success(self.request, 'Subscribed to newsletter!')
        return super().form_valid(form)


class GuestOrderTrackingView(FormView):
    template_name = 'orders/track.html'
    form_class = OrderTrackingForm

    def form_valid(self, form):
        order_id = form.cleaned_data['order_id']
        email = form.cleaned_data['email']
        
        try:
            order = Order.objects.get(id=order_id, user__email=email)
            return render(self.request, self.template_name, {
                'form': form,
                'order': order,
                'order_items': order.items.all(),
            })
        except Order.DoesNotExist:
            messages.error(self.request, 'Order not found.')
            return self.form_invalid(form)


# ========================
# AJAX/API ENDPOINTS
# ========================

class VariantStockCheckView(View):
    def get(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, id=variant_id)
        available = variant.available_stock()
        
        return JsonResponse({
            'available': available,
            'in_stock': available > 0,
            'is_low': variant.inventory.is_low() if hasattr(variant, 'inventory') else False
        })


class ProductAutocompleteView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 2:
            return JsonResponse({'results': []})
        
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(brand__icontains=query),
            is_active=True
        )[:10]
        
        results = [{
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'url': p.get_absolute_url(),
        } for p in products]
        
        return JsonResponse({'results': results})