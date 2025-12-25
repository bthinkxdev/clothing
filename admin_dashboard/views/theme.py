# app/theme.py

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect

from ..forms import ThemeForm
from app.models import SiteTheme


@staff_member_required
def theme_settings(request):
    """View for managing site theme"""
    theme = SiteTheme.get_active_theme()
    
    if request.method == 'POST':
        form = ThemeForm(request.POST, instance=theme)
        if form.is_valid():
            form.save()
            messages.success(request, 'Theme updated successfully!')
            return redirect('admin_dashboard:theme_settings')
    else:
        form = ThemeForm(instance=theme)
    
    return render(request, 'admin_dashboard/theme/theme_settings.html', {
        'form': form,
        'theme': theme,
        'admin_user': request.user,
        'pending_actions': {'total': 0},
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': '/admin/'},
            {'title': 'Theme Settings', 'url': None},
        ],
    })