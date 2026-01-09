(function () {
    'use strict';

    const STATUS_CLASS_MAP = {
        active: 'badge-success',
        blocked: 'badge-danger',
        inactive: 'badge-pill',
        pending: 'badge-warning',
        paid: 'badge-info',
        processing: 'badge-info',
        shipped: 'badge-info',
        delivered: 'badge-success',
        cancelled: 'badge-danger',
        refunded: 'badge-warning'
    };

    document.addEventListener('DOMContentLoaded', initCustomerModule);

    function initCustomerModule() {
        applyStatusBadges();
        setupFilterControls();
        setupBlockActions();
        setupWalletForm();
        exposeDebugAPI();
    }

    function setupFilterControls() {
        const filterForm = document.querySelector('form.filter-section');
        if (!filterForm) return;

        const searchInput = filterForm.querySelector('input[name="search"]');
        const selects = filterForm.querySelectorAll('select.filter-select');
        const submitBtn = filterForm.querySelector('button[type="submit"]');
        const debouncedSubmit = debounce(() => submitForm(filterForm), 350);

        selects.forEach(select => {
            select.addEventListener('change', () => {
                filterTableRows(searchInput?.value, select.value);
                debouncedSubmit();
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', () => {
                filterTableRows(searchInput.value, getSelectedStatus());
                debouncedSubmit();
            });

            searchInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    submitForm(filterForm);
                }
            });
        }

        filterForm.addEventListener('submit', () => setBusy(submitBtn, true));
    }

    function filterTableRows(query, statusValue) {
        const tbody = document.querySelector('.card-table tbody');
        if (!tbody) return;

        const normalizedQuery = (query || '').trim().toLowerCase();
        const normalizedStatus = (statusValue || '').trim().toLowerCase();
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const emptyRow = rows.find(row => row.querySelector('.empty-state-full'));

        let visibleCount = 0;

        rows.forEach(row => {
            if (row === emptyRow) return;

            const text = row.textContent.toLowerCase();
            const rowStatus = (row.querySelector('td:nth-child(6)')?.textContent || '').toLowerCase();
            const matchesSearch = !normalizedQuery || text.includes(normalizedQuery);
            const matchesStatus = !normalizedStatus || rowStatus.includes(normalizedStatus);

            const show = matchesSearch && matchesStatus;
            row.style.display = show ? '' : 'none';
            if (show) visibleCount += 1;
        });

        if (emptyRow) {
            emptyRow.style.display = visibleCount === 0 ? '' : 'none';
        }
    }

    function applyStatusBadges() {
        const badges = document.querySelectorAll('.badge, .status-badge');
        badges.forEach(badge => {
            const status = (badge.textContent || '').trim().toLowerCase();
            const cssClass = STATUS_CLASS_MAP[status];
            if (!cssClass) return;

            badge.classList.remove('badge-success', 'badge-danger', 'badge-warning', 'badge-info', 'badge-pill');
            badge.classList.add(cssClass);
            if (!badge.classList.contains('badge-pill')) {
                badge.classList.add('badge-pill');
            }
        });
    }

    function setupBlockActions() {
        const buttons = document.querySelectorAll('[data-action="toggle-customer-block"], [data-customer-block], [data-block-url]');
        if (!buttons.length) return;

        buttons.forEach(button => {
            button.addEventListener('click', async (event) => {
                event.preventDefault();

                const customerId = button.dataset.customerId || button.dataset.id;
                const url = button.dataset.url || button.dataset.blockUrl || buildCustomerUrl(customerId, 'block');
                if (!customerId || !url) {
                    console.warn('Missing customer id or url for block action');
                    return;
                }

                toggleBusy(button, true);

                try {
                    const response = await postJSON(url, {});
                    const isBlocked = response?.data?.is_blocked ?? response?.is_blocked;
                    updateBlockUI(isBlocked, button);
                    notify(response?.message || (isBlocked ? 'Customer blocked' : 'Customer unblocked'), 'success');
                } catch (error) {
                    notify(error.message || 'Unable to update customer status', 'error');
                } finally {
                    toggleBusy(button, false);
                }
            });
        });
    }

    function setupWalletForm() {
        const walletForm = document.querySelector('[data-wallet-form], #walletForm, #walletAdjustmentForm');
        if (!walletForm) return;

        walletForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const form = event.currentTarget;
            const customerId = form.dataset.customerId || form.querySelector('[name="customer_id"]')?.value;
            const amountInput = form.querySelector('[name="amount"]');
            const reasonInput = form.querySelector('[name="reason"]');
            const submitBtn = form.querySelector('button[type="submit"]');

            const amount = parseFloat(amountInput?.value || '0');
            if (isNaN(amount) || amount === 0) {
                notify('Enter a non-zero amount to adjust wallet', 'warning');
                return;
            }

            const payload = {
                amount,
                reason: reasonInput?.value || 'Manual adjustment by admin'
            };
            const url = form.dataset.url || buildCustomerUrl(customerId, 'wallet');

            if (!customerId || !url) {
                console.warn('Missing customer id or url for wallet update');
                return;
            }

            toggleBusy(submitBtn, true);

            try {
                const response = await postJSON(url, payload);
                const newBalance = response?.data?.new_balance ?? response?.new_balance;
                const balanceField = document.querySelector('[data-wallet-balance]') || document.getElementById('walletBalance');
                if (balanceField && newBalance !== undefined) {
                    balanceField.textContent = formatCurrency(newBalance);
                }
                notify(response?.message || 'Wallet updated successfully', 'success');
            } catch (error) {
                notify(error.message || 'Unable to update wallet', 'error');
            } finally {
                toggleBusy(submitBtn, false);
            }
        });
    }

    function updateBlockUI(isBlocked, triggerButton) {
        if (typeof isBlocked !== 'boolean') return;

        const statusBadge = document.querySelector('[data-customer-status]') || document.querySelector('.info-item .badge');
        if (statusBadge) {
            statusBadge.textContent = isBlocked ? 'Blocked' : 'Active';
            applyStatusBadges();
        }

        if (triggerButton) {
            const blockedLabel = triggerButton.dataset.blockedText || 'Unblock';
            const activeLabel = triggerButton.dataset.activeText || 'Block';
            triggerButton.textContent = isBlocked ? blockedLabel : activeLabel;
        }
    }

    function buildCustomerUrl(customerId, action) {
        if (!customerId) return '';
        const base = getDashboardBase();
        const normalizedAction = action === 'wallet' ? 'wallet' : 'block';
        return `${base}/customers/${customerId}/${normalizedAction}/`;
    }

    function submitForm(form) {
        if (!form) return;
        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    function setBusy(button, isBusy) {
        if (!button) return;
        button.disabled = !!isBusy;
        if (isBusy) {
            button.dataset.originalText = button.dataset.originalText || button.textContent;
            button.textContent = button.dataset.loadingText || 'Applying...';
        } else if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
        }
    }

    function toggleBusy(element, isBusy) {
        if (!element) return;
        element.disabled = !!isBusy;
        element.classList.toggle('loading', !!isBusy);
    }

    async function postJSON(url, payload) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(payload || {})
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
        } catch (error) {
            return {};
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

    function notify(message, type = 'info') {
        if (window.adminDashboard?.showNotification) {
            window.adminDashboard.showNotification(message, type);
        } else if (window.alert) {
            window.alert(message);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }

    function debounce(fn, wait = 250) {
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

    function formatCurrency(amount) {
        const value = parseFloat(amount || 0);
        if (isNaN(value)) return '₹0.00';
        return '₹' + value.toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function getSelectedStatus() {
        const statusSelect = document.querySelector('select[name="status"]');
        return statusSelect ? statusSelect.value : '';
    }

    function exposeDebugAPI() {
        window.customerDashboard = {
            applyStatusBadges,
            filterTableRows,
            setupFilterControls,
            setupBlockActions,
            setupWalletForm
        };
    }
})();

