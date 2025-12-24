from django.db import connection
from django.db.models import Q, Avg, Count, Min, Max, Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView

from ..models import (
    Product,
    ProductVariant,
    Category,
    Review,
    OrderItem,
    ProductImage,
    ProductView as ProductViewLog,
)
from .base import CommonContextMixin


class ProductListView(CommonContextMixin, ListView):
    model = Product
    template_name = "products/list.html"
    context_object_name = "products"
    paginate_by = 24

    def get_queryset(self):
        if hasattr(self, "_cached_queryset"):
            return self._cached_queryset

        queryset = (
            Product.objects.filter(is_active=True)
            .prefetch_related(
                "variants__inventory",
                Prefetch("images", queryset=ProductImage.objects.order_by("-is_feature", "order", "id")),
            )
            .select_related("category")
        )

        category_slug = self.kwargs.get("category_slug")
        subcategory_slug = self.kwargs.get("subcategory_slug")

        if subcategory_slug:
            category = get_object_or_404(
                Category, slug=subcategory_slug, is_active=True
            )
            queryset = queryset.filter(category=category)
        elif category_slug:
            category = get_object_or_404(Category, slug=category_slug, is_active=True)
            category_ids = [category.id] + list(
                category.children.values_list("id", flat=True)
            )
            queryset = queryset.filter(category_id__in=category_ids)

        sizes = self.request.GET.getlist("size")
        if sizes:
            queryset = queryset.filter(variants__size__in=sizes).distinct()

        colors = self.request.GET.getlist("color")
        if colors:
            queryset = queryset.filter(variants__color__in=colors).distinct()

        brands = self.request.GET.getlist("brand")
        if brands:
            queryset = queryset.filter(brand__in=brands)

        price_min = self.request.GET.get("price_min")
        price_max = self.request.GET.get("price_max")
        if price_min:
            queryset = queryset.filter(variants__price__gte=price_min).distinct()
        if price_max:
            queryset = queryset.filter(variants__price__lte=price_max).distinct()

        discount = self.request.GET.get("discount")
        if discount:
            queryset = queryset.filter(
                variants__discount_percent__gte=discount
            ).distinct()

        availability = self.request.GET.get("availability")
        if availability == "in_stock":
            queryset = queryset.filter(
                variants__inventory__quantity__gt=0
            ).distinct()
        elif availability == "out_of_stock":
            queryset = queryset.filter(variants__inventory__quantity=0).distinct()
        elif availability == "preorder":
            queryset = queryset.filter(variants__is_preorder=True).distinct()

        rating = self.request.GET.get("rating")
        if rating:
            queryset = queryset.annotate(avg_rating=Avg("reviews__rating")).filter(
                avg_rating__gte=rating
            )

        sort_by = self.request.GET.get("sort", "popularity")
        if sort_by == "price_low":
            queryset = queryset.order_by("variants__price")
        elif sort_by == "price_high":
            queryset = queryset.order_by("-variants__price")
        elif sort_by == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort_by == "discount":
            queryset = queryset.order_by("-variants__discount_percent")
        elif sort_by == "rating":
            queryset = queryset.annotate(avg_rating=Avg("reviews__rating")).order_by(
                "-avg_rating"
            )
        elif sort_by == "popularity":
            queryset = queryset.annotate(view_count=Count("views")).order_by(
                "-view_count"
            )
        else:
            queryset = queryset.order_by("-created_at")

        self._cached_queryset = queryset.distinct()
        return self._cached_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        category_slug = self.kwargs.get("category_slug")
        subcategory_slug = self.kwargs.get("subcategory_slug")

        if subcategory_slug:
            context["current_category"] = get_object_or_404(
                Category, slug=subcategory_slug
            )
        elif category_slug:
            context["current_category"] = get_object_or_404(
                Category, slug=category_slug
            )
        else:
            context["current_category"] = None

        breadcrumbs = [{"name": "Home", "url": "/"}]
        if context["current_category"]:
            if context["current_category"].parent:
                breadcrumbs.append(
                    {
                        "name": context["current_category"].parent.name,
                        "url": reverse(
                            "product_list_category",
                            kwargs={"category_slug": context["current_category"].parent.slug},
                        ),
                    }
                )
            breadcrumbs.append({"name": context["current_category"].name, "url": ""})
        context["breadcrumbs"] = breadcrumbs

        context["available_sizes"] = (
            ProductVariant.objects.filter(product__is_active=True)
            .values_list("size", flat=True)
            .distinct()
            .exclude(size__isnull=True)
        )

        context["available_colors"] = (
            ProductVariant.objects.filter(product__is_active=True)
            .values_list("color", flat=True)
            .distinct()
            .exclude(color__isnull=True)
        )

        context["available_brands"] = (
            Product.objects.filter(is_active=True)
            .values_list("brand", flat=True)
            .distinct()
            .exclude(brand="")
        )

        price_range = ProductVariant.objects.filter(product__is_active=True).aggregate(
            min_price=Min("price"), max_price=Max("price")
        )
        context["price_range"] = price_range

        context["applied_filters"] = {
            "sizes": self.request.GET.getlist("size"),
            "colors": self.request.GET.getlist("color"),
            "brands": self.request.GET.getlist("brand"),
            "price_min": self.request.GET.get("price_min"),
            "price_max": self.request.GET.get("price_max"),
            "discount": self.request.GET.get("discount"),
            "availability": self.request.GET.get("availability"),
            "rating": self.request.GET.get("rating"),
        }

        context["sort_by"] = self.request.GET.get("sort", "popularity")
        context["per_page"] = int(self.request.GET.get("per_page", 24))
        queryset = getattr(self, "_cached_queryset", None) or self.get_queryset()
        context["total_count"] = queryset.count()

        return context


class ProductDetailView(CommonContextMixin, DetailView):
    model = Product
    template_name = "products/detail.html"
    context_object_name = "product"
    slug_field = "slug"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_active=True)
            .prefetch_related(
                "variants__inventory",
                Prefetch("images", queryset=ProductImage.objects.order_by("-is_feature", "order", "id")),
                "reviews",
            )
            .select_related("category")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        if self.request.user.is_authenticated:
            ProductViewLog.objects.create(product=product, user=self.request.user)
        else:
            session_id = self.request.session.session_key
            if session_id:
                ProductViewLog.objects.create(product=product, session_id=session_id)

        context["variants"] = product.variants.filter(is_active=True).select_related("inventory")
        context["default_variant"] = product.main_variant()
        context["images"] = product.ordered_images()

        reviews = product.reviews.filter(approved=True)
        context["reviews"] = reviews[:10]
        context["total_reviews"] = reviews.count()
        context["avg_rating"] = product.avg_rating()

        rating_counts = dict(
            reviews.values("rating").annotate(count=Count("id")).values_list("rating", "count")
        )
        total_reviews = context["total_reviews"] or 1  # avoid divide by zero
        context["rating_breakdown"] = {
            rating: {
                "count": rating_counts.get(rating, 0),
                "percentage": (rating_counts.get(rating, 0) / total_reviews) * 100,
            }
            for rating in range(1, 6)
        }

        if self.request.user.is_authenticated:
            has_purchased = OrderItem.objects.filter(
                order__user=self.request.user,
                order__status="delivered",
                variant__product=product,
            ).exists()
            context["can_review"] = has_purchased
            context["user_review"] = Review.objects.filter(
                user=self.request.user, product=product
            ).first()
        else:
            context["can_review"] = False
            context["user_review"] = None

        context["similar_products"] = (
            Product.objects.filter(category=product.category, is_active=True)
            .exclude(id=product.id)
            .prefetch_related(
                "variants",
                Prefetch("images", queryset=ProductImage.objects.order_by("-is_feature", "order", "id")),
            )[:8]
        )

        recently_viewed_ids = self.request.session.get("recently_viewed", [])
        context["recently_viewed"] = (
            Product.objects.filter(id__in=recently_viewed_ids, is_active=True)
            .exclude(id=product.id)
            .prefetch_related(
                "variants",
                Prefetch("images", queryset=ProductImage.objects.order_by("-is_feature", "order", "id")),
            )[:8]
        )

        if product.id not in recently_viewed_ids:
            recently_viewed_ids.insert(0, product.id)
            self.request.session["recently_viewed"] = recently_viewed_ids[:20]

        breadcrumbs = [{"name": "Home", "url": "/"}]
        if product.category:
            if product.category.parent:
                breadcrumbs.append(
                    {
                        "name": product.category.parent.name,
                        "url": reverse(
                            "product_list_category",
                            kwargs={"category_slug": product.category.parent.slug},
                        ),
                    }
                )
            breadcrumbs.append(
                {
                    "name": product.category.name,
                    "url": reverse(
                        "product_list_category", kwargs={"category_slug": product.category.slug}
                    ),
                }
            )
        breadcrumbs.append({"name": product.name, "url": ""})
        context["breadcrumbs"] = breadcrumbs

        return context


class ProductQuickView(CommonContextMixin, DetailView):
    model = Product
    template_name = "products/quick_view.html"
    context_object_name = "product"
    slug_field = "slug"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_active=True)
            .prefetch_related(
                "variants__inventory",
                Prefetch("images", queryset=ProductImage.objects.order_by("-is_feature", "order", "id")),
                "reviews",
            )
            .select_related("category")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context["images"] = product.ordered_images()
        context["variants"] = product.variants.filter(is_active=True).select_related("inventory")
        context["default_variant"] = product.main_variant()
        context["avg_rating"] = product.avg_rating()
        context["total_reviews"] = product.reviews.filter(approved=True).count()
        return context


class ProductSearchView(CommonContextMixin, ListView):
    model = Product
    template_name = "products/search.html"
    context_object_name = "products"
    paginate_by = 24

    def _filter_by_tag(self, term):
        """Database-agnostic tag filtering (SQLite fallback)."""
        if connection.vendor == "sqlite":
            products = Product.objects.filter(is_active=True)
            term_lower = term.lower()
            ids = []
            for product in products:
                if isinstance(product.tags, list) and any(
                    term_lower in str(tag).lower() for tag in product.tags
                ):
                    ids.append(product.id)
            return Product.objects.filter(id__in=ids)
        return Product.objects.filter(is_active=True, tags__contains=[term])

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        if not query:
            return Product.objects.none()

        if hasattr(self, "_cached_queryset"):
            return self._cached_queryset

        base = (
            Product.objects.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(short_description__icontains=query)
                | Q(brand__icontains=query)
                | Q(category__name__icontains=query)
            )
            .filter(is_active=True)
            .prefetch_related(
                "variants",
                Prefetch("images", queryset=ProductImage.objects.order_by("-is_feature", "order", "id")),
            )
        )

        tag_qs = self._filter_by_tag(query)

        self._cached_queryset = (base | tag_qs).distinct()
        return self._cached_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        context["query"] = query
        queryset = getattr(self, "_cached_queryset", None) or self.get_queryset()
        context["total_results"] = queryset.count()

        if context["total_results"] == 0:
            context["popular_searches"] = [
                "T-shirts",
                "Jeans",
                "Dresses",
                "Shoes",
                "Jackets",
            ]
            if connection.vendor == "sqlite":
                trending_ids = []
                for product in Product.objects.filter(is_active=True):
                    if isinstance(product.tags, list) and "trending" in product.tags:
                        trending_ids.append(product.id)
                context["trending_products"] = Product.objects.filter(id__in=trending_ids)[:8]
            else:
                context["trending_products"] = Product.objects.filter(
                    is_active=True, tags__contains=["trending"]
                )[:8]

        return context

