# downloader_ytdlp/apps.py
from django.apps import AppConfig

class DownloaderConfig(AppConfig): # Make sure this class name is correct
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'downloader_ytdlp' # <---- CHANGE THIS LINE