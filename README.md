# 🎙️ Audio Transcription Service

> **Transform audio into structured, searchable content with AI-powered transcription**

An open-source REST API service that leverages Google's Gemini 2.5 Flash to transcribe audio files from Google Drive folders into structured JSON with speaker detection, summaries, and key topics.

---

## 🌟 Why This Project Exists

Whether you're archiving sermons, documenting podcasts, transcribing meetings, or making lectures searchable, manually transcribing hours of audio is tedious. This service was built to:

- **Save Time** - Batch process entire Google Drive folders automatically
- **Preserve Knowledge** - Convert ephemeral audio into permanent, searchable text
- **Enable Discovery** - Extract speakers, topics, and summaries using AI
- **Stay Affordable** - Use Google's free tier (1,500 requests/day) or pay-as-you-go
- **Maintain Privacy** - Self-host your own instance; your audio never touches third parties

## 🎯 What It Does

```
Google Drive Folder → Audio Files → AI Transcription → Structured JSON/Text
```

**Input:** A public Google Drive folder with audio files (MP3, WAV, M4A, etc.)

**Output:** Rich transcription data including:
- Full verbatim transcription
- Automatic speaker identification
- AI-generated summary
- Key topics and themes
- Processing metadata
- Language detection

**How:** Simple REST API - send a folder link, get back structured results via API endpoints.

## ✨ Key Features

### 🚀 **Production-Ready API**
- RESTful endpoints with OpenAPI/Swagger docs
- Background job processing
- Real-time status checking
- No file downloads needed - everything via API

### 🔐 **Secure & Multi-Tenant**
- API keys via standard Authorization headers
- Each user brings their own Gemini API key
- No shared credentials or rate limits

### 📁 **Smart Google Drive Integration**
- Direct download from public folders (no OAuth!)
- Recursive folder scanning
- Automatic file type detection
- Works with files without extensions

### 💰 **Cost Management**
- Built-in usage tracking
- Daily rate limit monitoring
- Burn rate calculations
- Automatic warnings at 50%, 75%, 90% usage

### 🎤 **Powered by Gemini 2.5 Flash**
- Latest AI transcription technology
- Speaker diarization
- Contextual summaries
- Multi-language support

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│   FastAPI    │─────▶│ Google      │
│             │      │   REST API   │      │ Drive       │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Gemini     │
                     │  2.5 Flash   │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Structured  │
                     │  JSON/Text   │
                     └──────────────┘
```

**Stack:**
- **Framework:** FastAPI (async Python)
- **AI:** Google Gemini 2.5 Flash
- **Audio Processing:** FFmpeg + pydub
- **File Handling:** gdown (no auth needed!)
- **Deployment:** Docker, Railway, Cloud Run ready

## 🚀 Quick Start

### 5-Minute Setup

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/audio_tagging_service.git
cd audio_tagging_service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Get your Gemini API key (free!)
# Visit: https://makersuite.google.com/app/apikey

# 3. Run the service
export GEMINI_KEY=your_api_key_here
python main.py
```

### Try It Out

```bash
# Make a Google Drive folder public and copy its ID
# Example: https://drive.google.com/drive/folders/YOUR_FOLDER_ID

# Start transcription
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GEMINI_KEY" \
  -d '{"google_drive_link": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID"}'

# Returns: {"job_id": "abc-123", "status": "queued", ...}

# Check results (replace abc-123 with your job_id)
curl http://localhost:8000/transcribe/abc-123/results
```

That's it! 🎉

## 📖 Detailed Usage

### 1. Start Transcription Job

**Option 1: Using Authorization Header (Recommended)**
```bash
curl -X POST "https://your-api.com/transcribe" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GEMINI_API_KEY" \
  -d '{"google_drive_link": "https://drive.google.com/drive/folders/YOUR_ID"}'
```

**Option 2: If GEMINI_KEY set as environment variable**
```bash
curl -X POST "https://your-api.com/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"google_drive_link": "https://drive.google.com/drive/folders/YOUR_ID"}'
```

Response:
```json
{
  "job_id": "abc-123-xyz",
  "status": "queued",
  "message": "Transcription job started"
}
```

### 2. Get Results

```bash
curl "https://your-api.com/transcribe/abc-123-xyz/results"
```

Response:
```json
{
  "job_id": "abc-123-xyz",
  "status": "completed",
  "results": [
    {
      "file_path": "sermon1.mp3",
      "success": true,
      "result": {
        "transcription": "Full text here...",
        "language": "en",
        "speakers": ["Speaker 1", "Speaker 2"],
        "summary": "Summary of content...",
        "key_topics": ["faith", "prayer"],
        "processing_time": 45.2
      }
    }
  ]
}
```

### 3. Check Usage

```bash
curl "https://your-api.com/usage"
```

Response:
```json
{
  "tier": "free",
  "requests_today": 45,
  "daily_limit": 1500,
  "requests_remaining": 1455,
  "warnings": []
}
```

## 💰 Pricing

| Tier | Requests/Day | Cost |
|------|-------------|------|
| **Free** | 1,500 | $0/month |
| **Paid (Small)** | 10,000 | ~$10-20/month |
| **Paid (Medium)** | Unlimited | ~$50-100/month |

**Hosting:** Railway ($5/month) or Google Cloud Run (pay-per-use)

## 🔧 Configuration

**Two ways to provide your Gemini API key:**

1. **Authorization Header (Recommended)** - Pass with each request
   ```bash
   -H "Authorization: Bearer YOUR_API_KEY"
   ```

2. **Environment Variable** - Set once for all requests
   ```env
   GEMINI_KEY=your_gemini_api_key
   ```

Optional settings:
```env
NODE_ENV=production
PORT=8000
MAX_AUDIO_SIZE_MB=200
```

## 📚 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/transcribe` | POST | Start job |
| `/transcribe/{id}` | GET | Check status |
| `/transcribe/{id}/results` | GET | Get results |
| `/usage` | GET | Usage stats |
| `/usage/burn-rate` | GET | Cost estimate |
| `/docs` | GET | API documentation |

## 📚 API Endpoints

Full interactive API documentation available at `/docs` (Swagger UI) when running.

## 🎯 Real-World Use Cases

### 🙏 Religious Organizations
- Archive years of sermon audio into searchable text
- Create study materials from teachings
- Make content accessible to hearing-impaired members

### 🎓 Education
- Transcribe lecture recordings for students
- Create searchable course archives
- Generate study guides from class discussions

### 🎙️ Content Creators
- Convert podcast episodes to blog posts
- Generate show notes automatically
- Create searchable audio libraries

### 💼 Business
- Document meeting discussions
- Create training material transcripts
- Archive company presentations

## 🤝 Contributing

We welcome contributions! This project needs help with:

### 🐛 **Bug Fixes & Improvements**
- Error handling edge cases
- Performance optimizations
- Memory usage improvements

### ✨ **Feature Ideas**
- [ ] Support for Azure/AWS storage (not just Google Drive)
- [ ] Webhook notifications when jobs complete
- [ ] Custom vocabulary/terminology support
- [ ] Multi-language UI
- [ ] Timestamp editing/correction interface
- [ ] Export to SRT/VTT subtitle formats
- [ ] Integration with popular CMS platforms

### 📖 **Documentation**
- Tutorial videos
- Integration examples (Python, JavaScript, etc.)
- Deployment guides for different platforms
- Troubleshooting guides

### 🧪 **Testing**
- Integration tests
- Load testing
- Edge case coverage

### **How to Contribute:**

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** with clear commit messages
4. **Add tests** if applicable
5. **Update documentation** if needed
6. **Submit a pull request**

**First time contributing?** Look for issues tagged `good-first-issue` or `help-wanted`

## 🛠️ Development Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/audio_tagging_service.git
cd audio_tagging_service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your GEMINI_KEY

# Run locally
python main.py
```

Visit `http://localhost:8000/docs` for interactive API documentation.

## 📋 Project Roadmap

- [x] Core transcription functionality
- [x] Google Drive integration
- [x] Speaker detection
- [x] Usage tracking
- [x] API-first design
- [x] Multi-tenant support
- [ ] Webhook notifications
- [ ] Additional storage backends (S3, Azure Blob)
- [ ] Subtitle file export (SRT/VTT)
- [ ] Custom vocabulary support
- [ ] Web UI for non-developers

## 🔍 Troubleshooting

**"GEMINI_KEY is required"**
- Provide via `Authorization: Bearer YOUR_KEY` header or set as environment variable

**"No audio files found"**
- Ensure Google Drive folder is publicly accessible
- Check file formats (MP3, WAV, M4A, AAC, OGG, FLAC, OPUS)
- Files without extensions are assumed to be MP3

**"Permission denied errors"**
- Service uses `/tmp` for temporary storage
- Ensure container/server has write access to `/tmp`

## 📖 Documentation

- [Quick Deploy Guide](QUICK_DEPLOY.md) - Platform-specific deployment
- [Quick Start Guide](QUICK_START.md) - Getting started tutorial
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI
- [Changelog](CHANGELOG.md) - Version history

## 📊 Project Stats

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **License:** MIT (or your chosen license)
- **Status:** Active Development

## 💬 Community & Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/audio_tagging_service/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/audio_tagging_service/discussions)
- **Questions:** Tag your question with `audio-transcription` on Stack Overflow

## 🙏 Acknowledgments

Built with:
- [Google Gemini AI](https://ai.google.dev/) - Transcription engine
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [FFmpeg](https://ffmpeg.org/) - Audio processing
- [gdown](https://github.com/wkentaro/gdown) - Google Drive downloads

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⭐ If you find this project useful, please consider giving it a star on GitHub!**

Made with ❤️ by developers who believe audio content should be accessible and searchable.
