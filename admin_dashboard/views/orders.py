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
from ..utils import FilterHelper, PaginationHelper, PermissionHelper
from ..forms import OrderUpdateForm, OrderBulkUpdateForm
from django.contrib import messages


class OrderListView(BaseAdminListView):
    """List all orders with filtering"""
    
    model = Order
    template_name = 'admin_dashboard/orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25
    vendor_field = None
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Orders', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = Order.objects.select_related(
            'user', 'address', 'coupon'
        ).prefetch_related('items', 'payments')

        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                Q(vendor=vendor) | Q(items__variant__product__vendor=vendor)
            ).distinct()
        
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
    vendor_field = None
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Orders', 'url': reverse_lazy('admin_dashboard:order_list')},
            {'title': f'Order #{str(self.object.id)[:8]}', 'url': '#'},
        ]
    
    def get_queryset(self):
        queryset = Order.objects.select_related(
            'user', 'address', 'coupon'
        ).prefetch_related(
            'items__variant__product__images',
            'payments'
        )
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                Q(vendor=vendor) | Q(items__variant__product__vendor=vendor)
            ).distinct()
        return queryset
    
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
    vendor_field = None
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Orders', 'url': reverse_lazy('admin_dashboard:order_list')},
            {'title': f'Order #{str(self.object.id)[:8]}', 'url': reverse_lazy('admin_dashboard:order_detail', kwargs={'pk': self.object.pk})},
            {'title': 'Update', 'url': '#'},
        ]
    
    def get_success_url(self):
        return reverse_lazy('admin_dashboard:order_detail', kwargs={'pk': self.object.pk})
    
    def get_queryset(self):
        queryset = Order.objects.all()
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                Q(vendor=vendor) | Q(items__variant__product__vendor=vendor)
            ).distinct()
        return queryset
    
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
            queryset = Order.objects.all()
            if PermissionHelper.is_vendor(request.user):
                vendor = PermissionHelper.get_vendor(request.user)
                queryset = queryset.filter(
                    Q(vendor=vendor) | Q(items__variant__product__vendor=vendor)
                ).distinct()
            order = queryset.get(pk=pk)
            
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
    vendor_field = None

    def get_queryset(self):
        queryset = Order.objects.select_related("user", "address", "coupon")
        if PermissionHelper.is_vendor(self.request.user):
            vendor = PermissionHelper.get_vendor(self.request.user)
            queryset = queryset.filter(
                Q(vendor=vendor) | Q(items__variant__product__vendor=vendor)
            ).distinct()
        return queryset
    vendor_field = None
    
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
        """Generate PDF invoice with ReportLab (pure Python, no GTK deps)"""
        from io import BytesIO
        from decimal import Decimal

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            )
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            messages.error(self.request, 'PDF generation not available (install reportlab)')
            return redirect('admin_dashboard:order_detail', pk=self.object.pk)

        # Register a font that supports Indian Rupee symbol
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            font_name = 'DejaVuSans'
        except:
            # Fallback: use Rs. instead of ₹ symbol with default fonts
            font_name = 'Helvetica'

        def fmt_money(value):
            try:
                if font_name == 'DejaVuSans':
                    return f"₹{Decimal(value):,.2f}"
                else:
                    return f"Rs. {Decimal(value):,.2f}"
            except Exception:
                if font_name == 'DejaVuSans':
                    return f"₹{value}"
                else:
                    return f"Rs. {value}"

        order = invoice_data.get('order')
        items = list(invoice_data.get('items') or [])

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=f"Invoice {invoice_data.get('invoice_number')}"
        )

        styles = getSampleStyleSheet()
        
        # Update styles to use the registered font
        h1 = styles['Heading1']
        h1.fontName = font_name
        
        h2 = styles['Heading2']
        h2.fontName = font_name
        
        body = styles['BodyText']
        body.fontName = font_name

        elements = []

        elements.append(Paragraph("Invoice", h1))
        elements.append(Paragraph(invoice_data.get('invoice_number', ''), h2))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"Date: {invoice_data.get('invoice_date'):%Y-%m-%d}", body))
        elements.append(Paragraph(f"Order ID: {order.id}", body))
        elements.append(Paragraph(f"Customer: {order.user.username}", body))
        elements.append(Paragraph(f"Email: {order.user.email}", body))

        if order.address:
            addr = order.address
            address_lines = [
                addr.full_name or '',
                addr.line1 or '',
                addr.line2 or '',
                f"{addr.city or ''}, {addr.state or ''} {addr.postal_code or ''}",
                addr.country or '',
                f"Phone: {addr.phone}" if getattr(addr, 'phone', '') else ''
            ]
            address_lines = [line for line in address_lines if line and line.strip()]
            elements.append(Paragraph("Shipping Address:", h2))
            for line in address_lines:
                elements.append(Paragraph(line, body))
        elements.append(Spacer(1, 12))

        # Items table
        table_data = [["#", "Item", "Qty", "Unit Price", "Total"]]
        for idx, item in enumerate(items, start=1):
            product_name = getattr(item.variant.product, "name", str(item.variant))
            qty = item.quantity
            unit = fmt_money(item.unit_price)
            line_total = fmt_money(item.line_total())
            table_data.append([idx, product_name, qty, unit, line_total])

        item_table = Table(table_data, hAlign='LEFT')
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name), 
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 12))

        # Totals summary
        summary_rows = [
            ["Subtotal", fmt_money(order.subtotal)],
            ["Shipping", fmt_money(order.shipping_amount)],
            ["Tax", fmt_money(order.tax_amount)],
            ["Discount", f"-{fmt_money(order.discount_amount)}" if order.discount_amount else fmt_money(0)]
        ]
        summary_rows.append(["Total", fmt_money(order.total)])

        summary_table = Table(summary_rows, colWidths=[80 * mm, 40 * mm], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),  # Apply font to summary table
            ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(summary_table)

        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_data.get("invoice_number")}.pdf"'
        return response


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
                scoped_ids = order_ids
                if PermissionHelper.is_vendor(request.user):
                    vendor = PermissionHelper.get_vendor(request.user)
                    scoped_ids = list(
                        Order.objects.filter(
                            Q(vendor=vendor) | Q(items__variant__product__vendor=vendor),
                            id__in=order_ids,
                        ).values_list("id", flat=True)
                    )
                count = OrderManagementService.bulk_update_order_status(
                    scoped_ids,
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