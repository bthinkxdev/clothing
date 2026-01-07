// static/admin_dashboard/js/payments.js

document.addEventListener('DOMContentLoaded', function () {
    initializePaymentManagement();
});

function initializePaymentManagement() {
    const statusFilter = document.getElementById('statusFilter');
    const methodFilter = document.getElementById('methodFilter');

    // Set dropdown values from URL parameters on page load
    const urlParams = new URLSearchParams(window.location.search);
    
    if (statusFilter) {
        const statusParam = urlParams.get('status');
        if (statusParam) {
            statusFilter.value = statusParam;
        }
        statusFilter.addEventListener('change', filterPayments);
    }

    if (methodFilter) {
        const methodParam = urlParams.get('method');
        if (methodParam) {
            methodFilter.value = methodParam;
        }
        methodFilter.addEventListener('change', filterPayments);
    }
}

function filterPayments() {
    const statusFilter = document.getElementById('statusFilter')?.value || '';
    const methodFilter = document.getElementById('methodFilter')?.value || '';

    // Build URL with query parameters
    const url = new URL(window.location.origin + window.location.pathname);
    
    if (statusFilter) {
        url.searchParams.set('status', statusFilter);
    }
    
    if (methodFilter) {
        url.searchParams.set('method', methodFilter);
    }
    
    // Reload page with new filters (or no filters if all cleared)
    window.location.href = url.toString();
}