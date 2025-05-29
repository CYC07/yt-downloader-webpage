# downloader_ytdlp/auth_urls.py
from django.urls import path
# Make sure to import from .auth_views (relative import)
from . import auth_views

urlpatterns = [
    path('register/', auth_views.register_user, name='register'),
    path('login/', auth_views.login_user, name='login'),
    path('logout/', auth_views.logout_user, name='logout'),
    path('status/', auth_views.check_auth_status, name='status'),
]