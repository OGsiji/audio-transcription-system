# Dockerfile for Audio Transcription Service
FROM python:3.11-slim

# Set environment variables to improve security and performance
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONFAULTHANDLER=1

# Install system dependencies and create a non-root user
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # FFmpeg for audio processing
    ffmpeg \
    # Cleanup to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy requirements and set proper permissions
COPY --chown=appuser:appuser requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser main.py ./
COPY --chown=appuser:appuser entrypoint.sh ./

RUN chmod +x ./entrypoint.sh

# Create directories for audio downloads and transcriptions
RUN mkdir -p ./audio_downloads ./transcriptions /tmp/audio_processing && \
    chown -R appuser:appuser ./audio_downloads ./transcriptions /tmp/audio_processing

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use entrypoint for more flexible command execution
ENTRYPOINT ["./entrypoint.sh"]
