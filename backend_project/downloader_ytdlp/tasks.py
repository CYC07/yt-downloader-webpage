# downloader_ytdlp/tasks.py
import yt_dlp
import os
import traceback # For printing detailed errors
import uuid
import time # Import time for sleep
import json # Not strictly needed for return, but useful if parsing info.json for more details

from celery import shared_task
from django.conf import settings
from pathvalidate import sanitize_filename # For sanitizing user input for filenames

from .models import DownloadLog # Assuming DownloadLog model is in the same app's models.py

# --- Helper function for progress hook ---
def update_progress(task_instance, d):
    """
    Callback function used by yt-dlp's progress_hooks.
    Updates the Celery task state with progress information.
    Uses string literals for states.
    """
    try:
        status_message = 'Downloading...'
        playlist_info = ""
        if d.get('playlist_index') and d.get('playlist_n_entries'):
            playlist_info = f" (Item {d['playlist_index']}/{d['playlist_n_entries']})"
            status_message = f"Downloading Playlist Item {d['playlist_index']} of {d['playlist_n_entries']}"

        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes')
            if total_bytes and downloaded_bytes:
                try:
                    percent = int((downloaded_bytes / total_bytes) * 100)
                    current_state_obj = task_instance.AsyncResult(task_instance.request.id)
                    if current_state_obj.state not in ['SUCCESS', 'FAILURE', 'REVOKED'] and (percent % 5 == 0 or percent == 100):
                         task_instance.update_state(
                             state='PROGRESS',
                             meta={'status': f"{status_message}{playlist_info}", 'progress': percent}
                         )
                except ZeroDivisionError:
                      task_instance.update_state(
                          state='PROGRESS',
                          meta={'status': f"{status_message}{playlist_info}", 'progress': 0}
                      )
        elif d['status'] == 'finished':
            task_instance.update_state(
                state='PROGRESS',
                meta={'status': f"Processing Item{playlist_info}...", 'progress': 99}
            )
        elif d['status'] == 'error':
            print(f"Progress hook reported an error for task {task_instance.request.id}{playlist_info}")
    except Exception as exc:
        print(f"!!! ERROR within progress hook for task {task_instance.request.id} !!!")
        traceback.print_exc()


# --- Main Celery Task ---
@shared_task(bind=True, throws=(yt_dlp.utils.DownloadError, FileNotFoundError, Exception))
def download_video_task(self, *, url, format_code, format_type, target_username, is_playlist=False, filename_template=None, log_id=None):
    """
    Downloads video/audio or playlist using yt-dlp.
    Embeds metadata and thumbnail into the output file where supported.
    Handles progress updates and reports success or failure via return/raise.
    Accepts keyword arguments.
    Updates DownloadLog model.
    """
    task_id = self.request.id # Celery's internal task ID
    print(f"Starting task {task_id} for target_user={target_username}, format_code={format_code}, type={format_type}, playlist={is_playlist}, template='{filename_template}', url={url}, log_id={log_id}")

    log_entry = None
    if log_id:
        try:
            log_entry = DownloadLog.objects.get(id=log_id)
        except DownloadLog.DoesNotExist:
            print(f"Error: Could not find DownloadLog with id {log_id} for task {task_id}")
            # Task will proceed but won't update this specific log entry if not found

    # Update log to STARTED if found
    if log_entry:
        log_entry.status = 'STARTED'
        log_entry.save(update_fields=['status', 'updated_at'])

    # Setup download directory
    user_download_dir = os.path.join(settings.MEDIA_ROOT, 'downloads', target_username)
    task_specific_download_dir = os.path.join(user_download_dir, task_id) # Use Celery task_id for unique folder
    os.makedirs(task_specific_download_dir, exist_ok=True)
    print(f"Task {task_id}: Download directory: {task_specific_download_dir}")

    try:
        self.update_state(state='STARTED', meta={'status': 'Initializing...', 'progress': 0})

        # --- Output Template Construction ---
        default_template_single = '%(title)s [%(id)s].%(ext)s'
        default_template_playlist = '%(playlist_index)s - %(title)s [%(id)s].%(ext)s'
        sanitized_user_template = ""
        if filename_template:
            temp_template = filename_template.replace('../', '').replace('..\\', '')
            sanitized_user_template = sanitize_filename(temp_template, platform="auto", replacement_text="_")
        chosen_template = (sanitized_user_template if sanitized_user_template else 
                           (default_template_playlist if is_playlist else default_template_single))
        if os.path.isabs(chosen_template) or '..' in chosen_template.split(os.sep):
            print(f"Task {task_id}: Invalid template path chars, reverting to default.")
            chosen_template = default_template_playlist if is_playlist else default_template_single
        output_template_with_ext = os.path.join(task_specific_download_dir, chosen_template)
        # Forcing MP4/target audio extension often requires post-processing, so use yt-dlp's %(ext)s for initial download
        # The actual final extension is determined later.
        print(f"Task {task_id}: Base output template pattern: {output_template_with_ext}")

        # --- Prepare yt-dlp Options ---
        ydl_opts = {
            'outtmpl': output_template_with_ext, # Let yt-dlp fill %(ext)s initially
            'progress_hooks': [lambda d: update_progress(self, d)],
            'nocheckcertificate': True, 'noplaylist': not is_playlist,
            'max_downloads': 1 if not is_playlist else None,
            'quiet': False, 'no_warnings': False, 'ignoreerrors': is_playlist,
            'addmetadata': True, 'metadatacommand': 'ffmpeg', 'parsemetadata': '%(artist,title)s',
            'ppa': [
                'Metadata+ffmpeg:-metadata', f'artist={'"%(uploader)s"'}',
                'Metadata+ffmpeg:-metadata', f'album_artist={'"%(uploader)s"'}',
                'Metadata+ffmpeg:-metadata', f'date={'"%(upload_date)s"'}',
                'Metadata+ffmpeg:-metadata', f'comment={'"%(description)s"'}',
            ],
            'writethumbnail': False, 'embedthumbnail': False,
        }
        postprocessors = []
        actual_format_code_for_yt_dlp = format_code
        target_final_codec = None # Store the final target codec/format name for extension determination
        can_embed_thumbnail = False
        expected_final_extension = '.mp4' # Default for video

        # --- Determine Format Code, Post-Processing, and Thumbnail Support ---
        if '_convert_' in format_code: # Audio Conversion
            parts = format_code.split('_convert_'); source_audio_code=parts[0]; target_final_codec=parts[1]
            actual_format_code_for_yt_dlp = source_audio_code
            expected_final_extension = f'.{target_final_codec}'
            if target_final_codec == 'mp3': pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}; can_embed_thumbnail = True;
            elif target_final_codec == 'wav': pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}; can_embed_thumbnail = False;
            elif target_final_codec == 'aac': pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'aac', 'preferredquality': '192'}; can_embed_thumbnail = True;
            elif target_final_codec == 'flac': pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'flac'}; can_embed_thumbnail = True;
            elif target_final_codec == 'opus': pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'opus'}; can_embed_thumbnail = True;
            else: pp = None; print(f"Warning: Unsupported conversion target '{target_final_codec}'.")
            if pp: postprocessors.append(pp)
            ydl_opts['keepvideo'] = False # For audio extraction
        else: # Direct Download or Video Merge/Conversion
            actual_format_code_for_yt_dlp = format_code
            target_final_codec = format_code # Store original code for reference
            if format_type == 'video':
                expected_final_extension = '.mp4' # Force MP4 output for videos
                can_embed_thumbnail = True
                # Ensure MP4 container by adding a video convertor postprocessor
                # This will remux or convert to MP4.
                postprocessors.append({'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'})
            elif format_type == 'audio':
                 # Determine likely extension for direct audio download
                 if 'mp3' in format_code.lower(): expected_final_extension = '.mp3'; can_embed_thumbnail = True;
                 elif 'm4a' in format_code.lower(): expected_final_extension = '.m4a'; can_embed_thumbnail = True;
                 elif 'aac' in format_code.lower(): expected_final_extension = '.aac'; can_embed_thumbnail = True;
                 elif 'wav' in format_code.lower(): expected_final_extension = '.wav'; can_embed_thumbnail = False;
                 elif 'flac' in format_code.lower(): expected_final_extension = '.flac'; can_embed_thumbnail = True;
                 elif 'opus' in format_code.lower(): expected_final_extension = '.opus'; can_embed_thumbnail = True; # Often in .ogg
                 else: expected_final_extension = '.audio'; can_embed_thumbnail = False; # Fallback

        # Conditionally enable thumbnail embedding in options
        if can_embed_thumbnail:
            print(f"Task {task_id}: Enabling thumbnail writing and embedding.")
            ydl_opts['writethumbnail'] = True
            ydl_opts['embedthumbnail'] = True
            # Add EmbedThumbnail PP explicitly if no other PPs will handle it
            if not any(pp.get('key') in ['FFmpegExtractAudio', 'FFmpegVideoConvertor'] for pp in postprocessors):
                postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
        else:
            print(f"Task {task_id}: Thumbnail embedding disabled for target format '{target_final_codec or actual_format_code_for_yt_dlp}'.")
            ydl_opts['writethumbnail'] = False # Ensure it's off
            ydl_opts['embedthumbnail'] = False

        # Assign final format code and postprocessors
        ydl_opts['format'] = actual_format_code_for_yt_dlp
        if postprocessors:
            existing_pps = ydl_opts.get('postprocessors', [])
            # Add new PPs, avoid duplicates if 'postprocessors' key was already there
            ydl_opts['postprocessors'] = existing_pps + [pp for pp in postprocessors if pp not in existing_pps]

        # Clean up max_downloads option if None
        if ydl_opts.get('max_downloads') is None:
            del ydl_opts['max_downloads']

        # 3. Perform the download
        if log_entry: log_entry.status = 'DOWNLOADING'; log_entry.save(update_fields=['status', 'updated_at'])
        self.update_state(state='PROGRESS', meta={'status': 'Starting download...', 'progress': 5})
        print(f"Task {task_id}: Running yt-dlp with final options: {ydl_opts}")
        download_success_flag = False
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            download_success_flag = True
            print(f"Task {task_id}: yt-dlp download process finished ok.")
        except yt_dlp.utils.MaxDownloadsReached:
            if not is_playlist:
                download_success_flag = True
                print(f"Task {task_id}: yt-dlp finished via MaxDownloadsReached (expected).")
            else:
                print(f"Task {task_id}: WARNING - MaxDownloadsReached during playlist download?")
                download_success_flag = True # Assume success for playlist and check files

        # 4. Find and verify downloaded files if download block seemed okay
        if not download_success_flag:
            raise Exception("Download process failed before file verification stage.")

        if log_entry: log_entry.status = 'VERIFYING'; log_entry.save(update_fields=['status', 'updated_at'])
        self.update_state(state='PROGRESS', meta={'status': 'Verifying output...', 'progress': 99})
        print(f"Task {task_id}: Scanning {task_specific_download_dir} for final media file(s)...")

        downloaded_files_info_list = []
        temp_files_to_remove_list = []
        try:
            possible_files_in_dir = os.listdir(task_specific_download_dir)
        except FileNotFoundError:
            possible_files_in_dir = []
            print(f"Task {task_id}: Task directory not found during verification.")

        if not possible_files_in_dir and download_success_flag:
            raise FileNotFoundError(f"No files found in {task_specific_download_dir} after download process claimed success.")

        print(f"Task {task_id}: Found raw files in task directory: {possible_files_in_dir}")

        KNOWN_MEDIA_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.flv', '.avi', '.mov', '.mp3', '.m4a', '.aac', '.wav', '.opus', '.flac'}
        # Target extension for primary media file, taking from forced conversion or best guess
        target_media_extension = expected_final_extension.lower() if '.' in expected_final_extension else None

        for fname in possible_files_in_dir:
            file_path = os.path.join(task_specific_download_dir, fname)
            if not os.path.isfile(file_path): continue

            _, ext = os.path.splitext(fname)
            ext_lower = ext.lower()

            is_primary_target_media = False
            if target_media_extension and ext_lower == target_media_extension:
                is_primary_target_media = True
            elif not target_media_extension and ext_lower in KNOWN_MEDIA_EXTENSIONS: # Fallback if ext wasn't certain
                is_primary_target_media = True # Could be the one if no specific ext was forced

            if is_primary_target_media:
                 relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                 file_url = os.path.join(settings.MEDIA_URL, relative_path).replace("\\", "/")
                 downloaded_files_info_list.append({'filename': fname, 'file_url': file_url})
                 print(f"Task {task_id}: Found valid media file: {fname}")
            elif ext_lower in {'.json', '.jpg', '.jpeg', '.png', '.webp', '.part', '.ytdl', '.temp'} or \
                 (target_media_extension and ext_lower != target_media_extension and ext_lower in KNOWN_MEDIA_EXTENSIONS):
                 # If it's a known temp file OR a media file that isn't our *final target* extension (e.g. original webm after mp4 conversion)
                 temp_files_to_remove_list.append(file_path)
                 print(f"Task {task_id}: Identified intermediate/temp file for removal: {fname}")
            else:
                 print(f"Task {task_id}: Skipping unknown file type during filtering: {fname}")

        # --- Optional Cleanup of temp files ---
        print(f"Task {task_id}: Cleaning up {len(temp_files_to_remove_list)} intermediate/temp file(s)...")
        for temp_path in temp_files_to_remove_list:
            try:
                print(f"Task {task_id}: Removing file: {os.path.basename(temp_path)}")
                os.remove(temp_path)
            except OSError as rm_err:
                print(f"Warning: Could not remove temp file {os.path.basename(temp_path)}: {rm_err}")

        if not downloaded_files_info_list and download_success_flag:
            raise FileNotFoundError(f"No file with expected characteristics (e.g., extension '{expected_final_extension}') found in {task_specific_download_dir} after processing. Raw files: {possible_files_in_dir}")

        # 5. Prepare and return success result
        if log_entry:
            log_entry.status = 'SUCCESS'
            log_entry.downloaded_files_info = downloaded_files_info_list
            log_entry.save(update_fields=['status', 'downloaded_files_info', 'updated_at'])
        print(f"Task {task_id}: Success! Resulting files: {downloaded_files_info_list}")
        return downloaded_files_info_list

    # --- Exception Handling ---
    except Exception as e: # Catches DownloadError, FileNotFoundError, and any other
        error_message = f'{type(e).__name__}: {str(e)}'
        print(f"Task {task_id} failed: {error_message}")
        if log_entry:
            log_entry.status = 'FAILURE'
            log_entry.error_message = error_message # Store the simplified error
            log_entry.save(update_fields=['status', 'error_message', 'updated_at'])
        traceback.print_exc() # Log full traceback to Celery worker console
        raise # Re-raise for Celery to store the actual exception object in result