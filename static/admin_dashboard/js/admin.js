// static/admin_dashboard/js/admin.js

document.addEventListener('DOMContentLoaded', function() {
    // Menu Toggle
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.querySelector('.admin-sidebar');
    const overlay = document.getElementById('overlay');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        });
    }
    
    // Notification Panel
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationPanel = document.getElementById('notificationPanel');
    const closeNotifications = document.getElementById('closeNotifications');
    
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            notificationPanel.classList.add('active');
            overlay.classList.add('active');
        });
    }
    
    if (closeNotifications) {
        closeNotifications.addEventListener('click', function() {
            notificationPanel.classList.remove('active');
            overlay.classList.remove('active');
        });
    }
    
    // Overlay Click
    if (overlay) {
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            notificationPanel.classList.remove('active');
            overlay.classList.remove('active');
        });
    }
    
    // Alert Close
    const alertCloseButtons = document.querySelectorAll('.alert-close');
    alertCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.alert').style.animation = 'slideUp 0.3s ease';
            setTimeout(() => {
                this.closest('.alert').remove();
            }, 300);
        });
    });
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.animation = 'slideUp 0.3s ease';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
});

// Add slideUp animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-10px);
        }
    }
`;
document.head.appendChild(style);

// Helper Functions
function formatCurrency(amount) {
    return '₹' + parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatNumber(num) {
    return parseFloat(num).toLocaleString('en-IN');
}

function formatPercentage(value) {
    return parseFloat(value).toFixed(1) + '%';
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}

// AJAX Helper
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    };
    
    const config = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// Show Notification
function showNotification(message, type = 'info') {
    const alertHTML = `
        <div class="alert alert-${type}">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            ${message}
            <button class="alert-close">&times;</button>
        </div>
    `;
    
    const container = document.querySelector('.messages-container') || createMessageContainer();
    container.insertAdjacentHTML('beforeend', alertHTML);
    
    // Auto remove
    setTimeout(() => {
        const alert = container.lastElementChild;
        if (alert) {
            alert.style.animation = 'slideUp 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        }
    }, 5000);
}

function createMessageContainer() {
    const container = document.createElement('div');
    container.className = 'messages-container';
    document.querySelector('.admin-content').insertBefore(
        container,
        document.querySelector('.admin-content').firstChild
    );
    return container;
}

// Export Functions
window.adminDashboard = {
    formatCurrency,
    formatNumber,
    formatPercentage,
    apiRequest,
    showNotification
};