// static/admin_dashboard/js/payments.js

document.addEventListener('DOMContentLoaded', function () {
    initializePaymentManagement();
});

function initializePaymentManagement() {
    const statusFilter = document.getElementById('statusFilter');
    const methodFilter = document.getElementById('methodFilter');

    if (statusFilter) {
        statusFilter.addEventListener('change', filterPayments);
    }

    if (methodFilter) {
        methodFilter.addEventListener('change', filterPayments);
    }
}

function filterPayments() {
    const statusFilter = document.getElementById('statusFilter')?.value || '';
    const methodFilter = document.getElementById('methodFilter')?.value || '';

    const rows = document.querySelectorAll('.data-table tbody tr:not(:last-child)');

    rows.forEach(row => {
        const statusBadge = row.querySelector('.payment-status');
        const methodBadge = row.querySelector('.method-badge');

        let status = '';
        let method = '';

        if (statusBadge) {
            if (statusBadge.classList.contains('status-pending')) status = 'pending';
            else if (statusBadge.classList.contains('status-completed')) status = 'completed';
            else if (statusBadge.classList.contains('status-failed')) status = 'failed';
            else if (statusBadge.classList.contains('status-refunded')) status = 'refunded';
        }

        if (methodBadge) {
            if (methodBadge.classList.contains('method-cod')) method = 'cod';
            else if (methodBadge.classList.contains('method-razorpay')) method = 'razorpay';
            else if (methodBadge.classList.contains('method-wallet')) method = 'wallet';
        }

        const matchesStatus = !statusFilter || status === statusFilter;
        const matchesMethod = !methodFilter || method === methodFilter;

        if (matchesStatus && matchesMethod) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}
