/**
 * DEMO SCRIPT - FOR DEMONSTRATION PURPOSES ONLY
 * 
 * This script automatically fills OTP as "123456" and submits it
 * after the user sends OTP request.
 * 
 * ⚠️ REMOVE THIS SCRIPT IN PRODUCTION ⚠️
 */

(function() {
    'use strict';

    console.log('🎭 DEMO MODE: Auto-OTP enabled');

    document.addEventListener('DOMContentLoaded', () => {
        const sendBtn = document.querySelector('[data-otp-send]');
        const verifyBtn = document.querySelector('[data-otp-verify]');
        const otpInput = document.querySelector('[data-otp-code]');
        const statusBox = document.querySelector('[data-otp-status]');

        if (!verifyBtn || !otpInput) {
            console.warn('🎭 DEMO MODE: Required elements not found');
            return;
        }

        // If on OTP verify page directly (no send button), auto-fill immediately
        if (!sendBtn && otpInput && verifyBtn) {
            console.log('🎭 DEMO MODE: OTP verify page detected, auto-filling...');
            setTimeout(() => {
                otpInput.value = '123456';
                otpInput.dispatchEvent(new Event('input', { bubbles: true }));
                otpInput.style.border = '2px solid #28a745';
                
                const demoMsg = document.createElement('div');
                demoMsg.textContent = '🎭 DEMO: Auto-filled OTP (123456)';
                demoMsg.style.cssText = `
                    color: #28a745;
                    font-size: 12px;
                    margin-top: 8px;
                    padding: 6px 12px;
                    background: #e8f5e9;
                    border-radius: 4px;
                    font-weight: 600;
                `;
                otpInput.parentElement.appendChild(demoMsg);
                
                console.log('🎭 DEMO MODE: Ready to verify with 123456');
            }, 500);
            
            // Continue with other setup
        }

        // Only set up MutationObserver if we have a send button (combined login page)
        if (!sendBtn) return;

        // Create a MutationObserver to watch for status changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    const statusText = statusBox.textContent.trim().toLowerCase();
                    
                    // Check if OTP was sent successfully
                    if (statusText.includes('otp sent') || statusText.includes('check your phone')) {
                        console.log('🎭 DEMO MODE: OTP sent detected, auto-filling...');
                        
                        // Wait a brief moment for visual effect
                        setTimeout(() => {
                            // Auto-fill OTP
                            otpInput.value = '123456';
                            otpInput.dispatchEvent(new Event('input', { bubbles: true }));
                            
                            // Visual feedback
                            otpInput.style.border = '2px solid #28a745';
                            otpInput.style.transition = 'all 0.3s ease';
                            
                            console.log('🎭 DEMO MODE: OTP filled with 123456');
                            
                            // Show demo message
                            const demoMsg = document.createElement('div');
                            demoMsg.textContent = '🎭 DEMO: Auto-filled OTP (123456)';
                            demoMsg.style.cssText = `
                                color: #28a745;
                                font-size: 12px;
                                margin-top: 8px;
                                padding: 6px 12px;
                                background: #e8f5e9;
                                border-radius: 4px;
                                font-weight: 600;
                            `;
                            otpInput.parentElement.appendChild(demoMsg);
                            
                            // Auto-click verify button after 1 second
                            setTimeout(() => {
                                console.log('🎭 DEMO MODE: Auto-clicking verify button...');
                                verifyBtn.click();
                                
                                // Remove demo message
                                setTimeout(() => {
                                    demoMsg.remove();
                                }, 2000);
                            }, 1000);
                            
                        }, 500);
                    }
                }
            });
        });

        // Start observing status box for text changes
        if (statusBox) {
            observer.observe(statusBox, {
                childList: true,
                characterData: true,
                subtree: true
            });
        }

        // Also add a direct event listener as backup
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                console.log('🎭 DEMO MODE: Send OTP clicked, waiting for response...');
            });
        }

        // Add visual indicator that demo mode is active
        const demoIndicator = document.createElement('div');
        demoIndicator.innerHTML = '🎭 <strong>DEMO MODE</strong> - OTP will auto-fill as 123456';
        demoIndicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
            color: white;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            animation: pulse 2s ease-in-out infinite;
        `;
        
        // Add pulse animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.05); opacity: 0.9; }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(demoIndicator);

        // Console warning
        console.log(`
╔════════════════════════════════════════╗
║  ⚠️  DEMO MODE ACTIVE  ⚠️              ║
║                                        ║
║  OTP will auto-fill with: 123456      ║
║  Remove auth-demo.js in production!   ║
╚════════════════════════════════════════╝
        `);
    });
})();

