"""
app/admin.py - Super User-Friendly Customized Admin Dashboard
"""
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count, Q, Avg, F
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import (
    User, Address, Category, Product, ProductImage, ProductVariant, Inventory,
    Cart, CartItem, Wishlist, WishlistItem,
    Coupon, CouponUsage, GiftCard, LoyaltyPoint,
    Order, OrderItem, Payment,
    Review, Banner, NewsletterSubscriber, Referral,
    ProductView, AbandonedCartSnapshot, ShippingZone, SiteTheme
)


# ============================================
# CUSTOM ADMIN SITE WITH DASHBOARD
# ============================================
class CustomAdminSite(admin.AdminSite):
    site_header = "🛍️ My Awesome Store Dashboard"
    site_title = "Store Admin"
    index_title = "Welcome! Let's manage your store easily 😊"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='custom_dashboard'),
            path('quick-order-update/<uuid:order_id>/', self.admin_view(self.quick_order_update), name='quick_order_update'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Custom dashboard with beautiful cards and stats"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Calculate statistics
        context = {
            'total_orders': Order.objects.count(),
            'pending_orders': Order.objects.filter(status='pending').count(),
            'today_orders': Order.objects.filter(placed_at__date=today).count(),
            'week_revenue': Order.objects.filter(placed_at__date__gte=week_ago, status__in=['paid', 'delivered']).aggregate(Sum('total'))['total__sum'] or 0,
            'month_revenue': Order.objects.filter(placed_at__date__gte=month_ago, status__in=['paid', 'delivered']).aggregate(Sum('total'))['total__sum'] or 0,
            'total_customers': User.objects.filter(role='customer').count(),
            'new_customers_week': User.objects.filter(date_joined__date__gte=week_ago).count(),
            'low_stock_items': Inventory.objects.filter(quantity__lte=5).count(),
            'pending_reviews': Review.objects.filter(approved=False).count(),
            'recent_orders': Order.objects.select_related('user').order_by('-placed_at')[:10],
        }
        
        return render(request, 'custom_dashboard.html', context)
    
    def quick_order_update(self, request, order_id):
        """Quick AJAX order status update"""
        if request.method == 'POST':
            order = Order.objects.get(id=order_id)
            new_status = request.POST.get('status')
            order.status = new_status
            order.save()
            return JsonResponse({'success': True, 'message': f'Order updated to {new_status}!'})
        return JsonResponse({'success': False})

# Create custom admin site instance
custom_admin_site = CustomAdminSite(name='custom_admin')


# ============================================
# ENHANCED USER ADMIN
# ============================================
@admin.register(User, site=custom_admin_site)
class EnhancedUserAdmin(admin.ModelAdmin):
    list_display = ('user_avatar', 'username_display', 'email_display', 'role_badge', 'wallet_display', 'status_badge', 'orders_count', 'joined_date')
    list_filter = ('role', 'is_active', 'is_blocked', 'date_joined')
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_per_page = 20
    
    actions = ['block_users', 'unblock_users', 'add_wallet_balance']
    
    def user_avatar(self, obj):
        """Display user avatar/icon"""
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        color = colors[hash(obj.username) % len(colors)]
        initial = obj.username[0].upper()
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;background:{};color:white;'
            'display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:18px;">{}</div>',
            color, initial
        )
    user_avatar.short_description = '👤'
    
    def username_display(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        name = full_name if full_name else obj.username
        return format_html(
            '<strong style="color:#2c3e50;font-size:14px;">{}</strong><br>'
            '<small style="color:#7f8c8d;">@{}</small>',
            name, obj.username
        )
    username_display.short_description = '👤 User'
    
    def email_display(self, obj):
        return format_html(
            '<a href="mailto:{}" style="color:#3498db;text-decoration:none;">'
            '<i class="fas fa-envelope"></i> {}</a>',
            obj.email, obj.email
        )
    email_display.short_description = '📧 Email'
    
    def role_badge(self, obj):
        colors = {
            'customer': '#3498db',
            'staff': '#9b59b6',
            'admin': '#e74c3c'
        }
        icons = {
            'customer': '🛒',
            'staff': '👔',
            'admin': '👑'
        }
        return format_html(
            '<span style="background:{};color:white;padding:5px 12px;border-radius:15px;'
            'font-size:12px;font-weight:bold;white-space:nowrap;">{} {}</span>',
            colors.get(obj.role, '#95a5a6'),
            icons.get(obj.role, '👤'),
            obj.get_role_display()
        )
    role_badge.short_description = '🎭 Role'
    
    def wallet_display(self, obj):
        color = '#27ae60' if obj.wallet_balance > 0 else '#95a5a6'
        return format_html(
            '<strong style="color:{};font-size:14px;">₹{:,.2f}</strong>',
            color, obj.wallet_balance
        )
    wallet_display.short_description = '💰 Wallet'
    
    def status_badge(self, obj):
        if obj.is_blocked:
            return format_html('<span style="background:#e74c3c;color:white;padding:5px 10px;border-radius:10px;font-size:11px;">🚫 Blocked</span>')
        elif obj.is_active:
            return format_html('<span style="background:#27ae60;color:white;padding:5px 10px;border-radius:10px;font-size:11px;">✅ Active</span>')
        else:
            return format_html('<span style="background:#95a5a6;color:white;padding:5px 10px;border-radius:10px;font-size:11px;">⏸️ Inactive</span>')
    status_badge.short_description = '📊 Status'
    
    def orders_count(self, obj):
        count = obj.orders.count()
        url = reverse('admin:app_order_changelist') + f'?user__id__exact={obj.id}'
        return format_html(
            '<a href="{}" style="color:#3498db;text-decoration:none;font-weight:bold;">'
            '📦 {} orders</a>',
            url, count
        )
    orders_count.short_description = '📦 Orders'
    
    def joined_date(self, obj):
        return format_html(
            '<span style="color:#7f8c8d;font-size:12px;">{}</span>',
            obj.date_joined.strftime('%b %d, %Y')
        )
    joined_date.short_description = '📅 Joined'
    
    @admin.action(description='🚫 Block selected users')
    def block_users(self, request, queryset):
        count = queryset.update(is_blocked=True)
        self.message_user(request, f'✅ {count} users have been blocked.', messages.SUCCESS)
    
    @admin.action(description='✅ Unblock selected users')
    def unblock_users(self, request, queryset):
        count = queryset.update(is_blocked=False)
        self.message_user(request, f'✅ {count} users have been unblocked.', messages.SUCCESS)
    
    @admin.action(description='💰 Add ₹100 to wallet')
    def add_wallet_balance(self, request, queryset):
        for user in queryset:
            user.wallet_balance += Decimal('100.00')
            user.save()
        self.message_user(request, f'✅ Added ₹100 to {queryset.count()} users.', messages.SUCCESS)


# ============================================
# SUPER ENHANCED ORDER ADMIN
# ============================================
@admin.register(Order, site=custom_admin_site)
class SuperOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number_badge', 'customer_info', 'order_items_preview', 
        'amount_display', 'status_dropdown', 'payment_status', 
        'tracking_info', 'order_date', 'quick_actions'
    )
    list_filter = ('status', 'placed_at', 'updated_at')
    search_fields = ('id', 'user__username', 'user__email', 'tracking_number')
    ordering = ('-placed_at',)
    list_per_page = 25
    
    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered', 'cancel_orders']
    
    readonly_fields = ('id', 'placed_at', 'updated_at', 'order_summary_card')
    
    fieldsets = (
        ('📦 Order Information', {
            'fields': ('id', 'user', 'status', 'placed_at', 'updated_at'),
            'classes': ('wide',)
        }),
        ('💰 Payment Details', {
            'fields': ('subtotal', 'shipping_amount', 'tax_amount', 'discount_amount', 'total', 'coupon'),
        }),
        ('🚚 Shipping Information', {
            'fields': ('address', 'courier', 'tracking_number', 'expected_delivery'),
        }),
        ('📝 Additional Info', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('📊 Order Summary', {
            'fields': ('order_summary_card',),
        })
    )
    
    def order_number_badge(self, obj):
        """Large, colorful order number"""
        return format_html(
            '<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);'
            'color:white;padding:10px 15px;border-radius:10px;text-align:center;'
            'font-weight:bold;min-width:120px;">'
            '<div style="font-size:10px;opacity:0.9;">ORDER</div>'
            '<div style="font-size:16px;">#{}</div>'
            '</div>',
            str(obj.id)[:8].upper()
        )
    order_number_badge.short_description = '🔢 Order #'
    
    def customer_info(self, obj):
        """Customer details with avatar"""
        initial = obj.user.username[0].upper()
        email = obj.user.email
        phone = obj.user.phone or 'N/A'
        return format_html(
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<div style="width:35px;height:35px;border-radius:50%;background:#3498db;'
            'color:white;display:flex;align-items:center;justify-content:center;'
            'font-weight:bold;">{}</div>'
            '<div>'
            '<strong style="color:#2c3e50;">{}</strong><br>'
            '<small style="color:#7f8c8d;">📧 {}</small><br>'
            '<small style="color:#7f8c8d;">📱 {}</small>'
            '</div></div>',
            initial, obj.user.username, email, phone
        )
    customer_info.short_description = '👤 Customer'
    
    def order_items_preview(self, obj):
        """Show order items in a beautiful way"""
        items = obj.items.all()[:3]
        html = '<div style="max-width:200px;">'
        for item in items:
            html += f'<div style="padding:5px 0;border-bottom:1px solid #ecf0f1;">' \
                    f'<strong>{item.variant.product.name}</strong><br>' \
                    f'<small style="color:#7f8c8d;">Size: {item.variant.size or "N/A"} | ' \
                    f'Qty: {item.quantity} | ₹{item.unit_price}</small></div>'
        
        total_items = obj.items.count()
        if total_items > 3:
            html += f'<small style="color:#3498db;font-weight:bold;">+ {total_items - 3} more items</small>'
        html += '</div>'
        return format_html(html)
    order_items_preview.short_description = '📋 Items'
    
    def amount_display(self, obj):
        """Display amount with beautiful styling"""
        total = Decimal(obj.total) if obj.total is not None else Decimal('0')
        subtotal = Decimal(obj.subtotal) if obj.subtotal is not None else Decimal('0')
        discount = Decimal(obj.discount_amount) if obj.discount_amount is not None else Decimal('0')
        return format_html(
            '<div style="text-align:center;">'
            '<div style="font-size:20px;font-weight:bold;color:#27ae60;">₹{:,.2f}</div>'
            '<small style="color:#7f8c8d;">Subtotal: ₹{:,.2f}</small><br>'
            '<small style="color:#e74c3c;">Discount: ₹{:,.2f}</small>'
            '</div>',
            total, subtotal, discount
        )
    amount_display.short_description = '💰 Amount'
    
    def status_dropdown(self, obj):
        """Interactive status dropdown for quick update"""
        statuses = dict(Order.ORDER_STATUS)
        status_colors = {
            'pending': '#f39c12',
            'paid': '#3498db',
            'processing': '#9b59b6',
            'shipped': '#1abc9c',
            'delivered': '#27ae60',
            'cancelled': '#e74c3c',
            'refunded': '#95a5a6'
        }
        
        current_color = status_colors.get(obj.status, '#95a5a6')
        
        return format_html(
            '<select onchange="updateOrderStatus(this, \'{}\')" '
            'style="padding:8px 12px;border:2px solid {};background:{};color:white;'
            'border-radius:8px;font-weight:bold;cursor:pointer;font-size:13px;">'
            '{}'
            '</select>',
            obj.id,
            current_color,
            current_color,
            ''.join([
                f'<option value="{status}" {"selected" if status == obj.status else ""}>{label}</option>'
                for status, label in statuses.items()
            ])
        )
    status_dropdown.short_description = '📊 Status'
    
    def payment_status(self, obj):
        """Display payment status with icon"""
        payments = obj.payments.filter(status='success')
        if payments.exists():
            return format_html(
                '<span style="background:#27ae60;color:white;padding:5px 10px;'
                'border-radius:8px;font-size:11px;font-weight:bold;">✅ PAID</span>'
            )
        elif obj.payments.filter(status='pending').exists():
            return format_html(
                '<span style="background:#f39c12;color:white;padding:5px 10px;'
                'border-radius:8px;font-size:11px;font-weight:bold;">⏳ PENDING</span>'
            )
        else:
            return format_html(
                '<span style="background:#e74c3c;color:white;padding:5px 10px;'
                'border-radius:8px;font-size:11px;font-weight:bold;">❌ UNPAID</span>'
            )
    payment_status.short_description = '💳 Payment'
    
    def tracking_info(self, obj):
        """Display tracking information"""
        if obj.tracking_number:
            return format_html(
                '<div style="background:#ecf0f1;padding:8px;border-radius:5px;text-align:center;">'
                '<strong style="color:#2c3e50;">🚚 {}</strong><br>'
                '<small style="color:#7f8c8d;font-family:monospace;">{}</small>'
                '</div>',
                obj.courier or 'Courier',
                obj.tracking_number
            )
        return format_html('<span style="color:#95a5a6;">No tracking yet</span>')
    tracking_info.short_description = '🚚 Tracking'
    
    def order_date(self, obj):
        """Display order date beautifully"""
        time_diff = timezone.now() - obj.placed_at
        if time_diff.days == 0:
            time_str = '🔥 Today'
        elif time_diff.days == 1:
            time_str = 'Yesterday'
        else:
            time_str = f'{time_diff.days} days ago'
        
        return format_html(
            '<div style="text-align:center;">'
            '<strong style="color:#2c3e50;">{}</strong><br>'
            '<small style="color:#7f8c8d;">{}</small>'
            '</div>',
            obj.placed_at.strftime('%b %d, %Y'),
            time_str
        )
    order_date.short_description = '📅 Date'
    
    def quick_actions(self, obj):
        """Quick action buttons"""
        return format_html(
            '<div style="display:flex;flex-direction:column;gap:5px;">'
            '<a href="{}" style="background:#3498db;color:white;padding:5px 10px;'
            'border-radius:5px;text-decoration:none;font-size:11px;text-align:center;">👁️ View</a>'
            '<a href="{}" style="background:#27ae60;color:white;padding:5px 10px;'
            'border-radius:5px;text-decoration:none;font-size:11px;text-align:center;">✏️ Edit</a>'
            '</div>',
            reverse('admin:app_order_change', args=[obj.id]),
            reverse('admin:app_order_change', args=[obj.id])
        )
    quick_actions.short_description = '⚡ Actions'
    
    def order_summary_card(self, obj):
        """Beautiful order summary card"""
        items_html = ''.join([
            f'<tr><td>{item.variant.product.name}</td>'
            f'<td>{item.variant.size or "N/A"}</td>'
            f'<td>{item.quantity}</td>'
            f'<td>₹{item.unit_price}</td>'
            f'<td><strong>₹{item.line_total()}</strong></td></tr>'
            for item in obj.items.all()
        ])
        
        return format_html(
            '<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);'
            'padding:20px;border-radius:15px;color:white;">'
            '<h2 style="margin:0 0 20px 0;">📦 Order Summary</h2>'
            '<table style="width:100%;background:white;color:#2c3e50;border-radius:10px;overflow:hidden;">'
            '<thead><tr style="background:#34495e;color:white;">'
            '<th style="padding:10px;text-align:left;">Product</th>'
            '<th style="padding:10px;">Size</th>'
            '<th style="padding:10px;">Qty</th>'
            '<th style="padding:10px;">Price</th>'
            '<th style="padding:10px;">Total</th>'
            '</tr></thead>'
            '<tbody>{}</tbody>'
            '</table>'
            '<div style="background:white;color:#2c3e50;padding:15px;margin-top:10px;border-radius:10px;">'
            '<div style="display:flex;justify-content:space-between;padding:5px 0;">'
            '<span>Subtotal:</span><strong>₹{:,.2f}</strong></div>'
            '<div style="display:flex;justify-content:space-between;padding:5px 0;">'
            '<span>Shipping:</span><strong>₹{:,.2f}</strong></div>'
            '<div style="display:flex;justify-content:space-between;padding:5px 0;">'
            '<span>Tax:</span><strong>₹{:,.2f}</strong></div>'
            '<div style="display:flex;justify-content:space-between;padding:5px 0;color:#e74c3c;">'
            '<span>Discount:</span><strong>-₹{:,.2f}</strong></div>'
            '<div style="display:flex;justify-content:space-between;padding:10px 0;'
            'border-top:2px solid #34495e;margin-top:10px;font-size:20px;">'
            '<span>TOTAL:</span><strong style="color:#27ae60;">₹{:,.2f}</strong></div>'
            '</div></div>',
            items_html,
            obj.subtotal, obj.shipping_amount, obj.tax_amount,
            obj.discount_amount, obj.total
        )
    order_summary_card.short_description = 'Order Details'
    
    # Actions
    @admin.action(description='✅ Mark as PAID')
    def mark_as_paid(self, request, queryset):
        queryset.update(status='paid')
        self.message_user(request, '✅ Orders marked as paid!', messages.SUCCESS)
    
    @admin.action(description='🚚 Mark as SHIPPED')
    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, '🚚 Orders marked as shipped!', messages.SUCCESS)
    
    @admin.action(description='📦 Mark as DELIVERED')
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, '📦 Orders marked as delivered!', messages.SUCCESS)
    
    @admin.action(description='❌ Cancel Orders')
    def cancel_orders(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, '❌ Orders cancelled!', messages.WARNING)
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/order_quick_update.js',)


# ============================================
# PRODUCT ADMIN
# ============================================
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('sku', 'size', 'color', 'price', 'mrp', 'discount_percent', 'stock_display', 'is_active')
    readonly_fields = ('stock_display',)
    
    def stock_display(self, obj):
        if hasattr(obj, 'inventory'):
            qty = obj.inventory.quantity
            color = '#27ae60' if qty > 10 else '#f39c12' if qty > 0 else '#e74c3c'
            return format_html(
                '<strong style="color:{};">{} in stock</strong>',
                color, qty
            )
        return '-'
    stock_display.short_description = '📦 Stock'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'image_preview', 'alt_text', 'is_feature', 'order')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:100px;max-height:100px;'
                'border-radius:8px;border:2px solid #ecf0f1;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(Product, site=custom_admin_site)
class EnhancedProductAdmin(admin.ModelAdmin):
    list_display = ('product_card', 'category_badge', 'brand_badge', 'price_range', 'stock_indicator', 'rating_display', 'status_toggle', 'created_date')
    list_filter = ('is_active', 'category', 'brand', 'created_at')
    search_fields = ('name', 'slug', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline, ProductImageInline]
    list_per_page = 20
    
    def product_card(self, obj):
        image_url = obj.images.first().image.url if obj.images.exists() else '/static/images/no-image.jpg'
        return format_html(
            '<div style="display:flex;align-items:center;gap:15px;">'
            '<img src="{}" style="width:60px;height:60px;object-fit:cover;'
            'border-radius:10px;border:2px solid #ecf0f1;" />'
            '<div><strong style="color:#2c3e50;font-size:14px;">{}</strong><br>'
            '<small style="color:#7f8c8d;">{}</small></div></div>',
            image_url, obj.name, obj.slug
        )
    product_card.short_description = '🎁 Product'
    
    def category_badge(self, obj):
        if obj.category:
            return format_html(
                '<span style="background:#3498db;color:white;padding:5px 10px;'
                'border-radius:8px;font-size:11px;">📂 {}</span>',
                obj.category.name
            )
        return '-'
    category_badge.short_description = 'Category'
    
    def brand_badge(self, obj):
        if obj.brand:
            return format_html(
                '<span style="background:#9b59b6;color:white;padding:5px 10px;'
                'border-radius:8px;font-size:11px;">🏷️ {}</span>',
                obj.brand
            )
        return '-'
    brand_badge.short_description = 'Brand'
    
    def price_range(self, obj):
        variants = obj.variants.all()
        if variants:
            min_price = min(v.price for v in variants)
            max_price = max(v.price for v in variants)
            if min_price == max_price:
                return format_html('<strong style="color:#27ae60;font-size:14px;">₹{:,.2f}</strong>', min_price)
            return format_html(
                '<strong style="color:#27ae60;font-size:14px;">₹{:,.2f} - ₹{:,.2f}</strong>',
                min_price, max_price
            )
        return '-'
    price_range.short_description = '💰 Price'
    
    def stock_indicator(self, obj):
        total_stock = sum(v.inventory.quantity for v in obj.variants.all() if hasattr(v, 'inventory'))
        if total_stock == 0:
            return format_html('<span style="background:#e74c3c;color:white;padding:5px 10px;border-radius:8px;font-size:11px;">❌ Out of Stock</span>')
        elif total_stock <= 10:
            return format_html('<span style="background:#f39c12;color:white;padding:5px 10px;border-radius:8px;font-size:11px;">⚠️ Low ({} left)</span>', total_stock)
        else:
            return format_html('<span style="background:#27ae60;color:white;padding:5px 10px;border-radius:8px;font-size:11px;">✅ In Stock ({})</span>', total_stock)
    stock_indicator.short_description = '📦 Stock'
    
    def rating_display(self, obj):
        avg = obj.avg_rating()
        stars = '⭐' * int(avg)
        return format_html(
            '<div style="font-size:16px;">{}</div>'
            '<small style="color:#7f8c8d;">{:.1f}/5</small>',
            stars or '☆☆☆☆☆', avg
        )
    rating_display.short_description = '⭐ Rating'
    
    def status_toggle(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#27ae60;color:white;padding:5px 10px;border-radius:8px;font-size:11px;">✅ Active</span>')
        return format_html('<span style="background:#95a5a6;color:white;padding:5px 10px;border-radius:8px;font-size:11px;">⏸️ Inactive</span>')
    status_toggle.short_description = 'Status'
    
    def created_date(self, obj):
        return obj.created_at.strftime('%b %d, %Y')
    created_date.short_description = '📅 Created'


# ============================================
# INVENTORY ADMIN
# ============================================
@admin.register(Inventory, site=custom_admin_site)
class EnhancedInventoryAdmin(admin.ModelAdmin):
    list_display = ('product_info', 'stock_gauge', 'reserved_display', 'threshold_badge', 'quick_adjust')
    list_filter = ('variant__product__category',)
    search_fields = ('variant__sku', 'variant__product__name')
    list_per_page = 30
    
    def product_info(self, obj):
        return format_html(
            '<strong style="color:#2c3e50;">{}</strong><br>'
            '<small style="color:#7f8c8d;">SKU: {}</small><br>'
            '<small style="color:#7f8c8d;">Size: {} | Color: {}</small>',
            obj.variant.product.name,
            obj.variant.sku,
            obj.variant.size or 'N/A',
            obj.variant.color or 'N/A'
        )
    product_info.short_description = '📦 Product'
    
    def stock_gauge(self, obj):
        qty = obj.quantity
        if qty == 0:
            color = '#e74c3c'
            icon = '❌'
            status = 'OUT'
        elif qty <= obj.low_stock_threshold:
            color = '#f39c12'
            icon = '⚠️'
            status = 'LOW'
        else:
            color = '#27ae60'
            icon = '✅'
            status = 'OK'
        
        return format_html(
            '<div style="text-align:center;">'
            '<div style="background:{};color:white;padding:10px;border-radius:10px;'
            'font-weight:bold;font-size:20px;">{} {}</div>'
            '<small style="color:#7f8c8d;font-weight:bold;">{}</small>'
            '</div>',
            color, icon, qty, status
        )
    stock_gauge.short_description = '📊 Stock Level'
    
    def reserved_display(self, obj):
        if obj.reserved > 0:
            return format_html(
                '<span style="background:#f39c12;color:white;padding:5px 10px;'
                'border-radius:8px;font-weight:bold;">🔒 {} Reserved</span>',
                obj.reserved
            )
        return format_html('<span style="color:#95a5a6;">No reservations</span>')
    reserved_display.short_description = '🔒 Reserved'
    
    def threshold_badge(self, obj):
        return format_html(
            '<div style="background:#ecf0f1;padding:8px;border-radius:8px;text-align:center;">'
            '<strong style="color:#34495e;">Alert at: {}</strong>'
            '</div>',
            obj.low_stock_threshold
        )
    threshold_badge.short_description = '⚠️ Threshold'
    
    def quick_adjust(self, obj):
        return format_html(
            '<div style="display:flex;gap:5px;">'
            '<button onclick="adjustStock(\'{}\', 10)" '
            'style="background:#27ae60;color:white;border:none;padding:5px 10px;'
            'border-radius:5px;cursor:pointer;font-weight:bold;">+10</button>'
            '<button onclick="adjustStock(\'{}\', -5)" '
            'style="background:#e74c3c;color:white;border:none;padding:5px 10px;'
            'border-radius:5px;cursor:pointer;font-weight:bold;">-5</button>'
            '</div>',
            obj.id, obj.id
        )
    quick_adjust.short_description = '⚡ Quick Adjust'


# ============================================
# CATEGORY ADMIN
# ============================================
@admin.register(Category, site=custom_admin_site)
class EnhancedCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name_icon', 'parent_display', 'product_count', 'status_badge', 'sort_order_display')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    
    def category_name_icon(self, obj):
        return format_html(
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<span style="font-size:30px;">📁</span>'
            '<strong style="color:#2c3e50;font-size:15px;">{}</strong>'
            '</div>',
            obj.name
        )
    category_name_icon.short_description = '📂 Category'
    
    def parent_display(self, obj):
        if obj.parent:
            return format_html(
                '<span style="background:#95a5a6;color:white;padding:5px 10px;'
                'border-radius:8px;font-size:11px;">↳ {}</span>',
                obj.parent.name
            )
        return format_html('<span style="background:#3498db;color:white;padding:5px 10px;border-radius:8px;font-size:11px;">🏠 Main Category</span>')
    parent_display.short_description = 'Parent'
    
    def product_count(self, obj):
        count = obj.products.count()
        return format_html(
            '<strong style="color:#27ae60;font-size:16px;">{}</strong> products',
            count
        )
    product_count.short_description = '📦 Products'
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#27ae60;color:white;padding:5px 10px;border-radius:8px;">✅ Active</span>')
        return format_html('<span style="background:#e74c3c;color:white;padding:5px 10px;border-radius:8px;">❌ Inactive</span>')
    status_badge.short_description = 'Status'
    
    def sort_order_display(self, obj):
        return format_html(
            '<div style="background:#ecf0f1;padding:8px;border-radius:8px;'
            'text-align:center;font-weight:bold;color:#34495e;">{}</div>',
            obj.sort_order
        )
    sort_order_display.short_description = '🔢 Order'


# ============================================
# COUPON ADMIN
# ============================================
@admin.register(Coupon, site=custom_admin_site)
class EnhancedCouponAdmin(admin.ModelAdmin):
    list_display = ('coupon_code_badge', 'discount_display', 'validity_period', 'usage_stats', 'status_indicator')
    list_filter = ('active', 'coupon_type', 'start_date', 'end_date')
    search_fields = ('code', 'description')
    filter_horizontal = ('applicable_products', 'applicable_categories')
    
    def coupon_code_badge(self, obj):
        return format_html(
            '<div style="background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);'
            'color:white;padding:12px 20px;border-radius:10px;text-align:center;'
            'font-weight:bold;font-size:16px;letter-spacing:2px;border:3px dashed white;">'
            '{}'
            '</div>',
            obj.code
        )
    coupon_code_badge.short_description = '🎫 Coupon Code'
    
    def discount_display(self, obj):
        if obj.coupon_type == 'percent':
            icon = '📊'
            value = f'{obj.value}%'
            color = '#e74c3c'
        else:
            icon = '💰'
            value = f'₹{obj.value}'
            color = '#27ae60'
        
        return format_html(
            '<div style="text-align:center;">'
            '<span style="font-size:30px;">{}</span><br>'
            '<strong style="color:{};font-size:20px;">{} OFF</strong>'
            '</div>',
            icon, color, value
        )
    discount_display.short_description = '💸 Discount'
    
    def validity_period(self, obj):
        now = timezone.now()
        is_active = obj.start_date <= now <= obj.end_date
        
        return format_html(
            '<div style="background:{};color:white;padding:10px;border-radius:8px;text-align:center;">'
            '<small>From: {}</small><br>'
            '<small>To: {}</small>'
            '</div>',
            '#27ae60' if is_active else '#95a5a6',
            obj.start_date.strftime('%b %d, %Y'),
            obj.end_date.strftime('%b %d, %Y')
        )
    validity_period.short_description = '📅 Valid Period'
    
    def usage_stats(self, obj):
        used = obj.usages.count()
        max_usage = obj.max_usage or '∞'
        
        return format_html(
            '<div style="text-align:center;background:#ecf0f1;padding:10px;border-radius:8px;">'
            '<div style="font-size:24px;font-weight:bold;color:#2c3e50;">{} / {}</div>'
            '<small style="color:#7f8c8d;">Times Used</small>'
            '</div>',
            used, max_usage
        )
    usage_stats.short_description = '📈 Usage'
    
    def status_indicator(self, obj):
        now = timezone.now()
        if not obj.active:
            return format_html('<span style="background:#e74c3c;color:white;padding:8px 12px;border-radius:8px;">❌ Disabled</span>')
        elif now < obj.start_date:
            return format_html('<span style="background:#3498db;color:white;padding:8px 12px;border-radius:8px;">⏰ Scheduled</span>')
        elif now > obj.end_date:
            return format_html('<span style="background:#95a5a6;color:white;padding:8px 12px;border-radius:8px;">⏱️ Expired</span>')
        else:
            return format_html('<span style="background:#27ae60;color:white;padding:8px 12px;border-radius:8px;">✅ Active</span>')
    status_indicator.short_description = '🚦 Status'


# ============================================
# REVIEW ADMIN
# ============================================
@admin.register(Review, site=custom_admin_site)
class EnhancedReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer_info', 'product_info', 'rating_stars', 'review_preview', 'approval_status', 'review_date', 'quick_approve')
    list_filter = ('approved', 'rating', 'created_at')
    search_fields = ('user__username', 'product__name', 'body', 'title')
    actions = ['approve_reviews', 'reject_reviews']
    
    def reviewer_info(self, obj):
        return format_html(
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<div style="width:40px;height:40px;border-radius:50%;background:#3498db;'
            'color:white;display:flex;align-items:center;justify-content:center;'
            'font-weight:bold;font-size:18px;">{}</div>'
            '<strong style="color:#2c3e50;">{}</strong>'
            '</div>',
            obj.user.username[0].upper(), obj.user.username
        )
    reviewer_info.short_description = '👤 Reviewer'
    
    def product_info(self, obj):
        return format_html(
            '<strong style="color:#2c3e50;">{}</strong>',
            obj.product.name
        )
    product_info.short_description = '📦 Product'
    
    def rating_stars(self, obj):
        stars = '⭐' * obj.rating
        empty = '☆' * (5 - obj.rating)
        return format_html(
            '<div style="font-size:20px;">{}{}</div>',
            stars, empty
        )
    rating_stars.short_description = '⭐ Rating'
    
    def review_preview(self, obj):
        title = obj.title or 'No title'
        body = obj.body[:80] + '...' if len(obj.body) > 80 else obj.body
        return format_html(
            '<div style="max-width:300px;background:#ecf0f1;padding:10px;border-radius:8px;">'
            '<strong style="color:#2c3e50;">{}</strong><br>'
            '<small style="color:#7f8c8d;">{}</small>'
            '</div>',
            title, body
        )
    review_preview.short_description = '💬 Review'
    
    def approval_status(self, obj):
        if obj.approved:
            return format_html('<span style="background:#27ae60;color:white;padding:8px 12px;border-radius:8px;font-weight:bold;">✅ Approved</span>')
        return format_html('<span style="background:#f39c12;color:white;padding:8px 12px;border-radius:8px;font-weight:bold;">⏳ Pending</span>')
    approval_status.short_description = 'Status'
    
    def review_date(self, obj):
        return obj.created_at.strftime('%b %d, %Y')
    review_date.short_description = '📅 Date'
    
    def quick_approve(self, obj):
        if not obj.approved:
            return format_html(
                '<button onclick="approveReview(\'{}\')" '
                'style="background:#27ae60;color:white;border:none;padding:8px 15px;'
                'border-radius:8px;cursor:pointer;font-weight:bold;">✅ Approve</button>',
                obj.id
            )
        return format_html('<span style="color:#27ae60;font-weight:bold;">✓ Approved</span>')
    quick_approve.short_description = '⚡ Action'
    
    @admin.action(description='✅ Approve selected reviews')
    def approve_reviews(self, request, queryset):
        count = queryset.update(approved=True)
        self.message_user(request, f'✅ {count} reviews approved!', messages.SUCCESS)
    
    @admin.action(description='❌ Reject selected reviews')
    def reject_reviews(self, request, queryset):
        count = queryset.update(approved=False)
        self.message_user(request, f'❌ {count} reviews rejected!', messages.WARNING)


# ============================================
# REGISTER REMAINING MODELS
# ============================================
@admin.register(Address, site=custom_admin_site)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'city', 'state', 'is_default', 'created_at')
    list_filter = ('is_default', 'state', 'country')
    search_fields = ('full_name', 'city', 'line1')

@admin.register(Payment, site=custom_admin_site)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'method', 'amount', 'status', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('id', 'order__id', 'reference')

@admin.register(Cart, site=custom_admin_site)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'item_count', 'total', 'is_active', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username',)

@admin.register(Banner, site=custom_admin_site)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'active', 'order', 'start_date', 'end_date')
    list_filter = ('active',)

@admin.register(NewsletterSubscriber, site=custom_admin_site)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'active', 'subscribed_at')
    list_filter = ('active',)


@admin.register(SiteTheme, site=custom_admin_site)
class SiteThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'primary_color', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'is_active')
        }),
        ('Brand Colors', {
            'fields': ('primary_color', 'primary_dark', 'secondary_color', 'accent_color'),
            'description': 'Main brand colors for buttons, links, and highlights'
        }),
        ('Text & Surfaces', {
            'fields': ('text_dark', 'text_light', 'bg_cream', 'border_color'),
            'description': 'Text colors and background colors'
        }),
        ('State Colors', {
            'fields': ('error_color', 'success_color', 'warning_color', 'info_color'),
            'description': 'Colors for alerts and notifications'
        }),
        ('Typography & Layout', {
            'fields': ('font_family', 'border_radius'),
            'description': 'Font and border settings'
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/theme-admin.css',)
        }
        js = ('admin/js/theme-admin.js',)



# Register remaining models simply
custom_admin_site.register(ProductImage)
custom_admin_site.register(ProductVariant)
custom_admin_site.register(CartItem)
custom_admin_site.register(Wishlist)
custom_admin_site.register(WishlistItem)
custom_admin_site.register(OrderItem)
custom_admin_site.register(GiftCard)
custom_admin_site.register(LoyaltyPoint)
custom_admin_site.register(CouponUsage)
custom_admin_site.register(Referral)
custom_admin_site.register(ProductView)
custom_admin_site.register(AbandonedCartSnapshot)
custom_admin_site.register(ShippingZone)
# Register django-allauth models with custom admin site
try:
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
    from django.contrib.auth.models import Group
    
    # Unregister from default admin if registered
    try:
        admin.site.unregister(EmailAddress)
    except admin.sites.NotRegistered:
        pass
    try:
        admin.site.unregister(SocialAccount)
    except admin.sites.NotRegistered:
        pass
    try:
        admin.site.unregister(SocialApp)
    except admin.sites.NotRegistered:
        pass
    try:
        admin.site.unregister(SocialToken)
    except admin.sites.NotRegistered:
        pass
    
    # Register with custom admin site
    custom_admin_site.register(EmailAddress)
    custom_admin_site.register(SocialAccount)
    custom_admin_site.register(SocialApp)
    custom_admin_site.register(SocialToken)
    custom_admin_site.register(Group)
except ImportError:
    # django-allauth not installed or models not available
    pass