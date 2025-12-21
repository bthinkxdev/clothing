# chatbot/admin.py
from django.contrib import admin
from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'started_at', 'last_activity', 'is_active']
    list_filter = ['is_active', 'started_at']
    search_fields = ['session_id', 'user__username', 'user__email']
    readonly_fields = ['session_id', 'started_at', 'last_activity']
    date_hierarchy = 'started_at'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'message_type', 'content_preview', 'intent', 'created_at']
    list_filter = ['message_type', 'intent', 'created_at']
    search_fields = ['session_id', 'content', 'user__username']
    readonly_fields = ['session_id', 'user', 'message_type', 'content', 'intent', 'metadata', 'created_at']
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False