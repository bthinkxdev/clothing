# app/urls.py
from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # ========================
    # HOME & PUBLIC PAGES
    # ========================
    path('', views.HomeView.as_view(), name='home'),
    
    # ========================
    # AUTHENTICATION
    # ========================
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/otp/send/', views.OTPSendView.as_view(), name='otp_send'),
    path('auth/otp/verify/', views.OTPVerifyView.as_view(), name='otp_verify'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    # ========================
    # PRODUCTS & CATALOG
    # ========================
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<slug:category_slug>/', views.ProductListView.as_view(), name='product_list_category'),
    path('products/<slug:category_slug>/<slug:subcategory_slug>/', views.ProductListView.as_view(), name='product_list_subcategory'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<slug:slug>/quick-view/', views.ProductQuickView.as_view(), name='product_quick_view'),
    path('search/', views.ProductSearchView.as_view(), name='product_search'),
    
    # ========================
    # CART MANAGEMENT
    # ========================
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.CartAddView.as_view(), name='cart_add'),
    path('cart/update/<int:item_id>/', views.CartUpdateView.as_view(), name='cart_update'),
    path('cart/remove/<int:item_id>/', views.CartRemoveView.as_view(), name='cart_remove'),
    path('cart/clear/', views.CartClearView.as_view(), name='cart_clear'),
    
    # ========================
    # WISHLIST
    # ========================
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('wishlist/add/', views.WishlistAddView.as_view(), name='wishlist_add'),
    path('wishlist/remove/<int:item_id>/', views.WishlistRemoveView.as_view(), name='wishlist_remove'),
    path('wishlist/move-to-cart/<int:item_id>/', views.WishlistMoveToCartView.as_view(), name='wishlist_move_to_cart'),
    
    # ========================
    # CHECKOUT FLOW
    # ========================
    path('checkout/', views.CheckoutAddressView.as_view(), name='checkout'),
    path('checkout/address/', views.CheckoutAddressView.as_view(), name='checkout_address'),
    path('checkout/address/select/<int:address_id>/', views.CheckoutAddressSelectView.as_view(), name='checkout_address_select'),
    path('checkout/shipping/', views.CheckoutShippingView.as_view(), name='checkout_shipping'),
    path('checkout/payment/', views.CheckoutPaymentView.as_view(), name='checkout_payment'),
    path('checkout/apply-coupon/', views.ApplyCouponView.as_view(), name='apply_coupon'),
    path('checkout/remove-coupon/', views.RemoveCouponView.as_view(), name='remove_coupon'),
    
    # ========================
    # ORDER MANAGEMENT
    # ========================
    path('order/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('order/<uuid:id>/success/', views.OrderSuccessView.as_view(), name='order_success'),
    path('order/<uuid:id>/failure/', views.OrderFailureView.as_view(), name='order_failure'),
    path('orders/', views.MyOrdersView.as_view(), name='my_orders'),
    path('orders/<uuid:id>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<uuid:id>/cancel/', views.OrderCancelView.as_view(), name='order_cancel'),
    path('track-order/', views.GuestOrderTrackingView.as_view(), name='track_order'),
    
    # ========================
    # PAYMENT CALLBACKS
    # ========================
    path('payment/razorpay/verify/', views.RazorpayVerifyView.as_view(), name='razorpay_verify'),
    
    # ========================
    # USER ACCOUNT
    # ========================
    path('account/', views.AccountDashboardView.as_view(), name='account_dashboard'),
    path('account/profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('account/wallet/', views.WalletView.as_view(), name='wallet'),
    path('account/coupons/', views.MyCouponsView.as_view(), name='my_coupons'),
    
    # ========================
    # ADDRESS MANAGEMENT
    # ========================
    path('account/addresses/', views.AddressListView.as_view(), name='address_list'),
    path('account/addresses/add/', views.AddressCreateView.as_view(), name='address_add'),
    path('account/addresses/edit/<int:pk>/', views.AddressUpdateView.as_view(), name='address_edit'),
    path('account/addresses/delete/<int:pk>/', views.AddressDeleteView.as_view(), name='address_delete'),
    
    # ========================
    # REVIEWS
    # ========================
    path('account/reviews/', views.MyReviewsView.as_view(), name='my_reviews'),
    path('account/reviews/add/<slug:slug>/', views.ReviewCreateView.as_view(), name='review_add'),
    
    # ========================
    # STATIC PAGES
    # ========================
    path('about/', TemplateView.as_view(template_name='static_pages/about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='static_pages/contact.html'), name='contact'),
    path('faq/', TemplateView.as_view(template_name='static_pages/faq.html'), name='faq'),
    path('terms/', TemplateView.as_view(template_name='static_pages/terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='static_pages/privacy.html'), name='privacy'),
    path('shipping-policy/', TemplateView.as_view(template_name='static_pages/shipping_policy.html'), name='shipping_policy'),
    path('return-policy/', TemplateView.as_view(template_name='static_pages/return_policy.html'), name='return_policy'),
    
    # ========================
    # MISC
    # ========================
    path('newsletter/subscribe/', views.NewsletterSubscribeView.as_view(), name='newsletter_subscribe'),
    
    # ========================
    # AJAX/API ENDPOINTS
    # ========================
    path('api/variants/<int:variant_id>/stock/', views.VariantStockCheckView.as_view(), name='variant_stock_check'),
    path('api/products/autocomplete/', views.ProductAutocompleteView.as_view(), name='product_autocomplete'),

    path('theme.css', views.theme_css, name='dynamic_theme_css'),
    
]