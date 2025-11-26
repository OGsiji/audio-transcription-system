import logging
import asyncio
import os
import time
from typing import Dict, List, Optional, Any
import tempfile
from pathlib import Path

import ffmpeg

from src.config.settings import settings
from src.video_processor.s3_video_analyzer import S3VideoAnalyzer
from src.video_processor.google_generative_ai import EnhancedGoogleGenerativeService

# Configure logging
environment = settings.NODE_ENV
log_level = logging.DEBUG if environment == "development" else logging.INFO

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Reduce third-party noise
logging.getLogger("kafka").setLevel(logging.WARNING)


class EnhancedVideoProcessor:
    """
    Enhanced Video Processor focusing on video processing workflow, orchestration, and quality analysis

    Responsibilities:
    - Video file extraction and validation
    - Video download and processing (compression, format conversion)
    - Quality analysis and assessment
    - Workflow orchestration between stages
    - File cleanup and resource management

    AI/ML tasks are delegated to EnhancedGoogleGenerativeService
    """

    def __init__(self):
        # Initialize video analyzer for quality assessment
        self.video_analyzer = S3VideoAnalyzer(
            settings.AWS_ACCESS_KEY_ID,  # ✅ aws_access_key (first parameter)
            settings.AWS_SECRET_ACCESS_KEY,
            settings.AWS_REGION,
        )

        # Initialize AI service for content analysis
        self.ai_service = EnhancedGoogleGenerativeService()

        # Create output directories
        self.output_dir = settings.OUTPUT_DIR
        self.temp_dir = settings.TEMP_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        # Video processing configuration
        self.max_video_size = (
            settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
        )  # Convert to bytes
        self.max_duration = settings.MAX_VIDEO_DURATION_SECONDS
        self.supported_formats = settings.get_supported_video_formats()
        self.ffmpeg_quality = settings.get_ffmpeg_quality_settings()

        logging.info("Enhanced Video Processor initialized successfully")

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the video processor"""
        ai_health = self.ai_service.get_health_status()

        return {
            "video_analyzer": "healthy" if self.video_analyzer else "unhealthy",
            "ai_service": ai_health,
            "output_directory": (
                "healthy" if os.path.exists(self.output_dir) else "unhealthy"
            ),
            "temp_directory": (
                "healthy" if os.path.exists(self.temp_dir) else "unhealthy"
            ),
            "ffmpeg_available": self._check_ffmpeg_availability(),
            "configuration": {
                "max_video_size_mb": settings.MAX_VIDEO_SIZE_MB,
                "max_duration_seconds": self.max_duration,
                "supported_formats": self.supported_formats,
                "quality_preset": settings.VIDEO_COMPRESSION_QUALITY,
            },
        }

    def _check_ffmpeg_availability(self) -> str:
        """Check if FFmpeg is available"""
        try:
            import subprocess

            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            return "healthy" if result.returncode == 0 else "unhealthy"
        except Exception:
            return "unhealthy"

    def extract_video_files(self, circo_post: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and validate video files from CircoPost media field"""
        try:
            media_files = circo_post.get("files", [])
            video_files = []

            for media_item in media_files:
                if media_item.get("fileType") == "Video":
                    video_file = {
                        "id": media_item.get("id"),
                        "name": media_item.get("name"),
                        "original": media_item.get("original"),
                        "cachedOriginal": media_item.get("cachedOriginal"),
                        "signed": media_item.get("signed"),
                        "fileType": media_item.get("fileType"),
                        "path": media_item.get("path"),
                        "bucket": media_item.get("bucket"),
                    }

                    # Validate video file
                    if self._validate_video_file(video_file):
                        video_files.append(video_file)
                    else:
                        logging.warning(
                            f"Video file validation failed: {video_file.get('name')}"
                        )

            logging.info(
                f"Extracted {len(video_files)} valid video files from CircoPost"
            )
            return video_files

        except Exception as e:
            logging.error(f"Error extracting video files: {e}")
            return []

    def _validate_video_file(self, video_file: Dict[str, Any]) -> bool:
        """Validate video file metadata"""
        try:
            # Check if we have a valid URL
            url = video_file.get("original") or video_file.get("cachedOriginal")
            if not url:
                return False

            # Check file name and extension
            name = video_file.get("name", "")
            if name:
                extension = name.split(".")[-1].lower() if "." in name else ""
                if extension not in self.supported_formats:
                    logging.warning(f"Unsupported video format: {extension}")
                    return False

            return True

        except Exception as e:
            logging.error(f"Error validating video file: {e}")
            return False

    async def process_safety_and_tagging(
        self, circo_post: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Stage 1: Safety Check + Video Tagging

        This method handles video processing and delegates AI analysis to the AI service
        """
        start_time = time.time()
        job_id = circo_post.get("jobId", "unknown")

        try:
            video_files = self.extract_video_files(circo_post)

            if not video_files:
                logging.warning(f"No video files found for job ID: {job_id}")
                return {
                    "jobId": job_id,
                    "safety_check": {
                        "contentFlag": "BLOCK_VIOLATION",
                        "reason": "No video files found",
                    },
                    "tags": [],
                    "aiContext": "No video content available for analysis",
                }

            # Process the first video file (primary video)
            primary_video = video_files[0]
            video_url = primary_video.get("original") or primary_video.get(
                "cachedOriginal"
            )

            if not video_url:
                logging.error(f"No valid video URL for job ID: {job_id}")
                return {
                    "jobId": job_id,
                    "safety_check": {
                        "contentFlag": "BLOCK_VIOLATION",
                        "reason": "No valid video URL found",
                    },
                    "tags": [],
                    "aiContext": "Video URL not accessible",
                }

            # Download and process video for analysis
            processed_video_path = await self.download_and_process_video(
                video_url, job_id
            )

            if not processed_video_path:
                return {
                    "jobId": job_id,
                    "safety_check": {
                        "contentFlag": "BLOCK_VIOLATION",
                        "reason": "Video processing failed",
                    },
                    "tags": [],
                    "aiContext": "Video could not be processed for analysis",
                }

            # Delegate AI analysis to the AI service
            analysis_result = await self.ai_service.analyze_video_safety_and_tags(
                processed_video_path, circo_post
            )

            # Add processing time metadata
            processing_time = time.time() - start_time
            if "analysis_metadata" in analysis_result:
                analysis_result["analysis_metadata"][
                    "processing_time"
                ] = processing_time

            # Clean up processed video
            self.cleanup_files([processed_video_path])

            # Send Slack notification via AI service
            await self.ai_service.send_safety_notification(
                analysis_result,
                self._extract_video_info_from_files(video_files),
                circo_post,
            )

            return analysis_result

        except Exception as e:
            logging.error(f"Error in safety and tagging processing: {e}")
            return {
                "jobId": job_id,
                "safety_check": {
                    "contentFlag": "BLOCK_VIOLATION",
                    "reason": f"Processing error: {str(e)}",
                },
                "tags": [],
                "aiContext": f"Error during analysis: {str(e)}",
            }

    async def download_and_process_video(
        self, video_url: str, job_id: str
    ) -> Optional[str]:
        """
        Download and compress video for analysis

        Args:
            video_url: URL of the video to process
            job_id: Job identifier for file naming

        Returns:
            Path to processed video file or None if failed
        """
        try:
            output_path = os.path.join(self.output_dir, f"{job_id}_processed.mp4")

            # 🔥 KEY CHANGE: Convert to presigned URL before ffmpeg call
            accessible_url = self.video_analyzer._get_presigned_url(video_url)

            logging.info(accessible_url)

            # Use FFmpeg to download and compress video
            ffmpeg_cmd = (
                ffmpeg.input(accessible_url)  # Use presigned URL here
                .output(
                    output_path,
                    vf=f"scale={self.ffmpeg_quality['scale']},fps={self.ffmpeg_quality['fps']}",
                    video_bitrate=self.ffmpeg_quality["video_bitrate"],
                    audio_bitrate=self.ffmpeg_quality["audio_bitrate"],
                    vcodec="libx265",
                    pix_fmt="yuv420p",
                )
                .overwrite_output()
            )

            # Run with timeout
            ffmpeg_cmd.run(quiet=True)

            # Validate output file
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logging.info(f"Video processed successfully: {output_path}")
                return output_path
            else:
                logging.error(
                    f"Processed video file is empty or missing: {output_path}"
                )
                return None

        except ffmpeg.Error as e:
            logging.error(f"FFmpeg error processing video {video_url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error downloading/processing video {video_url}: {e}")
            return None

    async def process_quality_and_description(
        self,
        circo_post: Dict[str, Any],
        ai_context: Optional[str] = None,  # Fix: Optional type
    ) -> Optional[Dict[str, Any]]:
        """
        Stage 2: Quality Analysis and Description Analysis

        Args:
            circo_post: CircoPost data
            ai_context: AI context from Stage 1 (safety analysis)

        Returns:
            Dict containing quality analysis and description analysis results
        """
        try:
            job_id = circo_post.get("jobId", "unknown")
            video_files = self.extract_video_files(circo_post)

            if not video_files:
                return {
                    "jobId": job_id,
                    "quality_analysis": {"error": "No video files found"},
                    "description_analysis": {"error": "No video files found"},
                }

            primary_video = video_files[0]
            video_url = primary_video.get("original") or primary_video.get(
                "cachedOriginal"
            )

            # Fix: Check if video_url is not None before passing to analyze_video_quality
            if not video_url:
                return {
                    "jobId": job_id,
                    "quality_analysis": {"error": "No video URL found"},
                    "description_analysis": {"error": "No video URL found"},
                }

            # Quality Analysis
            quality_result = await self.analyze_video_quality(video_url)

            # Description Analysis - use AI context from Stage 1
            user_title = circo_post.get("secondaryCaption", "")
            user_caption = circo_post.get("primaryCaption", "")
            total_description = f"{user_title}\n{user_caption}".strip()
            if ai_context:
                description_result = (
                    await self.ai_service.analyze_description_alignment(
                        total_description, ai_context
                    )
                )
            else:
                logging.warning("No AI context provided for description analysis")
                description_result = {
                    "alignmentScore": 0,
                    "alignmentLevel": "POOR",
                    "justification": "No AI context available for comparison",
                    "suggestion": "AI context is required for accurate description analysis",
                }

            return {
                "jobId": job_id,
                "quality_analysis": quality_result,
                "description_analysis": description_result,
                "video_info": self._extract_video_info_from_files(video_files),
            }

        except Exception as e:
            logging.error(f"Error in quality and description processing: {e}")
            return {
                "jobId": circo_post.get("jobId", "unknown"),
                "quality_analysis": {"error": str(e)},
                "description_analysis": {"error": str(e)},
            }

    async def analyze_video_quality(self, video_url: str) -> Dict[str, Any]:
        """
        Analyze video quality using S3VideoAnalyzer

        Args:
            video_url: URL of the video to analyze

        Returns:
            Dict containing comprehensive quality analysis
        """
        try:
            # Get detailed video information using the analyzer
            detailed_info = self.video_analyzer.get_detailed_info(video_url)

            if not detailed_info:
                return {
                    "quality_score": 0,
                    "quality_level": "POOR",
                    "error": "Could not analyze video",
                    "timestamp": int(time.time()),
                }

            video_info = detailed_info.get("video", {})
            audio_analysis = detailed_info.get("audio_analysis", {})
            file_info = detailed_info.get("file_info", {})
            quality_assessment = detailed_info.get("quality_assessment", {})

            # Calculate quality score based on multiple factors
            quality_score = self.calculate_quality_score(
                video_info, audio_analysis, file_info
            )
            quality_level = self.get_quality_level(quality_score)

            # Comprehensive quality analysis result
            result = {
                "quality_score": quality_score,
                "quality_level": quality_level,
                "resolution": f"{video_info.get('width', 0)}x{video_info.get('height', 0)}",
                "quality_rating": video_info.get("quality_rating", "Unknown"),
                "fps": video_info.get("fps", 0),
                "has_audio": audio_analysis.get("has_audio", False),
                "orientation": video_info.get("orientation", "unknown"),
                "codec": video_info.get("codec", "unknown"),
                "bitrate": video_info.get("bit_rate", 0),
                "file_size_mb": round(
                    file_info.get("size_bytes", 0) / (1024 * 1024), 2
                ),
                "duration": file_info.get("duration", 0),
                "aspect_ratio": video_info.get("aspect_ratio", 0),
                "pixel_format": video_info.get("pixel_format", "unknown"),
                "overall_assessment": quality_assessment,
                "meets_minimum_standards": self._check_minimum_standards(
                    quality_score, video_info
                ),
                "timestamp": int(time.time()),
            }

            # Add audio details if available
            if audio_analysis.get("has_audio") and isinstance(
                audio_analysis.get("audio_details"), dict
            ):
                audio_details = audio_analysis["audio_details"]
                result["audio_details"] = {
                    "codec": audio_details.get("codec", "unknown"),
                    "channels": audio_details.get("channels", 0),
                    "sample_rate": audio_details.get("sample_rate", 0),
                    "bitrate_kbps": audio_details.get("bitrate_kbps", 0),
                }

            return result

        except Exception as e:
            logging.error(f"Error in quality analysis: {e}")
            return {
                "quality_score": 0,
                "quality_level": "POOR",
                "error": str(e),
                "timestamp": int(time.time()),
            }

    def calculate_quality_score(
        self,
        video_info: Dict[str, Any],
        audio_analysis: Dict[str, Any],
        file_info: Dict[str, Any],
    ) -> int:
        """
        Calculate overall quality score (0-100) based on multiple factors

        Args:
            video_info: Video stream information
            audio_analysis: Audio analysis results
            file_info: File metadata

        Returns:
            Quality score from 0-100
        """
        score = 0

        # Resolution scoring (35 points)
        quality_rating = video_info.get("quality_rating", "Unknown")
        resolution_scores = {
            "4K": 35,
            "1440p": 30,
            "1080p": 25,
            "720p": 20,
            "480p": 12,
            "360p": 8,
            "240p": 4,
            "144p": 1,
        }
        score += resolution_scores.get(quality_rating, 0)

        # FPS scoring (20 points)
        fps = video_info.get("fps", 0)
        if fps >= 60:
            score += 20
        elif fps >= 30:
            score += 16
        elif fps >= 24:
            score += 12
        elif fps >= 15:
            score += 8
        elif fps >= 10:
            score += 4

        # Audio scoring (20 points)
        if audio_analysis.get("has_audio", False):
            score += 12
            audio_details = audio_analysis.get("audio_details", {})
            if isinstance(audio_details, dict):
                channels = audio_details.get("channels", 0)
                sample_rate = audio_details.get("sample_rate", 0)
                if channels >= 2:
                    score += 4
                if sample_rate >= 44100:
                    score += 4

        # Codec efficiency (15 points)
        codec = video_info.get("codec", "").lower()
        if "h265" in codec or "hevc" in codec:
            score += 15
        elif "h264" in codec:
            score += 12
        elif "vp9" in codec:
            score += 10
        elif codec:
            score += 5

        # Bitrate optimization (10 points)
        bitrate = video_info.get("bit_rate", 0)
        width = video_info.get("width", 0)
        height = video_info.get("height", 0)
        if width > 0 and height > 0 and bitrate > 0:
            pixels = width * height
            bitrate_per_pixel = bitrate / pixels
            # Optimal bitrate range depends on resolution
            if quality_rating in ["4K", "1440p"]:
                optimal_range = (0.2, 0.8)
            elif quality_rating in ["1080p", "720p"]:
                optimal_range = (0.1, 0.4)
            else:
                optimal_range = (0.05, 0.2)

            if optimal_range[0] <= bitrate_per_pixel <= optimal_range[1]:
                score += 10
            elif bitrate_per_pixel <= optimal_range[1] * 1.5:
                score += 6
            else:
                score += 2

        return min(score, 100)

    def get_quality_level(self, score: int) -> str:
        """Convert quality score to descriptive level"""
        if score >= settings.EXCELLENT_ALIGNMENT_SCORE:  # 90+
            return "EXCELLENT"
        elif score >= 65:
            return "GOOD"
        elif score >= settings.MIN_QUALITY_SCORE:  # 45+
            return "FAIR"
        else:
            return "POOR"

    def _check_minimum_standards(
        self, quality_score: int, video_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if video meets minimum quality standards"""
        meets_standards = True
        issues = []

        # Check quality score
        if quality_score < settings.MIN_QUALITY_SCORE:
            meets_standards = False
            issues.append(
                f"Quality score {quality_score} below minimum {settings.MIN_QUALITY_SCORE}"
            )

        # Check resolution
        width = video_info.get("width", 0)
        height = video_info.get("height", 0)
        if (
            width < settings.MIN_RESOLUTION_WIDTH
            or height < settings.MIN_RESOLUTION_HEIGHT
        ):
            meets_standards = False
            issues.append(
                f"Resolution {width}x{height} below minimum {settings.MIN_RESOLUTION_WIDTH}x{settings.MIN_RESOLUTION_HEIGHT}"
            )

        # Check FPS
        fps = video_info.get("fps", 0)
        if fps < settings.MIN_FPS:
            meets_standards = False
            issues.append(f"FPS {fps} below minimum {settings.MIN_FPS}")

        return {
            "meets_standards": meets_standards,
            "issues": issues,
            "score": quality_score,
        }

    def _extract_video_info_from_files(
        self, video_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract video information from video files list"""
        if not video_files:
            return {"name": "unknown", "url": "unknown", "id": "unknown"}

        primary_video = video_files[0]
        return {
            "name": primary_video.get("name", "unknown"),
            "url": primary_video.get("original")
            or primary_video.get("cachedOriginal", "unknown"),
            "id": primary_video.get("id", "unknown"),
        }

    def cleanup_files(self, files: List[str]):
        """Clean up temporary files"""
        if not settings.CLEANUP_TEMP_FILES:
            logging.info("File cleanup disabled, skipping cleanup")
            return

        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logging.error(f"Error cleaning up file {file_path}: {e}")

    async def get_video_thumbnail_info(self, video_url: str) -> Dict[str, Any]:
        """Get thumbnail extraction information for a video"""
        try:
            return self.video_analyzer.get_video_thumbnail_info(video_url)
        except Exception as e:
            logging.error(f"Error getting thumbnail info: {e}")
            return {"error": str(e)}

    async def validate_video_accessibility(self, video_url: str) -> Dict[str, Any]:
        """Validate if video URL is accessible and processable"""
        try:
            validation_result = self.video_analyzer.validate_video_file(video_url)
            return validation_result
        except Exception as e:
            logging.error(f"Error validating video accessibility: {e}")
            return {"is_valid": False, "error": str(e)}

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and configuration"""
        return {
            "configuration": {
                "max_video_size_mb": settings.MAX_VIDEO_SIZE_MB,
                "max_duration_seconds": self.max_duration,
                "supported_formats": self.supported_formats,
                "ffmpeg_quality_preset": settings.VIDEO_COMPRESSION_QUALITY,
                "min_quality_score": settings.MIN_QUALITY_SCORE,
                "min_alignment_score": settings.MIN_ALIGNMENT_SCORE,
            },
            "directories": {
                "output_dir": self.output_dir,
                "temp_dir": self.temp_dir,
                "output_exists": os.path.exists(self.output_dir),
                "temp_exists": os.path.exists(self.temp_dir),
            },
            "features": {
                "cleanup_enabled": settings.CLEANUP_TEMP_FILES,
                "quality_analysis_enabled": settings.ENABLE_QUALITY_ANALYSIS,
                "description_analysis_enabled": settings.ENABLE_DESCRIPTION_ANALYSIS,
                "slack_notifications_enabled": settings.ENABLE_SLACK_NOTIFICATIONS,
            },
        }
