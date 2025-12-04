# Audio Transcription API

Convert audio recordings into structured, searchable text. Built for turning sermon series, podcast episodes, and lecture recordings into publishable books and digital content.

## What This Does

This REST API takes audio files from Google Drive and returns:
- Complete transcriptions with speaker identification
- Summaries and key topics
- Structured JSON output ready for editing and publishing

**Primary use case:** Transform a series of recordings (sermons, lectures, podcasts) into material for books, study guides, or searchable archives.

## Quick Start

### Requirements
- Python 3.12+
- Google Gemini API key ([get one free](https://makersuite.google.com/app/apikey))
- FFmpeg (`brew install ffmpeg` on macOS)

### Installation

```bash
git clone https://github.com/yourusername/audio-transcription-api.git
cd audio-transcription-api

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
export GEMINI_KEY=your_api_key_here

# Run the service
python main.py
```

Visit `http://localhost:8000/docs` to see the API documentation.

### Basic Usage

1. **Upload audio to Google Drive** (make the folder public)
2. **Start transcription:**

```bash
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_link": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID",
    "gemini_api_key": "YOUR_API_KEY"
  }'
```

Returns: `{"job_id": "abc-123", "status": "queued"}`

3. **Check progress:**

```bash
curl http://localhost:8000/transcribe/abc-123
```

4. **Get results when complete:**

```bash
curl http://localhost:8000/transcribe/abc-123/results
```

## Response Format

```json
{
  "job_id": "abc-123",
  "status": "completed",
  "results": [
    {
      "file_path": "sermon-01.mp3",
      "success": true,
      "result": {
        "transcription": "Complete text of the recording...",
        "language": "en",
        "speakers": ["Speaker 1", "Speaker 2"],
        "summary": "Brief summary of the content",
        "key_topics": ["faith", "prayer", "community"],
        "processing_time": 45.2
      }
    }
  ]
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/transcribe` | POST | Start transcription job |
| `/transcribe/{job_id}` | GET | Check job status |
| `/transcribe/{job_id}/results` | GET | Get transcription results |
| `/usage` | GET | API usage statistics |
| `/docs` | GET | Interactive API documentation |

## Supported Audio Formats

MP3, WAV, M4A, AAC, OGG, FLAC, OPUS

Maximum file size: 200MB per file

## Configuration

### Environment Variables

```env
# Required
GEMINI_KEY=your_gemini_api_key

# Optional
PORT=8000
NODE_ENV=production
MAX_AUDIO_SIZE_MB=200
CLEANUP_TEMP_FILES=true
```

### API Key Options

**Option 1:** Include in each request (recommended for multi-user deployments)
```json
{
  "google_drive_link": "...",
  "gemini_api_key": "your_key"
}
```

**Option 2:** Set as environment variable (simpler for single-user)
```bash
export GEMINI_KEY=your_key
```

## Deployment

### Docker

```bash
docker build -t audio-transcription .
docker run -p 8000:8000 -e GEMINI_KEY=your_key audio-transcription
```

### Railway / Render / Fly.io

1. Fork this repository
2. Connect to your deployment platform
3. Set environment variable: `GEMINI_KEY=your_api_key`
4. Deploy

See [QUICK_DEPLOY.md](QUICK_DEPLOY.md) for detailed platform-specific instructions.

## Product Vision

### Current Features
- Batch transcription from Google Drive folders
- Speaker identification
- Content summaries and topic extraction
- Usage tracking and cost monitoring
- Multi-user support (each user brings their own API key)

### Roadmap

**Phase 1: Enhanced Output** (Current)
- [x] Basic transcription with speaker detection
- [x] Summaries and key topics
- [ ] Export to common formats (DOCX, PDF, Markdown)
- [ ] Chapter/section detection for long recordings

**Phase 2: Book Publishing Pipeline**
- [ ] Series organization (group related recordings)
- [ ] Automated chapter generation
- [ ] Editorial workflow (mark sections for editing)
- [ ] Export templates for book formatting
- [ ] Table of contents generation

**Phase 3: Advanced Features**
- [ ] Custom vocabulary support (proper nouns, technical terms)
- [ ] Timestamp linking to original audio
- [ ] Web interface for non-technical users
- [ ] Webhook notifications
- [ ] Additional storage backends (S3, Dropbox)

## Use Cases

### Religious Organizations
Archive sermon series into searchable text. Create study guides and devotional books from years of teachings.

### Educational Content
Convert lecture series into textbooks or course materials. Make audio content accessible to students with hearing impairments.

### Podcast Creators
Generate show notes, blog posts, and books from podcast episodes. Build searchable archives of your content.

### Business & Training
Document meetings, create training manuals from recorded sessions, archive company knowledge.

## Contributing

We welcome contributions! Areas where help is needed:

### Code
- Export formats (DOCX, PDF, Markdown)
- Additional storage backends (S3, Azure, Dropbox)
- Performance optimizations
- Test coverage

### Documentation
- Tutorial videos
- Integration examples
- Translation to other languages

### Testing
- Try with different audio types
- Report bugs and edge cases
- Suggest improvements

**To contribute:**
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with clear commit messages
4. Submit a pull request

Issues tagged `good-first-issue` are great starting points.

## Architecture

Built with:
- **FastAPI** - Modern Python web framework
- **Google Gemini 2.5 Flash** - Transcription and language processing
- **FFmpeg** - Audio file handling
- **gdown** - Google Drive integration (no OAuth required)

The service processes audio files one at a time, uploads them to Google's Gemini API for transcription, and returns structured results via REST endpoints.

## Troubleshooting

**"GEMINI_KEY is required"**
- Provide `gemini_api_key` in request body OR set `GEMINI_KEY` environment variable

**"No audio files found"**
- Ensure Google Drive folder is publicly accessible
- Verify folder contains supported audio formats
- Check folder URL is correct

**"Out of memory" errors**
- Increase MAX_CHUNK_SIZE_MB in settings
- Use smaller audio files
- Deploy with more RAM (upgrade hosting tier)

**Python 3.13 compatibility issues**
- Use Python 3.12: `python3.12 -m venv venv`
- The `audioop` module was removed in Python 3.13

## Costs

**Google Gemini API:**
- Free tier: 1,500 requests/day
- Paid tier: $0.075 per 1M input tokens (~$10-20/month for moderate use)

**Hosting:**
- Railway/Render: ~$5/month
- Google Cloud Run: Pay per use (typically $1-10/month)
- Self-hosted: Free

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Documentation:** [Quick Start Guide](QUICK_START.md) | [Deployment Guide](QUICK_DEPLOY.md)
- **Issues:** [GitHub Issues](https://github.com/yourusername/audio-transcription-api/issues)
- **Questions:** Open a [Discussion](https://github.com/yourusername/audio-transcription-api/discussions)

---

Built for archiving knowledge and making audio content accessible.
