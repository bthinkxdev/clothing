# app/theme.py


from django.contrib import messages
from django.http import HttpResponse


from ..models import SiteTheme, DesignPattern


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to 'r, g, b' string; return fallback for invalid."""
    try:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            raise ValueError
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return f"{r}, {g}, {b}"
    except Exception:
        return "139, 69, 19"  # fallback to primary default


def theme_css(request):
    """Serve CSS variables based on the active theme and design pattern."""
    theme = SiteTheme.get_active_theme()
    pattern = theme.design_pattern or DesignPattern.get_active_pattern()

    defaults = {
        "--primary-color": "#8B4513",
        "--primary-rgb": "139, 69, 19",
        "--primary-dark": "#6B3410",
        "--secondary-color": "#D2691E",
        "--accent-color": "#FFD700",
        "--font-family": "'Inter', sans-serif",
        "--border-radius": "8px",
        "--text-dark": "#2C2C2C",
        "--text-light": "#666666",
        "--bg-cream": "#FAF7F2",
        "--white": "#FFFFFF",
        "--border-color": "#E5E5E5",
        "--error-color": "#DC3545",
        "--success-color": "#28A745",
        "--warning-color": "#FFC107",
        "--info-color": "#17A2B8",
        "--success-soft": "#D4EDDA",
        "--success-soft-text": "#155724",
        "--error-soft": "#F8D7DA",
        "--error-soft-text": "#721C24",
        "--warning-soft": "#FFF3CD",
        "--warning-soft-text": "#856404",
        "--warning-soft-border": "#FFE8A1",
        "--info-soft": "#D1ECF1",
        "--info-soft-text": "#0C5460",
        "--indigo-500": "#667eea",
        "--indigo-500-rgb": "102, 126, 234",
        "--purple-600": "#764ba2",
        "--purple-600-rgb": "118, 75, 162",
        "--emerald-500": "#10b981",
        "--emerald-500-rgb": "16, 185, 129",
        "--rose-500": "#ef4444",
        "--rose-500-rgb": "239, 68, 68",
        "--gray-50": "#f9fafb",
        "--gray-100": "#f3f4f6",
        "--gray-200": "#e5e7eb",
        "--gray-300": "#d1d5db",
        "--gray-400": "#9ca3af",
        "--gray-500": "#6b7280",
        "--gray-600": "#4b5563",
        "--gray-700": "#374151",
        "--gray-800": "#1f2937",
        "--gray-900": "#111827",
        "--slate-50": "#f1f5f9",
        "--slate-300": "#cbd5e1",
        "--slate-400": "#94a3b8",
        "--bg-cream-soft": "#F5E6D3",
    }

    # Apply theme overrides
    overrides = theme.to_css_vars()
    css_vars = {**defaults, **overrides}

    # Apply design pattern overrides
    if pattern:
        css_vars.update({
            "--radius-xxs": f"{pattern.radius_xxs}px",
            "--radius-xs": f"{pattern.radius_xs}px",
            "--radius-sm": f"{pattern.radius_sm}px",
            "--radius-md": f"{pattern.radius_md}px",
            "--radius-lg": f"{pattern.radius_lg}px",
            "--radius-xl": f"{pattern.radius_xl}px",
            "--shadow-sm": pattern.shadow_sm,
            "--shadow-md": pattern.shadow_md,
            "--shadow-lg": pattern.shadow_lg,
            "--shadow-card": pattern.shadow_md,
            "--shadow-btn": pattern.shadow_sm,
            "--shadow-floating": pattern.shadow_floating,
            "--backdrop-blur": f"{pattern.backdrop_blur}px",
            "--border-soft": f"{pattern.border_width}px solid rgba(0, 0, 0, {pattern.border_opacity})",
        })

    # Derive rgb values from possibly overridden primary color
    css_vars["--primary-rgb"] = _hex_to_rgb(css_vars["--primary-color"])
    # Carry through optional theme-level typography/roundness
    if getattr(theme, "font_family", None):
        css_vars["--font-family"] = theme.font_family
    if getattr(theme, "border_radius", None):
        css_vars["--border-radius"] = theme.border_radius

    css_lines = [":root {"]
    for key, value in css_vars.items():
        css_lines.append(f"    {key}: {value};")
    css_lines.append("}")

    return HttpResponse("\n".join(css_lines), content_type="text/css")

