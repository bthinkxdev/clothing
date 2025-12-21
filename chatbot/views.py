# chatbot/views.py
import uuid
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .services import ChatbotService
from .models import ChatMessage, ChatSession


class ChatbotAPIView(View):
    """Handle chatbot API requests"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chatbot = ChatbotService()
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            
            if not message:
                return JsonResponse({
                    'error': 'Message is required'
                }, status=400)
            
            # Get or create session
            session_id = request.session.get('chat_session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
                request.session['chat_session_id'] = session_id
            
            # Get or create chat session
            chat_session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={'user': request.user if request.user.is_authenticated else None}
            )
            
            # Log user message
            ChatMessage.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=session_id,
                message_type='user',
                content=message
            )
            
            # Get conversation context
            context = request.session.get('chatbot_context', {})
            
            # Process message
            response = self.chatbot.process_message(
                message=message,
                user=request.user if request.user.is_authenticated else None,
                session_id=session_id,
                context=context
            )
            
            # Update context if size recommendation
            if 'state' in response:
                context['size_state'] = response['state']
                request.session['chatbot_context'] = context
                del response['state']  # Don't send to client
            
            # Log bot response
            ChatMessage.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=session_id,
                message_type='bot',
                content=response.get('reply', ''),
                intent=response.get('intent', 'general'),
                metadata=response
            )
            
            return JsonResponse(response)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'An error occurred',
                'details': str(e)
            }, status=500)


@require_http_methods(["GET"])
def get_chat_history(request):
    """Get chat history for current session"""
    session_id = request.session.get('chat_session_id')
    
    if not session_id:
        return JsonResponse({
            'messages': []
        })
    
    messages = ChatMessage.objects.filter(
        session_id=session_id
    ).order_by('created_at')[:50]
    
    return JsonResponse({
        'messages': [
            {
                'type': msg.message_type,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'metadata': msg.metadata
            }
            for msg in messages
        ]
    })


@require_http_methods(["POST"])
@csrf_exempt
def clear_chat(request):
    """Clear current chat session"""
    session_id = request.session.get('chat_session_id')
    
    if session_id:
        # Mark session as inactive
        ChatSession.objects.filter(session_id=session_id).update(is_active=False)
        
        # Clear session data
        if 'chat_session_id' in request.session:
            del request.session['chat_session_id']
        if 'chatbot_context' in request.session:
            del request.session['chatbot_context']
    
    return JsonResponse({
        'success': True,
        'message': 'Chat cleared'
    })