from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView

from ..forms import NewsletterForm
from ..models import NewsletterSubscriber


class NewsletterSubscribeView(FormView):
    form_class = NewsletterForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        NewsletterSubscriber.objects.get_or_create(email=email)
        messages.success(self.request, "Subscribed to newsletter!")
        return super().form_valid(form)

