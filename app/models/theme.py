from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

__all__ = ["DesignPattern", "SiteTheme"]


class DesignPattern(models.Model):
    """Model to store design pattern configurations"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Radius Scale (in pixels)
    radius_xxs = models.IntegerField(default=2, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_xs = models.IntegerField(default=4, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_sm = models.IntegerField(default=6, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_md = models.IntegerField(default=10, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_lg = models.IntegerField(default=14, validators=[MinValueValidator(0), MaxValueValidator(50)])
    radius_xl = models.IntegerField(default=18, validators=[MinValueValidator(0), MaxValueValidator(50)])

    # Shadow configurations
    shadow_sm = models.CharField(max_length=200, default="0 2px 6px rgba(0, 0, 0, 0.06)")
    shadow_md = models.CharField(max_length=200, default="0 6px 18px rgba(0, 0, 0, 0.08)")
    shadow_lg = models.CharField(max_length=200, default="0 10px 30px rgba(0, 0, 0, 0.12)")
    shadow_floating = models.CharField(max_length=200, default="0 20px 50px rgba(0, 0, 0, 0.12)")

    # Backdrop blur
    backdrop_blur = models.IntegerField(default=12, validators=[MinValueValidator(0), MaxValueValidator(50)])

    # Border configurations
    border_width = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(10)])
    border_opacity = models.FloatField(default=0.06, validators=[MinValueValidator(0), MaxValueValidator(1)])

    class Meta:
        ordering = ["-is_active", "-is_default", "-created_at"]
        verbose_name = "Design Pattern"
        verbose_name_plural = "Design Patterns"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            DesignPattern.objects.filter(is_active=True).update(is_active=False)
        if self.is_default:
            DesignPattern.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def generate_css(self):
        """Generate CSS variables from the pattern"""
        return f"""
/* Design Pattern: {self.name} */
:root {{
    --radius-xxs: {self.radius_xxs}px;
    --radius-xs: {self.radius_xs}px;
    --radius-sm: {self.radius_sm}px;
    --radius-md: {self.radius_md}px;
    --radius-lg: {self.radius_lg}px;
    --radius-xl: {self.radius_xl}px;
    --shadow-sm: {self.shadow_sm};
    --shadow-md: {self.shadow_md};
    --shadow-lg: {self.shadow_lg};
    --shadow-card: var(--shadow-md);
    --shadow-btn: var(--shadow-sm);
    --shadow-floating: {self.shadow_floating};
    --backdrop-blur: {self.backdrop_blur}px;
    --border-soft: {self.border_width}px solid rgba(0, 0, 0, {self.border_opacity});
}}
"""

    @classmethod
    def get_active_pattern(cls):
        """Get the currently active design pattern"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return cls.objects.filter(is_default=True).first() or cls.create_default_pattern()

    @classmethod
    def create_default_pattern(cls):
        """Create a default design pattern"""
        return cls.objects.create(
            name="Default Pattern",
            description="Default design pattern with standard values",
            is_default=True,
            is_active=True,
        )


class SiteTheme(models.Model):
    """Store site-wide theme configuration"""

    name = models.CharField(max_length=100, default="Default Theme")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    design_pattern = models.ForeignKey(DesignPattern, on_delete=models.SET_NULL, null=True, blank=True)

    # Brand Colors
    primary_color = models.CharField(max_length=7, default="#FF6B6B", help_text="Hex color code")
    primary_dark = models.CharField(max_length=7, default="#E85555")
    secondary_color = models.CharField(max_length=7, default="#FFA07A")
    accent_color = models.CharField(max_length=7, default="#FFD93D")

    # Text & Surfaces
    text_dark = models.CharField(max_length=7, default="#2D3142")
    text_light = models.CharField(max_length=7, default="#6C757D")
    bg_cream = models.CharField(max_length=7, default="#FFFFFF")
    border_color = models.CharField(max_length=7, default="#E8E8E8")

    # State Colors
    error_color = models.CharField(max_length=7, default="#FF5252")
    success_color = models.CharField(max_length=7, default="#4CAF50")
    warning_color = models.CharField(max_length=7, default="#FFB300")
    info_color = models.CharField(max_length=7, default="#00BCD4")

    # Additional Settings
    border_radius = models.CharField(max_length=10, default="8px")
    font_family = models.CharField(max_length=200, default="'Inter', sans-serif")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-updated_at"]

    def __str__(self):
        return f"{self.name} {'(Active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        if self.is_active:
            SiteTheme.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        """Get the currently active theme or create default"""
        theme = cls.objects.filter(is_active=True).first()
        if not theme:
            theme = cls.objects.create(name="Default Theme", is_active=True)
        return theme

    def to_css_vars(self):
        """Convert theme to CSS variables dictionary"""
        return {
            "--primary-color": self.primary_color,
            "--primary-dark": self.primary_dark,
            "--secondary-color": self.secondary_color,
            "--accent-color": self.accent_color,
            "--text-dark": self.text_dark,
            "--text-light": self.text_light,
            "--bg-cream": self.bg_cream,
            "--border-color": self.border_color,
            "--error-color": self.error_color,
            "--success-color": self.success_color,
            "--warning-color": self.warning_color,
            "--info-color": self.info_color,
        }

