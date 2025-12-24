from django.db import connection
from django.utils import timezone
from django.views.generic import TemplateView

from ..models import Banner, Product, Category
from .base import CommonContextMixin


class HomeView(CommonContextMixin, TemplateView):
    template_name = "home.html"

    def _filter_by_tag(self, queryset, tag):
        """Filter products by tag in a database-agnostic way."""
        db_backend = connection.vendor
        if db_backend == "sqlite":
            products = list(queryset)
            return [p for p in products if isinstance(p.tags, list) and tag in p.tags]
        return queryset.filter(tags__contains=[tag])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        context["banners"] = (
            Banner.objects.filter(
                active=True, start_date__lte=now, end_date__gte=now
            ).order_by("order")
        )

        base_queryset = Product.objects.filter(is_active=True).prefetch_related(
            "variants", "images"
        )
        context["new_arrivals"] = self._filter_by_tag(base_queryset, "new")[:12]
        context["best_sellers"] = self._filter_by_tag(base_queryset, "best-seller")[:12]

        context["sale_products"] = (
            Product.objects.filter(
                is_active=True, variants__discount_percent__gt=0
            ).distinct()
            .prefetch_related("variants", "images")[:12]
        )

        context["featured_categories"] = Category.objects.filter(
            is_active=True, parent=None
        )[:8]

        return context

