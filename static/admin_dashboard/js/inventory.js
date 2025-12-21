// static/admin_dashboard/js/inventory.js

document.addEventListener('DOMContentLoaded', function () {
    initializeInventoryManagement();
});

function initializeInventoryManagement() {
    const searchInput = document.getElementById('inventorySearch');
    if (searchInput) {
        searchInput.addEventListener('input', filterInventory);
    }

    const stockFilter = document.getElementById('stockFilter');
    if (stockFilter) {
        stockFilter.addEventListener('change', filterInventory);
    }
}

function filterInventory() {
    const searchTerm = document.getElementById('inventorySearch')?.value.toLowerCase() || '';
    const stockFilter = document.getElementById('stockFilter')?.value || '';

    const rows = document.querySelectorAll('.data-table tbody tr:not(:last-child)');

    rows.forEach(row => {
        const product = row.querySelector('.product-info strong')?.textContent.toLowerCase() || '';
        const sku = row.querySelector('code')?.textContent.toLowerCase() || '';
        const stockBadge = row.querySelector('.stock-badge');

        let stockStatus = '';
        if (stockBadge) {
            if (stockBadge.classList.contains('stock-out')) stockStatus = 'out_of_stock';
            else if (stockBadge.classList.contains('stock-low')) stockStatus = 'low_stock';
            else if (stockBadge.classList.contains('stock-in')) stockStatus = 'in_stock';
        }

        const matchesSearch = product.includes(searchTerm) || sku.includes(searchTerm);
        const matchesStock = !stockFilter || stockStatus === stockFilter;

        if (matchesSearch && matchesStock) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}
