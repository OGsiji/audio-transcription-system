# Audio Transcription Service

A FastAPI-based microservice for transcribing audio files from Google Drive using Google Gemini AI.

## Features

- 🎤 **Audio Transcription**: Transcribe audio files using Google Gemini 2.5 Flash
- 📁 **Google Drive Integration**: Process audio files directly from public Google Drive folders (no authentication needed!)
- 🔄 **Batch Processing**: Automatically process multiple audio files
- 🎯 **Recursive Folder Search**: Scan subfolders for audio files
- ⚡ **Async Processing**: Non-blocking background job processing
- 📊 **Detailed Results**: Speaker identification, summaries, and key topics
- 📝 **Formatted Transcripts**: Clean, readable text files ready for Google Docs (both JSON and TXT output)
- 📄 **Combined Transcripts**: Automatically creates a single combined transcript for all files
- ⏭️ **Smart Skip**: Automatically skips already transcribed files (no re-processing!)
- 🎬 **Audio Chunking**: Automatic splitting of large audio files for processing
- 🧹 **Automatic Cleanup**: Optional cleanup of temporary files

## Supported Audio Formats

- MP3
- WAV
- M4A
- AAC
- OGG
- FLAC
- OPUS

## Prerequisites

- Python 3.11+
- FFmpeg (for audio processing)
- Google Gemini API key (get from https://makersuite.google.com/app/apikey)
- Public Google Drive folder link (no authentication needed!)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd audio_tagging_service
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 4. Configure API Keys

**Simple Setup - Only One Key Needed!**

1. Get your Gemini API key from https://makersuite.google.com/app/apikey
2. Make sure your Google Drive folder is set to "Anyone with the link can view"

Create a `.env` file in the project root:

```env
# ===== REQUIRED =====
GEMINI_KEY=your_gemini_api_key_here

# ===== OPTIONAL =====
NODE_ENV=development
SERVER_HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

That's it! No Google Drive API key, no service accounts, no JSON files, no complicated setup.

**Quick test your setup:**
```bash
python test_setup.py
```

## Running the Service

### Quick Start (Recommended)

```bash
# Use the startup script (handles everything automatically)
./start.sh
```

### Local Development

```bash
python main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --timeout-keep-alive 7200
```

### Docker

```bash
# Build the image
docker build -t audio-transcription-service .

# Run the container
docker run -p 8000:8000 \
  -e GEMINI_KEY=your_api_key \
  -v $(pwd)/transcriptions:/app/transcriptions \
  -v $(pwd)/audio_downloads:/app/audio_downloads \
  audio-transcription-service
```

## API Documentation

Once the service is running, access the interactive API docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Endpoints

#### 1. Health Check
```
GET /
```

Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "audio-transcription",
  "version": "3.0.0",
  "environment": "development",
  "services": {
    "audio_processor": true,
    "google_drive": true
  },
  "active_jobs": 2
}
```

#### 2. Start Transcription Job
```
POST /transcribe
```

Start a new transcription job for a Google Drive folder.

**Request Body:**
```json
{
  "google_drive_link": "https://drive.google.com/drive/folders/1abc123xyz...",
  "recursive": true,
  "max_file_size_mb": 100,
  "output_dir": null
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Transcription job started"
}
```

#### 3. Get Job Status
```
GET /transcribe/{job_id}
```

Check the status of a transcription job.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Job status: processing",
  "total_files": 5,
  "processed_files": 3
}
```

#### 4. Get Job Results
```
GET /transcribe/{job_id}/results
```

Get detailed transcription results for a completed job.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "total_files": 5,
  "successful": 5,
  "failed": 0,
  "output_dir": "./transcriptions/550e8400-e29b-41d4-a716-446655440000",
  "results": [
    {
      "file_path": "./audio_downloads/550e8400.../audio1.mp3",
      "success": true,
      "result": {
        "transcription": "Full transcription text...",
        "language": "en",
        "speakers": ["Speaker 1"],
        "summary": "Brief summary of the audio content",
        "key_topics": ["topic1", "topic2"],
        "timestamps": [
          {"time": "00:00", "text": "Segment text"},
          {"time": "00:30", "text": "Another segment"}
        ],
        "processing_time": 12.5,
        "model": "gemini-2.5-flash",
        "file_name": "audio1.mp3",
        "file_size_mb": 5.2
      }
    }
  ]
}
```

#### 5. List All Jobs
```
GET /jobs
```

List all transcription jobs.

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "total_files": 5,
      "processed_files": 5
    }
  ]
}
```

#### 6. Service Metrics
```
GET /metrics
```

Get service configuration and features.

## Monitoring Jobs

### Using the Monitor Script (Easiest!)

```bash
# Start a job and note the job_id
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"google_drive_link": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID"}'

# Monitor the job with real-time progress
python monitor_job.py <job_id>
```

The monitor script shows:
- Real-time progress bar
- Files completed count
- Current status
- Automatic results display when done
- Commands to view your transcripts

## Usage Example

### Using cURL

```bash
# 1. Start a transcription job
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_link": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID",
    "recursive": true,
    "max_file_size_mb": 100
  }'

# Response: {"job_id": "abc-123", "status": "queued", ...}

# 2. Check job status
curl "http://localhost:8000/transcribe/abc-123"

# 3. Get results when completed
curl "http://localhost:8000/transcribe/abc-123/results"
```

### Using Python

```python
import requests
import time

# Start transcription
response = requests.post(
    "http://localhost:8000/transcribe",
    json={
        "google_drive_link": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID",
        "recursive": True,
        "max_file_size_mb": 100
    }
)
job_id = response.json()["job_id"]
print(f"Job started: {job_id}")

# Poll for status
while True:
    status_response = requests.get(f"http://localhost:8000/transcribe/{job_id}")
    status = status_response.json()["status"]
    print(f"Status: {status}")

    if status == "completed":
        # Get results
        results = requests.get(f"http://localhost:8000/transcribe/{job_id}/results")
        print(results.json())
        break
    elif status == "failed":
        print("Job failed!")
        break

    time.sleep(5)  # Wait 5 seconds before checking again
```

## Output Format

Transcription results are saved in **both JSON and formatted text** in the output directory:

```
transcriptions/
└── job-id/
    ├── audio1_transcription.json       # Raw JSON data
    ├── audio1_transcript.txt           # Clean, readable transcript
    ├── audio2_transcription.json
    ├── audio2_transcript.txt
    ├── audio3_transcription.json
    ├── audio3_transcript.txt
    └── combined_transcript.txt         # All transcripts combined
```

### JSON Files (.json)
Each JSON file contains structured data:
- Full transcription text
- Detected language
- Speaker identification
- Summary
- Key topics
- Timestamped segments
- Processing metadata

### Text Files (.txt)
Clean, formatted transcripts ready for reading or importing into Google Docs:
- Professional header with metadata (filename, date, language, speakers)
- Optional summary section
- Key topics highlighted
- Full transcript with proper paragraph formatting (no timestamps)
- Proper paragraph formatting for readability
- Text wrapped to 80 characters
- **Smart Skip**: Already transcribed files are automatically skipped on re-runs

### Combined Transcript (combined_transcript.txt)
A single document containing all transcripts from the job, perfect for reviewing multiple audio files at once.

### Example Formatted Transcript

Here's what a formatted transcript looks like:

```
================================================================================
AUDIO TRANSCRIPTION
================================================================================

File: sermon_part1.mp3
Date: 2025-11-26 15:30:42
Language: English
Speakers: Speaker 1, Speaker 2
Transcribed by: gemini-2.5-flash
Processing time: 45.23 seconds

--------------------------------------------------------------------------------
SUMMARY
--------------------------------------------------------------------------------

A discussion about spiritual growth and the importance of prayer in daily life,
featuring insights from two speakers sharing their experiences and biblical
references.

--------------------------------------------------------------------------------
KEY TOPICS
--------------------------------------------------------------------------------

• Prayer and meditation
• Spiritual growth
• Biblical teachings
• Community fellowship

================================================================================
FULL TRANSCRIPT
================================================================================

Welcome everyone to today's session. We're going to be discussing the
importance of maintaining a consistent prayer life and how it impacts our
spiritual growth. As we've seen in previous discussions, the foundation of our
faith relies heavily on our connection with God through prayer.

That's absolutely right. I'd like to add that many believers struggle with
consistency, not because they lack desire, but because they haven't established
a structured approach to their prayer time. Let me share some practical steps
that have helped me personally...

--------------------------------------------------------------------------------
End of Transcript
--------------------------------------------------------------------------------
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_KEY` | **Required** | Google Gemini API key (from makersuite.google.com) |
| `NODE_ENV` | development | Environment (development/production) |
| `SERVER_HOST` | 0.0.0.0 | Server bind address |
| `PORT` | 8000 | Server port |
| `MAX_AUDIO_SIZE_MB` | 200 | Maximum audio file size |
| `MAX_AUDIO_DURATION_SECONDS` | 7200 | Maximum audio duration (2 hours) |
| `MAX_CHUNK_SIZE_MB` | 20 | Max chunk size for processing |
| `CLEANUP_TEMP_FILES` | true | Clean up temporary files |
| `TEMP_DIR` | /tmp/audio_processing | Temporary processing directory |
| `DOWNLOAD_DIR` | ./audio_downloads | Downloaded audio directory |
| `OUTPUT_DIR` | ./transcriptions | Transcription output directory |

## Architecture

```
┌─────────────────┐
│   Google Drive  │
│  Public Folder  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Google Drive Service (gdown)      │
│   - Direct download (no auth!)      │
│   - File listing (recursive)        │
│   - Batch download                  │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Audio Transcription Processor     │
│   - Audio conversion                │
│   - Chunking (if needed)            │
│   - Gemini AI transcription         │
│   - Result aggregation              │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Transcript Formatter              │
│   - Clean text formatting           │
│   - Paragraph generation            │
│   - Combined transcript creation    │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Output Files                      │
│   - JSON (structured data)          │
│   - TXT (readable transcripts)      │
│   - Combined transcript             │
└─────────────────────────────────────┘
```

## Project Structure

```
audio_tagging_service/
├── main.py                          # FastAPI application
├── monitor_job.py                   # Job monitoring script
├── start.sh                         # Startup script
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container definition
├── README.md                        # This file
│
├── src/
│   ├── config/
│   │   └── settings.py              # Configuration management
│   ├── services/
│   │   └── google_drive_service.py  # Google Drive integration (gdown)
│   ├── audio_processor/
│   │   ├── audio_transcription_processor.py  # Audio transcription
│   │   └── transcript_formatter.py  # Text formatting
│   └── monitoring/
│       └── health_check.py          # Health monitoring
│
├── audio_downloads/                 # Downloaded audio files
├── transcriptions/                  # Transcription output (JSON + TXT)
└── tests/                          # Test suite
```

## Troubleshooting

### Common Issues

**1. Google Drive Download Failed**
- Ensure the folder is set to "Anyone with the link can view"
- Check that the folder link is correct (should contain `/folders/`)
- Verify the folder contains audio files (supported formats only)
- Check internet connection

**2. FFmpeg Not Found**
- Install FFmpeg using your package manager
- Verify installation: `ffmpeg -version`
- On macOS: `brew install ffmpeg`
- On Ubuntu: `sudo apt-get install ffmpeg`

**3. Worker Timeout**
- Large files may take time to download and process
- Monitor progress using: `python monitor_job.py <job_id>`
- The service timeout is set to 7200 seconds (2 hours)
- Check server logs for detailed progress

**4. Large Audio Files Failing**
- Files are automatically chunked if they exceed `MAX_CHUNK_SIZE_MB` (20MB)
- Increase `MAX_AUDIO_SIZE_MB` if needed (default: 200MB)
- Ensure sufficient disk space in `TEMP_DIR`

**5. Transcription Quality Issues**
- Try different audio formats (convert to MP3 or WAV)
- Check audio quality and clarity
- Reduce background noise if possible
- Verify audio file isn't corrupted

**6. Job Shows 0 Files**
- Verify the Google Drive folder contains audio files (not just subfolders)
- Check that files have supported extensions (.mp3, .wav, .m4a, etc.)
- Try setting `recursive: true` in the request
- Use monitor script to see detailed progress

## Performance Considerations

- **Concurrent Processing**: Limited by `MAX_CONCURRENT_PROCESSING` (default: 5)
- **File Size**: Large files are automatically chunked based on `MAX_CHUNK_SIZE_MB`
- **Memory Usage**: Approximately 2GB per concurrent job
- **API Quotas**: Subject to Google Gemini API rate limits

## Security

- Service runs as non-root user in Docker
- Google Drive credentials are never logged
- Temporary files are automatically cleaned up
- API endpoints can be secured with authentication middleware

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.
