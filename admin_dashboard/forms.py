# admin_dashboard/forms.py
from django import forms
from django.forms import inlineformset_factory
from app.models import (
    Order, Product, ProductVariant, ProductImage,
    Inventory, Coupon, Category, User, SiteTheme
)


class OrderUpdateForm(forms.ModelForm):
    """Form for updating orders"""
    
    class Meta:
        model = Order
        fields = ['status', 'courier', 'tracking_number', 'expected_delivery', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'courier': forms.TextInput(attrs={'class': 'form-control'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control'}),
            'expected_delivery': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class OrderBulkUpdateForm(forms.Form):
    """Form for bulk order updates"""
    
    order_ids = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ('update_status', 'Update Status'),
            ('export', 'Export'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=Order.ORDER_STATUS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ProductForm(forms.ModelForm):
    """Form for creating/updating products"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'sku', 'short_description', 'description',
            'category', 'brand', 'is_active', 'tags',
            'meta_title', 'meta_description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Comma-separated tags'
            }),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        
        # Check for duplicate slugs (excluding current instance)
        qs = Product.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError('Product with this slug already exists.')
        
        return slug


class ProductVariantForm(forms.ModelForm):
    """Form for product variants"""
    
    class Meta:
        model = ProductVariant
        fields = [
            'sku', 'size', 'color', 'material', 'price', 'mrp',
            'discount_percent', 'is_active', 'is_preorder'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mrp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_preorder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# Formset for managing multiple variants
ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    extra=1,
    can_delete=True
)


class ProductImageForm(forms.ModelForm):
    """Form for product images"""
    
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_feature', 'order']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_feature': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# Formset for managing multiple images
ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=3,
    can_delete=True
)


class InventoryForm(forms.ModelForm):
    """Form for updating inventory"""
    
    class Meta:
        model = Inventory
        fields = ['quantity', 'low_stock_threshold', 'reserved']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'reserved': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 0:
            raise forms.ValidationError('Quantity cannot be negative')
        return quantity


class CouponForm(forms.ModelForm):
    """Form for creating/updating coupons"""
    
    class Meta:
        model = Coupon
        fields = [
            'code', 'description', 'coupon_type', 'value',
            'min_purchase_amount', 'start_date', 'end_date',
            'max_usage', 'per_user_limit', 'active',
            'applicable_products', 'applicable_categories'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SAVE20'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'coupon_type': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_purchase_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'max_usage': forms.NumberInput(attrs={'class': 'form-control'}),
            'per_user_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'applicable_products': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'applicable_categories': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError('End date must be after start date')
        
        return cleaned_data


class CategoryForm(forms.ModelForm):
    """Form for categories"""
    
    class Meta:
        model = Category
        fields = ['name', 'slug', 'parent', 'description', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CustomerFilterForm(forms.Form):
    """Form for filtering customers"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username, email, phone...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('active', 'Active'),
            ('blocked', 'Blocked'),
            ('inactive', 'Inactive'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    order_by = forms.ChoiceField(
        required=False,
        choices=[
            ('-date_joined', 'Newest First'),
            ('date_joined', 'Oldest First'),
            ('-total_spent', 'Highest Spender'),
            ('username', 'Name A-Z'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class DateRangeFilterForm(forms.Form):
    """Form for date range filtering"""
    
    period = forms.ChoiceField(
        required=False,
        choices=[
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('last_7_days', 'Last 7 Days'),
            ('last_30_days', 'Last 30 Days'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class WalletAdjustmentForm(forms.Form):
    """Form for adjusting customer wallet"""
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount (use negative for deduction)',
            'step': '0.01'
        })
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Reason for adjustment...'
        })
    )


class ThemeForm(forms.ModelForm):
    class Meta:
        model = SiteTheme
        fields = [
            'name', 'primary_color', 'primary_dark', 'secondary_color', 
            'accent_color', 'text_dark', 'text_light', 'bg_cream', 
            'border_color', 'error_color', 'success_color', 
            'warning_color', 'info_color', 'font_family', 'border_radius'
        ]
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'primary_dark': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'accent_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'text_dark': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'text_light': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'bg_cream': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'border_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'error_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'success_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'warning_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'info_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
        }