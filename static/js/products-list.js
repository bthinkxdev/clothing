// Product list page JS

function updateSort(value) {
    const url = new URL(window.location);
    url.searchParams.set('sort', value);
    window.location = url;
}

function toggleFilters(force) {
    const sidebar = document.querySelector('.filters-sidebar');
    const overlay = document.querySelector('[data-filters-overlay]');
    if (!sidebar) return;
    const shouldOpen = force === true ? true : force === false ? false : !sidebar.classList.contains('active');
    sidebar.classList.toggle('active', shouldOpen);
    if (overlay) overlay.classList.toggle('active', shouldOpen);
    document.body.style.overflow = shouldOpen ? 'hidden' : '';
}

// Close filters on escape for mobile
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const sidebar = document.querySelector('.filters-sidebar');
        if (sidebar && sidebar.classList.contains('active')) {
            toggleFilters(false);
        }
    }
});

// Close on overlay click
document.addEventListener('click', (e) => {
    const overlay = document.querySelector('[data-filters-overlay]');
    if (overlay && e.target === overlay && overlay.classList.contains('active')) {
        toggleFilters(false);
    }
});

// Expose to global scope for inline handlers if needed
window.updateSort = updateSort;
window.toggleFilters = toggleFilters;

