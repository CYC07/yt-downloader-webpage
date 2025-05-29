# downloader_ytdlp/views.py
import traceback
import yt_dlp
import pprint
import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes

from celery.result import AsyncResult

from django.contrib.auth.models import User
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from .tasks import download_video_task
from .models import DownloadLog, ForumTopic, ForumPost
from .serializers import (
    UserSerializer, DownloadLogSerializer,
    ForumTopicSerializer, ForumPostSerializer, ForumTopicDetailSerializer,
    BasicUserSerializer
)

# Helper Decorator
def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'error': 'Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# DownloadView
class DownloadView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        url = request.data.get('url'); format_code = request.data.get('format_code'); format_type = request.data.get('format_type'); is_playlist = request.data.get('is_playlist', False); filename_template = request.data.get('filename_template', None)
        acting_user = request.user; user_to_download_for = acting_user;
        if not url or not format_code or not format_type: return Response({'error': 'URL, code, type required'}, status=status.HTTP_400_BAD_REQUEST)
        validator = URLValidator();
        try: validator(url)
        except ValidationError: return Response({'error': 'Invalid URL'}, status=status.HTTP_400_BAD_REQUEST)
        if format_type not in ['video', 'audio']: return Response({'error': 'Invalid format_type'}, status=status.HTTP_400_BAD_REQUEST)
        log_entry = None
        try:
            log_entry = DownloadLog.objects.create(user=acting_user,target_user_for_download=user_to_download_for,url=url,format_code_selected=format_code,format_type_selected=format_type,is_playlist_download=is_playlist)
        except Exception as e: print(f"Error creating DownloadLog: {e}"); traceback.print_exc(); return Response({'error': 'Could not initiate download log.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        print(f"Dispatching: User '{acting_user.username}' (LogID:{log_entry.id}), Template:'{filename_template if filename_template else 'Default'}'")
        try:
            task = download_video_task.delay(url=url,format_code=format_code,format_type=format_type,target_username=user_to_download_for.username,is_playlist=is_playlist,filename_template=filename_template,log_id=log_entry.id)
            log_entry.task_id = task.id; log_entry.save(update_fields=['task_id','updated_at'])
            print(f"Task dispatched: {task.id}")
            return Response({'task_id': task.id, 'log_id': str(log_entry.id)}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            log_entry.status='FAILURE'; log_entry.error_message=f"Queue fail: {str(e)}"; log_entry.task_id=f"FAIL_Q_{uuid.uuid4()}"; log_entry.save(update_fields=['status','error_message','task_id','updated_at'])
            print(f"Error dispatching Celery task: {e}"); traceback.print_exc(); return Response({'error': 'Failed to queue download task.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# get_available_formats (Corrected)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_available_formats(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)

    validator = URLValidator()
    try:
        validator(url)
    except ValidationError:
        return Response({'error': 'Invalid URL format'}, status=status.HTTP_400_BAD_REQUEST)

    print(f"Fetching formats for URL: {url}")
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True, 'nocheckcertificate': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

        print(f"--- INFO DICT for {url} (get_available_formats) ---"); pprint.pprint(info_dict)
        raw_formats_from_yt_dlp = info_dict.get('formats', [])
        print(f"--- RAW FORMATS COUNT from yt-dlp: {len(raw_formats_from_yt_dlp)} ---")
        if raw_formats_from_yt_dlp: print("--- FIRST RAW FORMAT EXAMPLE: ---"); pprint.pprint(raw_formats_from_yt_dlp[0])
        else: print("--- No formats found in raw info_dict from yt-dlp ---")

        processed_formats = []

        # --- Add Standard "Best" Options First ---
        processed_formats.append({'code': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'description': 'Best Overall MP4 (Video+Audio, Recommended)', 'type': 'video', 'extension': 'mp4', 'filesize': None, 'sort_key': 10000})
        processed_formats.append({'code': 'bestvideo+bestaudio/best', 'description': 'Best Overall (Video+Audio, yt-dlp chooses container)', 'type': 'video', 'extension': 'video', 'filesize': None, 'sort_key': 9900})
        processed_formats.append({'code': 'bestaudio[ext=m4a]/bestaudio', 'description': 'Best Audio M4A (AAC)', 'type': 'audio', 'extension': 'm4a', 'filesize': None, 'sort_key': 5000})
        processed_formats.append({'code': 'bestaudio_convert_mp3', 'description': 'Convert Best Audio to MP3 (~192k)', 'type': 'audio', 'extension': 'mp3', 'filesize': None, 'sort_key': 4900})
        processed_formats.append({'code': 'bestaudio_convert_wav', 'description': 'Convert Best Audio to WAV', 'type': 'audio', 'extension': 'wav', 'filesize': None, 'sort_key': 4800})
        processed_formats.append({'code': 'bestaudio_convert_aac', 'description': 'Convert Best Audio to AAC (~192k)', 'type': 'audio', 'extension': 'aac', 'filesize': None, 'sort_key': 4700})

        # --- Process Individual Streams (Excluding Manifests) ---
        best_audio_stream_info = None
        audio_streams = [f for f in raw_formats_from_yt_dlp if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none' and f.get('url') and not f.get('manifest_url')]
        if audio_streams:
            audio_streams.sort(key=lambda x: -(x.get('abr') or 0))
            best_audio_stream_info = audio_streams[0]
        added_video_resolutions_for_merging = set()

        for f in raw_formats_from_yt_dlp:
            if f.get('manifest_url') or not f.get('url') or not f.get('format_id') or f.get('protocol') in ['mhtml']: continue
            format_id=f.get('format_id'); ext=f.get('ext','?'); filesize=f.get('filesize')or f.get('filesize_approx'); filesize_str=f"{round(filesize/(1024*1024),1)}MB"if filesize else'?'; vcodec=f.get('vcodec','none'); acodec=f.get('acodec','none'); height=f.get('height'); abr=f.get('abr'); vbr=f.get('vbr'); fps=f.get('fps'); note_parts=[]; width=f.get('width')
            if f.get('format_note'): note_parts.append(f.get('format_note'))
            elif f.get('format'): note_parts.append(f.get('format'))
            else: note_parts.append(format_id)
            if width and height: note_parts.append(f"{width}x{height}")
            if fps: note_parts.append(f"{int(fps)}fps")
            format_entry=None; current_format_type='unknown'

            # A. Directly Downloadable Combined Video+Audio (Progressive)
            if vcodec!='none'and acodec!='none':
                current_format_type='video'; desc=' '.join(note_parts); desc+=f" ({ext}, Vid+Aud)";
                if vbr:desc+=f" V:{round(vbr)}k";
                if abr:desc+=f" A:{round(abr)}k";
                desc+=f" ~{filesize_str}"; format_entry={'code':format_id,'description':desc,'type':current_format_type,'extension':ext,'filesize':filesize,'sort_key':(height or 0)*100+(abr or 0)}

            # B. Video-Only Stream => ONLY create a "Merged with Best Audio" option
            elif vcodec!='none'and acodec=='none':
                # current_format_type='video_only'; # No longer needed if not listing video-only
                resolution_key=f"{height}p_{ext}"
                # Create a "Merged with Best Audio" option if it's decent resolution
                if height and height>=480 and resolution_key not in added_video_resolutions_for_merging:
                    merged_code=f"{format_id}+bestaudio" # yt-dlp will pick best available audio
                    desc_merged=' '.join(note_parts); # Start with video specific note (e.g. 1080p)
                    desc_merged+=f" ({ext} + Best Audio)" # Clarify it's merged
                    if vbr:desc_merged+=f" V:{round(vbr)}k";
                    if best_audio_stream_info and best_audio_stream_info.get('abr'):desc_merged+=f" A:~{round(best_audio_stream_info.get('abr'))}k (est.)";
                    desc_merged+=f" ~{filesize_str} (video stream size)";
                    # This is the entry that will be added
                    format_entry={'code':merged_code,'description':desc_merged,'type':'video','extension':ext,'filesize':filesize,'sort_key':(height or 0)*1000+500} # Prioritize merged
                    added_video_resolutions_for_merging.add(resolution_key)
                # We are NOT adding the video-only stream itself to processed_formats anymore.
                # format_entry might be None if resolution too low or already added.

            # C. Audio-Only Stream
            elif vcodec=='none'and acodec!='none':
                current_format_type='audio'; desc_ao=' '.join(note_parts); desc_ao+=f" ({ext}, Audio Only)";
                if abr:desc_ao+=f" A:{round(abr)}k";
                desc_ao+=f" ~{filesize_str}";
                processed_formats.append({'code':format_id,'description':desc_ao,'type':current_format_type,'extension':ext,'filesize':filesize,'sort_key':abr or 0})
                if ext!='mp3':processed_formats.append({'code':f"{format_id}_convert_mp3",'description':f"Convert '{note_parts[0]} ({ext})' to MP3 (~192k)",'type':'audio','extension':'mp3','filesize':None,'sort_key':abr or 0}) # Use note_parts[0] for base desc
                if ext!='wav':processed_formats.append({'code':f"{format_id}_convert_wav",'description':f"Convert '{note_parts[0]} ({ext})' to WAV",'type':'audio','extension':'wav','filesize':None,'sort_key':abr or 0})
                format_entry=None # Handled by appending directly

            if format_entry: # This will now only add combined (Block A) or merged video+audio (Block B)
                processed_formats.append(format_entry)

        # Sort and Deduplicate (as before)
        processed_formats.sort(key=lambda x:(x['type']!='video',x['type']!='audio',-(x.get('sort_key')or 0)),reverse=False)
        final_unique_formats=[]; seen_codes=set()
        for pf in processed_formats:
            if pf['code']not in seen_codes:final_unique_formats.append(pf);seen_codes.add(pf['code'])

        print(f"Processed and sending {len(final_unique_formats)} unique formats for {url} to frontend.")
        return Response({'formats': final_unique_formats}, status=status.HTTP_200_OK)

    except yt_dlp.utils.DownloadError as e: print(f"yt-dlp DL Error fetching formats for {url}: {e}"); return Response({'error':f'Could not retrieve formats: {str(e)}'},status=status.HTTP_400_BAD_REQUEST)
    except Exception as e: print(f"Unexpected error fetching formats for {url}:"); traceback.print_exc(); return Response({'error':'An unexpected error occurred while fetching formats.'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# get_task_status
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_status(request, task_id):
    try:
        task_result = AsyncResult(task_id)
        response_data = {'task_id': task_id, 'status': task_result.status, 'info': None, 'result': None}
        try:
             if isinstance(task_result.info, dict): response_data['info'] = task_result.info
             elif task_result.info is not None: print(f"Warning: Task {task_id} info not dict: {type(task_result.info)}")
        except Exception as info_exc: print(f"Error retrieving info: {info_exc}"); response_data['info'] = {'error': 'Could not retrieve metadata'}
        if task_result.ready():
            if task_result.successful():
                response_data['status'] = 'SUCCESS'
                response_data['result'] = task_result.result
            elif task_result.failed():
                response_data['status'] = 'FAILURE'
                exc = task_result.result; response_data['result'] = {'exc_type': type(exc).__name__, 'exc_message': str(exc)}
                if response_data.get('info') and 'status' in response_data['info']: response_data['status_message'] = response_data['info'].get('status')
        return Response(response_data)
    except Exception as e: print(f"--- ERROR in get_task_status for {task_id} ---"); traceback.print_exc(); return Response({'error': 'Internal error checking status.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Forum Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def forum_topic_list_create(request):
    if request.method == 'GET': topics = ForumTopic.objects.all().order_by('-updated_at'); serializer = ForumTopicSerializer(topics, many=True, context={'request': request}); return Response(serializer.data)
    elif request.method == 'POST': serializer = ForumTopicSerializer(data=request.data, context={'request': request});
    if serializer.is_valid(): serializer.save(author=request.user); return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def forum_topic_detail(request, topic_id):
    try: topic = ForumTopic.objects.get(pk=topic_id)
    except ForumTopic.DoesNotExist: return Response({'error': 'Topic not found.'}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError: return Response({'error': 'Invalid Topic ID format.'}, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'GET': serializer = ForumTopicDetailSerializer(topic, context={'request': request}); return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def forum_post_create(request, topic_id):
    try: topic = ForumTopic.objects.get(pk=topic_id)
    except ForumTopic.DoesNotExist: return Response({'error': 'Topic not found to post in.'}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError: return Response({'error': 'Invalid Topic ID format.'}, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'POST':
        serializer = ForumPostSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(): serializer.save(author=request.user, topic=topic); return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)