# admin_dashboard/views/__init__.py

# Dashboard & Analytics Views
from .dashboard import (
    DashboardHomeView,
    AnalyticsDashboardView,
    SalesReportView,
    SalesReportExportView,
    RevenueAnalyticsView,
    DashboardStatsAPIView,
    SalesChartAPIView,
    RevenueChartAPIView,
    OrderStatusChartAPIView,
    ProductPerformanceAPIView,
    CustomerAnalyticsAPIView,
)

# Order Management Views
from .orders import (
    OrderListView,
    OrderDetailView,
    OrderUpdateView,
    OrderCancelView,
    OrderInvoiceView,
    OrderBulkUpdateView,
)

# Product Management Views
from .products import (
    ProductListView,
    ProductDetailView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
    ProductVariantManageView,
    ProductBulkUpdateView,
)

# Customer Management Views
from .customers import (
    CustomerListView,
    CustomerDetailView,
    CustomerOrdersView,
    CustomerCartView,
    CustomerWishlistView,
    CustomerBlockView,
    CustomerWalletView,
)

# Other Management Views
from .other import (
    InventoryListView,
    InventoryUpdateView,
    LowStockReportView,
    InventoryBulkUpdateView,
    CouponListView,
    CouponDetailView,
    CouponCreateView,
    CouponUpdateView,
    CouponDeleteView,
    CouponToggleView,
    CategoryListView,
    CategoryCreateView,
    CategoryUpdateView,
    CategoryDeleteView,
    ReviewListView,
    ReviewApproveView,
    ReviewDeleteView,
    PaymentListView,
    PaymentDetailView,
)

# Theme Management Views
from .theme import theme_settings
# Auth
from .auth import AdminLoginView, AdminLogoutView
# Vendor settings
from .vendor_settings import VendorSettingsUpdateView

__all__ = [
    # Auth
    'AdminLoginView',
    'AdminLogoutView',
    
    # Dashboard
    'DashboardHomeView',
    'AnalyticsDashboardView',
    'SalesReportView',
    'SalesReportExportView',
    'RevenueAnalyticsView',
    'DashboardStatsAPIView',
    'SalesChartAPIView',
    'RevenueChartAPIView',
    'OrderStatusChartAPIView',
    'ProductPerformanceAPIView',
    'CustomerAnalyticsAPIView',
    
    # Orders
    'OrderListView',
    'OrderDetailView',
    'OrderUpdateView',
    'OrderCancelView',
    'OrderInvoiceView',
    'OrderBulkUpdateView',
    
    # Products
    'ProductListView',
    'ProductDetailView',
    'ProductCreateView',
    'ProductUpdateView',
    'ProductDeleteView',
    'ProductVariantManageView',
    'ProductBulkUpdateView',
    
    # Customers
    'CustomerListView',
    'CustomerDetailView',
    'CustomerOrdersView',
    'CustomerCartView',
    'CustomerWishlistView',
    'CustomerBlockView',
    'CustomerWalletView',
    
    # Inventory
    'InventoryListView',
    'InventoryUpdateView',
    'LowStockReportView',
    'InventoryBulkUpdateView',
    
    # Coupons
    'CouponListView',
    'CouponDetailView',
    'CouponCreateView',
    'CouponUpdateView',
    'CouponDeleteView',
    'CouponToggleView',
    
    # Categories
    'CategoryListView',
    'CategoryCreateView',
    'CategoryUpdateView',
    'CategoryDeleteView',
    
    # Reviews
    'ReviewListView',
    'ReviewApproveView',
    'ReviewDeleteView',
    
    # Payments
    'PaymentListView',
    'PaymentDetailView',

    # Vendor settings
    'VendorSettingsUpdateView',

    # Theme Management (merged)
    'theme_settings',
]