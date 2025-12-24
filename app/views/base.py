from ..models import Cart, Wishlist, Category


class CartMixin:
    """Mixin to add cart context to views."""

    def get_cart_context(self):
        if self.request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=self.request.user, is_active=True)
            cart_count = cart.item_count()
        else:
            cart = None
            cart_count = 0
        return {"cart": cart, "cart_count": cart_count}


class WishlistMixin:
    """Mixin to add wishlist context."""

    def get_wishlist_context(self):
        if self.request.user.is_authenticated:
            wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
            wishlist_count = wishlist.items.count()
        else:
            wishlist = None
            wishlist_count = 0
        return {"wishlist": wishlist, "wishlist_count": wishlist_count}


class CommonContextMixin(CartMixin, WishlistMixin):
    """Combines common context data for all views."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_cart_context())
        context.update(self.get_wishlist_context())
        context["categories"] = Category.objects.filter(is_active=True, parent=None)
        return context

