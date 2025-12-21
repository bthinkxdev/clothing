# admin_dashboard/views/base.py
from typing import Any, Dict
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import JsonResponse

from ..utils import PermissionHelper, NotificationHelper
from ..services import DashboardAnalyticsService


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to require admin/staff permissions"""
    
    login_url = reverse_lazy('admin_dashboard:login')
    
    def test_func(self) -> bool:
        """Test if user has admin permissions"""
        return PermissionHelper.check_admin_permission(self.request.user)
    
    def handle_no_permission(self):
        """Handle users without permission"""
        messages.error(self.request, 'You do not have permission to access this page.')
        return redirect('home')


class BaseAdminView(AdminRequiredMixin, View):
    """Base view for all admin views"""
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add common context to all admin views"""
        context = super().get_context_data(**kwargs) if hasattr(super(), 'get_context_data') else {}
        
        # Add pending actions count
        context['pending_actions'] = NotificationHelper.get_pending_actions()
        
        # Add current user info
        context['admin_user'] = self.request.user
        
        # Add breadcrumbs (override in child classes)
        context['breadcrumbs'] = self.get_breadcrumbs()
        
        return context
    
    def get_breadcrumbs(self) -> list:
        """Get breadcrumbs for navigation (override in child classes)"""
        return [
            {'title': 'Dashboard', 'url': reverse_lazy('admin_dashboard:home')},
        ]


class BaseAdminTemplateView(BaseAdminView, TemplateView):
    """Base template view for admin"""
    pass


class BaseAdminListView(BaseAdminView, ListView):
    """Base list view for admin"""
    
    paginate_by = 25
    context_object_name = 'items'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['filters'] = self.get_filter_options()
        
        # Add search query
        context['search_query'] = self.request.GET.get('search', '')
        
        return context
    
    def get_filter_options(self) -> Dict:
        """Get filter options for the list (override in child classes)"""
        return {}


class BaseAdminDetailView(BaseAdminView, DetailView):
    """Base detail view for admin"""
    
    context_object_name = 'item'


class BaseAdminCreateView(BaseAdminView, CreateView):
    """Base create view for admin"""
    
    def form_valid(self, form):
        """Add success message on form valid"""
        response = super().form_valid(form)
        messages.success(self.request, f'{self.model.__name__} created successfully!')
        return response
    
    def form_invalid(self, form):
        """Add error message on form invalid"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class BaseAdminUpdateView(BaseAdminView, UpdateView):
    """Base update view for admin"""
    
    def form_valid(self, form):
        """Add success message on form valid"""
        response = super().form_valid(form)
        messages.success(self.request, f'{self.model.__name__} updated successfully!')
        return response
    
    def form_invalid(self, form):
        """Add error message on form invalid"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class BaseAdminDeleteView(BaseAdminView, DeleteView):
    """Base delete view for admin"""
    
    def delete(self, request, *args, **kwargs):
        """Add success message on delete"""
        messages.success(request, f'{self.model.__name__} deleted successfully!')
        return super().delete(request, *args, **kwargs)


class BaseAdminAPIView(AdminRequiredMixin, View):
    """Base API view for AJAX requests"""
    
    def dispatch(self, request, *args, **kwargs):
        """Ensure JSON responses for API views"""
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def json_response(self, data: Dict, status: int = 200) -> JsonResponse:
        """Helper to return JSON response"""
        return JsonResponse(data, status=status)
    
    def success_response(self, data: Dict = None, message: str = None) -> JsonResponse:
        """Return success JSON response"""
        response = {'success': True}
        if message:
            response['message'] = message
        if data:
            response['data'] = data
        return self.json_response(response)
    
    def error_response(self, message: str, status: int = 400) -> JsonResponse:
        """Return error JSON response"""
        return self.json_response({
            'success': False,
            'error': message
        }, status=status)