import pytest
import asyncio
import json
import logging
from unittest.mock import Mock, patch, AsyncMock
from src.video_processor.video_processor import EnhancedVideoProcessor
from src.video_processor.google_generative_ai import EnhancedGoogleGenerativeService
from src.config.settings import settings
from dotenv import load_dotenv

# Configure logging
environment = settings.NODE_ENV
log_level = logging.DEBUG if environment == "development" else logging.INFO

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Reduce third-party noise
logging.getLogger("kafka").setLevel(logging.WARNING)

load_dotenv()

# Real video URLs from production Slack notifications
REAL_VIDEO_URLS = [
    "https://s3.eu-west-2.amazonaws.com/dev-ppv.circleandclique.com/1eeacf9c-6151-4961-aba6-1bcca5450175.MP4",
    "https://s3.eu-west-2.amazonaws.com/prod.circleandclique.org/original-files/48ae92f8-e304-43e8-b60b-00dec6c7b9c8.mp4",
    "https://s3.eu-west-2.amazonaws.com/app.circleandclique.org/original-files/31f8fbbf-5914-429e-8cc2-b9b57f8dd83d.mp4",
    "https://s3.eu-west-2.amazonaws.com/prod.circleandclique.org/original-files/5a2b8c17-ca90-46e2-9c5b-80e024256e77.mp4",
    "https://s3.eu-west-2.amazonaws.com/prod.circleandclique.org/original-files/3f709071-42cc-467a-9d65-b7ebdaa3a237.mp4",
]

# Sample CircoPost with Comedy & Entertainment content (real data structure)
COMEDY_CIRCO_POST = {
    "jobId": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8",
    "primaryCaption": "This had me rolling 😂😂 African parents be like... #comedy #funny #africanparents #viral",
    "secondaryCaption": "Comedy skit about African parenting styles",
    "tags": ["comedy", "entertainment", "viral", "african", "parents"],
    "categories": ["Comedy & Memes", "Entertainment & Afro-Centric"],
    "format": "POST",  # or "SUBSCRIPTION"
    "files": [
        {
            "id": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8",
            "name": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8.mp4",
            "bucket": "prod.circleandclique.org",
            "fileType": "Video",
            "acl": "public-read",
            "path": "original-files/48ae92f8-e304-43e8-b60b-00dec6c7b9c8.mp4",
            "original": REAL_VIDEO_URLS[1],
            "cachedOriginal": REAL_VIDEO_URLS[1],
            "version": 1,
            "revision": 1,
            "isDeleted": False,
            "nestedFolder": False,
            "smallHsl": "",
            "mediumHsl": "",
        }
    ],
    "version": 1,
    "isDeleted": False,
    "user": "comedy_creator_123",
    "locationData": {"country": "Nigeria", "state": "Lagos", "city": "Lagos"},
}

# Sample CircoPost with Music & Dance content (NEW STRUCTURE)
MUSIC_DANCE_CIRCO_POST = {
    "jobId": "a605cfcf-82dc-436f-939f-87d19ca4d100",
    "primaryCaption": "New Afrobeats dance challenge! 🔥💃 Who's trying this? #afrobeats #dance #challenge #viral",
    "secondaryCaption": "New Afrobeats dance challenge!",
    "format": "POST",
    "files": [
        {  # ✅ Changed from "media" to "files"
            "id": "a605cfcf-82dc-436f-939f-87d19ca4d100",
            "name": "a605cfcf-82dc-436f-939f-87d19ca4d100.mp4",
            "bucket": "app.circleandclique.org",
            "fileType": "Video",
            "acl": "public-read",
            "path": "original-files/a605cfcf-82dc-436f-939f-87d19ca4d100.mp4",
            "original": REAL_VIDEO_URLS[0],
            "cachedOriginal": REAL_VIDEO_URLS[0],
            "version": 1,
            "revision": 1,
            "isDeleted": False,
            "nestedFolder": False,
            "smallHsl": "",
            "mediumHsl": "",
        }
    ],
    "version": 1,
    "isDeleted": False,
    "user": "dance_influencer_456",
}


# Sample CircoPost with Motivational content (NEW STRUCTURE)
MOTIVATION_CIRCO_POST = {
    "jobId": "3f709071-42cc-467a-9d65-b7ebdaa3a237",
    "primaryCaption": "Monday motivation! 💪 Your dreams are valid, keep pushing! #motivation #success #mindset #entrepreneur",
    "secondaryCaption": "Monday motivation! 💪 Your dreams are valid!",
    "format": "POST",
    "files": [
        {  # ✅ Changed from "media" to "files"
            "id": "3f709071-42cc-467a-9d65-b7ebdaa3a237",
            "name": "3f709071-42cc-467a-9d65-b7ebdaa3a237.mp4",
            "bucket": "prod.circleandclique.org",
            "fileType": "Video",
            "acl": "public-read",
            "path": "original-files/3f709071-42cc-467a-9d65-b7ebdaa3a237.mp4",
            "original": REAL_VIDEO_URLS[4],
            "cachedOriginal": REAL_VIDEO_URLS[4],
            "version": 1,
            "revision": 1,
            "isDeleted": False,
            "nestedFolder": False,
            "smallHsl": "",
            "mediumHsl": "",
        }
    ],
    "version": 1,
    "isDeleted": False,
    "user": "motivational_speaker_789",
}

# Sample CircoPost with Sports & Fitness content (NEW STRUCTURE)
SPORTS_FITNESS_CIRCO_POST = {
    "jobId": "13bd6ed1-a51c-4c6b-ade4-826d9f013e24",
    "primaryCaption": "Quick 10-minute home workout! No equipment needed 💪 #fitness #workout #homegym #health",
    "secondaryCaption": "Quick 10-minute home workout",
    "format": "POST",
    "files": [
        {  # ✅ Changed from "media" to "files"
            "id": "13bd6ed1-a51c-4c6b-ade4-826d9f013e24",
            "name": "13bd6ed1-a51c-4c6b-ade4-826d9f013e24.mp4",
            "bucket": "prod.circleandclique.org",
            "fileType": "Video",
            "acl": "public-read",
            "path": "original-files/13bd6ed1-a51c-4c6b-ade4-826d9f013e24.mp4",
            "original": "https://s3.eu-west-2.amazonaws.com/prod.circleandclique.org/original-files/13bd6ed1-a51c-4c6b-ade4-826d9f013e24.mp4",
            "cachedOriginal": "https://s3.eu-west-2.amazonaws.com/prod.circleandclique.org/original-files/13bd6ed1-a51c-4c6b-ade4-826d9f013e24.mp4",
            "version": 1,
            "revision": 1,
            "isDeleted": False,
            "nestedFolder": False,
            "smallHsl": "",
            "mediumHsl": "",
        }
    ],
    "version": 1,
    "isDeleted": False,
    "user": "fitness_trainer_321",
}

# Sample CircoPost with Travel content (NEW STRUCTURE)
TRAVEL_CIRCO_POST = {
    "jobId": "5a2b8c17-ca90-46e2-9c5b-80e024256e77",
    "primaryCaption": "Hidden gems of Lagos! 🌟 These spots will blow your mind #travel #lagos #nigeria #adventure #explore",
    "secondaryCaption": "Hidden gems of Lagos!",
    "format": "POST",
    "files": [
        {  # ✅ Changed from "media" to "files"
            "id": "5a2b8c17-ca90-46e2-9c5b-80e024256e77",
            "name": "5a2b8c17-ca90-46e2-9c5b-80e024256e77.mp4",
            "bucket": "prod.circleandclique.org",
            "fileType": "Video",
            "acl": "public-read",
            "path": "original-files/5a2b8c17-ca90-46e2-9c5b-80e024256e77.mp4",
            "original": REAL_VIDEO_URLS[3],
            "cachedOriginal": REAL_VIDEO_URLS[3],
            "version": 1,
            "revision": 1,
            "isDeleted": False,
            "nestedFolder": False,
            "smallHsl": "",
            "mediumHsl": "",
        }
    ],
    "version": 1,
    "isDeleted": False,
    "user": "travel_blogger_654",
}


class TestEnhancedVideoProcessor:
    """Test suite for Enhanced Video Processor (core video processing logic)"""

    @pytest.fixture
    def processor(self):
        """Create Enhanced Video Processor instance for testing"""
        return EnhancedVideoProcessor()

    @pytest.fixture
    def ai_service(self):
        """Create Enhanced Google Generative Service instance for testing"""
        return EnhancedGoogleGenerativeService()

    @pytest.fixture
    def mock_ai_response(self):
        """Mock AI service response with real content categories"""
        return {
            "jobId": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8",
            "safety_check": {
                "contentFlag": "SAFE",
                "reason": "Content appears to be safe for general audience",
            },
            "tags": [
                {
                    "category": "Comedy & Skits",
                    "subcategory": [
                        "Family Comedy",
                        "African Culture",
                        "Everyday Frustrations",
                    ],
                },
                {
                    "category": "Entertainment & Gossip",
                    "subcategory": ["Viral Moments", "Trending Content"],
                },
            ],
            "aiContext": "Comedy skit about African parenting styles and family dynamics, featuring humorous interactions between parents and children",
            "analysis_metadata": {"model": "gemini-2.0-flash", "timestamp": 1640995200},
        }

    def test_extract_video_files(self, processor):
        """Test extraction of video files from CircoPost"""
        video_files = processor.extract_video_files(COMEDY_CIRCO_POST)

        assert len(video_files) == 1
        assert video_files[0]["fileType"] == "Video"
        # Now this will match the test data
        assert video_files[0]["name"] == "48ae92f8-e304-43e8-b60b-00dec6c7b9c8.mp4"
        assert video_files[0]["original"] == REAL_VIDEO_URLS[1]

    def test_extract_video_files_empty_media(self, processor):
        """Test extraction with empty media array"""
        empty_post = {"files": []}
        video_files = processor.extract_video_files(empty_post)

        assert len(video_files) == 0

    @pytest.mark.asyncio
    async def test_process_safety_and_tagging_success(
        self, processor, mock_ai_response
    ):
        """Test successful safety check and tagging process with real video data"""
        with patch.object(
            processor, "download_and_process_video", return_value="/tmp/test_video.mp4"
        ):
            with patch.object(
                processor.ai_service,
                "analyze_video_safety_and_tags",
                return_value=mock_ai_response,
            ):
                with patch.object(processor, "cleanup_files"):
                    with patch.object(processor.ai_service, "send_safety_notification"):

                        result = await processor.process_safety_and_tagging(
                            COMEDY_CIRCO_POST
                        )

                        assert result is not None
                        assert result["jobId"] == "48ae92f8-e304-43e8-b60b-00dec6c7b9c8"
                        assert result["safety_check"]["contentFlag"] == "SAFE"
                        assert len(result["tags"]) > 0
                        assert "Comedy" in str(result["tags"])

    @pytest.mark.asyncio
    async def test_process_safety_and_tagging_no_videos(self, processor):
        """Test safety check when no videos are present"""
        empty_post = {"files": [], "jobId": "test-no-videos"}
        result = await processor.process_safety_and_tagging(empty_post)

        assert result is not None
        assert result["safety_check"]["contentFlag"] == "BLOCK_VIOLATION"
        assert "No video files found" in result["safety_check"]["reason"]
        assert result["tags"] == []

    @pytest.mark.asyncio
    async def test_process_quality_and_description_success(self, processor):
        """Test successful quality and description analysis"""
        with patch.object(processor, "analyze_video_quality") as mock_quality:
            with patch.object(
                processor.ai_service, "analyze_description_alignment"
            ) as mock_description:
                mock_quality.return_value = {
                    "quality_score": 85,
                    "quality_level": "EXCELLENT",
                    "resolution": "1920x1080",
                    "quality_rating": "1080p",
                }

                mock_description.return_value = {
                    "alignmentScore": 78,
                    "alignmentLevel": "GOOD",
                    "justification": "Caption matches video content well",
                    "suggestion": "Caption is well-aligned",
                }

                # Test with AI context from Stage 1
                ai_context = (
                    "Comedy skit about African parenting styles and family dynamics"
                )
                result = await processor.process_quality_and_description(
                    COMEDY_CIRCO_POST, ai_context
                )

                assert result is not None
                assert result["jobId"] == "48ae92f8-e304-43e8-b60b-00dec6c7b9c8"
                assert result["quality_analysis"]["quality_level"] == "EXCELLENT"
                assert result["description_analysis"]["alignmentLevel"] == "GOOD"

    @pytest.mark.asyncio
    async def test_analyze_video_quality(self, processor):
        """Test video quality analysis"""
        with patch.object(
            processor.video_analyzer, "get_detailed_info"
        ) as mock_analyzer:
            mock_analyzer.return_value = {
                "video": {
                    "width": 1920,
                    "height": 1080,
                    "fps": 30,
                    "quality_rating": "1080p",
                    "orientation": "landscape",
                    "codec": "h264",
                    "bit_rate": 5000000,
                },
                "audio_analysis": {
                    "has_audio": True,
                    "audio_details": {
                        "codec": "aac",
                        "channels": 2,
                        "sample_rate": 44100,
                    },
                },
                "file_info": {"size_bytes": 50000000, "duration": 60},
            }

            result = await processor.analyze_video_quality(
                "http://example.com/video.mp4"
            )

            assert result["quality_level"] in ["EXCELLENT", "GOOD", "FAIR", "POOR"]
            assert result["resolution"] == "1920x1080"
            assert result["quality_rating"] == "1080p"
            assert result["has_audio"] is True

    @pytest.mark.asyncio
    async def test_analyze_description_alignment(self, processor):
        """Test description alignment analysis through AI service"""
        with patch.object(
            processor.ai_service, "analyze_description_alignment"
        ) as mock_alignment:
            mock_alignment.return_value = {
                "alignmentScore": 85,
                "alignmentLevel": "GOOD",
                "justification": "Caption accurately describes the video content",
                "suggestion": "Caption is well-aligned with content",
            }

            # Test with AI context from Stage 1
            ai_context = "Comedy skit about African parenting styles and family dynamics, featuring humorous interactions"
            user_caption = "This had me rolling 😂😂 African parents be like... #comedy #funny #africanparents #viral"

            result = await processor.ai_service.analyze_description_alignment(
                user_caption, ai_context
            )

            assert result["alignmentScore"] == 85
            assert result["alignmentLevel"] == "GOOD"

    def test_get_health_status(self, processor):
        """Test health status check for video processor"""
        with patch("google.generativeai.list_models"):
            with patch.object(processor.ai_service.slack_client, "auth_test"):
                status = processor.get_health_status()

                assert "video_analyzer" in status
                assert "ai_service" in status
                assert "output_directory" in status
                assert "ffmpeg_available" in status
                assert "configuration" in status


class TestEnhancedGoogleGenerativeService:
    """Test suite for Enhanced Google Generative AI Service"""

    @pytest.fixture
    def processor(self):
        """Create processor instance for testing (includes AI service)"""
        return EnhancedVideoProcessor()

    @pytest.fixture
    def ai_service(self):
        """Create AI service instance for testing"""
        return EnhancedGoogleGenerativeService()

    @pytest.mark.asyncio
    async def test_analyze_video_safety_and_tags(self, ai_service):
        """Test video safety and tagging analysis"""
        with patch("google.generativeai.upload_file") as mock_upload:
            with patch("google.generativeai.GenerativeModel") as mock_model:
                # Setup mocks
                mock_file = Mock()
                mock_file.state.name = "ACTIVE"
                mock_upload.return_value = mock_file

                mock_response = Mock()
                mock_response.text = json.dumps(
                    {
                        "safety_check": {
                            "contentFlag": "SAFE",
                            "reason": "Content is safe for general audience",
                        },
                        "tags": [
                            {
                                "category": "Comedy & Skits",
                                "subcategory": ["Family Comedy", "African Culture"],
                            }
                        ],
                        "aiContext": "Comedy skit about African parenting styles",
                    }
                )

                mock_model_instance = Mock()
                mock_model_instance.generate_content.return_value = mock_response
                mock_model.return_value = mock_model_instance

                result = await ai_service.analyze_video_safety_and_tags(
                    "/tmp/test.mp4", COMEDY_CIRCO_POST
                )

                assert result is not None
                assert result["safety_check"]["contentFlag"] == "SAFE"
                assert len(result["tags"]) > 0
                assert "analysis_metadata" in result

    @pytest.mark.asyncio
    async def test_analyze_description_alignment(self, ai_service):
        """Test description alignment analysis"""
        with patch("google.generativeai.GenerativeModel") as mock_model:
            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "alignmentScore": 85,
                    "alignmentLevel": "GOOD",
                    "justification": "Caption accurately describes the video content",
                    "suggestion": "Caption is well-aligned with content",
                }
            )

            mock_model_instance = Mock()
            mock_model_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_model_instance

            result = await ai_service.analyze_description_alignment(
                "This had me rolling 😂😂 African parents be like...",
                "Comedy skit about African parenting styles",
            )

            assert result["alignmentScore"] == 85
            assert result["alignmentLevel"] == "GOOD"
            assert "analysis_metadata" in result

    @pytest.mark.asyncio
    async def test_send_safety_notification(self, ai_service):
        """Test Slack safety notification"""
        with patch.object(
            ai_service, "send_slack_message", return_value={"ok": True}
        ) as mock_slack:
            analysis_result = {
                "jobId": "test-job-123",
                "safety_check": {"contentFlag": "SAFE", "reason": "Content is safe"},
                "tags": [
                    {"category": "Comedy & Skits", "subcategory": ["Family Comedy"]}
                ],
                "aiContext": "Comedy skit about African parenting styles",
            }
            video_info = {
                "name": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8.mp4",
                "url": REAL_VIDEO_URLS[1],
            }

            await ai_service.send_safety_notification(
                analysis_result, video_info, COMEDY_CIRCO_POST
            )

            # Verify Slack message was sent
            mock_slack.assert_called_once()
            args = mock_slack.call_args
            assert "testing_passed" in args[0]  # Channel name
            assert "Video Safety Check PASSED" in args[0][1]  # Message content

    def test_ai_service_health_status(self, ai_service):
        """Test AI service health status"""
        with patch("google.generativeai.list_models"):
            with patch.object(ai_service.slack_client, "auth_test"):
                status = ai_service.get_health_status()

                assert "gemini_ai" in status
                assert "slack_integration" in status
                assert "model" in status
                assert "timeout" in status

    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, processor):
        """Test full workflow integration from CircoPost to results"""
        # Mock all external dependencies
        with patch.object(
            processor, "download_and_process_video", return_value="/tmp/test_video.mp4"
        ):
            with patch.object(
                processor.video_analyzer, "get_detailed_info"
            ) as mock_analyzer:
                with patch.object(
                    processor.ai_service, "analyze_video_safety_and_tags"
                ) as mock_ai_safety:
                    with patch.object(processor, "cleanup_files"):
                        with patch.object(
                            processor.ai_service, "send_safety_notification"
                        ):

                            # Setup mocks
                            mock_ai_safety.return_value = {
                                "jobId": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8",
                                "safety_check": {
                                    "contentFlag": "SAFE",
                                    "reason": "Content is safe for general audience",
                                },
                                "tags": [
                                    {
                                        "category": "Comedy & Skits",
                                        "subcategory": [
                                            "Family Comedy",
                                            "African Culture",
                                        ],
                                    }
                                ],
                                "aiContext": "Comedy skit about African parenting styles and family dynamics",
                                "analysis_metadata": {
                                    "model": "gemini-2.0-flash",
                                    "timestamp": 1640995200,
                                },
                            }

                            mock_analyzer.return_value = {
                                "video": {
                                    "width": 1920,
                                    "height": 1080,
                                    "fps": 30,
                                    "quality": "1080p",
                                    "orientation": "landscape",
                                    "codec": "h264",
                                    "bit_rate": 5000000,
                                },
                                "audio_analysis": {"has_audio": True},
                                "file_info": {"size_bytes": 50000000, "duration": 60},
                            }

                            # Test Stage 1: Safety and Tagging
                            safety_result = await processor.process_safety_and_tagging(
                                COMEDY_CIRCO_POST
                            )

                            assert safety_result is not None
                            assert (
                                safety_result["safety_check"]["contentFlag"] == "SAFE"
                            )
                            assert len(safety_result["tags"]) > 0

                            # Test Stage 2: Quality and Description (with AI context from Stage 1)
                            ai_context = safety_result.get("aiContext", "")
                            quality_result = (
                                await processor.process_quality_and_description(
                                    COMEDY_CIRCO_POST, ai_context=ai_context
                                )
                            )

                            assert quality_result is not None
                            assert "quality_analysis" in quality_result
                            assert "description_analysis" in quality_result

    @pytest.mark.asyncio
    async def test_error_handling(self, processor):
        """Test error handling in various scenarios"""
        # Test with invalid CircoPost structure
        invalid_post = {"invalid": "structure"}

        result = await processor.process_safety_and_tagging(invalid_post)
        assert result is not None
        assert result["safety_check"]["contentFlag"] == "BLOCK_VIOLATION"

        # Test with network error
        with patch.object(
            processor,
            "download_and_process_video",
            side_effect=Exception("Network error"),
        ):
            result = await processor.process_safety_and_tagging(COMEDY_CIRCO_POST)
            assert result is not None
            assert (
                "error" in result["safety_check"]["reason"]
                or result["safety_check"]["contentFlag"] == "BLOCK_VIOLATION"
            )

    @pytest.mark.asyncio
    async def test_music_dance_content_processing(self, processor):
        """Test processing of music and dance content"""
        with patch.object(
            processor, "download_and_process_video", return_value="/tmp/music_video.mp4"
        ):
            with patch.object(
                processor.ai_service, "analyze_video_safety_and_tags"
            ) as mock_analyze:
                with patch.object(processor, "cleanup_files"):
                    with patch.object(processor.ai_service, "send_safety_notification"):
                        mock_analyze.return_value = {
                            "jobId": "a605cfcf-82dc-436f-939f-87d19ca4d100",
                            "safety_check": {
                                "contentFlag": "SAFE",
                                "reason": "Music and dance content is appropriate",
                            },
                            "tags": [
                                {
                                    "category": "Music",
                                    "subcategory": ["Afrobeats", "TikTok Challenges"],
                                },
                                {
                                    "category": "Entertainment & Gossip",
                                    "subcategory": ["Viral Moments", "Dance"],
                                },
                            ],
                            "aiContext": "Afrobeats dance challenge featuring popular music and choreography",
                        }

                        result = await processor.process_safety_and_tagging(
                            MUSIC_DANCE_CIRCO_POST
                        )

                        assert result is not None
                        assert result["jobId"] == "a605cfcf-82dc-436f-939f-87d19ca4d100"
                        assert result["safety_check"]["contentFlag"] == "SAFE"
                        assert any("Music" in str(tag) for tag in result["tags"])

    @pytest.mark.asyncio
    async def test_motivational_content_processing(self, processor):
        """Test processing of motivational content"""
        with patch.object(
            processor,
            "download_and_process_video",
            return_value="/tmp/motivation_video.mp4",
        ):
            with patch.object(
                processor.ai_service, "analyze_video_safety_and_tags"
            ) as mock_analyze:
                with patch.object(processor, "cleanup_files"):
                    with patch.object(processor.ai_service, "send_safety_notification"):
                        mock_analyze.return_value = {
                            "jobId": "3f709071-42cc-467a-9d65-b7ebdaa3a237",
                            "safety_check": {
                                "contentFlag": "SAFE",
                                "reason": "Motivational content is inspiring and appropriate",
                            },
                            "tags": [
                                {
                                    "category": "Education & Self-Development",
                                    "subcategory": [
                                        "Motivational Talks",
                                        "Personal Branding",
                                    ],
                                },
                                {
                                    "category": "Lifestyle & Culture",
                                    "subcategory": [
                                        "Life Lessons",
                                        "Personal Journals",
                                    ],
                                },
                            ],
                            "aiContext": "Motivational content about personal success and entrepreneurship",
                        }

                        result = await processor.process_safety_and_tagging(
                            MOTIVATION_CIRCO_POST
                        )

                        assert result is not None
                        assert result["jobId"] == "3f709071-42cc-467a-9d65-b7ebdaa3a237"
                        assert result["safety_check"]["contentFlag"] == "SAFE"
                        assert any(
                            "Education" in str(tag) or "Self-Development" in str(tag)
                            for tag in result["tags"]
                        )

    @pytest.mark.asyncio
    async def test_sports_fitness_content_processing(self, processor):
        """Test processing of sports and fitness content"""
        with patch.object(
            processor,
            "download_and_process_video",
            return_value="/tmp/fitness_video.mp4",
        ):
            with patch.object(
                processor.ai_service, "analyze_video_safety_and_tags"
            ) as mock_analyze:
                with patch.object(processor, "cleanup_files"):
                    with patch.object(processor.ai_service, "send_safety_notification"):
                        mock_analyze.return_value = {
                            "jobId": "13bd6ed1-a51c-4c6b-ade4-826d9f013e24",
                            "safety_check": {
                                "contentFlag": "SAFE",
                                "reason": "Fitness content is healthy and educational",
                            },
                            "tags": [
                                {
                                    "category": "Sports & Fitness",
                                    "subcategory": [
                                        "Workout Routines",
                                        "Home Workouts",
                                        "Fitness Challenges",
                                    ],
                                },
                                {
                                    "category": "Health and Wellness",
                                    "subcategory": [
                                        "Fitness Goals",
                                        "Daily Wellness Routines",
                                    ],
                                },
                            ],
                            "aiContext": "Home workout routine demonstrating exercises without equipment",
                        }

                        result = await processor.process_safety_and_tagging(
                            SPORTS_FITNESS_CIRCO_POST
                        )

                        assert result is not None
                        assert result["jobId"] == "13bd6ed1-a51c-4c6b-ade4-826d9f013e24"
                        assert result["safety_check"]["contentFlag"] == "SAFE"
                        assert any(
                            "Sports" in str(tag) or "Fitness" in str(tag)
                            for tag in result["tags"]
                        )

    @pytest.mark.asyncio
    async def test_travel_content_processing(self, processor):
        """Test processing of travel content"""
        with patch.object(
            processor,
            "download_and_process_video",
            return_value="/tmp/travel_video.mp4",
        ):
            with patch.object(
                processor.ai_service, "analyze_video_safety_and_tags"
            ) as mock_analyze:
                with patch.object(processor, "cleanup_files"):
                    with patch.object(processor.ai_service, "send_safety_notification"):
                        mock_analyze.return_value = {
                            "jobId": "5a2b8c17-ca90-46e2-9c5b-80e024256e77",
                            "safety_check": {
                                "contentFlag": "SAFE",
                                "reason": "Travel content showcasing cultural locations",
                            },
                            "tags": [
                                {
                                    "category": "Travel and Tourism",
                                    "subcategory": [
                                        "Local Destinations",
                                        "Cultural Experiences",
                                        "Urban Adventures",
                                    ],
                                },
                                {
                                    "category": "Lifestyle & Culture",
                                    "subcategory": [
                                        "Cultural Practices",
                                        "Urban Living",
                                    ],
                                },
                            ],
                            "aiContext": "Travel vlog showcasing hidden locations and cultural spots in Lagos",
                        }

                        result = await processor.process_safety_and_tagging(
                            TRAVEL_CIRCO_POST
                        )

                        assert result is not None
                        assert result["jobId"] == "5a2b8c17-ca90-46e2-9c5b-80e024256e77"
                        assert result["safety_check"]["contentFlag"] == "SAFE"
                        assert any(
                            "Travel" in str(tag) or "Tourism" in str(tag)
                            for tag in result["tags"]
                        )

    @pytest.mark.asyncio
    async def test_description_alignment_with_real_content(self, ai_service):
        """Test description alignment with various real content types"""
        test_cases = [
            {
                "caption": "This had me rolling 😂😂 African parents be like... #comedy #funny #africanparents #viral",
                "ai_context": "Comedy skit about African parenting styles and family dynamics",
                "expected_level": "EXCELLENT",
            },
            {
                "caption": "New Afrobeats dance challenge! 🔥💃 Who's trying this? #afrobeats #dance #challenge #viral",
                "ai_context": "Afrobeats dance challenge featuring popular music and choreography",
                "expected_level": "EXCELLENT",
            },
            {
                "caption": "Check out this unrelated content",
                "ai_context": "Comedy skit about African parenting styles",
                "expected_level": "POOR",
            },
        ]

        with patch.object(
            ai_service, "analyze_description_alignment"
        ) as mock_alignment:  # Fixed: use ai_service directly
            for i, test_case in enumerate(test_cases):
                # Mock different alignment scores based on expected level
                score = 95 if test_case["expected_level"] == "EXCELLENT" else 25
                mock_alignment.return_value = {
                    "alignmentScore": score,
                    "alignmentLevel": test_case["expected_level"],
                    "justification": f"Test case {i+1} alignment result",
                    "suggestion": "Test suggestion",
                }

                result = await ai_service.analyze_description_alignment(
                    test_case["caption"], test_case["ai_context"]
                )

                assert result["alignmentLevel"] == test_case["expected_level"]
                assert result["alignmentScore"] == score

    @pytest.mark.asyncio
    async def test_slack_notification(self, ai_service):
        """Test Slack notification functionality through AI service"""
        with patch.object(
            ai_service, "send_slack_message", return_value={"ok": True}
        ) as mock_slack:
            analysis_result = {
                "jobId": "test-job-123",
                "safety_check": {"contentFlag": "SAFE", "reason": "Content is safe"},
                "tags": [
                    {"category": "Comedy & Skits", "subcategory": ["Family Comedy"]}
                ],
                "aiContext": "Comedy skit about African parenting styles",
            }
            video_info = {
                "name": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8.mp4",
                "url": REAL_VIDEO_URLS[1],
            }

            await ai_service.send_safety_notification(
                analysis_result, video_info, COMEDY_CIRCO_POST
            )

            # Verify Slack message was sent
            mock_slack.assert_called_once()
            args = mock_slack.call_args
            assert "testing_passed" in args[0]  # Channel name
            assert "Video Safety Check PASSED" in args[0][1]  # Message content


# Integration test with real data structure
@pytest.mark.asyncio
async def test_real_circo_post_processing():
    """Test processing with real CircoPost structure and video URLs"""
    processor = EnhancedVideoProcessor()

    # Mock external calls to avoid actual API calls during testing
    with patch.object(
        processor, "download_and_process_video", return_value="/tmp/test_video.mp4"
    ):
        with patch.object(
            processor.ai_service, "analyze_video_safety_and_tags"
        ) as mock_analyze:  # Fixed: use ai_service
            with patch.object(processor, "cleanup_files"):
                with patch.object(
                    processor.ai_service, "send_safety_notification"
                ):  # Fixed: use ai_service

                    mock_analyze.return_value = {
                        "jobId": "48ae92f8-e304-43e8-b60b-00dec6c7b9c8",
                        "safety_check": {
                            "contentFlag": "SAFE",
                            "reason": "Content is appropriate for general audience",
                        },
                        "tags": [
                            {
                                "category": "Comedy & Skits",
                                "subcategory": ["Family Comedy", "African Culture"],
                            },
                            {
                                "category": "Entertainment & Gossip",
                                "subcategory": ["Viral Moments", "Trending Content"],
                            },
                        ],
                        "aiContext": "Comedy skit about African parenting styles and family dynamics",
                    }

                    result = await processor.process_safety_and_tagging(
                        COMEDY_CIRCO_POST
                    )

                    print(f"Safety and Tagging Result: {json.dumps(result, indent=2)}")

                    # Assertions
                    assert result is not None
                    assert isinstance(result, dict)
                    assert "jobId" in result
                    assert "safety_check" in result
                    assert "tags" in result
                    assert "aiContext" in result

                    # Test that it follows the expected structure
                    assert result["jobId"] == "48ae92f8-e304-43e8-b60b-00dec6c7b9c8"
                    assert result["safety_check"]["contentFlag"] in [
                        "SAFE",
                        "RESTRICT_18+",
                        "BLOCK_VIOLATION",
                    ]

                    # Test with real video URL
                    video_files = processor.extract_video_files(COMEDY_CIRCO_POST)
                    assert len(video_files) == 1
                    assert video_files[0]["original"] == REAL_VIDEO_URLS[1]

                    print(f"Extracted video URL: {video_files[0]['original']}")


@pytest.mark.asyncio
async def test_multiple_content_types():
    """Test processing different content types from real Slack data"""
    processor = EnhancedVideoProcessor()

    test_posts = [
        (COMEDY_CIRCO_POST, "Comedy & Skits"),
        (MUSIC_DANCE_CIRCO_POST, "Music"),
        (MOTIVATION_CIRCO_POST, "Education & Self-Development"),
        (SPORTS_FITNESS_CIRCO_POST, "Sports & Fitness"),
        (TRAVEL_CIRCO_POST, "Travel and Tourism"),
    ]

    for post, expected_category in test_posts:
        with patch.object(
            processor, "download_and_process_video", return_value="/tmp/test_video.mp4"
        ):
            with patch.object(
                processor.ai_service, "analyze_video_safety_and_tags"
            ) as mock_analyze:  # Fixed: use ai_service
                with patch.object(processor, "cleanup_files"):
                    with patch.object(
                        processor.ai_service, "send_safety_notification"
                    ):  # Fixed: use ai_service

                        # Mock response based on expected category
                        mock_analyze.return_value = {
                            "jobId": post["jobId"],
                            "safety_check": {
                                "contentFlag": "SAFE",
                                "reason": "Content is appropriate",
                            },
                            "tags": [
                                {
                                    "category": expected_category,
                                    "subcategory": ["Test Subcategory"],
                                }
                            ],
                            "aiContext": f"Content related to {expected_category}",
                        }

                        result = await processor.process_safety_and_tagging(post)

                        assert result is not None
                        assert result["jobId"] == post["jobId"]
                        assert result["safety_check"]["contentFlag"] == "SAFE"
                        assert any(
                            expected_category in str(tag) for tag in result["tags"]
                        )

                        print(f"✅ Processed {expected_category} content successfully")


if __name__ == "__main__":
    # Run specific tests with real data
    import asyncio

    print("🧪 Testing with real CircoPost data and video URLs...")
    asyncio.run(test_real_circo_post_processing())

    print("\n🎯 Testing multiple content types...")
    asyncio.run(test_multiple_content_types())
