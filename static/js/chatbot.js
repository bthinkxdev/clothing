// static/js/chatbot.js

class ChatbotWidget {
    constructor() {
        this.isOpen = false;
        this.isTyping = false;
        this.messageQueue = [];
        
        this.icon = document.getElementById('chatbot-icon');
        this.window = document.getElementById('chatbot-window');
        this.closeBtn = document.getElementById('chatbot-close');
        this.input = document.getElementById('chatbot-input');
        this.sendBtn = document.getElementById('chatbot-send');
        this.messagesContainer = document.getElementById('chatbot-messages');
        this.suggestionsContainer = document.getElementById('chatbot-suggestions');
        this.typingIndicator = document.getElementById('chatbot-typing');
        
        this.init();
    }
    
    init() {
        // Event listeners
        this.icon.addEventListener('click', () => this.toggle());
        this.closeBtn.addEventListener('click', () => this.close());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // Load chat history
        this.loadHistory();
        
        // Handle suggestion clicks (delegated)
        this.suggestionsContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-btn')) {
                this.sendMessage(e.target.textContent);
            }
        });
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.window.style.display = 'flex';
        this.isOpen = true;
        this.input.focus();
        this.scrollToBottom();
        this.clearUnreadBadge();
    }
    
    close() {
        this.window.style.display = 'none';
        this.isOpen = false;
    }
    
    async sendMessage(text = null) {
        const message = text || this.input.value.trim();
        
        if (!message) return;
        
        // Clear input
        this.input.value = '';
        this.sendBtn.disabled = true;
        
        // Add user message to UI
        this.addMessage(message, 'user');
        
        // Clear suggestions
        this.suggestionsContainer.innerHTML = '';
        
        // Show typing indicator
        this.showTyping();
        
        try {
            // Send to backend
            const response = await fetch('/chatbot/ask/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ message })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            
            // Hide typing indicator
            this.hideTyping();
            
            // Add bot response
            this.addBotResponse(data);
            
        } catch (error) {
            console.error('Error:', error);
            this.hideTyping();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        } finally {
            this.sendBtn.disabled = false;
        }
    }
    
    addMessage(content, type = 'bot') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chatbot-message ${type}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Convert markdown-style bold to HTML
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        contentDiv.innerHTML = `<p>${content}</p>`;
        messageDiv.appendChild(contentDiv);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addBotResponse(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message bot-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Format reply
        let reply = data.reply || 'I understand. How else can I help?';
        reply = reply.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        reply = reply.replace(/\n/g, '<br>');
        
        contentDiv.innerHTML = `<p>${reply}</p>`;
        
        // Add products if present
        if (data.products && data.products.length > 0) {
            data.products.forEach(product => {
                contentDiv.appendChild(this.createProductCard(product));
            });
        }
        
        // Add order details if present
        if (data.order_details) {
            contentDiv.appendChild(this.createOrderDetails(data.order_details));
        }
        
        // Add orders list if present
        if (data.orders && data.orders.length > 0) {
            const ordersDiv = document.createElement('div');
            ordersDiv.className = 'orders-list';
            data.orders.forEach(order => {
                ordersDiv.appendChild(this.createOrderSummary(order));
            });
            contentDiv.appendChild(ordersDiv);
        }
        
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        
        // Add suggestions
        if (data.suggestions && data.suggestions.length > 0) {
            this.showSuggestions(data.suggestions);
        }
        
        this.scrollToBottom();
    }
    
    createProductCard(product) {
        const card = document.createElement('div');
        card.className = 'product-card';
        
        const imageHtml = product.image 
            ? `<img src="${product.image}" alt="${product.name}">`
            : '<div style="width:60px;height:60px;background:#e5e7eb;border-radius:6px;"></div>';
        
        const mrpHtml = product.mrp 
            ? `<span class="product-card-mrp">₹${product.mrp}</span>`
            : '';
        
        card.innerHTML = `
            ${imageHtml}
            <div class="product-card-info">
                <div class="product-card-name">${product.name}</div>
                <div>
                    <span class="product-card-price">₹${product.price}</span>
                    ${mrpHtml}
                </div>
                <div class="product-card-stock">${product.stock_status}</div>
                <a href="/products/${product.slug}/" class="product-card-link">View Details →</a>
            </div>
        `;
        
        return card;
    }
    
    createOrderDetails(order) {
        const details = document.createElement('div');
        details.className = 'order-details';
        
        let itemsHtml = '';
        if (order.items && order.items.length > 0) {
            itemsHtml = '<div style="margin-top:8px;"><strong>Items:</strong><br>';
            order.items.forEach(item => {
                itemsHtml += `• ${item.name} (${item.quantity}x) - ₹${item.price}<br>`;
            });
            itemsHtml += '</div>';
        }
        
        const trackingHtml = order.tracking_number 
            ? `<div class="order-details-row">
                <span class="order-details-label">Tracking:</span>
                <span class="order-details-value">${order.tracking_number}</span>
               </div>`
            : '';
        
        const deliveryHtml = order.expected_delivery
            ? `<div class="order-details-row">
                <span class="order-details-label">Expected Delivery:</span>
                <span class="order-details-value">${order.expected_delivery}</span>
               </div>`
            : '';
        
        details.innerHTML = `
            <div class="order-details-row">
                <span class="order-details-label">Order ID:</span>
                <span class="order-details-value">#${order.id}</span>
            </div>
            <div class="order-details-row">
                <span class="order-details-label">Status:</span>
                <span class="order-details-value">${order.status.toUpperCase()}</span>
            </div>
            <div class="order-details-row">
                <span class="order-details-label">Total:</span>
                <span class="order-details-value">₹${order.total}</span>
            </div>
            ${trackingHtml}
            ${deliveryHtml}
            ${itemsHtml}
        `;
        
        return details;
    }
    
    createOrderSummary(order) {
        const summary = document.createElement('div');
        summary.className = 'product-card';
        summary.style.cursor = 'pointer';
        summary.onclick = () => {
            this.sendMessage(`Track order ${order.id}`);
        };
        
        summary.innerHTML = `
            <div style="width:60px;height:60px;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);border-radius:6px;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;">
                #${order.id.substring(0, 4)}
            </div>
            <div class="product-card-info">
                <div class="product-card-name">Order #${order.id}</div>
                <div class="product-card-price">₹${order.total}</div>
                <div class="product-card-stock">${order.status} • ${order.date}</div>
            </div>
        `;
        
        return summary;
    }
    
    showSuggestions(suggestions) {
        this.suggestionsContainer.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = suggestion;
            this.suggestionsContainer.appendChild(btn);
        });
    }
    
    showTyping() {
        this.isTyping = true;
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        this.typingIndicator.style.display = 'none';
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }
    
    async loadHistory() {
        try {
            const response = await fetch('/chatbot/history/');
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                // Clear default welcome message
                this.messagesContainer.innerHTML = '';
                
                data.messages.forEach(msg => {
                    if (msg.type === 'user') {
                        this.addMessage(msg.content, 'user');
                    } else {
                        if (msg.metadata && Object.keys(msg.metadata).length > 0) {
                            this.addBotResponse(msg.metadata);
                        } else {
                            this.addMessage(msg.content, 'bot');
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }
    
    clearUnreadBadge() {
        const badge = document.getElementById('chatbot-unread');
        if (badge) {
            badge.style.display = 'none';
            badge.textContent = '0';
        }
    }
    
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.chatbot = new ChatbotWidget();
});