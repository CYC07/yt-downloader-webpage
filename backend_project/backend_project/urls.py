# backend_project/backend_project/urls.py
from django.contrib import admin
from django.urls import path, include # Make sure include is imported
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Delegates URLs starting with 'api/auth/' to downloader_ytdlp/auth_urls.py
    path('api/auth/', include('downloader_ytdlp.auth_urls')),
    # Delegates URLs starting with 'api/' (that aren't 'api/auth/') to downloader_ytdlp/urls.py
    path('api/', include('downloader_ytdlp.urls')),
]

# Serve media files during development (Important for downloaded files)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)