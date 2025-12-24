from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from ..forms import ReviewForm
from ..models import Product, Review, OrderItem


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = "reviews/form.html"
    success_url = reverse_lazy("my_reviews")

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, slug=kwargs["slug"])

        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status="delivered",
            variant__product=self.product,
        ).exists()

        if not has_purchased:
            messages.error(request, "You can only review products you have purchased.")
            return redirect("product_detail", slug=self.product.slug)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.product = self.product
        messages.success(self.request, "Review submitted successfully.")
        return super().form_valid(form)


class MyReviewsView(LoginRequiredMixin, ListView):
    template_name = "account/reviews.html"
    context_object_name = "my_reviews"

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user).select_related("product")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Reviews", "url": ""},
        ]
        return context

