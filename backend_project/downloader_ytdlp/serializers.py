from django.contrib.auth.models import User
from rest_framework import serializers
from .models import DownloadLog, ForumTopic, ForumPost # Ensure these models are defined in models.py

# --- User Serializers ---
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff', 'date_joined']
        read_only_fields = ['is_staff', 'date_joined']

class BasicUserSerializer(serializers.ModelSerializer): # For simpler listings
    class Meta:
        model = User
        fields = ['id', 'username']

# --- Download Log Serializer ---
class DownloadLogSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer(read_only=True)
    target_user_for_download = BasicUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = DownloadLog
        fields = [
            'id', 'user', 'target_user_for_download', 'url',
            'format_code_selected', 'format_type_selected',
            'is_playlist_download', 'task_id', 'status',
            'created_at', 'updated_at', 'downloaded_files_info', 'error_message'
        ]

# --- Forum Serializers ---

# --- CORRECTED ForumPostSerializer ---
class ForumPostSerializer(serializers.ModelSerializer):
    author = BasicUserSerializer(read_only=True)
    # When responding, include the topic's ID.
    # The `source='topic.id'` tells DRF to get the value from the `id` attribute of the `topic` foreign key.
    # It's `read_only=True` because for *creating* a post via this serializer (used in forum_post_create view),
    # the topic is determined by the URL and set in the view's `serializer.save(topic=topic_instance)`,
    # not passed in the request body data for this specific endpoint.
    topic_id = serializers.IntegerField(source='topic.id', read_only=True)

    class Meta:
        model = ForumPost
        # 'topic' (the ForeignKey field) is not listed here as a writable field because the view handles it.
        # We list 'topic_id' to include it in the serialized output (response).
        fields = ['id', 'author', 'content', 'created_at', 'updated_at', 'topic_id']
        # Fields set by the system/view, not by direct user input in the request body for this serializer.
        read_only_fields = ['author', 'created_at', 'updated_at']
        # We don't need to list 'topic' in read_only_fields if it's not in 'fields' for writing.
        # The 'topic_id' field we added is already read_only.

# Serializer for listing topics (shows less detail)
class ForumTopicSerializer(serializers.ModelSerializer):
    author = BasicUserSerializer(read_only=True)
    post_count = serializers.SerializerMethodField()
    # Use 'updated_at' from the topic model, which should be updated by the Post.save() method
    latest_post_at = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = ForumTopic
        fields = ['id', 'title', 'author', 'created_at', 'updated_at', 'post_count', 'latest_post_at']
        read_only_fields = ['author', 'created_at', 'updated_at', 'post_count', 'latest_post_at']

    def get_post_count(self, obj):
        return obj.posts.count()

# Serializer for viewing a single topic with all its posts (posts are nested)
class ForumTopicDetailSerializer(serializers.ModelSerializer):
    author = BasicUserSerializer(read_only=True)
    posts = ForumPostSerializer(many=True, read_only=True) # Uses the corrected ForumPostSerializer

    class Meta:
        model = ForumTopic
        fields = ['id', 'title', 'author', 'created_at', 'updated_at', 'posts']
        read_only_fields = ['author', 'created_at', 'updated_at', 'posts']