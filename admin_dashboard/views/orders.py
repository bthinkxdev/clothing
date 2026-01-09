# admin_dashboard/views/orders.py
from django.shortcuts import get_object_or_404,redirect
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string

from .base import (
    BaseAdminListView, BaseAdminDetailView, 
    BaseAdminUpdateView, BaseAdminAPIView
)
from app.models import Order, Payment
from ..services import OrderManagementService
from ..utils import FilterHelper, PaginationHelper
from ..forms import OrderUpdateForm, OrderBulkUpdateForm
from django.contrib import messages


class OrderListView(BaseAdminListView):
    """List all orders with filtering"""
    
    model = Order
    template_name = 'admin_dashboard/orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Orders', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'user', 'address', 'coupon'
        ).prefetch_related('items', 'payments')
        
        # Apply filters
        filters = FilterHelper.build_order_filters(self.request)
        
        # Handle search separately
        search = filters.pop('_search', None)
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(tracking_number__icontains=search)
            )
        
        queryset = queryset.filter(**filters)
        # distinct() to prevent duplicate orders when filtering by payment method
        queryset = queryset.distinct()
        
        # Ordering
        order_by = self.request.GET.get('order_by', '-placed_at')
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_filter_options(self):
        return {
            'statuses': Order.ORDER_STATUS,
            'payment_methods': Payment.PAYMENT_METHOD,
        }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add summary statistics
        queryset = self.get_queryset()
        context['total_orders'] = queryset.count()
        context['total_revenue'] = sum(order.total for order in queryset)
        
        # Current filters
        context['current_status'] = self.request.GET.get('status', '')
        context['current_payment_method'] = self.request.GET.get('payment_method', '')
        context['date_range'] = self.request.GET.get('date_range', 'last_30_days')

         # Include filter options in context
        context['filter_options'] = self.get_filter_options()
        
        return context


class OrderDetailView(BaseAdminDetailView):
    """View detailed order information"""
    
    model = Order
    template_name = 'admin_dashboard/orders/order_detail.html'
    context_object_name = 'order'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Orders', 'url': reverse_lazy('admin_dashboard:order_list')},
            {'title': f'Order #{str(self.object.id)[:8]}', 'url': '#'},
        ]
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'user', 'address', 'coupon'
        ).prefetch_related(
            'items__variant__product__images',
            'payments'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        order = self.object
        
        # Calculate additional metrics
        context['item_count'] = order.items.count()
        context['total_quantity'] = sum(item.quantity for item in order.items.all())
        
        # Get payment information
        context['payments'] = order.payments.all()
        context['total_paid'] = sum(
            p.amount for p in order.payments.filter(status='success')
        )
        
        # Order timeline
        context['timeline'] = OrderManagementService.get_order_timeline(str(self.object.id))
        
        return context


class OrderUpdateView(BaseAdminUpdateView):
    """Update order details"""
    
    model = Order
    form_class = OrderUpdateForm
    template_name = 'admin_dashboard/orders/order_update.html'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Orders', 'url': reverse_lazy('admin_dashboard:order_list')},
            {'title': f'Order #{str(self.object.id)[:8]}', 'url': reverse_lazy('admin_dashboard:order_detail', kwargs={'pk': self.object.pk})},
            {'title': 'Update', 'url': '#'},
        ]
    
    def get_success_url(self):
        return reverse_lazy('admin_dashboard:order_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Handle status change
        old_status = self.object.status
        new_status = form.cleaned_data['status']
        
        if old_status != new_status:
            try:
                notes = form.cleaned_data.get('notes', '')
                OrderManagementService.update_order_status(
                    str(self.object.id),
                    new_status,
                    notes
                )
                messages.success(self.request, f'Order status updated to {new_status}')
            except ValueError as e:
                messages.error(self.request, str(e))
                return self.form_invalid(form)
        
        return super().form_valid(form)


class OrderCancelView(BaseAdminAPIView):
    """Cancel an order"""
    
    def post(self, request, pk, *args, **kwargs):
        try:
            order = Order.objects.get(pk=pk)
            
            # Check if order can be cancelled
            if order.status in ['delivered', 'cancelled', 'refunded']:
                return self.error_response(
                    f'Cannot cancel order with status: {order.status}'
                )
            
            # Cancel order
            reason = request.POST.get('reason', 'Cancelled by admin')
            OrderManagementService.update_order_status(
                str(order.id),
                'cancelled',
                f'Cancellation reason: {reason}'
            )
            
            return self.success_response(message='Order cancelled successfully')
            
        except Order.DoesNotExist:
            return self.error_response('Order not found', status=404)
        except Exception as e:
            return self.error_response(str(e))


class OrderInvoiceView(BaseAdminDetailView):
    """Generate and display order invoice"""
    
    model = Order
    template_name = 'admin_dashboard/orders/order_invoice.html'
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Get invoice data
        invoice_data = OrderManagementService.generate_invoice_data(str(self.object.id))
        
        # Check if PDF download is requested
        if request.GET.get('download') == 'pdf':
            return self.generate_pdf_invoice(invoice_data)
        
        context = self.get_context_data(object=self.object)
        context.update(invoice_data)
        
        return self.render_to_response(context)
    
    def generate_pdf_invoice(self, invoice_data):
        """Generate PDF invoice (requires reportlab or weasyprint)"""
        try:
            from django.template.loader import render_to_string
            from weasyprint import HTML
            
            html_string = render_to_string(
                'admin_dashboard/orders/invoice_pdf.html',
                invoice_data
            )
            
            pdf_file = HTML(string=html_string).write_pdf()
            
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_data["invoice_number"]}.pdf"'
            
            return response
            
        except ImportError:
            messages.error(self.request, 'PDF generation not available')
            return redirect('admin_dashboard:order_detail', pk=self.object.pk)


class OrderBulkUpdateView(BaseAdminAPIView):
    """Bulk update multiple orders"""
    
    def post(self, request, *args, **kwargs):
        import json
        
        try:
            data = json.loads(request.body)
            order_ids = data.get('order_ids', [])
            action = data.get('action')
            new_status = data.get('status')
            
            if not order_ids:
                return self.error_response('No orders selected')
            
            if action == 'update_status' and new_status:
                count = OrderManagementService.bulk_update_order_status(
                    order_ids,
                    new_status
                )
                return self.success_response(
                    message=f'{count} orders updated successfully'
                )
            
            return self.error_response('Invalid action')
            
        except json.JSONDecodeError:
            return self.error_response('Invalid JSON data')
        except Exception as e:
            return self.error_response(str(e))