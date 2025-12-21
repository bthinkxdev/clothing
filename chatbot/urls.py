# chatbot/urls.py
from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('ask/', views.ChatbotAPIView.as_view(), name='ask'),
    path('history/', views.get_chat_history, name='history'),
    path('clear/', views.clear_chat, name='clear'),
]