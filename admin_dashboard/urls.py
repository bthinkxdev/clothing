# admin_dashboard/urls.py
from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Auth
    path('login/', views.AdminLoginView.as_view(), name='login'),
    path('logout/', views.AdminLogoutView.as_view(), name='logout'),
    # Dashboard Home
    path('', views.DashboardHomeView.as_view(), name='home'),
    
    # Analytics & Reports
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics'),
    path('sales-report/', views.SalesReportView.as_view(), name='sales_report'),
    path('sales-report/export/', views.SalesReportExportView.as_view(), name='sales_report_export'),
    path('revenue-analytics/', views.RevenueAnalyticsView.as_view(), name='revenue_analytics'),
    
    # Order Management
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/<uuid:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<uuid:pk>/update/', views.OrderUpdateView.as_view(), name='order_update'),
    path('orders/<uuid:pk>/cancel/', views.OrderCancelView.as_view(), name='order_cancel'),
    path('orders/<uuid:pk>/invoice/', views.OrderInvoiceView.as_view(), name='order_invoice'),
    path('orders/bulk-update/', views.OrderBulkUpdateView.as_view(), name='order_bulk_update'),
    
    # Product Management
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<slug:slug>/update/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<slug:slug>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('products/<slug:slug>/variants/', views.ProductVariantManageView.as_view(), name='product_variants'),
    path('products/bulk-update/', views.ProductBulkUpdateView.as_view(), name='product_bulk_update'),
    
    # Inventory Management
    path('inventory/', views.InventoryListView.as_view(), name='inventory_list'),
    path('inventory/<int:pk>/update/', views.InventoryUpdateView.as_view(), name='inventory_update'),
    path('inventory/low-stock/', views.LowStockReportView.as_view(), name='low_stock_report'),
    path('inventory/bulk-update/', views.InventoryBulkUpdateView.as_view(), name='inventory_bulk_update'),
    
    # Customer Management
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/orders/', views.CustomerOrdersView.as_view(), name='customer_orders'),
    path('customers/<int:pk>/cart/', views.CustomerCartView.as_view(), name='customer_cart'),
    path('customers/<int:pk>/wishlist/', views.CustomerWishlistView.as_view(), name='customer_wishlist'),
    path('customers/<int:pk>/block/', views.CustomerBlockView.as_view(), name='customer_block'),
    path('customers/<int:pk>/wallet/', views.CustomerWalletView.as_view(), name='customer_wallet'),
    
    # Coupon Management
    path('coupons/', views.CouponListView.as_view(), name='coupon_list'),
    path('coupons/create/', views.CouponCreateView.as_view(), name='coupon_create'),
    path('coupons/<int:pk>/', views.CouponDetailView.as_view(), name='coupon_detail'),
    path('coupons/<int:pk>/update/', views.CouponUpdateView.as_view(), name='coupon_update'),
    path('coupons/<int:pk>/delete/', views.CouponDeleteView.as_view(), name='coupon_delete'),
    path('coupons/<int:pk>/toggle/', views.CouponToggleView.as_view(), name='coupon_toggle'),
    
    # Category Management
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Reviews Management
    path('reviews/', views.ReviewListView.as_view(), name='review_list'),
    path('reviews/<int:pk>/approve/', views.ReviewApproveView.as_view(), name='review_approve'),
    path('reviews/<int:pk>/delete/', views.ReviewDeleteView.as_view(), name='review_delete'),
    
    # Payment Management
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/<uuid:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    
    # API Endpoints for AJAX
    path('api/dashboard-stats/', views.DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
    path('api/sales-chart/', views.SalesChartAPIView.as_view(), name='api_sales_chart'),
    path('api/revenue-chart/', views.RevenueChartAPIView.as_view(), name='api_revenue_chart'),
    path('api/order-status-chart/', views.OrderStatusChartAPIView.as_view(), name='api_order_status_chart'),
    path('api/product-performance/', views.ProductPerformanceAPIView.as_view(), name='api_product_performance'),
    path('api/customer-analytics/', views.CustomerAnalyticsAPIView.as_view(), name='api_customer_analytics'),

    # Theme Management
    path('theme/settings/', views.theme_settings, name='theme_settings'),
]