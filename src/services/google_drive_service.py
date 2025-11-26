"""
Google Drive Service for Audio File Management
Downloads files directly from public Google Drive links using gdown
"""

import os
import logging
import re
from typing import List, Dict, Optional
import gdown

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for downloading from public Google Drive folders (no authentication!)"""

    def __init__(self):
        """
        Initialize Google Drive service
        No credentials needed for public folders!
        """
        logger.info("Google Drive service initialized (gdown mode - no API needed)")

    def extract_folder_id(self, drive_link: str) -> str:
        """
        Extract folder ID from Google Drive link

        Args:
            drive_link: Google Drive folder URL

        Returns:
            Folder ID
        """
        if '/folders/' in drive_link:
            folder_id = drive_link.split('/folders/')[-1].split('?')[0]
        elif 'id=' in drive_link:
            folder_id = drive_link.split('id=')[-1].split('&')[0]
        else:
            folder_id = drive_link

        logger.info(f"Extracted folder ID: {folder_id}")
        return folder_id

    def list_audio_files(self, folder_id: str, recursive: bool = True) -> List[Dict]:
        """
        List all audio files in a public Google Drive folder using gdown

        Args:
            folder_id: Google Drive folder ID
            recursive: Whether to search subfolders recursively

        Returns:
            List of audio file metadata dictionaries
        """
        audio_files = []
        audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.opus', '.wma']

        try:
            # Construct folder URL
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            logger.info(f"Accessing folder: {folder_url}")

            # Use gdown to list files in the folder
            # gdown.download_folder downloads everything, but we can use it to discover files
            # First, try to list the folder contents

            # Create a temporary directory to test folder access
            import tempfile
            temp_dir = tempfile.mkdtemp()

            try:
                # gdown will list files when we try to download the folder
                # We'll capture the file list from gdown's output
                file_list = gdown.download_folder(
                    url=folder_url,
                    output=temp_dir,
                    quiet=False,
                    use_cookies=False,
                    remaining_ok=True
                )

                # List downloaded files and identify audio files
                for root, dirs, files in os.walk(temp_dir):
                    for filename in files:
                        # Skip hidden files and system files
                        if filename.startswith('.') or filename == 'desktop.ini':
                            continue

                        file_path = os.path.join(root, filename)

                        # Check if file has an audio extension OR no extension at all
                        # (assume files without extensions from audio folders are audio files)
                        has_audio_ext = any(filename.lower().endswith(ext) for ext in audio_extensions)
                        has_no_ext = '.' not in filename or filename.endswith('-')

                        if has_audio_ext or has_no_ext:
                            rel_path = os.path.relpath(file_path, temp_dir)

                            # Get file size
                            file_size = os.path.getsize(file_path)

                            audio_files.append({
                                'id': filename,  # We'll use filename as ID since we have the file
                                'name': filename,
                                'path': rel_path,
                                'local_path': file_path,  # Already downloaded!
                                'size': file_size,
                                'mimeType': self._get_mime_type(filename)
                            })
                            logger.info(f"Found audio file: {filename}")

            except Exception as e:
                logger.error(f"Error listing folder with gdown: {e}")
                # Clean up temp directory
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise

            logger.info(f"Found {len(audio_files)} audio files in folder {folder_id}")
            return audio_files

        except Exception as error:
            logger.error(f"An error occurred while listing files: {error}")
            raise

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename extension"""
        ext_to_mime = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/m4a',
            '.aac': 'audio/aac',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.opus': 'audio/opus',
            '.wma': 'audio/x-ms-wma'
        }

        ext = os.path.splitext(filename)[1].lower()
        # If no extension, assume MP3 (most common)
        if not ext or ext == '-':
            return 'audio/mpeg'
        return ext_to_mime.get(ext, 'audio/mpeg')

    def download_file(self, file_id: str, destination_path: str, download_url: str = None,
                     local_path: str = None) -> str:
        """
        Download a file from Google Drive or copy if already downloaded

        Args:
            file_id: Google Drive file ID
            destination_path: Local path to save the file
            download_url: Direct download URL (optional)
            local_path: Local path if file is already downloaded

        Returns:
            Path to downloaded file
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            # If we already have the file locally (from gdown), just copy it
            if local_path and os.path.exists(local_path):
                logger.info(f"Copying file from {local_path} to {destination_path}")
                import shutil
                shutil.copy2(local_path, destination_path)
                return destination_path

            # Otherwise, download using gdown
            if download_url:
                logger.info(f"Downloading file to {destination_path}")
                gdown.download(download_url, destination_path, quiet=False)
            else:
                # Construct download URL
                download_url = f"https://drive.google.com/uc?id={file_id}"
                logger.info(f"Downloading file to {destination_path}")
                gdown.download(download_url, destination_path, quiet=False)

            logger.info(f"Downloaded file to {destination_path}")
            return destination_path

        except Exception as error:
            logger.error(f"An error occurred while downloading file: {error}")
            raise

    def batch_download_audio_files(
        self,
        folder_id: str,
        download_dir: str,
        recursive: bool = True,
        max_size_mb: Optional[int] = None
    ) -> List[str]:
        """
        Download all audio files from a folder

        Args:
            folder_id: Google Drive folder ID
            download_dir: Local directory to save files
            recursive: Whether to search subfolders recursively
            max_size_mb: Maximum file size in MB (skip larger files)

        Returns:
            List of downloaded file paths
        """
        # List files (this also downloads them to temp location)
        audio_files = self.list_audio_files(folder_id, recursive=recursive)
        downloaded_files = []

        logger.info(f"Starting batch download of {len(audio_files)} files")

        for file_info in audio_files:
            # Check file size if limit is set
            if max_size_mb and file_info.get('size', 0) > 0:
                file_size_mb = file_info['size'] / (1024 * 1024)
                if file_size_mb > max_size_mb:
                    logger.warning(
                        f"Skipping {file_info['name']} - "
                        f"size {file_size_mb:.2f}MB exceeds limit {max_size_mb}MB"
                    )
                    continue

            # Create local file path preserving folder structure
            local_path = os.path.join(download_dir, file_info['path'])

            try:
                # Copy from temp location to final destination
                downloaded_path = self.download_file(
                    file_info['id'],
                    local_path,
                    local_path=file_info.get('local_path')
                )
                downloaded_files.append(downloaded_path)
            except Exception as e:
                logger.error(f"Failed to download {file_info['name']}: {e}")
                continue

        logger.info(f"Successfully downloaded {len(downloaded_files)} files")
        return downloaded_files
