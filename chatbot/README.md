# Django E-commerce Chatbot Widget

A fully responsive, AI-powered floating chatbot widget for Django e-commerce applications with advanced features including order tracking, product search, size recommendations, and more.

## Features

### Core Functionality
- ✅ **Order Tracking**: Track orders by ID or view recent orders
- ✅ **Product Search**: Smart product finder with filters (name, category, size, color, price)
- ✅ **Size Recommendations**: AI-powered size suggestions based on measurements
- ✅ **Cart Assistance**: View cart, add items, manage quantities
- ✅ **Customer Support**: FAQ responses for shipping, returns, payments
- ✅ **Smart Intent Detection**: Automatic understanding of user queries

### UI/UX Features
- 🎨 Fully responsive design (desktop & mobile)
- 💬 Floating chat icon with unread badge
- ⚡ Smooth animations and transitions
- 📱 Mobile-optimized full-screen mode
- 🎯 Quick suggestion buttons
- 💳 Product cards and order summaries in chat
- ⌨️ Typing indicators
- 📜 Chat history persistence

### Technical Features
- 🔒 CSRF protection
- 🚀 Rate limiting support
- 💾 Session-based conversation context
- 📊 Analytics tracking
- 🗄️ Caching support for performance
- 🔍 Optimized database queries
- 📝 Comprehensive logging

## Installation

### 1. Create Chatbot App

```bash
python manage.py startapp chatbot
```

### 2. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ... existing apps ...
    'chatbot',
]
```

### 3. Copy Files

Copy all provided files to your Django project:

```
chatbot/
├── __init__.py
├── models.py           # ChatMessage, ChatSession
├── services.py         # ChatbotService, handlers
├── views.py            # ChatbotAPIView
├── urls.py             # URL routing
├── admin.py            # Admin interface
└── advanced_features.py # Optional extensions

templates/includes/
├── chatbot_icon.html
└── chatbot_window.html

static/
├── css/
│   └── chatbot.css
└── js/
    └── chatbot.js
```

### 4. Update URLs

```python
# project/urls.py
urlpatterns = [
    # ... existing patterns ...
    path('chatbot/', include('chatbot.urls')),
]
```

### 5. Update Base Template

```html
<!-- templates/base.html -->
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <!-- ... existing head ... -->
    <link rel="stylesheet" href="{% static 'css/chatbot.css' %}">
</head>
<body>
    <!-- ... your content ... -->
    
    <!-- Add before closing body tag -->
    {% include 'includes/chatbot_icon.html' %}
    {% include 'includes/chatbot_window.html' %}
    
    <script src="{% static 'js/chatbot.js' %}"></script>
</body>
</html>
```

### 6. Run Migrations

```bash
python manage.py makemigrations chatbot
python manage.py migrate chatbot
```

### 7. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

## Configuration

### Basic Settings

```python
# settings.py

CHATBOT_CONFIG = {
    'RATE_LIMIT': 30,  # requests per minute
    'SESSION_TIMEOUT': 3600,  # 1 hour
    'MAX_MESSAGE_LENGTH': 1000,
    'ENABLE_ANALYTICS': True,
    'CACHE_SEARCH_RESULTS': True,
}
```

### Cache Setup (Recommended)

**Option 1: Redis (Production)**
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

**Option 2: Database Cache (Simple)**
```bash
python manage.py createcachetable
```

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'chatbot_cache_table',
    }
}
```

## Usage

### Supported User Queries

**Order Tracking**
- "Track order 123"
- "Where is my order?"
- "Order status"

**Product Search**
- "Show me t-shirts"
- "Find black kurta"
- "Products under ₹500"
- "Do you have size XL?"

**Size Recommendation**
- "What size should I get?"
- "I'm 170cm and 70kg"
- "Recommend size for me"

**Cart Help**
- "View my cart"
- "Add to cart"
- "Shopping cart"

**Support**
- "Shipping policy"
- "Return policy"
- "Payment methods"
- "COD available?"

### API Endpoints

**POST /chatbot/ask/**
```json
{
  "message": "Track my order"
}
```

Response:
```json
{
  "reply": "Order status response...",
  "suggestions": ["Track another order", "Browse products"],
  "products": [...],
  "order_details": {...}
}
```

**GET /chatbot/history/**
Returns conversation history for current session.

**POST /chatbot/clear/**
Clears current chat session.

## Customization

### Styling

Modify `static/css/chatbot.css`:

```css
/* Change color scheme */
.chatbot-icon {
    background: linear-gradient(135deg, #your-color 0%, #your-color-2 100%);
}

.chatbot-header {
    background: linear-gradient(135deg, #your-color 0%, #your-color-2 100%);
}
```

### Adding New Intents

```python
# chatbot/services.py

# 1. Add pattern to IntentParser
INTENT_PATTERNS = {
    'your_intent': [
        r'your.*pattern',
        r'another.*pattern',
    ],
}

# 2. Create handler
class YourIntentHandler:
    def handle(self, message: str) -> Dict:
        return {
            'reply': 'Your response',
            'suggestions': ['Suggestion 1', 'Suggestion 2']
        }

# 3. Add to ChatbotService.process_message()
elif intent == 'your_intent':
    return self.your_handler.handle(message)
```

### Custom FAQ Responses

```python
# chatbot/services.py - FallbackHandler

FAQ_RESPONSES = {
    'your_topic': "Your custom FAQ response here...",
}
```

## Advanced Features

### Rate Limiting

```python
# settings.py
MIDDLEWARE = [
    # ...
    'chatbot.advanced_features.RateLimitMiddleware',
]
```

### Analytics

```python
from chatbot.advanced_features import AnalyticsTracker

# Track intent success
AnalyticsTracker.track_intent(session_id, intent, success=True)

# Get popular queries
popular = AnalyticsTracker.get_popular_queries()
```

### Cart Operations

```python
from chatbot.advanced_features import CartAssistantHandler

handler = CartAssistantHandler()
result = handler.add_to_cart(user, product_slug='blue-kurta', size='L', quantity=1)
```

## Performance Optimization

### Database Queries
- Uses `select_related()` and `prefetch_related()` for efficient joins
- Indexes on frequently queried fields
- Caching for search results

### Frontend
- CSS transitions instead of JavaScript animations
- Debounced search queries
- Lazy loading of chat history

## Security

- ✅ CSRF token validation
- ✅ Rate limiting to prevent abuse
- ✅ Input sanitization
- ✅ Session-based authentication
- ✅ No sensitive data in logs

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Troubleshooting

### Chatbot not appearing
1. Check static files are collected: `python manage.py collectstatic`
2. Verify templates are included in base.html
3. Check browser console for JavaScript errors

### Messages not sending
1. Verify CSRF token in cookies
2. Check `/chatbot/ask/` endpoint is accessible
3. Review Django logs for errors

### Slow responses
1. Enable caching (Redis recommended)
2. Check database query optimization
3. Review rate limiting settings

## API Integration (Optional)

To integrate with external AI services:

```python
# chatbot/services.py

import openai  # or your preferred AI service

class AIEnhancedParser:
    def parse_with_ai(self, message: str):
        # Use GPT or similar for advanced NLP
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}]
        )
        return response
```

## Testing

```bash
# Run tests
python manage.py test chatbot

# Test specific functionality
python manage.py shell
>>> from chatbot.services import ChatbotService
>>> bot = ChatbotService()
>>> result = bot.process_message("Track my order")
>>> print(result)
```

## Production Deployment

1. Set `DEBUG = False`
2. Configure proper ALLOWED_HOSTS
3. Enable Redis caching
4. Set up rate limiting
5. Configure logging
6. Use CDN for static files
7. Enable HTTPS

## License

MIT License - feel free to modify and use in your projects.

## Support

For issues or questions:
1. Check this documentation
2. Review Django logs
3. Check browser console
4. Open issue on project repository

## Roadmap

- [ ] WebSocket support for real-time chat
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] File upload support
- [ ] Integration with popular helpdesk systems
- [ ] Advanced analytics dashboard
- [ ] Machine learning for intent detection