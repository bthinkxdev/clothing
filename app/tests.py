from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import (
    Category, Product, ProductVariant, Inventory, Review,
    Wishlist, WishlistItem, Cart, CartItem
)


class ProductTestMixin:
    def create_product(
        self,
        name="Prod",
        slug="prod",
        category=None,
        brand="BrandX",
        tags=None,
        price=Decimal("100.00"),
        discount=0,
        size="M",
        color="Red",
        qty=10,
        is_preorder=False,
    ):
        if category is None:
            category = Category.objects.create(name="Cat", slug=f"cat-{slug}")
        product = Product.objects.create(
            name=name,
            slug=slug,
            category=category,
            brand=brand,
            tags=tags or [],
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku=f"SKU-{slug}",
            size=size,
            color=color,
            price=price,
            mrp=price,
            discount_percent=discount,
            is_preorder=is_preorder,
        )
        Inventory.objects.get_or_create(variant=variant, defaults={"quantity": qty})
        return product, variant


class ProductListViewTests(ProductTestMixin, TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Shoes", slug="shoes")
        # in-stock discounted
        self.p1, self.v1 = self.create_product(
            name="Red Shoe",
            slug="red-shoe",
            category=self.category,
            brand="Nike",
            tags=["new"],
            price=Decimal("200.00"),
            discount=20,
            size="9",
            color="Red",
            qty=5,
        )
        # out-of-stock non-discount
        self.p2, self.v2 = self.create_product(
            name="Blue Shoe",
            slug="blue-shoe",
            category=self.category,
            brand="Adidas",
            tags=["best-seller"],
            price=Decimal("300.00"),
            discount=0,
            size="10",
            color="Blue",
            qty=0,
        )
        # preorder
        self.p3, self.v3 = self.create_product(
            name="Preorder Shoe",
            slug="pre-shoe",
            category=self.category,
            brand="Puma",
            tags=["trending"],
            price=Decimal("150.00"),
            discount=10,
            size="8",
            color="Black",
            qty=0,
            is_preorder=True,
        )
        # rating: only p1 has high rating
        User = get_user_model()
        user = User.objects.create_user(username="u1", email="u@test.com", password="pass")
        Review.objects.create(user=user, product=self.p1, rating=5, approved=True)
        Review.objects.create(user=user, product=self.p2, rating=2, approved=True)

    def test_filter_size_color_brand(self):
        url = reverse("product_list")
        resp = self.client.get(url, {"size": "9", "color": "Red", "brand": "Nike"})
        self.assertContains(resp, "Red Shoe")
        self.assertNotContains(resp, "Blue Shoe")

    def test_filter_price_range(self):
        url = reverse("product_list")
        resp = self.client.get(url, {"price_min": "180", "price_max": "250"})
        self.assertContains(resp, "Red Shoe")
        self.assertNotContains(resp, "Blue Shoe")

    def test_filter_discount(self):
        url = reverse("product_list")
        resp = self.client.get(url, {"discount": "10"})
        self.assertContains(resp, "Red Shoe")
        self.assertContains(resp, "Preorder Shoe")
        self.assertNotContains(resp, "Blue Shoe")

    def test_filter_availability_in_stock(self):
        url = reverse("product_list")
        resp = self.client.get(url, {"availability": "in_stock"})
        self.assertContains(resp, "Red Shoe")
        self.assertNotContains(resp, "Blue Shoe")

    def test_filter_availability_out_of_stock(self):
        url = reverse("product_list")
        resp = self.client.get(url, {"availability": "out_of_stock"})
        self.assertContains(resp, "Blue Shoe")
        self.assertNotContains(resp, "Red Shoe")

    def test_filter_rating(self):
        url = reverse("product_list")
        resp = self.client.get(url, {"rating": "4"})
        self.assertContains(resp, "Red Shoe")
        self.assertNotContains(resp, "Blue Shoe")

    def test_sort_price_low_high(self):
        url = reverse("product_list")
        resp = self.client.get(url, {"sort": "price_low"})
        # first occurrence should be cheaper product
        content = resp.content.decode()
        self.assertTrue(content.index("Red Shoe") < content.index("Blue Shoe"))


class ProductSearchViewTests(ProductTestMixin, TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Hoodies", slug="hoodies")
        self.p1, _ = self.create_product(
            name="Black Hoodie",
            slug="black-hoodie",
            category=self.cat,
            brand="BrandA",
            tags=["warm", "black"],
            price=Decimal("120.00"),
        )
        self.p2, _ = self.create_product(
            name="Blue Hoodie",
            slug="blue-hoodie",
            category=self.cat,
            brand="BrandB",
            tags=["winter"],
            price=Decimal("110.00"),
        )

    def test_search_by_name(self):
        url = reverse("product_search")
        resp = self.client.get(url, {"q": "Black"})
        self.assertContains(resp, "Black Hoodie")
        self.assertNotContains(resp, "Blue Hoodie")

    def test_search_by_tag_sqlite_safe(self):
        url = reverse("product_search")
        resp = self.client.get(url, {"q": "black"})
        self.assertContains(resp, "Black Hoodie")

    def test_empty_query_returns_none(self):
        url = reverse("product_search")
        resp = self.client.get(url, {"q": ""})
        self.assertNotContains(resp, "Black Hoodie")
        self.assertNotContains(resp, "Blue Hoodie")


class WishlistViewTests(ProductTestMixin, TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="wishuser", email="w@test.com", password="pass")
        self.product, self.variant = self.create_product(
            name="Wish Prod",
            slug="wish-prod",
            tags=["new"],
            qty=3,
        )
        self.wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
        WishlistItem.objects.create(wishlist=self.wishlist, variant=self.variant)

    def test_wishlist_list(self):
        self.client.login(username="wishuser", password="pass")
        resp = self.client.get(reverse("wishlist"))
        self.assertContains(resp, "Wish Prod")

    def test_wishlist_move_to_cart(self):
        self.client.login(username="wishuser", password="pass")
        move_url = reverse("wishlist_move_to_cart", args=[self.wishlist.items.first().id])
        resp = self.client.post(move_url, follow=True)
        self.assertRedirects(resp, reverse("wishlist"))
        cart = Cart.objects.get(user=self.user, is_active=True)
        self.assertTrue(CartItem.objects.filter(cart=cart, variant=self.variant).exists())

    def test_wishlist_remove(self):
        self.client.login(username="wishuser", password="pass")
        remove_url = reverse("wishlist_remove", args=[self.wishlist.items.first().id])
        resp = self.client.post(remove_url, follow=True)
        self.assertRedirects(resp, reverse("wishlist"))
        self.assertFalse(self.wishlist.items.exists())
