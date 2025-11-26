# Audio Transcription Service

AI-powered audio transcription using Google Gemini 2.5 Flash. Perfect for sermons, podcasts, meetings, and lectures.

## ✨ Features

- 🎤 **Audio Transcription** - Gemini 2.5 Flash AI
- 📁 **Google Drive** - Direct download from public folders (no auth!)
- ⏭️ **Smart Skip** - Auto-skip already transcribed files
- 📊 **Usage Tracking** - Monitor costs and API usage
- 🎯 **Speaker Detection** - Automatic speaker identification
- 📝 **Clean Output** - Text ready for Google Docs

## 🚀 Quick Deploy (5 Minutes)

### Option 1: Railway (Easiest!)

1. Get API key: https://makersuite.google.com/app/apikey
2. Deploy: [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)
3. Add env var: `GEMINI_KEY=your_api_key`
4. Done! ✅

### Option 2: Docker

```bash
git clone <repo>
cd audio_tagging_service
echo "GEMINI_KEY=your_api_key" > .env
docker-compose up -d
```

## 📖 Usage

### Transcribe Audio

```bash
curl -X POST "https://your-api.com/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"google_drive_link": "https://drive.google.com/drive/folders/YOUR_ID"}'
```

### Check Usage

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

Required env var:
```env
GEMINI_KEY=your_gemini_api_key
```

Optional:
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

## 📝 Output

```
transcriptions/job-id/
├── audio1_transcription.json  # With timestamps
├── audio1_transcript.txt      # Clean text
└── combined_transcript.txt    # All merged
```

## 🔍 Troubleshooting

### "GEMINI_KEY is required"
Add environment variable in your deployment platform.

### "No audio files found"
1. Make Drive folder public
2. Check file formats (MP3, WAV, M4A, etc.)

### Deployment failing?
Check [QUICK_DEPLOY.md](QUICK_DEPLOY.md) for platform-specific guides.

## 📖 Documentation

- [Quick Deploy Guide](QUICK_DEPLOY.md) - Deployment instructions
- [Quick Start Guide](QUICK_START.md) - Setup and usage
- [Changelog](CHANGELOG.md) - Version history
- API Docs: `/docs` endpoint

## 🎯 Smart Features

**Smart Skip:** Already transcribed files are automatically skipped on re-runs

**Clean Transcripts:** No timestamps in text output - just clean, readable content

**Usage Monitoring:** Track API usage with automatic warnings at 50%, 75%, 90%

**Cost Tracking:** Monitor daily burn rate and monthly estimates

## 🤝 Support

- **Issues:** GitHub Issues
- **API Docs:** `https://your-api.com/docs`
- **Usage Stats:** `https://your-api.com/usage`

---

**Get started in 5 minutes!** 🚀
