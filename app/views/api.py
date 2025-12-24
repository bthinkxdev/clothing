from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.db.models import Q

from ..models import ProductVariant, Product


class VariantStockCheckView(View):
    def get(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, id=variant_id)
        available = variant.available_stock()

        return JsonResponse(
            {
                "available": available,
                "in_stock": available > 0,
                "is_low": variant.inventory.is_low() if hasattr(variant, "inventory") else False,
            }
        )


class ProductAutocompleteView(View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        if not query or len(query) < 2:
            return JsonResponse({"results": []})

        products = Product.objects.filter(
            (Q(name__icontains=query) | Q(brand__icontains=query)), is_active=True
        )[:10]

        results = [
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "url": product.get_absolute_url(),
            }
            for product in products
        ]

        return JsonResponse({"results": results})

