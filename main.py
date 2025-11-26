import asyncio
import logging
import os
import json
import signal
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from typing import Optional, List, Dict

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config.settings import settings
from src.services.google_drive_service import GoogleDriveService
from src.audio_processor.audio_transcription_processor import AudioTranscriptionProcessor
from src.monitoring.health_check import KafkaMonitorService
from src.monitoring.usage_tracker import UsageTracker

# Configure logging
environment = settings.NODE_ENV
LOG_LEVEL = logging.DEBUG if environment == "development" else logging.INFO

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)

# Create handler with formatter
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
root_logger.addHandler(handler)

# Add file handler for production
if environment == "production":
    file_handler = logging.FileHandler("app.log")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

# Reduce third-party noise
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("gunicorn").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Initialize services
monitor = KafkaMonitorService()
drive_service: Optional[GoogleDriveService] = None
usage_tracker: Optional[UsageTracker] = None


class TranscriptionRequest(BaseModel):
    """Request model for transcription"""
    google_drive_link: str
    gemini_api_key: Optional[str] = None  # Optional - can also use global env var
    recursive: bool = True
    max_file_size_mb: Optional[int] = None
    output_dir: Optional[str] = None


class TranscriptionStatus(BaseModel):
    """Response model for transcription status"""
    job_id: str
    status: str
    message: str
    total_files: Optional[int] = None
    processed_files: Optional[int] = None


# Global job tracking
active_jobs: Dict[str, Dict] = {}


def initialize_services():
    """Initialize Google Drive service and usage tracker"""
    global drive_service, usage_tracker

    try:
        # Validate required configuration
        logger.info("Validating configuration...")
        settings.validate_required_fields(require_gemini_key=False)

        if settings.GEMINI_KEY:
            logger.info("✅ Global GEMINI_KEY configured")
        else:
            logger.info("⚠️  No global GEMINI_KEY - users must provide via Authorization header")

        logger.info("✅ Configuration validated")

        # Initialize Google Drive service (no API key needed for public folders!)
        drive_service = GoogleDriveService()
        logger.info("Google Drive service initialized (direct download mode)")

        # Initialize usage tracker
        usage_tracker = UsageTracker(storage_path="./usage_data")
        logger.info("Usage tracker initialized")

    except ValueError as ve:
        # Configuration validation error - give helpful message
        logger.error(f"\n{'='*60}\n⚠️  CONFIGURATION ERROR\n{'='*60}\n{str(ve)}\n{'='*60}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


async def process_transcription_job(
    job_id: str,
    drive_link: str,
    recursive: bool,
    max_file_size_mb: Optional[int],
    output_dir: Optional[str],
    gemini_api_key: str
):
    """Background task to process transcription job"""
    try:
        logger.info(f"Starting transcription job {job_id}")
        active_jobs[job_id]["status"] = "processing"

        # Create audio processor with the provided API key
        job_audio_processor = AudioTranscriptionProcessor(
            gemini_api_key=gemini_api_key,
            model_name=settings.GEMINI_MODEL,
            temp_dir=settings.TEMP_DIR,
            cleanup_temp_files=settings.CLEANUP_TEMP_FILES,
            max_chunk_size_mb=settings.MAX_CHUNK_SIZE_MB
        )

        # Extract folder ID from drive link
        folder_id = drive_service.extract_folder_id(drive_link)

        # Setup download directory
        download_dir = os.path.join(settings.DOWNLOAD_DIR, job_id)
        os.makedirs(download_dir, exist_ok=True)

        # List audio files first (don't download yet)
        logger.info(f"Listing audio files from folder {folder_id}")
        audio_file_list = drive_service.list_audio_files(
            folder_id=folder_id,
            recursive=recursive
        )

        active_jobs[job_id]["total_files"] = len(audio_file_list)
        logger.info(f"Found {len(audio_file_list)} audio files")

        # Process files one by one (gdown already downloaded them all)
        results = []
        for i, audio_file_info in enumerate(audio_file_list, 1):
            try:
                filename = audio_file_info.get('name')
                # gdown already downloaded the file, use the local_path from the list
                local_path = audio_file_info.get('local_path')

                if not local_path or not os.path.exists(local_path):
                    logger.error(f"File not found locally: {filename}")
                    results.append({
                        "file_path": filename,
                        "success": False,
                        "error": "File not downloaded"
                    })
                    continue

                logger.info(f"Processing file {i}/{len(audio_file_list)}: {filename}")
                active_jobs[job_id]["processed_files"] = i - 1

                # Transcribe the file (already downloaded by gdown)
                logger.info(f"🎤 Transcribing: {filename}")
                result = job_audio_processor.transcribe_file(local_path)

                # Store result directly (no file saving needed for API)
                results.append({
                    "file_path": local_path,
                    "success": True,
                    "result": result
                })

                logger.info(f"✅ Completed: {filename}")

            except Exception as file_error:
                logger.error(f"Failed to process {filename}: {file_error}")
                results.append({
                    "file_path": filename,
                    "success": False,
                    "error": str(file_error)
                })

        # Update job status
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful

        active_jobs[job_id].update({
            "status": "completed",
            "processed_files": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        })

        logger.info(
            f"Transcription job {job_id} completed: "
            f"{successful} successful, {failed} failed"
        )

        # Cleanup downloaded files if configured
        if settings.CLEANUP_TEMP_FILES:
            import shutil
            shutil.rmtree(download_dir, ignore_errors=True)
            logger.info(f"Cleaned up downloaded files for job {job_id}")

    except Exception as e:
        logger.error(f"Transcription job {job_id} failed: {e}")
        active_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    logger.info("Starting Audio Transcription Service...")

    try:
        initialize_services()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    logger.info("Shutting down Audio Transcription Service...")


# FastAPI Application
app = FastAPI(
    title="Audio Transcription Service",
    description="Google Drive audio file transcription service using Gemini AI",
    version="3.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        status = {
            "status": "healthy",
            "service": "audio-transcription",
            "version": "3.0.0",
            "environment": environment,
            "services": {
                "google_drive": drive_service is not None,
                "gemini_key_configured": settings.GEMINI_KEY is not None
            },
            "active_jobs": len(active_jobs)
        }

        logger.info(f"Health Check Status: {status}")
        return JSONResponse(status_code=200, content=status)

    except Exception as e:
        logger.error(f"Health Check Failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint"""
    try:
        metrics = {
            "service": "audio-transcription",
            "version": "3.0.0",
            "environment": environment,
            "features": {
                "google_drive_integration": True,
                "audio_transcription": True,
                "gemini_integration": True,
                "batch_processing": True
            },
            "supported_formats": settings.get_supported_audio_formats(),
            "configuration": {
                "max_audio_size_mb": settings.MAX_AUDIO_SIZE_MB,
                "max_chunk_size_mb": settings.MAX_CHUNK_SIZE_MB,
                "cleanup_temp_files": settings.CLEANUP_TEMP_FILES
            }
        }

        return JSONResponse(status_code=200, content=metrics)

    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/transcribe", response_model=TranscriptionStatus)
async def transcribe_audio(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start audio transcription job from Google Drive folder

    **Authentication:**
    Provide your Gemini API key in one of two ways:
    1. In the request body: `"gemini_api_key": "YOUR_KEY"`
    2. As environment variable: `GEMINI_KEY=YOUR_KEY`

    Get your free API key at: https://makersuite.google.com/app/apikey

    Args:
        request: TranscriptionRequest with Google Drive link and API key

    Returns:
        TranscriptionStatus with job ID and status
    """
    # Use API key from request body or fall back to global env var
    gemini_api_key = request.gemini_api_key or settings.GEMINI_KEY

    if not gemini_api_key or len(gemini_api_key) < 10:
        raise HTTPException(
            status_code=401,
            detail="GEMINI_KEY required. Provide 'gemini_api_key' in request body or set as environment variable."
        )

    logger.info(f"Using {'request' if request.gemini_api_key else 'global'} API key")

    if not drive_service:
        raise HTTPException(
            status_code=503,
            detail="Google Drive service not configured"
        )

    try:
        # Generate job ID
        import uuid
        job_id = str(uuid.uuid4())

        # Initialize job tracking
        active_jobs[job_id] = {
            "status": "queued",
            "drive_link": request.google_drive_link,
            "recursive": request.recursive,
            "created_at": asyncio.get_event_loop().time()
        }

        # Start background task
        background_tasks.add_task(
            process_transcription_job,
            job_id=job_id,
            drive_link=request.google_drive_link,
            recursive=request.recursive,
            max_file_size_mb=request.max_file_size_mb,
            output_dir=request.output_dir,
            gemini_api_key=gemini_api_key
        )

        logger.info(f"Transcription job {job_id} queued")

        return TranscriptionStatus(
            job_id=job_id,
            status="queued",
            message="Transcription job started"
        )

    except Exception as e:
        logger.error(f"Failed to start transcription job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transcribe/{job_id}", response_model=TranscriptionStatus)
async def get_transcription_status(job_id: str):
    """
    Get status of transcription job

    Args:
        job_id: Job ID returned from /transcribe endpoint

    Returns:
        TranscriptionStatus with current job status
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    return TranscriptionStatus(
        job_id=job_id,
        status=job.get("status", "unknown"),
        message=f"Job status: {job.get('status', 'unknown')}",
        total_files=job.get("total_files"),
        processed_files=job.get("processed_files")
    )


@app.get("/transcribe/{job_id}/results")
async def get_transcription_results(job_id: str):
    """
    Get detailed results of completed transcription job

    Args:
        job_id: Job ID

    Returns:
        Detailed transcription results
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.get('status')}"
        )

    return JSONResponse(
        status_code=200,
        content={
            "job_id": job_id,
            "status": job.get("status"),
            "total_files": job.get("total_files"),
            "successful": job.get("successful"),
            "failed": job.get("failed"),
            "output_dir": job.get("output_dir"),
            "results": job.get("results", [])
        }
    )


@app.get("/jobs")
async def list_jobs():
    """List all transcription jobs"""
    return JSONResponse(
        status_code=200,
        content={
            "jobs": [
                {
                    "job_id": job_id,
                    "status": job.get("status"),
                    "total_files": job.get("total_files"),
                    "processed_files": job.get("processed_files")
                }
                for job_id, job in active_jobs.items()
            ]
        }
    )


@app.get("/usage")
async def get_usage_stats():
    """
    Get current API usage statistics

    Returns:
        Usage stats including tier, requests, limits, and cost
    """
    if not usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not initialized")

    try:
        stats = usage_tracker.get_usage_stats()
        return JSONResponse(status_code=200, content=stats)
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/usage/burn-rate")
async def get_burn_rate():
    """
    Get current API burn rate and cost estimates

    Returns:
        Burn rate statistics with daily and monthly estimates
    """
    if not usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not initialized")

    try:
        burn_rate = usage_tracker.get_burn_rate()
        return JSONResponse(status_code=200, content=burn_rate)
    except Exception as e:
        logger.error(f"Failed to get burn rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TierRequest(BaseModel):
    """Request model for setting API tier"""
    tier: str  # "free" or "paid"


@app.post("/usage/tier")
async def set_api_tier(request: TierRequest):
    """
    Set API tier (free or paid)

    Args:
        request: TierRequest with tier value

    Returns:
        Updated usage stats
    """
    if not usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not initialized")

    try:
        usage_tracker.set_tier(request.tier)
        stats = usage_tracker.get_usage_stats()
        return JSONResponse(
            status_code=200,
            content={"message": f"Tier set to {request.tier}", "stats": stats}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set tier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/usage/reset")
async def reset_usage_stats():
    """
    Reset usage statistics (use with caution!)

    Returns:
        Confirmation message
    """
    if not usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not initialized")

    try:
        usage_tracker.reset_stats()
        return JSONResponse(
            status_code=200,
            content={"message": "Usage statistics reset successfully"}
        )
    except Exception as e:
        logger.error(f"Failed to reset stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def signal_handler(sig, frame):
    """Signal handler for graceful shutdown"""
    print("Received shutdown signal, stopping Audio Transcription Service...")
    sys.exit(0)


if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        cmd = [
            "gunicorn",
            "main:app",
            "--bind",
            f"{settings.SERVER_HOST}:{settings.PORT}",
            "--workers",
            "1",
            "--timeout",
            "7200",  # 2 hours timeout for long downloads and transcriptions
            "--log-level",
            settings.LOG_LEVEL.lower(),
            "-k",
            "uvicorn.workers.UvicornWorker",
        ]

        subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        print(f"Server startup failed with exit code {e.returncode}: {e}")
        import traceback
        traceback.print_exc()

    except Exception as ex:
        print(f"Unexpected error: {ex}")
        import traceback
        traceback.print_exc()
