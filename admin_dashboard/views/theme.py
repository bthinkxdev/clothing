# app/theme.py

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect

from ..forms import ThemeForm, DesignPatternForm
from app.models import SiteTheme, DesignPattern


@staff_member_required
def theme_settings(request):
    """View for managing site theme + design pattern together."""
    theme = SiteTheme.get_active_theme()
    pattern = theme.design_pattern or DesignPattern.get_active_pattern()

    if request.method == 'POST':
        theme_form = ThemeForm(request.POST, instance=theme, prefix="theme")
        pattern_form = DesignPatternForm(request.POST, instance=pattern, prefix="pattern")

        if theme_form.is_valid() and pattern_form.is_valid():
            pattern_obj = pattern_form.save(commit=False)
            pattern_obj.is_active = True
            pattern_obj.save()

            saved_theme = theme_form.save(commit=False)
            saved_theme.design_pattern = pattern_obj
            saved_theme.save()

            messages.success(request, 'Theme and design pattern updated successfully!')
            return redirect('admin_dashboard:theme_settings')
    else:
        theme_form = ThemeForm(instance=theme, prefix="theme")
        pattern_form = DesignPatternForm(instance=pattern, prefix="pattern")

    return render(request, 'admin_dashboard/theme/theme_settings.html', {
        'theme_form': theme_form,
        'pattern_form': pattern_form,
        'theme': theme,
        'pattern': pattern,
        'admin_user': request.user,
        'pending_actions': {'total': 0},
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': '/admin/'},
            {'title': 'Theme Settings', 'url': None},
        ],
    })