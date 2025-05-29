# downloader_ytdlp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # --- Existing Download URLs ---
    path('download/', views.DownloadView.as_view(), name='download'),
    path('task_status/<str:task_id>/', views.get_task_status, name='task_status'),
    path('get_formats/', views.get_available_formats, name='get_formats'),

    # --- NEW Forum URLs ---
    path('forum/topics/', views.forum_topic_list_create, name='forum_topic_list_create'),
    path('forum/topics/<uuid:topic_id>/', views.forum_topic_detail, name='forum_topic_detail'),
    path('forum/topics/<uuid:topic_id>/posts/', views.forum_post_create, name='forum_post_create'),

    # ... (Admin URLs if you kept them) ...
]