from .models import SiteTheme

def theme_context(request):
    """
    Add active theme to all template contexts
    """
    theme = SiteTheme.get_active_theme()
    return {
        'site_theme': theme,
        'theme_css_vars': theme.to_css_vars(),
    }