# Deployment Guide

Complete guide to deploying the Audio Transcription Service with frontend.

## Table of Contents

1. [Quick Cleanup](#quick-cleanup)
2. [Deployment Options](#deployment-options)
3. [Frontend Architecture](#frontend-architecture)
4. [Usage Tracking & Monitoring](#usage-tracking--monitoring)
5. [Production Deployment](#production-deployment)

---

## Quick Cleanup

Before deploying, clean up unnecessary files:

```bash
# Run cleanup script
./cleanup.sh

# Verify clean structure
ls -la
```

### What Gets Removed:
- ✅ Virtual environments (`appenv/`, `audenv/`, `venv/`)
- ✅ Python cache files (`__pycache__/`, `*.pyc`)
- ✅ Redundant documentation
- ✅ Old CI/CD configs
- ✅ Test data (downloads & transcriptions)

### What Stays:
- ✅ Core application code (`src/`, `main.py`)
- ✅ Essential docs (`README.md`, `QUICK_START.md`)
- ✅ Configuration (`requirements.txt`, `.env.example`)
- ✅ Deployment files (`Dockerfile`, deployment configs)

---

## Deployment Options

### Option 1: Railway.app (Recommended - Easiest!)

**Pros:**
- Free tier available
- Automatic HTTPS
- GitHub integration
- Zero config deployment
- Built-in environment variables

**Steps:**
1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub"
4. Select your repository
5. Add environment variable: `GEMINI_KEY=your_api_key`
6. Deploy!

**Cost:**
- Free: $5 credit/month (enough for testing)
- Starter: $5/month for 500 hours
- Pro: $20/month unlimited

---

### Option 2: Render.com

**Pros:**
- Free tier (with limitations)
- Easy deployment
- Auto-deploy from git

**Steps:**
1. Create account on [render.com](https://render.com)
2. New Web Service → Connect repository
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variable: `GEMINI_KEY`

**Cost:**
- Free: Apps sleep after 15min inactivity
- Starter: $7/month (always on)

---

### Option 3: AWS (EC2 + S3)

**Pros:**
- Full control
- Scalable
- Can use S3 for transcription storage

**Steps:**
1. Launch EC2 instance (t3.small recommended)
2. Install Docker
3. Clone repository
4. Build and run:
```bash
docker build -t audio-transcription-service .
docker run -d -p 8000:8000 \
  -e GEMINI_KEY=your_key \
  -v /data/transcriptions:/app/transcriptions \
  audio-transcription-service
```

**Cost:**
- EC2 t3.small: ~$15/month
- S3 storage: ~$0.023/GB/month

---

### Option 4: Google Cloud Run (Serverless)

**Pros:**
- Pay-per-use (only charged when running)
- Auto-scaling
- Generous free tier

**Steps:**
1. Install gcloud CLI
2. Build and push:
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/audio-transcription
gcloud run deploy --image gcr.io/YOUR_PROJECT/audio-transcription \
  --set-env-vars GEMINI_KEY=your_key
```

**Cost:**
- Free tier: 2 million requests/month
- After: $0.40/million requests

---

### Option 5: DigitalOcean App Platform

**Pros:**
- Simple deployment
- Managed infrastructure
- Good documentation

**Steps:**
1. Create account on [digitalocean.com](https://digitalocean.com)
2. Apps → Create App → GitHub
3. Select repository
4. Add environment variables
5. Deploy

**Cost:**
- Basic: $5/month
- Professional: $12/month

---

## Frontend Architecture

### Recommended Stack

```
┌─────────────────────────────────────┐
│         React Frontend              │
│  - Next.js (recommended) or Vite    │
│  - TailwindCSS for styling          │
│  - Axios for API calls              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│      FastAPI Backend (this app)     │
│  - Audio transcription              │
│  - Usage tracking                   │
│  - Job management                   │
└─────────────────────────────────────┘
```

### Frontend Features

#### 1. **Dashboard Page**
```
┌────────────────────────────────────┐
│  📊 Usage Dashboard                │
├────────────────────────────────────┤
│  Tier: Free / Paid                 │
│  Requests Today: 45 / 1500         │
│  Daily Usage: [██████░░░░] 30%     │
│  Cost Today: $0.15                 │
│  Monthly Estimate: $4.50           │
└────────────────────────────────────┘
```

#### 2. **Upload Page**
```
┌────────────────────────────────────┐
│  🎤 New Transcription              │
├────────────────────────────────────┤
│  Google Drive Link:                │
│  [_________________________] 🔗    │
│                                    │
│  □ Recursive search                │
│  Max file size: [100] MB           │
│                                    │
│  [Start Transcription]             │
└────────────────────────────────────┘
```

#### 3. **Jobs Page**
```
┌────────────────────────────────────┐
│  📝 Transcription Jobs             │
├────────────────────────────────────┤
│  Job abc-123         ✅ Complete   │
│  Files: 5/5          View Results  │
│                                    │
│  Job def-456         🔄 Processing │
│  Files: 2/8          Monitor       │
└────────────────────────────────────┘
```

#### 4. **Results Page**
```
┌────────────────────────────────────┐
│  📄 Transcription Results          │
├────────────────────────────────────┤
│  File: sermon_part1.mp3            │
│  Language: English                 │
│  Speakers: 2                       │
│                                    │
│  [Download TXT] [Download JSON]    │
│  [Copy to Clipboard]               │
│                                    │
│  Full Transcript:                  │
│  Welcome to today's session...     │
└────────────────────────────────────┘
```

### Frontend Code Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx
│   │   ├── UploadForm.tsx
│   │   ├── JobList.tsx
│   │   ├── UsageWidget.tsx
│   │   └── TranscriptViewer.tsx
│   ├── pages/
│   │   ├── index.tsx          # Dashboard
│   │   ├── upload.tsx         # Upload page
│   │   ├── jobs.tsx           # Jobs list
│   │   └── results/[id].tsx   # Results page
│   ├── services/
│   │   └── api.ts             # API client
│   └── utils/
│       └── formatters.ts      # Text formatting
├── package.json
└── tailwind.config.js
```

### Sample Frontend API Client

```typescript
// src/services/api.ts
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = {
  // Start transcription
  async startTranscription(driveLink: string, options = {}) {
    const response = await axios.post(`${API_BASE}/transcribe`, {
      google_drive_link: driveLink,
      ...options
    });
    return response.data;
  },

  // Get job status
  async getJobStatus(jobId: string) {
    const response = await axios.get(`${API_BASE}/transcribe/${jobId}`);
    return response.data;
  },

  // Get usage stats
  async getUsageStats() {
    const response = await axios.get(`${API_BASE}/usage`);
    return response.data;
  },

  // Set API tier
  async setTier(tier: 'free' | 'paid') {
    const response = await axios.post(`${API_BASE}/usage/tier`, { tier });
    return response.data;
  }
};
```

---

## Usage Tracking & Monitoring

### Backend API Endpoints (Already Implemented!)

```bash
# Get usage statistics
GET /usage
Response:
{
  "tier": "free",
  "requests_today": 45,
  "daily_limit": 1500,
  "daily_usage_pct": 3.0,
  "total_cost_usd": 0.0,
  "warnings": []
}

# Get burn rate
GET /usage/burn-rate
Response:
{
  "daily_burn_rate_usd": 1.50,
  "monthly_estimate_usd": 45.00,
  "cost_today": 1.50
}

# Set tier (free/paid)
POST /usage/tier
Body: {"tier": "paid"}

# Reset usage stats
POST /usage/reset
```

### Usage Warning System

The system automatically tracks and warns users:

- **50% usage**: ℹ️ Info notification
- **75% usage**: ⚠️ Warning notification
- **90% usage**: 🚨 Critical alert

### Frontend Usage Widget

```tsx
function UsageWidget({ stats }) {
  const getStatusColor = (pct) => {
    if (pct >= 90) return 'red';
    if (pct >= 75) return 'yellow';
    return 'green';
  };

  return (
    <div className="usage-widget">
      <h3>API Usage</h3>
      <div className="progress-bar">
        <div
          className={`fill ${getStatusColor(stats.daily_usage_pct)}`}
          style={{ width: `${stats.daily_usage_pct}%` }}
        />
      </div>
      <p>{stats.requests_today} / {stats.daily_limit} requests</p>
      {stats.warnings.map(w => <Alert key={w}>{w}</Alert>)}
    </div>
  );
}
```

---

## Production Deployment

### 1. Prepare Environment

Create `.env` file:
```env
# Required
GEMINI_KEY=your_gemini_api_key

# Optional
NODE_ENV=production
PORT=8000
LOG_LEVEL=INFO
MAX_AUDIO_SIZE_MB=200
CLEANUP_TEMP_FILES=true
```

### 2. Build Docker Image

```bash
docker build -t audio-transcription-service:latest .
```

### 3. Run with Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_KEY=${GEMINI_KEY}
      - NODE_ENV=production
    volumes:
      - ./transcriptions:/app/transcriptions
      - ./usage_data:/app/usage_data
    restart: always

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api
    restart: always
```

Run:
```bash
docker-compose up -d
```

### 4. Setup Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. Enable HTTPS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Monitoring & Maintenance

### 1. Check Logs

```bash
# Docker logs
docker-compose logs -f

# Application logs
tail -f app.log
```

### 2. Monitor Usage

```bash
# Check usage stats
curl http://localhost:8000/usage

# Check health
curl http://localhost:8000/
```

### 3. Backup Transcriptions

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y-%m-%d)
tar -czf backup-$DATE.tar.gz transcriptions/ usage_data/
```

---

## Cost Estimates

### Free Tier (Gemini API)
- Requests: 1,500/day
- Cost: $0/month
- Best for: Testing, personal use

### Paid Tier
- Small usage (100 files/day): ~$5-10/month
- Medium usage (500 files/day): ~$25-50/month
- Heavy usage (2000 files/day): ~$100-200/month

### Hosting Costs
- Railway/Render: $5-20/month
- AWS: $15-50/month
- Google Cloud Run: $5-30/month (pay-per-use)

**Total Estimated Costs:**
- Personal/Testing: $5-10/month (free tier)
- Small Business: $20-50/month
- Medium Business: $75-150/month

---

## Next Steps

1. ✅ Run cleanup script: `./cleanup.sh`
2. ✅ Choose deployment platform (Railway recommended for simplicity)
3. ✅ Build frontend with Next.js/React
4. ✅ Deploy backend + frontend
5. ✅ Test usage tracking
6. ✅ Set up monitoring and alerts

---

## Support & Resources

- **Backend API Docs**: http://your-domain.com/docs
- **Frontend Template**: See `frontend-template/` folder (to be created)
- **Deployment Help**: Contact support or check logs

Good luck with your deployment! 🚀
