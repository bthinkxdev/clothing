from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, FormView

from razorpay.errors import BadRequestError

from ..forms import AddressForm
from ..models import Cart, Address, Coupon, Order, OrderItem, Payment
from ..utils import (
    calculate_tax,
    check_pincode_serviceability,
    get_razorpay_client,
    is_razorpay_configured,
)
from .base import CommonContextMixin


class CheckoutAddressView(LoginRequiredMixin, CommonContextMixin, FormView):
    template_name = "checkout/address.html"
    form_class = AddressForm
    success_url = reverse_lazy("checkout_shipping")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["addresses"] = self.request.user.addresses.all()
        context["default_address"] = self.request.user.addresses.filter(
            is_default=True
        ).first()
        context["selected_address_id"] = self.request.session.get("checkout_address_id")
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Checkout", "url": ""},
            {"name": "Address", "url": ""},
        ]

        cart = get_object_or_404(Cart, user=self.request.user, is_active=True)
        context["cart"] = cart
        context["cart_items"] = cart.items.select_related("variant__product").all()
        context["subtotal"] = cart.total()

        return context

    def form_valid(self, form):
        address = form.save(commit=False)
        address.user = self.request.user
        address.save()
        self.request.session["checkout_address_id"] = address.id
        messages.success(self.request, "Address added successfully.")
        return super().form_valid(form)


class CheckoutAddressSelectView(LoginRequiredMixin, View):
    def post(self, request, address_id):
        address = get_object_or_404(Address, id=address_id, user=request.user)
        request.session["checkout_address_id"] = address.id
        return redirect("checkout_shipping")


class CheckoutShippingView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = "checkout/shipping.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Checkout", "url": ""},
            {"name": "Shipping", "url": ""},
        ]

        address_id = self.request.session.get("checkout_address_id")
        if not address_id:
            return redirect("checkout_address")

        address = get_object_or_404(Address, id=address_id, user=self.request.user)
        context["selected_address"] = address

        cart = get_object_or_404(Cart, user=self.request.user, is_active=True)
        context["cart"] = cart
        context["shipping_options"] = self.get_shipping_options(address, cart)
        context["subtotal"] = cart.total()

        return context

    def get_shipping_options(self, address, cart):
        options = [
            {
                "id": "standard",
                "name": "Standard Shipping",
                "description": "5-7 business days",
                "cost": Decimal("50.00"),
                "estimated_days": 7,
            },
            {
                "id": "express",
                "name": "Express Shipping",
                "description": "2-3 business days",
                "cost": Decimal("150.00"),
                "estimated_days": 3,
            },
        ]

        if cart.total() >= Decimal("1000.00"):
            options[0]["cost"] = Decimal("0.00")
            options[0]["name"] = "Free Standard Shipping"

        return options

    def post(self, request):
        shipping_id = request.POST.get("shipping_option")
        request.session["checkout_shipping_id"] = shipping_id
        return redirect("checkout_payment")


class CheckoutPaymentView(LoginRequiredMixin, CommonContextMixin, TemplateView):
    template_name = "checkout/payment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": "Home", "url": "/"},
            {"name": "Checkout", "url": ""},
            {"name": "Payment", "url": ""},
        ]

        if not self.request.session.get("checkout_address_id"):
            return redirect("checkout_address")
        if not self.request.session.get("checkout_shipping_id"):
            return redirect("checkout_shipping")

        address = get_object_or_404(Address, id=self.request.session["checkout_address_id"])
        cart = get_object_or_404(Cart, user=self.request.user, is_active=True)

        context["selected_address"] = address
        context["cart"] = cart
        context["cart_items"] = cart.items.select_related("variant__product").all()

        subtotal = cart.total()
        shipping_cost = self.get_shipping_cost()
        tax = calculate_tax(cart)
        discount = Decimal("0.00")

        coupon_code = self.request.session.get("applied_coupon")
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, active=True).first()
            if coupon and coupon.is_valid_for_user(self.request.user, subtotal):
                discount = coupon.discount_amount(subtotal)
                context["applied_coupon"] = coupon

        context["subtotal"] = subtotal
        context["shipping"] = shipping_cost
        context["tax"] = tax
        context["discount"] = discount
        context["total"] = subtotal + shipping_cost + tax - discount

        context["payment_methods"] = self.get_payment_methods(address, cart)
        context["wallet_balance"] = self.request.user.wallet_balance

        return context

    def get_shipping_cost(self):
        shipping_id = self.request.session.get("checkout_shipping_id")
        if shipping_id == "express":
            return Decimal("150.00")
        return Decimal("50.00")

    def get_payment_methods(self, address, cart):
        methods = []
        if is_razorpay_configured():
            methods.append(
                {
                    "id": "razorpay",
                    "name": "Razorpay (Card/UPI/Net Banking)",
                    "icon": "razorpay",
                }
            )

        methods.append({"id": "wallet", "name": "Wallet", "icon": "wallet"})
        # if check_pincode_serviceability(address.postal_code, "cod"):
        #         methods.append(
        #             {
        #                 "id": "cod",
        #                 "name": "Cash on Delivery",
        #                 "icon": "cod",
        #                 "extra_charge": Decimal("40.00"),
        #             }
        #         )
        # COD always available (can add pincode check later if needed)
        methods.append(
            {
                "id": "cod",
                "name": "Cash on Delivery",
                "icon": "cod",
                "extra_charge": Decimal("40.00"),
            }
        )

        return methods


class ApplyCouponView(LoginRequiredMixin, View):
    def post(self, request):
        coupon_code = request.POST.get("coupon_code")
        cart = get_object_or_404(Cart, user=request.user, is_active=True)

        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            if coupon.is_valid_for_user(request.user, cart.total()):
                request.session["applied_coupon"] = coupon_code
                messages.success(request, f"Coupon {coupon_code} applied successfully!")
            else:
                messages.error(request, "This coupon is not valid for your order.")
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")

        return redirect("checkout_payment")


class RemoveCouponView(LoginRequiredMixin, View):
    def post(self, request):
        if "applied_coupon" in request.session:
            del request.session["applied_coupon"]
            messages.success(request, "Coupon removed.")
        return redirect("checkout_payment")


class OrderCreateView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request):
        address_id = request.session.get("checkout_address_id")
        shipping_id = request.session.get("checkout_shipping_id")
        payment_method = request.POST.get("payment_method")

        if not all([address_id, shipping_id, payment_method]):
            messages.error(request, "Please complete all checkout steps.")
            return redirect("checkout_address")

        if payment_method == "razorpay" and not is_razorpay_configured():
            messages.error(
                request,
                "Razorpay payments are not configured for this environment. Please choose another payment method.",
            )
            return redirect("checkout_payment")

        cart = get_object_or_404(Cart, user=request.user, is_active=True)
        address = get_object_or_404(Address, id=address_id, user=request.user)

        for item in cart.items.select_related("variant__inventory").all():
            if item.variant.available_stock() < item.quantity:
                messages.error(request, f"Insufficient stock for {item.variant.product.name}")
                return redirect("cart")

        subtotal = cart.total()
        shipping_cost = Decimal("50.00") if shipping_id == "standard" else Decimal("150.00")
        tax = calculate_tax(cart)
        discount = Decimal("0.00")
        
        # Add COD charges if COD is selected
        cod_charge = Decimal("0.00")
        if payment_method == "cod":
            cod_charge = Decimal("40.00")

        coupon = None
        coupon_code = request.session.get("applied_coupon")
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, active=True).first()
            if coupon:
                discount = coupon.discount_amount(subtotal)

        total = subtotal + shipping_cost + tax + cod_charge - discount

        order = Order.objects.create(
            user=request.user,
            address=address,
            status="pending",
            subtotal=subtotal,
            shipping_amount=shipping_cost,
            tax_amount=tax,
            discount_amount=discount,
            total=total,
            coupon=coupon,
        )

        for cart_item in cart.items.select_related("variant").all():
            OrderItem.objects.create(
                order=order,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                unit_price=cart_item.variant.get_price(),
            )

        for item in order.items.select_related("variant__inventory").all():
            item.variant.inventory.reserve(item.quantity)

        if coupon:
            from ..models import CouponUsage  # Lazy import to avoid circular imports

            CouponUsage.objects.create(coupon=coupon, user=request.user, order=order)

        if payment_method == "razorpay":
            payment = Payment.objects.create(
                order=order, amount=total, method="razorpay", status="initiated"
            )

            try:
                client = get_razorpay_client()
                razorpay_order = client.order.create(
                    {"amount": int(total * 100), "currency": "INR", "receipt": str(order.id)}
                )
            except (ImproperlyConfigured, BadRequestError) as exc:
                transaction.set_rollback(True)
                messages.error(
                    request,
                    "Razorpay payments are temporarily unavailable. Please choose another method.",
                )
                return redirect("checkout_payment")

            payment.reference = razorpay_order["id"]
            payment.save()

            request.session["pending_order_id"] = str(order.id)
            request.session["razorpay_order_id"] = razorpay_order["id"]

            return JsonResponse(
                {
                    "success": True,
                    "razorpay_order_id": razorpay_order["id"],
                    "amount": int(total * 100),
                    "currency": "INR",
                    "name": "Your Store",
                    "order_id": str(order.id),
                }
            )

        if payment_method == "wallet":
            if request.user.wallet_balance >= total:
                request.user.wallet_balance = F("wallet_balance") - total
                request.user.save()
                request.user.refresh_from_db()

                payment = Payment.objects.create(
                    order=order, amount=total, method="wallet", status="success"
                )

                order.mark_paid(payment)
                cart.items.all().delete()
                self.clear_checkout_session(request)

                return redirect("order_success", id=order.id)

            messages.error(request, "Insufficient wallet balance.")
            order.delete()
            return redirect("checkout_payment")

        if payment_method == "cod":
            Payment.objects.create(order=order, amount=total, method="cod", status="pending")
            order.status = "processing"
            order.save()

            cart.items.all().delete()
            self.clear_checkout_session(request)

            return redirect("order_success", id=order.id)

    def clear_checkout_session(self, request):
        keys_to_clear = [
            "checkout_address_id",
            "checkout_shipping_id",
            "applied_coupon",
            "pending_order_id",
        ]
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayVerifyView(View):
    def post(self, request):
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_signature = request.POST.get("razorpay_signature")

        client = get_razorpay_client()
        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_signature": razorpay_signature,
                }
            )

            payment = Payment.objects.get(reference=razorpay_order_id)
            payment.mark_success(
                {"payment_id": razorpay_payment_id, "signature": razorpay_signature}
            )

            cart = Cart.objects.get(user=payment.order.user, is_active=True)
            cart.items.all().delete()

            return JsonResponse({"success": True, "order_id": str(payment.order.id)})

        except Exception as exc:
            payment = Payment.objects.filter(reference=razorpay_order_id).first()
            if payment:
                payment.status = "failed"
                payment.save()

            return JsonResponse({"success": False, "error": str(exc)})

