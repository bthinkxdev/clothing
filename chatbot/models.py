# chatbot/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatMessage(models.Model):
    """Store chat conversation history"""
    MESSAGE_TYPE = (
        ('user', 'User'),
        ('bot', 'Bot'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='chat_messages',
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=255, db_index=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE)
    content = models.TextField()
    intent = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}"


class ChatSession(models.Model):
    """Track chat sessions"""
    session_id = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Session {self.session_id}"