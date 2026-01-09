// static/admin_dashboard/js/reviews.js

document.addEventListener('DOMContentLoaded', function () {
    initializeReviewManagement();
});

function initializeReviewManagement() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', filterReviews);
    }

    const approveButtons = document.querySelectorAll('.approve-btn');
    approveButtons.forEach(btn => {
        btn.addEventListener('click', handleApprove);
    });

    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', handleDelete);
    });
}

function filterReviews() {
    const statusFilter = document.getElementById('statusFilter')?.value || 'all';
    
    // Reload page with status parameter
    const url = new URL(window.location);
    url.searchParams.set('status', statusFilter);
    window.location.href = url.toString();
}

async function handleApprove(e) {
    const button = e.currentTarget;
    const reviewId = button.dataset.reviewId;

    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!csrfToken) {
            showNotification('CSRF token not found', 'error');
            return;
        }

        const response = await fetch(`/dashboard/reviews/${reviewId}/approve/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        });

        if (response.ok) {
            const card = button.closest('.review-card');
            const footer = card.querySelector('.review-footer');

            button.remove();

            const approvedBadge = document.createElement('span');
            approvedBadge.className = 'status-badge status-active';
            approvedBadge.innerHTML = '<i class="fas fa-check-circle"></i> Approved';
            footer.insertBefore(approvedBadge, footer.firstChild);

            showNotification('Review approved successfully', 'success');

            // Update counts in real time
            const pendingCountEl = document.querySelector('.stat-card:first-child h3');
            const approvedCountEl = document.querySelector('.stat-card:last-child h3');
            if (pendingCountEl) {
                const currentCount = parseInt(pendingCountEl.textContent);
                pendingCountEl.textContent = currentCount - 1;
            }
            if (approvedCountEl) {
                const currentCount = parseInt(approvedCountEl.textContent);
                approvedCountEl.textContent = currentCount + 1;
            }
        } else {
            throw new Error('Failed to approve review');
        }
    } catch (error) {
        console.error('Error approving review:', error);
        showNotification('Failed to approve review', 'error');
    }
}

async function handleDelete(e) {
    const button = e.currentTarget;
    const reviewId = button.dataset.reviewId;

    if (!confirm('Are you sure you want to delete this review?')) {
        return;
    }

    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!csrfToken) {
            showNotification('CSRF token not found', 'error');
            return;
        }

        const response = await fetch(`/dashboard/reviews/${reviewId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        });

        if (response.ok) {
            const card = button.closest('.review-card');
            card.style.opacity = '0';
            setTimeout(() => card.remove(), 300);

            showNotification('Review deleted successfully', 'success');
            // Update counts in real time
            const statusFilter = document.getElementById('statusFilter')?.value || 'pending';
            if (statusFilter === 'pending' || statusFilter === 'all') {
                const pendingCountEl = document.querySelector('.stat-card:first-child h3');
                if (pendingCountEl) {
                    const currentCount = parseInt(pendingCountEl.textContent);
                    pendingCountEl.textContent = currentCount - 1;
                }
            } else if (statusFilter === 'approved') {
                const approvedCountEl = document.querySelector('.stat-card:last-child h3');
                if (approvedCountEl) {
                    const currentCount = parseInt(approvedCountEl.textContent);
                    approvedCountEl.textContent = currentCount - 1;
                }
            }
        } else {
            throw new Error('Failed to delete review');
        }
    } catch (error) {
        console.error('Error deleting review:', error);
        showNotification('Failed to delete review', 'error');
    }
}

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
