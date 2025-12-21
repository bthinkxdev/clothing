// Auth OTP flow

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

document.addEventListener('DOMContentLoaded', () => {
    const phoneInput = document.querySelector('[data-otp-phone]');
    const sendBtn = document.querySelector('[data-otp-send]');
    const verifyBtn = document.querySelector('[data-otp-verify]');
    const otpInput = document.querySelector('[data-otp-code]');
    const statusBox = document.querySelector('[data-otp-status]');
    const nextUrl = document.querySelector('[data-next-url]');

    const showStatus = (text, isError = false) => {
        if (!statusBox) return;
        statusBox.textContent = text;
        statusBox.style.color = isError ? '#dc3545' : '#2c2c2c';
    };

    const csrf = (document.querySelector('input[name=csrfmiddlewaretoken]') || {}).value || getCookie('csrftoken') || '';

    if (sendBtn && phoneInput) {
        sendBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const phone = phoneInput.value.trim();
            if (!phone) {
                showStatus('Please enter phone number', true);
                return;
            }
            showStatus('Sending OTP...');
            fetch('/auth/otp/send/', {
                method: 'POST',
                headers: {
                    ...(csrf ? { 'X-CSRFToken': csrf } : {}),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ phone }),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showStatus('OTP sent. Please check your phone.');
                    } else {
                        showStatus(data.error || 'Failed to send OTP', true);
                    }
                })
                .catch(() => showStatus('Network error. Try again.', true));
        });
    }

    if (verifyBtn && otpInput) {
        verifyBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const otp = otpInput.value.trim();
            if (!otp) {
                showStatus('Enter the OTP', true);
                return;
            }
            showStatus('Verifying...');
            fetch('/auth/otp/verify/', {
                method: 'POST',
                headers: {
                    ...(csrf ? { 'X-CSRFToken': csrf } : {}),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    otp,
                    next: nextUrl ? nextUrl.value : '/',
                }),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        showStatus('Success! Redirecting...');
                        window.location.href = data.redirect || '/';
                    } else {
                        showStatus(data.error || 'Invalid OTP', true);
                    }
                })
                .catch(() => showStatus('Network error. Try again.', true));
        });
    }
});

