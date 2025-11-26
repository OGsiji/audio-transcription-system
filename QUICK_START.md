# Quick Start Guide

Get the Audio Transcription Service running in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] FFmpeg installed
- [ ] Google Gemini API key
- [ ] Public Google Drive folder link (no authentication needed!)

## Step 1: Install FFmpeg (if not already installed)

### macOS
```bash
brew install ffmpeg
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### Windows
Download from https://ffmpeg.org/download.html

Verify installation:
```bash
ffmpeg -version
```

## Step 2: Get Your API Key

### Get Gemini API Key
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key

### Prepare Your Google Drive Folder
1. Upload your audio files to Google Drive
2. Right-click the folder → Share → "Anyone with the link can view"
3. Copy the folder link

## Step 3: Configure the Service

```bash
# Clone/navigate to the project
cd audio_tagging_service

# Create .env file
cp .env.example .env

# Edit .env file
nano .env  # or use your favorite editor
```

Add your API key:
```env
# ===== REQUIRED =====
GEMINI_KEY=your_gemini_api_key_here

# ===== OPTIONAL =====
PORT=8000
LOG_LEVEL=INFO
```

That's it! No Google Drive credentials needed for public folders.

## Step 4: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## Step 5: Run the Service

### Option A: Using the startup script (recommended)
```bash
chmod +x start.sh
./start.sh
```

### Option B: Manual start
```bash
python main.py
```

### Option C: Development mode with auto-reload
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Step 6: Test It!

The service is now running at http://localhost:8000

### View API Documentation
Open in your browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Test with cURL

1. **Health Check**
```bash
curl http://localhost:8000/
```

2. **Start Transcription**

First, get your Google Drive folder URL. It looks like:
```
https://drive.google.com/drive/folders/1abc123xyz456def
```

Then run:
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_link": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID",
    "recursive": true,
    "max_file_size_mb": 100
  }'
```

You'll get a response like:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Transcription job started"
}
```

3. **Check Status**
```bash
curl "http://localhost:8000/transcribe/550e8400-e29b-41d4-a716-446655440000"
```

4. **Get Results** (when status is "completed")
```bash
curl "http://localhost:8000/transcribe/550e8400-e29b-41d4-a716-446655440000/results"
```

## Step 7: View Transcriptions

Results are saved in the `transcriptions/` directory:

```bash
# List transcription files
ls transcriptions/<job_id>/

# View formatted transcript (recommended!)
cat transcriptions/<job_id>/combined_transcript.txt

# View individual transcript
cat transcriptions/<job_id>/audio_file_transcript.txt

# View raw JSON data
cat transcriptions/<job_id>/audio_file_transcription.json
```

### Formatted Text Output (.txt)
Clean, readable transcripts perfect for Google Docs:
```
================================================================================
AUDIO TRANSCRIPTION
================================================================================

File: sermon_part1.mp3
Date: 2025-11-26 15:30:42
Language: English
Speakers: Speaker 1
Transcribed by: gemini-2.5-flash

--------------------------------------------------------------------------------
SUMMARY
--------------------------------------------------------------------------------

A discussion about spiritual growth and prayer...

================================================================================
FULL TRANSCRIPT
================================================================================

[00:00]
Welcome to today's session. We're going to be discussing the importance of
maintaining a consistent prayer life...
```

### JSON Output (.json)
Structured data for programmatic access:
```json
{
  "transcription": "Welcome to this podcast episode...",
  "language": "en",
  "speakers": ["Speaker 1", "Speaker 2"],
  "summary": "A discussion about AI and technology",
  "key_topics": ["artificial intelligence", "machine learning"],
  "timestamps": [
    {"time": "00:00", "text": "Welcome to this podcast episode"},
    {"time": "00:15", "text": "Today we're discussing AI"}
  ],
  "processing_time": 12.5,
  "model": "gemini-2.5-flash"
}
```

## Troubleshooting

### Service won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Use a different port
PORT=8080 python main.py
```

### FFmpeg not found
```bash
# Check installation
which ffmpeg

# If not found, install it (see Step 1)
```

### No audio files found
- Check that audio files are in the Drive folder
- Verify the folder is public ("Anyone with the link can view")
- Verify supported formats: MP3, WAV, M4A, AAC, OGG, FLAC, OPUS
- Try with `recursive: true` to scan subfolders
- Check server logs for detailed error messages

## Next Steps

### Add More Audio Files
Just add files to your Google Drive folder and run a new transcription job!

### Process Multiple Folders
Submit multiple jobs:
```bash
# Job 1
curl -X POST "http://localhost:8000/transcribe" -H "Content-Type: application/json" \
  -d '{"google_drive_link": "FOLDER_1_URL", "recursive": true}'

# Job 2
curl -X POST "http://localhost:8000/transcribe" -H "Content-Type: application/json" \
  -d '{"google_drive_link": "FOLDER_2_URL", "recursive": true}'
```

### List All Jobs
```bash
curl "http://localhost:8000/jobs"
```

### Production Deployment
See [README.md](README.md) for Docker deployment instructions.

## Common Use Cases

### 1. Transcribe a Podcast Series
```bash
# Share your podcast folder with the service account
# Then transcribe all episodes
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_link": "YOUR_PODCAST_FOLDER",
    "recursive": true
  }'
```

### 2. Transcribe Meeting Recordings
```bash
# Limit file size to avoid very long recordings
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_link": "YOUR_MEETINGS_FOLDER",
    "recursive": false,
    "max_file_size_mb": 50
  }'
```

### 3. Transcribe Audio Books
```bash
# Process chapter by chapter
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_link": "YOUR_AUDIOBOOK_FOLDER",
    "recursive": true,
    "output_dir": "./transcriptions/audiobook_name"
  }'
```

## Need Help?

- **API Documentation**: http://localhost:8000/docs
- **Full README**: [README.md](README.md)
- **Migration Guide**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Configuration Options**: [.env.example](.env.example)

---

**You're all set!** Start transcribing your audio files with AI-powered accuracy.
