# admin_dashboard/views/dashboard.py
from django.utils import timezone
from django.urls import reverse_lazy
from datetime import timedelta

from .base import BaseAdminTemplateView, BaseAdminAPIView
from ..services import DashboardAnalyticsService, SalesReportService
from ..utils import DateRangeHelper, ChartDataFormatter
from app.models import Order
import json

class DashboardHomeView(BaseAdminTemplateView):
    """Main dashboard home view with overview statistics"""
    
    template_name = 'admin_dashboard/dashboard_home.html'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request
        period = self.request.GET.get('period', 'last_30_days')
        start_date, end_date = DateRangeHelper.get_date_range(period)
        
        # Get dashboard statistics
        stats = DashboardAnalyticsService.get_dashboard_stats(start_date, end_date)

        # Get chart data scoped to selected period
        period_days = max(1, (end_date - start_date).days + 1)
        sales_trend = DashboardAnalyticsService.get_sales_trend(
            days=period_days,
            start_date=start_date,
            end_date=end_date
        )
        order_status = DashboardAnalyticsService.get_order_status_breakdown(
            start_date=start_date,
            end_date=end_date
        )
        category_revenue = DashboardAnalyticsService.get_revenue_by_category(start_date, end_date)
        customer_trend = DashboardAnalyticsService.get_customer_trend(start_date, end_date)
        
        # Convert to JSON for JavaScript
        sales_trend_json = json.dumps(list(sales_trend), default=str)
        order_status_json = json.dumps(order_status)
        category_revenue_json = json.dumps(list(category_revenue), default=str)
        customer_trend_json = json.dumps(list(customer_trend), default=str)
        
        context.update({
            'stats': stats,
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'sales_trend': sales_trend_json,
            'order_status': order_status_json,
            'category_revenue': category_revenue_json,
            'customer_trend': customer_trend_json,
        })
        # Get recent orders for activity feed
        recent_orders = Order.objects.select_related('user').filter(
            placed_at__range=[start_date, end_date]
        ).order_by('-placed_at')[:5]
        context['recent_orders'] = recent_orders
        return context


class AnalyticsDashboardView(BaseAdminTemplateView):
    """Comprehensive analytics dashboard with charts"""
    
    template_name = 'admin_dashboard/analytics.html'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Analytics', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        period = self.request.GET.get('period', 'last_30_days')
        start_date, end_date = DateRangeHelper.get_date_range(period)
        
        # Get analytics data
        stats = DashboardAnalyticsService.get_dashboard_stats(start_date, end_date)
        
        # Get chart data with date range
        period_days = max(1, (end_date - start_date).days + 1)
        sales_trend = DashboardAnalyticsService.get_sales_trend(
            days=period_days,
            start_date=start_date,
            end_date=end_date
        )
        category_revenue = DashboardAnalyticsService.get_revenue_by_category(start_date, end_date)
        customer_ltv = DashboardAnalyticsService.get_customer_lifetime_value()
        order_status = DashboardAnalyticsService.get_order_status_breakdown(start_date, end_date)
        sales_by_region = DashboardAnalyticsService.get_sales_by_region(start_date, end_date)
        # Convert to JSON for JavaScript
        context.update({
            'stats': stats,
            'sales_trend_json': json.dumps(list(sales_trend), default=str),
            'category_revenue_json': json.dumps(list(category_revenue), default=str),
            'customer_ltv_json': json.dumps(customer_ltv[:10], default=str),
            'sales_by_region_json': json.dumps(sales_by_region, default=str), 
            'order_status_json': json.dumps(order_status),
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
        })
        
        return context


class SalesReportView(BaseAdminTemplateView):
    """Detailed sales report view"""
    
    template_name = 'admin_dashboard/sales_report.html'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Sales Report', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range
        period = self.request.GET.get('period', 'last_30_days')
        if period == 'custom':
            start_str = self.request.GET.get('start_date')
            end_str = self.request.GET.get('end_date')
            start_date, end_date = DateRangeHelper.parse_custom_date_range(start_str, end_str)
        else:
            start_date, end_date = DateRangeHelper.get_date_range(period)
        
        # Get grouping
        group_by = self.request.GET.get('group_by', 'day')
        
        # Generate report
        report = SalesReportService.generate_sales_report(start_date, end_date, group_by)
        product_performance = SalesReportService.get_product_performance_report(start_date, end_date)
        
        context.update({
            'report': json.dumps(report, default=str),
            'raw_report': report,
            'product_performance': product_performance,
            'start_date': start_date,
            'end_date': end_date,
            'period': period,
            'group_by': group_by,
        })
        
        return context


class SalesReportExportView(BaseAdminAPIView):
    """Export sales report to CSV/Excel"""
    
    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse
        
        # Get parameters
        format_type = request.GET.get('format', 'csv')
        period = request.GET.get('period', 'last_30_days')
        
        if period == 'custom':
            start_str = request.GET.get('start_date')
            end_str = request.GET.get('end_date')
            start_date, end_date = DateRangeHelper.parse_custom_date_range(start_str, end_str)
        else:
            start_date, end_date = DateRangeHelper.get_date_range(period)
        
        if format_type == 'csv':
            # Generate CSV
            csv_content = SalesReportService.export_sales_report_csv(start_date, end_date)
            
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date.date()}_{end_date.date()}.csv"'
            return response

        elif format_type == 'excel':
            excel_content = SalesReportService.export_sales_report_excel(start_date, end_date)
            response = HttpResponse(
                excel_content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date.date()}_{end_date.date()}.xlsx"'
            return response

        else:
            return self.error_response('Invalid format type')


class RevenueAnalyticsView(BaseAdminTemplateView):
    """Revenue analytics with detailed breakdowns"""
    
    template_name = 'admin_dashboard/revenue_analytics.html'
    
    def get_breadcrumbs(self):
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
            {'title': 'Revenue Analytics', 'url': '#'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        period = self.request.GET.get('period', 'last_30_days')
        start_date, end_date = DateRangeHelper.get_date_range(period)
        
        # Get revenue data
        stats = DashboardAnalyticsService.get_dashboard_stats(start_date, end_date)
        category_revenue = DashboardAnalyticsService.get_revenue_by_category(start_date, end_date)
        
        context.update({
            'stats': stats,
            'category_revenue': category_revenue,
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
        })
        
        return context


# API Views for AJAX Chart Data

class DashboardStatsAPIView(BaseAdminAPIView):
    """API endpoint for dashboard statistics"""
    
    def get(self, request, *args, **kwargs):
        period = request.GET.get('period', 'last_30_days')
        start_date, end_date = DateRangeHelper.get_date_range(period)
        
        stats = DashboardAnalyticsService.get_dashboard_stats(start_date, end_date)
        
        return self.success_response(data=stats)


class SalesChartAPIView(BaseAdminAPIView):
    """API endpoint for sales trend chart"""
    
    def get(self, request, *args, **kwargs):
        days = int(request.GET.get('days', 30))
        
        sales_data = DashboardAnalyticsService.get_sales_trend(days)
        
        # Format for chart
        chart_data = ChartDataFormatter.format_line_chart(
            sales_data,
            x_key='date',
            y_keys=['revenue', 'orders'],
            labels=['Revenue (₹)', 'Orders']
        )
        
        return self.success_response(data=chart_data)


class RevenueChartAPIView(BaseAdminAPIView):
    """API endpoint for revenue chart"""
    
    def get(self, request, *args, **kwargs):
        period = request.GET.get('period', 'last_30_days')
        start_date, end_date = DateRangeHelper.get_date_range(period)
        
        category_data = DashboardAnalyticsService.get_revenue_by_category(start_date, end_date)
        
        # Format for chart
        chart_data = ChartDataFormatter.format_bar_chart(
            category_data,
            x_key='variant__product__category__name',
            y_key='revenue',
            label='Revenue by Category'
        )
        
        return self.success_response(data=chart_data)


class OrderStatusChartAPIView(BaseAdminAPIView):
    """API endpoint for order status breakdown chart"""
    
    def get(self, request, *args, **kwargs):
        status_data = DashboardAnalyticsService.get_order_status_breakdown()
        
        # Convert to list format
        data_list = [
            {'status': k, 'count': v}
            for k, v in status_data.items()
        ]
        
        # Format for pie chart
        chart_data = ChartDataFormatter.format_pie_chart(
            data_list,
            label_key='status',
            value_key='count'
        )
        
        return self.success_response(data=chart_data)


class ProductPerformanceAPIView(BaseAdminAPIView):
    """API endpoint for product performance data"""
    
    def get(self, request, *args, **kwargs):
        period = request.GET.get('period', 'last_30_days')
        start_date, end_date = DateRangeHelper.get_date_range(period)
        
        products = SalesReportService.get_product_performance_report(start_date, end_date)
        
        return self.success_response(data=list(products[:20]))


class CustomerAnalyticsAPIView(BaseAdminAPIView):
    """API endpoint for customer analytics"""
    
    def get(self, request, *args, **kwargs):
        customer_ltv = DashboardAnalyticsService.get_customer_lifetime_value()
        
        return self.success_response(data=customer_ltv)