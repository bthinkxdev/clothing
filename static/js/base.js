// Base JavaScript shared across pages

// Quick view modal logic
window.quickView = function quickView(slug) {
    const overlay = document.querySelector('[data-quickview-overlay]');
    const modal = document.querySelector('[data-quickview-modal]');
    const body = document.querySelector('body');

    if (!overlay || !modal) return;

    // open overlay
    overlay.classList.add('open');
    body.style.overflow = 'hidden';

    // loading state
    modal.innerHTML = '<div class="quick-view-loading">Loading...</div>';

    fetch(`/product/${slug}/quick-view/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
        .then((res) => {
            if (!res.ok) throw new Error('Failed to load quick view');
            return res.text();
        })
        .then((html) => {
            modal.innerHTML = html;
        })
        .catch(() => {
            modal.innerHTML = '<div class="quick-view-error">Unable to load product. Please try again.</div>';
        });
};

function closeQuickView() {
    const overlay = document.querySelector('[data-quickview-overlay]');
    const body = document.querySelector('body');
    if (overlay) {
        overlay.classList.remove('open');
        body.style.overflow = '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.querySelector('[data-quickview-overlay]');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay || e.target.closest('[data-quickview-close]')) {
                closeQuickView();
            }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeQuickView();
        }
    });
});

// Auto-dismiss alerts and close buttons
document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.messages-container .alert');
    alerts.forEach((alert) => {
        // Close button
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => alert.remove());
        }
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Mobile menu toggle
    const menuBtn = document.getElementById('mobileMenuBtn');
    const mainNav = document.querySelector('.main-nav');
    const mobileSearchTrigger = document.querySelector('.mobile-search');
    const mobileSearchPanel = document.querySelector('[data-mobile-search]');
    if (menuBtn && mainNav) {
        menuBtn.addEventListener('click', () => {
            mainNav.classList.toggle('mobile-open');
        });
    }

    // Mobile search toggle
    if (mobileSearchTrigger && mobileSearchPanel) {
        mobileSearchTrigger.addEventListener('click', (e) => {
            e.preventDefault();
            mobileSearchPanel.classList.toggle('active');
        });
        document.addEventListener('click', (e) => {
            if (!mobileSearchPanel.contains(e.target) && !mobileSearchTrigger.contains(e.target)) {
                mobileSearchPanel.classList.remove('active');
            }
        });
    }

    // Share buttons (product detail)
    const shareButtons = document.querySelectorAll('[data-share-url]');
    shareButtons.forEach((btn) => {
        btn.addEventListener('click', async () => {
            const url = btn.getAttribute('data-share-url') || window.location.href;
            if (navigator.share) {
                try {
                    await navigator.share({ url });
                } catch (err) {
                    // user cancelled or unsupported; silently ignore
                }
            } else if (navigator.clipboard) {
                try {
                    await navigator.clipboard.writeText(url);
                    alert('Link copied to clipboard');
                } catch (err) {
                    window.prompt('Copy link', url);
                }
            } else {
                window.prompt('Copy link', url);
            }
        });
    });
});

