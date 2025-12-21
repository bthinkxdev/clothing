// static/admin_dashboard/js/coupons.js

document.addEventListener('DOMContentLoaded', function () {
    initializeCouponManagement();
});

function initializeCouponManagement() {
    // Search functionality
    const searchInput = document.getElementById('couponSearch');
    if (searchInput) {
        searchInput.addEventListener('input', filterCoupons);
    }

    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', filterCoupons);
    }

    // Toggle switches
    const toggleInputs = document.querySelectorAll('.coupon-toggle-input');
    toggleInputs.forEach(input => {
        input.addEventListener('change', handleCouponToggle);
    });
}

// Filter coupons
function filterCoupons() {
    const searchTerm = document.getElementById('couponSearch')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('statusFilter')?.value || '';

    const cards = document.querySelectorAll('.coupon-card');

    cards.forEach(card => {
        const code = card.querySelector('.coupon-code span')?.textContent.toLowerCase() || '';
        const description = card.querySelector('.coupon-description')?.textContent.toLowerCase() || '';
        const isActive = card.querySelector('.coupon-toggle-input')?.checked;

        const matchesSearch = code.includes(searchTerm) || description.includes(searchTerm);
        let matchesStatus = true;

        if (statusFilter === 'active') {
            matchesStatus = isActive;
        } else if (statusFilter === 'inactive') {
            matchesStatus = !isActive;
        }

        if (matchesSearch && matchesStatus) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// Handle coupon toggle
async function handleCouponToggle(e) {
    const input = e.target;
    const couponId = input.dataset.couponId;
    const isActive = input.checked;

    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
            getCookie('csrftoken');

        const response = await fetch(`/admin-dashboard/coupons/${couponId}/toggle/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        });

        if (response.ok) {
            const data = await response.json();
            showNotification(data.message || 'Coupon status updated', 'success');
        } else {
            throw new Error('Failed to toggle coupon');
        }
    } catch (error) {
        console.error('Error toggling coupon:', error);
        input.checked = !isActive; // Revert the toggle
        showNotification('Failed to update coupon status', 'error');
    }
}

// Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        ${message}
        <button class="alert-close">&times;</button>
    `;

    let container = document.querySelector('.messages-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'messages-container';
        const content = document.querySelector('.admin-content');
        if (content) {
            content.insertBefore(container, content.firstChild);
        }
    }

    container.appendChild(notification);

    const closeBtn = notification.querySelector('.alert-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        });
    }

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Form validation
const couponForm = document.getElementById('couponForm');
if (couponForm) {
    couponForm.addEventListener('submit', function (e) {
        const code = this.querySelector('input[name="code"]')?.value;
        const value = this.querySelector('input[name="value"]')?.value;
        const startDate = this.querySelector('input[name="start_date"]')?.value;
        const endDate = this.querySelector('input[name="end_date"]')?.value;

        if (!code || !value || !startDate || !endDate) {
            e.preventDefault();
            showNotification('Please fill in all required fields', 'error');
            return false;
        }

        if (new Date(startDate) >= new Date(endDate)) {
            e.preventDefault();
            showNotification('End date must be after start date', 'error');
            return false;
        }
    });
}
