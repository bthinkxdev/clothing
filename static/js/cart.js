// Cart interactions: quantity update and remove confirmations

document.addEventListener('DOMContentLoaded', () => {
    const qtyForms = document.querySelectorAll('[data-qty-form]');

    qtyForms.forEach((form) => {
        const input = form.querySelector('input[type="number"]');
        const minus = form.querySelector('[data-qty-minus]');
        const plus = form.querySelector('[data-qty-plus]');
        if (!input) return;

        const clamp = () => {
            const min = parseInt(input.min || '1', 10);
            if (parseInt(input.value || '0', 10) < min) input.value = min;
        };

        if (minus) {
            minus.addEventListener('click', (e) => {
                e.preventDefault();
                input.value = Math.max(parseInt(input.min || '1', 10), parseInt(input.value || '1', 10) - 1);
                form.submit();
            });
        }
        if (plus) {
            plus.addEventListener('click', (e) => {
                e.preventDefault();
                input.value = parseInt(input.value || '1', 10) + 1;
                form.submit();
            });
        }

        input.addEventListener('change', () => {
            clamp();
            form.submit();
        });
    });

    document.querySelectorAll('[data-remove-form]').forEach((form) => {
        form.addEventListener('submit', (e) => {
            if (!confirm('Remove this item from cart?')) {
                e.preventDefault();
            }
        });
    });
});

