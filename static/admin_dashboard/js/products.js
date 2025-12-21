// static/admin_dashboard/js/products.js

document.addEventListener('DOMContentLoaded', function () {
    initializeProductManagement();
});

function initializeProductManagement() {
    const searchInput = document.getElementById('productSearch');
    if (searchInput) {
        searchInput.addEventListener('input', filterProducts);
    }

    const categoryFilter = document.getElementById('categoryFilter');
    const statusFilter = document.getElementById('statusFilter');

    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterProducts);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', filterProducts);
    }
}

function filterProducts() {
    const searchTerm = document.getElementById('productSearch')?.value.toLowerCase() || '';
    const categoryFilter = document.getElementById('categoryFilter')?.value || '';
    const statusFilter = document.getElementById('statusFilter')?.value || '';

    const cards = document.querySelectorAll('.product-card');

    cards.forEach(card => {
        const name = card.querySelector('.product-body h3')?.textContent.toLowerCase() || '';
        const category = card.querySelector('.product-category')?.textContent.toLowerCase() || '';
        const isInactive = card.querySelector('.inactive-badge') !== null;

        const matchesSearch = name.includes(searchTerm) || category.includes(searchTerm);
        let matchesStatus = true;

        if (statusFilter === 'active') {
            matchesStatus = !isInactive;
        } else if (statusFilter === 'inactive') {
            matchesStatus = isInactive;
        }

        if (matchesSearch && matchesStatus) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}
