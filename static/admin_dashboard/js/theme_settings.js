// Live preview updates
document.addEventListener('DOMContentLoaded', function() {
    const colorInputs = document.querySelectorAll('input[type="color"]');
    const patternInputs = document.querySelectorAll('[id^="id_pattern-"]');
    const patternCards = document.querySelectorAll('[data-preset]');
    
    colorInputs.forEach(input => {
        input.addEventListener('input', function() {
            updatePreview();
            updateColorPreview(this);
        });
    });

    patternInputs.forEach(input => {
        input.addEventListener('input', function() {
            updatePatternPreview();
        });
    });

    patternCards.forEach(card => {
        card.addEventListener('click', () => {
            const preset = card.dataset.preset;
            applyPatternPreset(preset);
            updatePatternPreview();
            setActivePatternCard(card);
        });
    });
    
    // Initialize preview
    updatePreview();
    updatePatternPreview();
});

function updateColorPreview(input) {
    const wrapper = input.closest('.color-input-wrapper');
    const preview = wrapper.querySelector('.color-preview');
    const textInput = wrapper.querySelector('.color-text-input');
    
    preview.style.background = input.value;
    textInput.value = input.value.toUpperCase();
}

function updatePreview() {
    const root = document.documentElement;
    
    const val = (id) => document.getElementById(id)?.value;
    const primary = val('id_theme-primary_color') || val('id_primary_color');
    const primaryDark = val('id_theme-primary_dark') || val('id_primary_dark');
    const secondary = val('id_theme-secondary_color') || val('id_secondary_color');
    const accent = val('id_theme-accent_color') || val('id_accent_color');
    const textDark = val('id_theme-text_dark') || val('id_text_dark');
    const textLight = val('id_theme-text_light') || val('id_text_light');
    const bg = val('id_theme-bg_cream') || val('id_bg_cream');
    const border = val('id_theme-border_color') || val('id_border_color');
    const success = val('id_theme-success_color') || val('id_success_color');
    const error = val('id_theme-error_color') || val('id_error_color');
    const warning = val('id_theme-warning_color') || val('id_warning_color');
    const info = val('id_theme-info_color') || val('id_info_color');
    
    root.style.setProperty('--preview-primary', primary);
    root.style.setProperty('--preview-primary-dark', primaryDark);
    root.style.setProperty('--preview-secondary', secondary);
    root.style.setProperty('--preview-accent', accent);
    root.style.setProperty('--preview-text-dark', textDark);
    root.style.setProperty('--preview-text-light', textLight);
    root.style.setProperty('--preview-bg', bg);
    root.style.setProperty('--preview-border', border);
    root.style.setProperty('--preview-success', success);
    root.style.setProperty('--preview-error', error);
    root.style.setProperty('--preview-warning', warning);
    root.style.setProperty('--preview-info', info);
}

function updatePatternPreview() {
    const root = document.documentElement;
    const getVal = (id) => document.getElementById(id)?.value;

    const radiusXXS = getVal('id_pattern-radius_xxs');
    const radiusXS = getVal('id_pattern-radius_xs');
    const radiusSM = getVal('id_pattern-radius_sm');
    const radiusMD = getVal('id_pattern-radius_md');
    const radiusLG = getVal('id_pattern-radius_lg');
    const radiusXL = getVal('id_pattern-radius_xl');

    const shadowSM = getVal('id_pattern-shadow_sm');
    const shadowMD = getVal('id_pattern-shadow_md');
    const shadowLG = getVal('id_pattern-shadow_lg');
    const shadowFloating = getVal('id_pattern-shadow_floating');

    const blur = getVal('id_pattern-backdrop_blur');
    const borderWidth = getVal('id_pattern-border_width');
    const borderOpacity = getVal('id_pattern-border_opacity');

    if (radiusXXS) root.style.setProperty('--radius-xxs', `${radiusXXS}px`);
    if (radiusXS) root.style.setProperty('--radius-xs', `${radiusXS}px`);
    if (radiusSM) root.style.setProperty('--radius-sm', `${radiusSM}px`);
    if (radiusMD) root.style.setProperty('--radius-md', `${radiusMD}px`);
    if (radiusLG) root.style.setProperty('--radius-lg', `${radiusLG}px`);
    if (radiusXL) root.style.setProperty('--radius-xl', `${radiusXL}px`);

    if (shadowSM) root.style.setProperty('--shadow-sm', shadowSM);
    if (shadowMD) root.style.setProperty('--shadow-md', shadowMD);
    if (shadowLG) root.style.setProperty('--shadow-lg', shadowLG);
    if (shadowFloating) root.style.setProperty('--shadow-floating', shadowFloating);
    if (shadowMD) root.style.setProperty('--shadow-card', shadowMD);
    if (shadowSM) root.style.setProperty('--shadow-btn', shadowSM);

    if (blur) root.style.setProperty('--backdrop-blur', `${blur}px`);
    if (borderWidth && borderOpacity !== undefined) {
        root.style.setProperty('--border-soft', `${borderWidth}px solid rgba(0,0,0,${borderOpacity || 0})`);
    }

    // Apply to preview elements directly for immediate reflection
    const radiusTargets = document.querySelectorAll('.preview-card, .preview-btn, .preview-alert, .preview-text, .color-input-wrapper');
    radiusTargets.forEach(el => el.style.borderRadius = `${radiusMD || 10}px`);

    const shadowTargetsSM = document.querySelectorAll('.preview-btn');
    shadowTargetsSM.forEach(el => {
        el.style.boxShadow = shadowSM || '';
    });

    const shadowTargetsCard = document.querySelectorAll('.preview-card, .preview-text');
    shadowTargetsCard.forEach(el => {
        el.style.boxShadow = shadowMD || '';
    });

    const alertTargets = document.querySelectorAll('.preview-alert');
    alertTargets.forEach(el => {
        el.style.boxShadow = shadowSM || '';
    });
}

function applyPatternPreset(presetName) {
    const presets = {
        'modern-rounded': {
            radius_xxs: 3, radius_xs: 6, radius_sm: 8, radius_md: 12, radius_lg: 16, radius_xl: 24,
            shadow_sm: '0 2px 8px rgba(0, 0, 0, 0.08)',
            shadow_md: '0 8px 24px rgba(0, 0, 0, 0.12)',
            shadow_lg: '0 16px 40px rgba(0, 0, 0, 0.16)',
            shadow_floating: '0 24px 60px rgba(0, 0, 0, 0.18)',
            backdrop_blur: 16,
            border_width: 1,
            border_opacity: 0.08,
        },
        'sharp-professional': {
            radius_xxs: 0, radius_xs: 0, radius_sm: 2, radius_md: 4, radius_lg: 6, radius_xl: 8,
            shadow_sm: '0 1px 3px rgba(0, 0, 0, 0.06)',
            shadow_md: '0 4px 12px rgba(0, 0, 0, 0.08)',
            shadow_lg: '0 8px 24px rgba(0, 0, 0, 0.10)',
            shadow_floating: '0 16px 40px rgba(0, 0, 0, 0.12)',
            backdrop_blur: 8,
            border_width: 1,
            border_opacity: 0.12,
        },
        'soft-minimal': {
            radius_xxs: 4, radius_xs: 8, radius_sm: 12, radius_md: 16, radius_lg: 20, radius_xl: 28,
            shadow_sm: '0 2px 6px rgba(0, 0, 0, 0.04)',
            shadow_md: '0 6px 16px rgba(0, 0, 0, 0.06)',
            shadow_lg: '0 12px 32px rgba(0, 0, 0, 0.08)',
            shadow_floating: '0 20px 50px rgba(0, 0, 0, 0.10)',
            backdrop_blur: 20,
            border_width: 1,
            border_opacity: 0.04,
        },
        'bold-dramatic': {
            radius_xxs: 2, radius_xs: 4, radius_sm: 8, radius_md: 12, radius_lg: 16, radius_xl: 20,
            shadow_sm: '0 4px 12px rgba(0, 0, 0, 0.12)',
            shadow_md: '0 12px 28px rgba(0, 0, 0, 0.16)',
            shadow_lg: '0 20px 48px rgba(0, 0, 0, 0.20)',
            shadow_floating: '0 32px 72px rgba(0, 0, 0, 0.24)',
            backdrop_blur: 12,
            border_width: 2,
            border_opacity: 0.10,
        },
        'ultra-soft': {
            radius_xxs: 6, radius_xs: 10, radius_sm: 14, radius_md: 18, radius_lg: 22, radius_xl: 30,
            shadow_sm: '0 3px 10px rgba(0, 0, 0, 0.08)',
            shadow_md: '0 10px 30px rgba(0, 0, 0, 0.12)',
            shadow_lg: '0 18px 48px rgba(0, 0, 0, 0.16)',
            shadow_floating: '0 26px 70px rgba(0, 0, 0, 0.20)',
            backdrop_blur: 18,
            border_width: 1,
            border_opacity: 0.06,
        },
        'geometric-modern': {
            radius_xxs: 1, radius_xs: 2, radius_sm: 4, radius_md: 8, radius_lg: 12, radius_xl: 16,
            shadow_sm: '0 2px 8px rgba(0, 0, 0, 0.10)',
            shadow_md: '0 8px 22px rgba(0, 0, 0, 0.14)',
            shadow_lg: '0 14px 36px rgba(0, 0, 0, 0.18)',
            shadow_floating: '0 24px 60px rgba(0, 0, 0, 0.20)',
            backdrop_blur: 10,
            border_width: 1,
            border_opacity: 0.08,
        },
        'playful-bouncy': {
            radius_xxs: 4, radius_xs: 8, radius_sm: 12, radius_md: 18, radius_lg: 24, radius_xl: 30,
            shadow_sm: '0 4px 12px rgba(0, 0, 0, 0.12)',
            shadow_md: '0 12px 30px rgba(0, 0, 0, 0.16)',
            shadow_lg: '0 20px 48px rgba(0, 0, 0, 0.20)',
            shadow_floating: '0 32px 72px rgba(0, 0, 0, 0.22)',
            backdrop_blur: 14,
            border_width: 2,
            border_opacity: 0.12,
        },
        'elegant-refined': {
            radius_xxs: 2, radius_xs: 4, radius_sm: 6, radius_md: 10, radius_lg: 14, radius_xl: 18,
            shadow_sm: '0 2px 6px rgba(0, 0, 0, 0.08)',
            shadow_md: '0 8px 20px rgba(0, 0, 0, 0.12)',
            shadow_lg: '0 14px 36px rgba(0, 0, 0, 0.16)',
            shadow_floating: '0 22px 60px rgba(0, 0, 0, 0.18)',
            backdrop_blur: 12,
            border_width: 1,
            border_opacity: 0.08,
        },
        'material-inspired': {
            radius_xxs: 2, radius_xs: 4, radius_sm: 6, radius_md: 8, radius_lg: 10, radius_xl: 14,
            shadow_sm: '0 2px 4px rgba(0,0,0,0.10)',
            shadow_md: '0 6px 12px rgba(0,0,0,0.14)',
            shadow_lg: '0 12px 24px rgba(0,0,0,0.18)',
            shadow_floating: '0 20px 40px rgba(0,0,0,0.20)',
            backdrop_blur: 6,
            border_width: 1,
            border_opacity: 0.08,
        },
        'glassmorphic': {
            radius_xxs: 6, radius_xs: 10, radius_sm: 14, radius_md: 18, radius_lg: 22, radius_xl: 28,
            shadow_sm: '0 6px 20px rgba(0, 0, 0, 0.15)',
            shadow_md: '0 12px 30px rgba(0, 0, 0, 0.18)',
            shadow_lg: '0 20px 50px rgba(0, 0, 0, 0.22)',
            shadow_floating: '0 30px 70px rgba(0, 0, 0, 0.25)',
            backdrop_blur: 20,
            border_width: 1,
            border_opacity: 0.18,
        },
        'retro-flat': {
            radius_xxs: 0, radius_xs: 2, radius_sm: 4, radius_md: 6, radius_lg: 8, radius_xl: 10,
            shadow_sm: 'none',
            shadow_md: 'none',
            shadow_lg: 'none',
            shadow_floating: 'none',
            backdrop_blur: 0,
            border_width: 1,
            border_opacity: 0.12,
        },
        'neomorphic': {
            radius_xxs: 8, radius_xs: 10, radius_sm: 14, radius_md: 18, radius_lg: 22, radius_xl: 28,
            shadow_sm: '8px 8px 16px rgba(0,0,0,0.15), -8px -8px 16px rgba(255,255,255,0.8)',
            shadow_md: '12px 12px 24px rgba(0,0,0,0.16), -12px -12px 24px rgba(255,255,255,0.85)',
            shadow_lg: '16px 16px 32px rgba(0,0,0,0.18), -16px -16px 32px rgba(255,255,255,0.9)',
            shadow_floating: '20px 20px 40px rgba(0,0,0,0.20), -20px -20px 40px rgba(255,255,255,0.92)',
            backdrop_blur: 10,
            border_width: 0,
            border_opacity: 0.0,
        },
    };

    const preset = presets[presetName];
    if (!preset) return;

    const setVal = (id, val) => {
        const el = document.getElementById(`id_pattern-${id}`);
        if (el) el.value = val;
    };

    setVal('radius_xxs', preset.radius_xxs);
    setVal('radius_xs', preset.radius_xs);
    setVal('radius_sm', preset.radius_sm);
    setVal('radius_md', preset.radius_md);
    setVal('radius_lg', preset.radius_lg);
    setVal('radius_xl', preset.radius_xl);

    setVal('shadow_sm', preset.shadow_sm);
    setVal('shadow_md', preset.shadow_md);
    setVal('shadow_lg', preset.shadow_lg);
    setVal('shadow_floating', preset.shadow_floating);

    setVal('backdrop_blur', preset.backdrop_blur);
    setVal('border_width', preset.border_width);
    setVal('border_opacity', preset.border_opacity);

    updatePatternPreview();
    showNotification(`Applied "${presetName.replace('-', ' ')}" design pattern`);
}

function setActivePatternCard(activeCard) {
    document.querySelectorAll('[data-preset]').forEach(card => card.classList.remove('active'));
    if (activeCard) activeCard.classList.add('active');
}

function applyPreset(presetName) {
    const presets = {
        'modern-pink': {
            primary: '#FF6B6B',
            primaryDark: '#E85555',
            secondary: '#FFA07A',
            accent: '#FFD93D',
            textDark: '#2D3142',
            textLight: '#6C757D',
            bg: '#FFFFFF',
            border: '#E8E8E8',
            success: '#4CAF50',
            error: '#FF5252',
            warning: '#FFB300',
            info: '#00BCD4'
        },
        'ocean-blue': {
            primary: '#667eea',
            primaryDark: '#5568d3',
            secondary: '#764ba2',
            accent: '#10b981',
            textDark: '#1f2937',
            textLight: '#6b7280',
            bg: '#f9fafb',
            border: '#e5e7eb',
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        },
        'forest-green': {
            primary: '#059669',
            primaryDark: '#047857',
            secondary: '#10b981',
            accent: '#fbbf24',
            textDark: '#14532d',
            textLight: '#6b7280',
            bg: '#f0fdf4',
            border: '#bbf7d0',
            success: '#22c55e',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#06b6d4'
        },
        'sunset-orange': {
            primary: '#f97316',
            primaryDark: '#ea580c',
            secondary: '#fb923c',
            accent: '#fbbf24',
            textDark: '#7c2d12',
            textLight: '#78716c',
            bg: '#fff7ed',
            border: '#fed7aa',
            success: '#84cc16',
            error: '#dc2626',
            warning: '#f59e0b',
            info: '#0ea5e9'
        },
        'royal-purple': {
            primary: '#9333ea',
            primaryDark: '#7e22ce',
            secondary: '#a855f7',
            accent: '#ec4899',
            textDark: '#1e1b4b',
            textLight: '#64748b',
            bg: '#faf5ff',
            border: '#e9d5ff',
            success: '#10b981',
            error: '#f43f5e',
            warning: '#f59e0b',
            info: '#8b5cf6'
        },
        'midnight-dark': {
            primary: '#3b82f6',
            primaryDark: '#2563eb',
            secondary: '#6366f1',
            accent: '#14b8a6',
            textDark: '#0f172a',
            textLight: '#475569',
            bg: '#f8fafc',
            border: '#cbd5e1',
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#06b6d4'
        },
        'coral-reef': {
            primary: '#f43f5e',
            primaryDark: '#e11d48',
            secondary: '#fb7185',
            accent: '#fbbf24',
            textDark: '#881337',
            textLight: '#78716c',
            bg: '#fff1f2',
            border: '#fecdd3',
            success: '#10b981',
            error: '#dc2626',
            warning: '#f59e0b',
            info: '#06b6d4'
        },
        'mint-fresh': {
            primary: '#14b8a6',
            primaryDark: '#0f766e',
            secondary: '#2dd4bf',
            accent: '#06b6d4',
            textDark: '#134e4a',
            textLight: '#64748b',
            bg: '#f0fdfa',
            border: '#99f6e4',
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#06b6d4'
        }
    };
    
    const preset = presets[presetName];
    if (!preset) return;
    
    // Apply colors to form inputs (prefixed ids)
    document.getElementById('id_theme-primary_color').value = preset.primary;
    document.getElementById('id_theme-primary_dark').value = preset.primaryDark;
    document.getElementById('id_theme-secondary_color').value = preset.secondary;
    document.getElementById('id_theme-accent_color').value = preset.accent;
    document.getElementById('id_theme-text_dark').value = preset.textDark;
    document.getElementById('id_theme-text_light').value = preset.textLight;
    document.getElementById('id_theme-bg_cream').value = preset.bg;
    document.getElementById('id_theme-border_color').value = preset.border;
    document.getElementById('id_theme-success_color').value = preset.success;
    document.getElementById('id_theme-error_color').value = preset.error;
    document.getElementById('id_theme-warning_color').value = preset.warning;
    document.getElementById('id_theme-info_color').value = preset.info;
    
    // Update all color previews
    document.querySelectorAll('input[type="color"]').forEach(input => {
        updateColorPreview(input);
    });
    
    // Update live preview
    updatePreview();
    
    // Show notification
    showNotification('Preset applied successfully!');
}

function resetForm() {
    if (confirm('Are you sure you want to reset the form? All unsaved changes will be lost.')) {
        document.getElementById('themeForm').reset();
        
        // Update all color previews after reset
        setTimeout(() => {
            document.querySelectorAll('input[type="color"]').forEach(input => {
                updateColorPreview(input);
            });
            updatePreview();
        }, 100);
    }
}

function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'alert alert-success';
    notification.innerHTML = `
        <i class="fas fa-check-circle"></i>
        ${message}
    `;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        padding: 1rem 1.5rem;
        background: #4CAF50;
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);


// Design Pattern Presets
const designPatternPresets = {
    'modern-rounded': {
        name: 'Modern Rounded',
        description: 'Smooth, contemporary feel with generous rounded corners and soft shadows',
        radius_xxs: 3,
        radius_xs: 6,
        radius_sm: 8,
        radius_md: 12,
        radius_lg: 16,
        radius_xl: 24,
        shadow_sm: '0 2px 8px rgba(0, 0, 0, 0.08)',
        shadow_md: '0 8px 24px rgba(0, 0, 0, 0.12)',
        shadow_lg: '0 16px 40px rgba(0, 0, 0, 0.16)',
        shadow_floating: '0 24px 60px rgba(0, 0, 0, 0.18)',
        backdrop_blur: 16,
        border_width: 1,
        border_opacity: 0.08,
    },
    'sharp-professional': {
        name: 'Sharp Professional',
        description: 'Clean, minimal rounding for a corporate and professional aesthetic',
        radius_xxs: 0,
        radius_xs: 0,
        radius_sm: 2,
        radius_md: 4,
        radius_lg: 6,
        radius_xl: 8,
        shadow_sm: '0 1px 3px rgba(0, 0, 0, 0.06)',
        shadow_md: '0 4px 12px rgba(0, 0, 0, 0.08)',
        shadow_lg: '0 8px 24px rgba(0, 0, 0, 0.10)',
        shadow_floating: '0 16px 40px rgba(0, 0, 0, 0.12)',
        backdrop_blur: 8,
        border_width: 1,
        border_opacity: 0.12,
    },
    'soft-minimal': {
        name: 'Soft Minimal',
        description: 'Extra soft corners and light shadows for a gentle, airy appearance',
        radius_xxs: 4,
        radius_xs: 8,
        radius_sm: 12,
        radius_md: 16,
        radius_lg: 20,
        radius_xl: 28,
        shadow_sm: '0 2px 6px rgba(0, 0, 0, 0.04)',
        shadow_md: '0 6px 16px rgba(0, 0, 0, 0.06)',
        shadow_lg: '0 12px 32px rgba(0, 0, 0, 0.08)',
        shadow_floating: '0 20px 50px rgba(0, 0, 0, 0.10)',
        backdrop_blur: 20,
        border_width: 1,
        border_opacity: 0.04,
    },
    'bold-dramatic': {
        name: 'Bold Dramatic',
        description: 'Strong shadows and medium rounding for maximum visual impact',
        radius_xxs: 2,
        radius_xs: 4,
        radius_sm: 8,
        radius_md: 12,
        radius_lg: 16,
        radius_xl: 20,
        shadow_sm: '0 4px 12px rgba(0, 0, 0, 0.12)',
        shadow_md: '0 12px 28px rgba(0, 0, 0, 0.16)',
        shadow_lg: '0 20px 48px rgba(0, 0, 0, 0.20)',
        shadow_floating: '0 32px 72px rgba(0, 0, 0, 0.24)',
        backdrop_blur: 12,
        border_width: 2,
        border_opacity: 0.10,
    },
    'ultra-soft': {
        name: 'Ultra Soft',
        description: 'Maximum softness with pill-shaped elements and barely-there shadows',
        radius_xxs: 6,
        radius_xs: 10,
        radius_sm: 14,
        radius_md: 20,
        radius_lg: 28,
        radius_xl: 40,
        shadow_sm: '0 1px 4px rgba(0, 0, 0, 0.03)',
        shadow_md: '0 4px 12px rgba(0, 0, 0, 0.05)',
        shadow_lg: '0 8px 24px rgba(0, 0, 0, 0.06)',
        shadow_floating: '0 16px 40px rgba(0, 0, 0, 0.08)',
        backdrop_blur: 24,
        border_width: 1,
        border_opacity: 0.03,
    },
    'geometric-modern': {
        name: 'Geometric Modern',
        description: 'Balanced geometry with moderate rounding and precise shadows',
        radius_xxs: 2,
        radius_xs: 4,
        radius_sm: 6,
        radius_md: 8,
        radius_lg: 12,
        radius_xl: 16,
        shadow_sm: '0 2px 6px rgba(0, 0, 0, 0.07)',
        shadow_md: '0 6px 18px rgba(0, 0, 0, 0.09)',
        shadow_lg: '0 12px 32px rgba(0, 0, 0, 0.12)',
        shadow_floating: '0 20px 50px rgba(0, 0, 0, 0.14)',
        backdrop_blur: 14,
        border_width: 1,
        border_opacity: 0.07,
    },
    'playful-bouncy': {
        name: 'Playful Bouncy',
        description: 'Fun and energetic with varied corner radii and dynamic shadows',
        radius_xxs: 4,
        radius_xs: 8,
        radius_sm: 12,
        radius_md: 18,
        radius_lg: 24,
        radius_xl: 32,
        shadow_sm: '0 3px 10px rgba(0, 0, 0, 0.10)',
        shadow_md: '0 10px 30px rgba(0, 0, 0, 0.14)',
        shadow_lg: '0 18px 50px rgba(0, 0, 0, 0.18)',
        shadow_floating: '0 28px 70px rgba(0, 0, 0, 0.22)',
        backdrop_blur: 18,
        border_width: 2,
        border_opacity: 0.08,
    },
    'elegant-refined': {
        name: 'Elegant Refined',
        description: 'Sophisticated and refined with subtle curves and delicate shadows',
        radius_xxs: 3,
        radius_xs: 5,
        radius_sm: 7,
        radius_md: 10,
        radius_lg: 14,
        radius_xl: 18,
        shadow_sm: '0 1px 5px rgba(0, 0, 0, 0.05)',
        shadow_md: '0 5px 15px rgba(0, 0, 0, 0.07)',
        shadow_lg: '0 10px 30px rgba(0, 0, 0, 0.09)',
        shadow_floating: '0 18px 50px rgba(0, 0, 0, 0.11)',
        backdrop_blur: 15,
        border_width: 1,
        border_opacity: 0.06,
    },
    'material-inspired': {
        name: 'Material Inspired',
        description: 'Google Material Design principles with elevation-based shadows',
        radius_xxs: 2,
        radius_xs: 4,
        radius_sm: 4,
        radius_md: 8,
        radius_lg: 12,
        radius_xl: 16,
        shadow_sm: '0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24)',
        shadow_md: '0 3px 6px rgba(0, 0, 0, 0.16), 0 3px 6px rgba(0, 0, 0, 0.23)',
        shadow_lg: '0 10px 20px rgba(0, 0, 0, 0.19), 0 6px 6px rgba(0, 0, 0, 0.23)',
        shadow_floating: '0 19px 38px rgba(0, 0, 0, 0.30), 0 15px 12px rgba(0, 0, 0, 0.22)',
        backdrop_blur: 10,
        border_width: 0,
        border_opacity: 0.00,
    },
    'glassmorphic': {
        name: 'Glassmorphic',
        description: 'Frosted glass aesthetic with heavy blur and minimal shadows',
        radius_xxs: 4,
        radius_xs: 8,
        radius_sm: 12,
        radius_md: 16,
        radius_lg: 20,
        radius_xl: 24,
        shadow_sm: '0 4px 6px rgba(0, 0, 0, 0.05)',
        shadow_md: '0 8px 16px rgba(0, 0, 0, 0.07)',
        shadow_lg: '0 12px 24px rgba(0, 0, 0, 0.09)',
        shadow_floating: '0 20px 40px rgba(0, 0, 0, 0.12)',
        backdrop_blur: 32,
        border_width: 1,
        border_opacity: 0.15,
    },
    'retro-flat': {
        name: 'Retro Flat',
        description: 'Flat design with minimal shadows and slight corner rounding',
        radius_xxs: 1,
        radius_xs: 2,
        radius_sm: 3,
        radius_md: 5,
        radius_lg: 8,
        radius_xl: 12,
        shadow_sm: '0 1px 2px rgba(0, 0, 0, 0.08)',
        shadow_md: '0 2px 4px rgba(0, 0, 0, 0.10)',
        shadow_lg: '0 4px 8px rgba(0, 0, 0, 0.12)',
        shadow_floating: '0 8px 16px rgba(0, 0, 0, 0.14)',
        backdrop_blur: 6,
        border_width: 2,
        border_opacity: 0.15,
    },
    'neomorphic': {
        name: 'Neomorphic',
        description: 'Soft UI with subtle embossed effect and gentle shadows',
        radius_xxs: 4,
        radius_xs: 8,
        radius_sm: 12,
        radius_md: 16,
        radius_lg: 20,
        radius_xl: 24,
        shadow_sm: '4px 4px 8px rgba(0, 0, 0, 0.1), -4px -4px 8px rgba(255, 255, 255, 0.9)',
        shadow_md: '8px 8px 16px rgba(0, 0, 0, 0.12), -8px -8px 16px rgba(255, 255, 255, 0.9)',
        shadow_lg: '12px 12px 24px rgba(0, 0, 0, 0.14), -12px -12px 24px rgba(255, 255, 255, 0.9)',
        shadow_floating: '20px 20px 40px rgba(0, 0, 0, 0.16), -20px -20px 40px rgba(255, 255, 255, 0.9)',
        backdrop_blur: 8,
        border_width: 0,
        border_opacity: 0.00,
    }
};

// Apply design pattern preset
function applyDesignPatternPreset(presetKey) {
    const preset = designPatternPresets[presetKey];
    if (!preset) return;

    // Apply to pattern form fields
    const fields = [
        'radius_xxs', 'radius_xs', 'radius_sm', 'radius_md', 'radius_lg', 'radius_xl',
        'shadow_sm', 'shadow_md', 'shadow_lg', 'shadow_floating',
        'backdrop_blur', 'border_width', 'border_opacity'
    ];

    fields.forEach(field => {
        const input = document.getElementById(`id_pattern-${field}`);
        if (input && preset[field] !== undefined) {
            input.value = preset[field];
        }
    });

    // Update pattern name and description
    const nameInput = document.getElementById('id_pattern-name');
    const descInput = document.getElementById('id_pattern-description');
    
    if (nameInput) nameInput.value = preset.name;
    if (descInput) descInput.value = preset.description;

    // Update live preview
    updateDesignPatternPreview(preset);

    // Highlight selected preset
    document.querySelectorAll('.design-preset-card').forEach(card => {
        card.classList.remove('selected');
    });
    const selectedCard = document.querySelector(`[data-preset="${presetKey}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    // Show notification
    showNotification(`Applied "${preset.name}" design pattern!`);
}

// Update design pattern preview
function updateDesignPatternPreview(preset) {
    const root = document.documentElement;
    
    // Update CSS variables for preview
    root.style.setProperty('--preview-radius-sm', `${preset.radius_sm}px`);
    root.style.setProperty('--preview-radius-md', `${preset.radius_md}px`);
    root.style.setProperty('--preview-radius-lg', `${preset.radius_lg}px`);
    root.style.setProperty('--preview-shadow-sm', preset.shadow_sm);
    root.style.setProperty('--preview-shadow-md', preset.shadow_md);
    root.style.setProperty('--preview-shadow-lg', preset.shadow_lg);
    root.style.setProperty('--preview-backdrop-blur', `${preset.backdrop_blur}px`);
    
    // Update preview elements
    const previewElements = document.querySelectorAll('.preview-pattern-demo');
    previewElements.forEach(el => {
        const size = el.dataset.size;
        if (size && preset[`radius_${size}`] !== undefined) {
            el.style.borderRadius = `${preset[`radius_${size}`]}px`;
        }
    });
}

// Initialize design pattern preset listener
document.addEventListener('DOMContentLoaded', function() {
    // Add click listeners to preset cards
    document.querySelectorAll('.design-preset-card').forEach(card => {
        card.addEventListener('click', function() {
            const presetKey = this.dataset.preset;
            applyDesignPatternPreset(presetKey);
        });
    });

    // Live update on form field changes
    const patternFields = document.querySelectorAll('[id^="id_pattern-"]');
    patternFields.forEach(field => {
        field.addEventListener('input', function() {
            const currentValues = {};
            
            ['radius_xxs', 'radius_xs', 'radius_sm', 'radius_md', 'radius_lg', 'radius_xl',
             'shadow_sm', 'shadow_md', 'shadow_lg', 'shadow_floating',
             'backdrop_blur', 'border_width', 'border_opacity'].forEach(fieldName => {
                const input = document.getElementById(`id_pattern-${fieldName}`);
                if (input) {
                    currentValues[fieldName] = input.value;
                }
            });
            
            updateDesignPatternPreview(currentValues);
        });
    });
});