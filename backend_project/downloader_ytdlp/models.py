# downloader_ytdlp/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

# --- Download Log Model ---
class DownloadLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # ... (user, target_user_for_download, url, etc. remain the same) ...
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_logs_initiated')
    target_user_for_download = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_logs_received', null=True, blank=True)
    url = models.URLField(max_length=2048)
    format_code_selected = models.CharField(max_length=100)
    format_type_selected = models.CharField(max_length=20)
    is_playlist_download = models.BooleanField(default=False)

    # --- MODIFIED task_id field ---
    task_id = models.CharField(max_length=100, unique=True, db_index=True, null=True, blank=True)
    #   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Allow null temporarily

    status = models.CharField(max_length=50, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloaded_files_info = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        user_display = self.target_user_for_download.username if self.target_user_for_download else self.user.username
        return f"{user_display} - {self.url[:50]} - {self.status}"

    class Meta:
        ordering = ['-created_at']
        
# --- Forum Models ---
class ForumTopic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # When last post was added or topic edited

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-updated_at']

class ForumPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # If posts can be edited

    def __str__(self):
        return f"Post by {self.author.username} in {self.topic.title[:30]}"

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding # Check if it's a new post
        super().save(*args, **kwargs)
        if self.topic and is_new: # Only update topic on new post creation
            self.topic.updated_at = self.created_at # Or use timezone.now() for better accuracy
            self.topic.save(update_fields=['updated_at'])