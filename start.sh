#!/bin/bash

# Audio Transcription Service Startup Script

echo "======================================"
echo "Audio Transcription Service"
echo "======================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file using .env.example as a template"
    echo ""
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your credentials"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d "appenv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created: venv/"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "appenv" ]; then
    source appenv/bin/activate
fi

# Install/update dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check FFmpeg installation
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "Warning: FFmpeg is not installed!"
    echo "Please install FFmpeg:"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu: sudo apt-get install ffmpeg"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to exit..."
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p audio_downloads transcriptions /tmp/audio_processing

# Start the service
echo ""
echo "Starting Audio Transcription Service..."
echo "API Documentation: http://localhost:${PORT:-8000}/docs"
echo "Health Check: http://localhost:${PORT:-8000}/"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

# Run with uvicorn for development or gunicorn for production
if [ "${NODE_ENV}" = "production" ]; then
    exec python main.py
else
    # Development mode with longer timeout for large file downloads
    exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --reload --timeout-keep-alive 7200
fi
