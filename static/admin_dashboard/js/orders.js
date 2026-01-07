
(function () {
    document.addEventListener('DOMContentLoaded', initOrders);

    const STATUS_CLASS_MAP = {
        pending: 'badge-warning',
        paid: 'badge-info',
        processing: 'badge-info',
        shipped: 'badge-info',
        delivered: 'badge-success',
        cancelled: 'badge-danger',
        refunded: 'badge-warning'
    };

    function initOrders() {
        applyStatusBadges();
        setupFilterAutoSubmit();
        setupLiveSearch();
        setupBulkSelection();
        setupBulkStatusUpdate();
        setupCancelButtons();
        setupInvoiceButtons();
    }

    function applyStatusBadges() {
        const badges = document.querySelectorAll('.badge, .status-badge');
        badges.forEach(badge => {
            const status = (badge.textContent || '').trim().toLowerCase();
            if (!STATUS_CLASS_MAP[status]) return;

            badge.classList.remove('badge-success', 'badge-danger', 'badge-warning', 'badge-info');
            badge.classList.add(STATUS_CLASS_MAP[status], 'badge-pill');
        });
    }

    function setupFilterAutoSubmit() {
        const filterForm = document.querySelector('.filter-section');
        if (!filterForm) return;

        const selects = filterForm.querySelectorAll('select.filter-select');
        selects.forEach(select => {
            select.addEventListener('change', () => {
                submitForm(filterForm);
            });
        });
    }

    function setupLiveSearch() {
        const searchInput = document.querySelector('.filter-section input[name="search"]');
        const tableBody = document.querySelector('.card-table tbody');
        if (!searchInput || !tableBody) return;

        const emptyRow = tableBody.querySelector('.empty-state-full')?.closest('tr');
        const rows = Array.from(tableBody.querySelectorAll('tr')).filter(tr => tr !== emptyRow);

        const handler = debounce(() => {
            const query = searchInput.value.trim().toLowerCase();
            let visibleCount = 0;

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const show = !query || text.includes(query);
                row.style.display = show ? '' : 'none';
                if (show) visibleCount += 1;
            });

            if (emptyRow) {
                emptyRow.style.display = visibleCount === 0 ? '' : 'none';
            }
        }, 200);

        searchInput.addEventListener('input', handler);
    }

    function setupBulkSelection() {
        const master = document.getElementById('selectAllOrders');
        const checkboxes = document.querySelectorAll('input[type="checkbox"][data-order-id]');
        if (!master || !checkboxes.length) return;

        master.addEventListener('change', () => {
            checkboxes.forEach(cb => cb.checked = master.checked);
            updateSelectedCount();
        });

        checkboxes.forEach(cb => cb.addEventListener('change', updateSelectedCount));
    }

    function setupBulkStatusUpdate() {
        const applyBtn = document.querySelector('[data-bulk-action="status"]') || document.getElementById('applyBulkAction');
        const statusSelect = document.getElementById('bulkStatus') || document.querySelector('[name="bulk_status"]');
        if (!applyBtn || !statusSelect) return;

        applyBtn.addEventListener('click', async (event) => {
            event.preventDefault();

            const orderIds = getSelectedOrderIds();
            if (!orderIds.length) {
                notify('Select at least one order', 'warning');
                return;
            }

            const newStatus = statusSelect.value;
            if (!newStatus) {
                notify('Choose a status to apply', 'warning');
                return;
            }

            const url = applyBtn.dataset.url || `${getDashboardBase()}/orders/bulk-update/`;
            toggleBusy(applyBtn, true);

            try {
                const response = await postJSON(url, {
                    order_ids: orderIds,
                    action: 'update_status',
                    status: newStatus
                });

                notify(response.message || 'Orders updated successfully', 'success');
                setTimeout(() => window.location.reload(), 600);
            } catch (error) {
                notify(error.message || 'Failed to update orders', 'error');
            } finally {
                toggleBusy(applyBtn, false);
            }
        });
    }

    function setupCancelButtons() {
        const cancelButtons = document.querySelectorAll('[data-action="cancel-order"], .js-cancel-order');
        if (!cancelButtons.length) return;

        cancelButtons.forEach(button => {
            button.addEventListener('click', async (event) => {
                event.preventDefault();

                const orderId = button.dataset.orderId || button.value;
                if (!orderId) return;

                if (!confirm('Cancel this order?')) return;

                const reasonFieldId = button.dataset.reasonInput;
                const reasonField = reasonFieldId ? document.getElementById(reasonFieldId) : null;
                const reason = (reasonField?.value || button.dataset.reason || '').trim() || 'Cancelled by admin';

                const url = button.dataset.url || `${getDashboardBase()}/orders/${orderId}/cancel/`;
                toggleBusy(button, true);

                try {
                    const response = await postForm(url, { reason });
                    notify(response.message || 'Order cancelled successfully', 'success');
                    setTimeout(() => window.location.reload(), 600);
                } catch (error) {
                    notify(error.message || 'Unable to cancel order', 'error');
                } finally {
                    toggleBusy(button, false);
                }
            });
        });
    }

    function setupInvoiceButtons() {
        const printBtn = document.querySelector('[data-action="print-invoice"]');
        if (printBtn) {
            printBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.print();
            });
        }
    }

    function getSelectedOrderIds() {
        const checkboxes = document.querySelectorAll('input[type="checkbox"][data-order-id]:checked');
        return Array.from(checkboxes).map(cb => cb.dataset.orderId || cb.value).filter(Boolean);
    }

    function updateSelectedCount() {
        const counter = document.querySelector('[data-selected-count]');
        if (!counter) return;
        counter.textContent = getSelectedOrderIds().length.toString();
    }

    function submitForm(form) {
        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    function toggleBusy(element, isBusy) {
        if (!element) return;
        element.disabled = !!isBusy;
        if (isBusy) {
            element.dataset.originalText = element.dataset.originalText || element.textContent;
            element.textContent = element.dataset.loadingText || 'Please wait...';
        } else if (element.dataset.originalText) {
            element.textContent = element.dataset.originalText;
        }
    }

    async function postJSON(url, payload) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(payload)
        });

        const data = await safeJson(response);
        if (!response.ok || data?.success === false) {
            const message = data?.error || data?.message || 'Request failed';
            throw new Error(message);
        }
        return data;
    }

    async function postForm(url, payload) {
        const formData = new FormData();
        Object.entries(payload || {}).forEach(([key, value]) => formData.append(key, value));

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() },
            body: formData
        });

        const data = await safeJson(response);
        if (!response.ok || data?.success === false) {
            const message = data?.error || data?.message || 'Request failed';
            throw new Error(message);
        }
        return data;
    }

    async function safeJson(response) {
        try {
            return await response.json();
        } catch (_) {
            return {};
        }
    }

    function notify(message, type = 'info') {
        if (window.adminDashboard?.showNotification) {
            window.adminDashboard.showNotification(message, type);
        } else {
            alert(message);
        }
    }

    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken') || '';
    }

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(`${name}=`)) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        return '';
    }

    function debounce(fn, wait = 200) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(null, args), wait);
        };
    }

    function getDashboardBase() {
        const match = window.location.pathname.match(/^\/([^/]+)/);
        return match ? `/${match[1]}` : '';
    }

    window.orderDashboard = {
        applyStatusBadges,
        setupFilterAutoSubmit,
        setupLiveSearch,
        setupBulkSelection,
        setupBulkStatusUpdate,
        setupCancelButtons,
        setupInvoiceButtons
    };
})();

