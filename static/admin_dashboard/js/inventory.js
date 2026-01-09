// static/admin_dashboard/js/inventory.js

document.addEventListener('DOMContentLoaded', function () {
    initializeInventoryManagement();
    initializeInventoryModal();
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

    filterInventory();
}

function filterInventory() {
    const searchTerm = document.getElementById('inventorySearch')?.value.toLowerCase() || '';
    const stockFilter = document.getElementById('stockFilter')?.value || '';

    const rows = document.querySelectorAll('.data-table tbody tr');
    const emptyRow = document.querySelector('.data-table tbody tr.empty-row');
    let visibleCount = 0;

    rows.forEach(row => {
        if (row.classList.contains('empty-row')) {
            return;
        }

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
            visibleCount += 1;
        } else {
            row.style.display = 'none';
        }
    });

    if (emptyRow) {
        emptyRow.style.display = visibleCount === 0 ? '' : 'none';
    }
}

function initializeInventoryModal() {
    const modal = document.getElementById('inventoryModal');
    if (!modal) return;

    const form = document.getElementById('inventoryEditForm');
    const quantityInput = document.getElementById('inventoryQuantity');
    const thresholdInput = document.getElementById('inventoryThreshold');
    const subtitle = document.getElementById('inventoryModalSubtitle');

    const openButtons = document.querySelectorAll('.open-inventory-modal');
    const closeButtons = document.querySelectorAll('.inventory-modal-close');

    const showModal = () => { modal.style.display = 'flex'; };
    const hideModal = () => { modal.style.display = 'none'; };

    openButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const quantity = btn.getAttribute('data-quantity') || 0;
            const threshold = btn.getAttribute('data-threshold') || 0;
            const name = btn.getAttribute('data-name') || '';
            const action = btn.getAttribute('data-action') || '';

            if (subtitle) {
                subtitle.textContent = name;
            }
            if (form) {
                form.setAttribute('action', action);
            }
            if (quantityInput) {
                quantityInput.value = quantity;
            }
            if (thresholdInput) {
                thresholdInput.value = threshold;
            }
            showModal();
        });
    });

    closeButtons.forEach(btn => btn.addEventListener('click', hideModal));
    modal.addEventListener('click', (e) => {
        if (e.target === modal) hideModal();
    });

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const action = form.getAttribute('action');
            if (!action) return;

            const formData = new FormData(form);
            try {
                const res = await fetch(action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCsrfToken(),
                    },
                    body: formData
                });
                if (res.ok) {
                    window.location.reload();
                }
            } catch (err) {
                console.error('Inventory update failed', err);
            }
        });
    }
}

function getCsrfToken() {
    const name = 'csrftoken=';
    const decoded = decodeURIComponent(document.cookie);
    const parts = decoded.split(';');
    for (let part of parts) {
        part = part.trim();
        if (part.startsWith(name)) {
            return part.substring(name.length, part.length);
        }
    }
    return '';
}
