// Live preview updates
document.addEventListener('DOMContentLoaded', function() {
    const colorInputs = document.querySelectorAll('input[type="color"]');
    
    colorInputs.forEach(input => {
        input.addEventListener('input', function() {
            updatePreview();
            updateColorPreview(this);
        });
    });
    
    // Initialize preview
    updatePreview();
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
    
    // Get all color values
    const primary = document.getElementById('id_primary_color').value;
    const primaryDark = document.getElementById('id_primary_dark').value;
    const secondary = document.getElementById('id_secondary_color').value;
    const accent = document.getElementById('id_accent_color').value;
    const textDark = document.getElementById('id_text_dark').value;
    const textLight = document.getElementById('id_text_light').value;
    const bg = document.getElementById('id_bg_cream').value;
    const border = document.getElementById('id_border_color').value;
    const success = document.getElementById('id_success_color').value;
    const error = document.getElementById('id_error_color').value;
    const warning = document.getElementById('id_warning_color').value;
    const info = document.getElementById('id_info_color').value;
    
    // Update CSS variables for preview
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
    
    // Apply colors to form inputs
    document.getElementById('id_primary_color').value = preset.primary;
    document.getElementById('id_primary_dark').value = preset.primaryDark;
    document.getElementById('id_secondary_color').value = preset.secondary;
    document.getElementById('id_accent_color').value = preset.accent;
    document.getElementById('id_text_dark').value = preset.textDark;
    document.getElementById('id_text_light').value = preset.textLight;
    document.getElementById('id_bg_cream').value = preset.bg;
    document.getElementById('id_border_color').value = preset.border;
    document.getElementById('id_success_color').value = preset.success;
    document.getElementById('id_error_color').value = preset.error;
    document.getElementById('id_warning_color').value = preset.warning;
    document.getElementById('id_info_color').value = preset.info;
    
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
