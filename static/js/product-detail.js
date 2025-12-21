// Product detail interactions

document.addEventListener('DOMContentLoaded', () => {
    const mainImg = document.querySelector('[data-main-image]');
    const thumbButtons = document.querySelectorAll('[data-thumb]');
    thumbButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            thumbButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const src = btn.dataset.src;
            if (mainImg && src) {
                mainImg.src = src;
            }
        });
    });
});

