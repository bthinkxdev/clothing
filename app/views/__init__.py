from .base import CartMixin, WishlistMixin, CommonContextMixin
from .home import HomeView
from .products import (
    ProductListView,
    ProductDetailView,
    ProductQuickView,
    ProductSearchView,
)
from .cart import (
    CartView,
    CartAddView,
    CartUpdateView,
    CartRemoveView,
    CartClearView,
)
from .wishlist import (
    WishlistView,
    WishlistAddView,
    WishlistRemoveView,
    WishlistMoveToCartView,
)
from .auth import LoginView, OTPSendView, OTPVerifyView, LogoutView
from .checkout import (
    CheckoutAddressView,
    CheckoutAddressSelectView,
    CheckoutShippingView,
    CheckoutPaymentView,
    ApplyCouponView,
    RemoveCouponView,
    OrderCreateView,
    RazorpayVerifyView,
)
from .orders import (
    OrderSuccessView,
    OrderFailureView,
    MyOrdersView,
    OrderDetailView,
    OrderCancelView,
    GuestOrderTrackingView,
)
from .account import (
    AccountDashboardView,
    ProfileEditView,
    AddressListView,
    AddressCreateView,
    AddressUpdateView,
    AddressDeleteView,
    WalletView,
    MyCouponsView,
)
from .reviews import ReviewCreateView, MyReviewsView
from .misc import NewsletterSubscribeView
from .api import VariantStockCheckView, ProductAutocompleteView

